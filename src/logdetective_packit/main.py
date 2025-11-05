import os
from importlib.metadata import version

from fastapi import FastAPI
import requests
from fedora_messaging.api import publish, Message
from fedora_messaging.config import conf

from logdetective_packit.models import BuildInfo

LD_URL = os.environ["LD_URL"]
LD_TOKEN = os.environ.get("LD_TOKEN", "")
PUBLISH_TIMEOUT = int(os.environ.get("PUBLISH_TIMEOUT", 30))

app = FastAPI(
    title="LogDetectivePackit",
    version=version("logdetective-packit"))

conf.setup_logging()

@app.post("/analyze")
async def analyze_build(build_info: BuildInfo) -> None:
    """Submit given build to Log Detective server for analysis.
    Only the first log URL is used for now."""

    build_logs = list(build_info.logs.items())
    log_url = build_logs[0][1]
    headers = {}
    # If Log Detective server requires authorization
    if LD_TOKEN:
        headers["Authorization"] = f"Bearer {LD_TOKEN}"
    try:
        response = requests.post(
            url=LD_URL, data={"url": log_url}, headers=headers,
        )
        response = {
            "log_detective_response": response.json(),
            "target_build": build_info.build_id
        }
        message = Message(body=response, topic="logdetective.analysis")
    except Exception as ex:
        message = Message(
            body={"result": f"Build analysis failed with {ex}"},
            topic="logdetective.analysis",
        )

    publish(message=message, timeout=PUBLISH_TIMEOUT)
