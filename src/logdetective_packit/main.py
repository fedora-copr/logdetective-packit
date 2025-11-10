import asyncio
from json import JSONDecodeError
import logging
import os
from importlib.metadata import version

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

from logdetective_packit.models import BuildInfo

TOPIC = "org.fedoraproject.prod.logdetective.analysis"
LD_URL = os.environ["LD_URL"]
LD_TOKEN = os.environ.get("LD_TOKEN", "")
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


async def call_log_detective(build_info: BuildInfo) -> None:
    """Analyze build logs using Log Detective API. Only the first log
    is analyzed."""
    build_logs = list(build_info.logs.items())
    log_url = build_logs[0][1]
    headers = {}

    # If Log Detective server requires authorization
    if LD_TOKEN:
        headers["Authorization"] = f"Bearer {LD_TOKEN}"
    try:
        async with AsyncClient() as client:
            response = await client.post(
                url=LD_URL,
                data={"url": log_url},
                headers=headers,
            )
        response.raise_for_status()
    except HTTPStatusError as ex:
        LOG.error("Request to Log Detective API at %s failed with %s", LD_URL, ex)
        message = Message(
            body={
                "result": f"Build analysis failed with `{ex}`",
                "target_build": build_info.build_id,
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
                "target_build": build_info.build_id,
            },
            topic=TOPIC,
        )
        await publish_message(message)
        raise ex

    response = {
        "log_detective_response": response,
        "target_build": build_info.build_id,
    }
    message = Message(body=response, topic="logdetective.analysis")
    await publish_message(message)


@app.post("/analyze")
async def analyze_build(build_info: BuildInfo) -> str:
    """Submit given build to Log Detective server for analysis.
    Only the first log URL is used for now. Request is made in a separate task."""

    asyncio.create_task(call_log_detective(build_info))

    return "success"
