import asyncio
from json import JSONDecodeError
import logging
import os
from importlib.metadata import version
import uuid

from fastapi import FastAPI
from httpx import AsyncClient, HTTPStatusError
from fedora_messaging.api import publish, Message
from fedora_messaging.config import conf
from fedora_messaging.exceptions import (
    ValidationError,
    PublishForbidden,
    PublishTimeout,
    PublishReturned,
)

from logdetective_packit.models import BuildInfo, Response

TOPIC = "logdetective.analysis"
LD_URL = os.environ["LD_URL"]
LD_TOKEN = os.environ.get("LD_TOKEN", "")
LD_TIMEOUT = int(os.environ.get("LD_TIMEOUT", 107))
PUBLISH_TIMEOUT = int(os.environ.get("PUBLISH_TIMEOUT", 30))

LOG = logging.Logger("LogDetectivePackit", level=logging.WARNING)

app = FastAPI(title="LogDetectivePackit", version=version("logdetective-packit"))

# Setup logging for fedora-messaging
conf.setup_logging()


async def publish_message(message: Message):
    try:
        await asyncio.to_thread(publish, message=message, timeout=PUBLISH_TIMEOUT)
    except (PublishReturned, PublishForbidden, PublishTimeout, ValidationError) as ex:
        LOG.error("Publishing result")
        raise ex


async def call_log_detective(
    build_info: BuildInfo, log_detective_analysis_id: str
) -> None:
    """Analyze build logs using Log Detective API. Only the first log
    is analyzed."""
    build_logs = list(build_info.logs.items())
    log_url = build_logs[0][1]
    headers = {}

    # If Log Detective server requires authorization
    if LD_TOKEN:
        headers["Authorization"] = f"Bearer {LD_TOKEN}"
    try:
        async with AsyncClient(timeout=LD_TIMEOUT) as client:
            response = await client.post(
                url=LD_URL,
                headers=headers,
                json={"url": log_url},
            )
        response.raise_for_status()
    except HTTPStatusError as ex:
        LOG.error(
            "Request to Log Detective API at %s failed with HTTP status error: %s",
            LD_URL,
            ex,
        )
        message = Message(
            body={
                "result": f"Build analysis failed with HTTP status error `{ex}`",
                "target_build": build_info.target_build,
                "log_detective_analysis_id": log_detective_analysis_id,
            },
            topic=TOPIC,
        )
        await publish_message(message)
        raise ex
    except Exception as ex:
        LOG.error("Request to Log Detective API at %s failed with %s", LD_URL, ex)
        message = Message(
            body={
                "result": f"Build analysis failed with `{ex}`",
                "target_build": build_info.target_build,
                "log_detective_analysis_id": log_detective_analysis_id,
            },
            topic=TOPIC,
        )
        await publish_message(message)
        raise ex

    try:
        response = response.json()
    except JSONDecodeError as ex:
        LOG.error("Decoding response from Log Detective API failed with %s", ex)
        message = Message(
            body={
                "result": f"Decoding response from Log Detective failed with `{ex}`",
                "target_build": build_info.target_build,
                "log_detective_analysis_id": log_detective_analysis_id,
            },
            topic=TOPIC,
        )
        await publish_message(message)
        raise ex

    response = {
        "log_detective_response": response,
        "target_build": build_info.target_build,
        "log_detective_analysis_id": log_detective_analysis_id,
    }
    message = Message(body=response, topic=TOPIC)
    await publish_message(message)


@app.post("/analyze", response_model=Response)
async def analyze_build(build_info: BuildInfo):
    """Submit given build to Log Detective server for analysis.
    Only the first log URL is used for now. Request is made in a separate task."""

    log_detective_analysis_id = str(uuid.uuid4())

    asyncio.create_task(call_log_detective(build_info, log_detective_analysis_id))

    return Response(log_detective_analysis_id=log_detective_analysis_id)
