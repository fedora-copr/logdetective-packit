# logdetective-packit 

[![Run pytest](https://github.com/fedora-copr/logdetective-packit/actions/workflows/pytest.yml/badge.svg)](https://github.com/fedora-copr/logdetective-packit/actions/workflows/pytest.yml) [![Container Image Build and Publish](https://github.com/fedora-copr/logdetective-packit/actions/workflows/image_publish.yml/badge.svg)](https://github.com/fedora-copr/logdetective-packit/actions/workflows/image_publish.yml)

Server providing interface between packit and Log Detective using Fedora
messaging infrastructure.
 
Requests sent to `/analyze` enpoint are routed to Log Detective server
with URL set by `LD_URL` environment variable. Eventual response is
posted on the public fedora messaging under `logdetective.analysis` topic,
with a unique build id to identify it for retrieval by Packit.

Should the analysis fail, for whatever reason, an error is posted to the same
`logdetective.analysis` topic.

The endpoint expects a JSON payload matching the `BuildInfo` model:

```
{
  "logs": {
    "builder-live.log": "http://example.com/logs/123/builder-live.log",
    "backend.log": "http://example.com/logs/123/backend.log"
  },
  "build_id": "12345"
}
```

logs (dict): A dictionary mapping log filenames to their full URL.

build_id (str): A unique identifier for the build, which will be included in the message.

## Run the container

```
podman run -d --name logdetective-packit \
  -p 8090:8090 \
  -e LD_URL="https.logdetective.example.com/api" \
  logdetective-packit:latest
```

If the selected Log Detective server requires authentication, set the token with `-e LD_TOKEN="your-token"` option.
Certificates necessary for communication over [public broker](https://fedora-messaging.readthedocs.io/en/stable/user-guide/quick-start.html#fedora-s-public-broker)
are part of the image, being installed as part of `fedora-messaging` package.

## Development

Dependencies and local environment are best managed trough `uv`.
Installing the project and all depencies locally with `uv sync --locked --all-extras --dev`.

This server should be kept as small and fast as possible. Processing of logs should all be done
on the side of Log Detective server itself.

### Testing

Tests should be executed with `uv`:

```
uv run pytest
```
