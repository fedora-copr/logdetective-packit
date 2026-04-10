import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from json import JSONDecodeError
import logging
import os
from importlib.metadata import version
from typing import Annotated
import uuid

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import sentry_sdk

from httpx import AsyncClient, HTTPStatusError
from fedora_messaging.api import publish
from fedora_messaging.config import conf
from fedora_messaging.exceptions import (
    ValidationError,
    PublishForbidden,
    PublishTimeout,
    PublishReturned,
)
from logdetective_packit_message import LogDetectiveResult, LogDetectiveMessage

from logdetective_packit.models import BuildInfo, Response

LD_URL = os.environ.get("LD_URL")
LD_TOKEN = os.environ.get("LD_TOKEN", "")
LD_TIMEOUT = int(os.environ.get("LD_TIMEOUT", 107))
PUBLISH_TIMEOUT = int(os.environ.get("PUBLISH_TIMEOUT", 30))
LD_PACKIT_TOKEN = os.environ.get("LD_PACKIT_TOKEN", "")

LOG = logging.getLogger("LogDetectivePackit")

http_bearer = HTTPBearer()

# Set the LD_PACKIT_INTERFACE_SENTRY_DSN env variable beforehand
sentry_sdk.init(
    dsn=os.environ.get("LD_PACKIT_INTERFACE_SENTRY_DSN"), traces_sample_rate=1.0
)

# Setup logging for fedora-messaging
conf.setup_logging()

http_client = AsyncClient(timeout=LD_TIMEOUT)

_log_detective_call_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handler running tasks when the server is being shut down."""
    yield
    if _log_detective_call_tasks:
        await asyncio.gather(*_log_detective_call_tasks, return_exceptions=True)


app = FastAPI(
    title="LogDetectivePackit",
    version=version("logdetective-packit"),
    lifespan=lifespan,
)


async def publish_message(message: LogDetectiveMessage):
    try:
        await asyncio.to_thread(publish, message=message, timeout=PUBLISH_TIMEOUT)
    except (PublishReturned, PublishForbidden, PublishTimeout, ValidationError) as ex:
        LOG.error("Publishing result")
        raise ex


def build_error_message(
    log_detective_analysis_id: str,
    log_detective_analysis_start: datetime,
    build_info: BuildInfo,
    error_msg: str = "",
) -> LogDetectiveMessage:
    """Build and return standard error message"""
    return LogDetectiveMessage(
        body={
            "status": LogDetectiveResult.error,
            "target_build": build_info.target_build,
            "build_system": build_info.build_system,
            "log_detective_analysis_id": log_detective_analysis_id,
            "log_detective_analysis_start": str(log_detective_analysis_start),
            "project_url": build_info.project_url,
            "pr_id": build_info.pr_id,
            "commit_sha": build_info.commit_sha,
            "error_msg": error_msg,
        },
    )


async def call_log_detective(
    build_info: BuildInfo,
    log_detective_analysis_id: str,
    log_detective_analysis_start: datetime,
) -> None:
    """Analyze build artifacts using Log Detective API. Only the first log
    is analyzed."""
    build_artifacts = list(build_info.artifacts.items())
    log_url = build_artifacts[0][1]
    headers = {}

    # If Log Detective server requires authorization
    if LD_TOKEN:
        headers["Authorization"] = f"Bearer {LD_TOKEN}"
    try:
        response = await http_client.post(
            url=LD_URL,
            headers=headers,
            json={"url": log_url},
        )
        response.raise_for_status()
    except HTTPStatusError as ex:
        msg = f"Request to Log Detective API at {LD_URL} failed with HTTP status error: {ex}"

        LOG.error(msg=msg)
        message = build_error_message(
            log_detective_analysis_id=log_detective_analysis_id,
            log_detective_analysis_start=log_detective_analysis_start,
            build_info=build_info,
            error_msg=msg,
        )
        await publish_message(message)
        raise ex
    except Exception as ex:
        msg = f"Request to Log Detective API at {LD_URL} failed with {ex}"
        LOG.error(msg=msg)
        message = build_error_message(
            log_detective_analysis_id=log_detective_analysis_id,
            log_detective_analysis_start=log_detective_analysis_start,
            build_info=build_info,
            error_msg=msg,
        )
        await publish_message(message)
        raise ex

    try:
        response = response.json()
    except JSONDecodeError as ex:
        msg = f"Decoding response from Log Detective API failed with {ex}"
        LOG.error(msg=msg)
        message = build_error_message(
            log_detective_analysis_id=log_detective_analysis_id,
            log_detective_analysis_start=log_detective_analysis_start,
            build_info=build_info,
            error_msg=msg,
        )
        await publish_message(message)
        raise ex

    response = {
        "status": LogDetectiveResult.complete,
        "log_detective_response": response,
        "target_build": build_info.target_build,
        "build_system": build_info.build_system,
        "log_detective_analysis_id": log_detective_analysis_id,
        "log_detective_analysis_start": str(log_detective_analysis_start),
        "project_url": build_info.project_url,
        "pr_id": build_info.pr_id,
        "commit_sha": build_info.commit_sha,
    }
    message = LogDetectiveMessage(body=response)
    await publish_message(message)


def analysis_task_callback(task: asyncio.Task):
    """Check that task didn't raise exception and was completed successfully."""
    try:
        if exc := task.exception():
            sentry_sdk.capture_exception(exc)
    # Check for errors that can be raised from exception() call
    except asyncio.CancelledError as cancelled_error:
        sentry_sdk.capture_exception(cancelled_error)


@app.post("/analyze", response_model=Response)
async def analyze_build(
    build_info: BuildInfo,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
):
    """Submit given build to Log Detective server for analysis.
    Only the first log URL is used for now. Request is made in a separate task."""

    if credentials.credentials != LD_PACKIT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    log_detective_analysis_id = str(uuid.uuid4())
    log_detective_analysis_start = datetime.now(timezone.utc)
    task = asyncio.create_task(
        call_log_detective(
            build_info,
            log_detective_analysis_id,
            log_detective_analysis_start=log_detective_analysis_start,
        )
    )
    _log_detective_call_tasks.add(task)

    # Verify that task was completed and remove it from set of running tasks
    task.add_done_callback(analysis_task_callback)
    task.add_done_callback(_log_detective_call_tasks.discard)

    return Response(
        log_detective_analysis_id=log_detective_analysis_id,
        creation_time=log_detective_analysis_start,
    )
