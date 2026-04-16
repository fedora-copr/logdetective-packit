# logdetective-packit

[![Run pytest](https://github.com/fedora-copr/logdetective-packit/actions/workflows/pytest.yml/badge.svg)](https://github.com/fedora-copr/logdetective-packit/actions/workflows/pytest.yml) [![Container Image Build and Publish](https://github.com/fedora-copr/logdetective-packit/actions/workflows/image_publish.yml/badge.svg)](https://github.com/fedora-copr/logdetective-packit/actions/workflows/image_publish.yml)

Server providing interface between [Packit](https://packit.dev/) and [Log Detective](https://github.com/fedora-copr/logdetective) using [Fedora
messaging infrastructure](https://docs.fedoraproject.org/en-US/infra/developer_guide/messaging/).

Requests sent to `/analyze` enpoint are routed to Log Detective server
with URL set by `LD_URL` environment variable. Eventual response is
posted on the public fedora messaging under `logdetective.analysis` topic,
with a unique build id to identify it for retrieval by Packit.

Should the analysis fail, for whatever reason, an error is posted to the same
`logdetective.analysis` topic.

The endpoint expects a JSON payload matching the `BuildInfo` model:

```json
{
  "artifacts": {
    "builder-live.log": "http://example.com/builder-live.log",
    "backend.log": "http://example.com/logs/123/backend.log"
  },
  "target_build": "12345",
  "build_system": "copr",
  "commit_sha": "9deb98c730bb4123f518ca13a0dbec5d7c0669ca",
  "project_url": "www.logdetective.com",
  "pr_id": 1,
  "build_metadata": {
    "commentary": "I've made a terrible mistake",
    "infra_status": "BROKEN"
  }
}
```

artifacts (dict): A dictionary mapping log filenames to their full URL or raw contents.

target_build (str): A unique identifier for the build, which will be included in the message.

build_system (str): Name of the build system used, in practice either `copr` or `koji`

commit_sha (str, optional): Hash of the commit from which the build was created

project_url (str, optional): URL of the project the build is for

pr_id (int, optional): Identifier of the pull request, or equivalent

build_metadata: (dict, optional): Dictionary of additional information about concluded build:

  specfile (str, optional): Contents of package spec file

  last_patch (str, optional): The last patch applied as a string

  commentary (str, optional): Additional relevant information, such as PR description

  infra_status (str, optional): Infrastructure status

Of these values, only `artifacts` and `build_metadata` are used by Log Detective itself.
The rest is used as part of a message sent to Fedora Messaging infrastructure,
to identify results.

When deployed the server must have `LD_PACKIT_TOKEN` environment variable set.
All requests on `/analyze` endpoint have to be authorized, comparing value of `LD_PACKIT_TOKEN`
to the value in their `Authorization` header.

For example `Authorization: Bearer secret-123`.

Additionally, for Sentry error and performance monitoring, `LD_PACKIT_INTERFACE_SENTRY_DSN` environment variable has to be set.

## Run the container

Images are published to quay.io. If it isn't available, or if you want
to test your own changes. First build your own image

```bash
podman build -t logdetective-packit .
```

and then run the container:

```bash
podman run -d --name logdetective-packit \
  -p 8090:8090 \
  -e LD_URL="https://logdetective.example.com/api" \
  logdetective-packit:latest
```

The `server/gunicorn.config.py` sets port `8090` as a default, unless the `PACKIT_INTERFACE_PORT` is set.
For production deployment, use the `PACKIT_INTERFACE_PORT` variable, to set port for the server.

If the selected Log Detective server requires authentication, set the token with `-e LD_TOKEN="your-token"` option.
For security purposes, this token should under no circumstances be the same as `LD_PACKIT_TOKEN`.

Certificates necessary for communication over [public broker](https://fedora-messaging.readthedocs.io/en/stable/user-guide/quick-start.html#fedora-s-public-broker)
are part of the image, being installed as part of `fedora-messaging` package.

## Development

Dependencies and local environment are best managed trough `uv`.
Installing the project and all dependencies locally with `uv sync --locked --all-extras --dev`.

This server should be kept as small and fast as possible. Processing of logs should all be done
on the side of Log Detective server itself.

### logdetective-packit-message package

The `schema/` directory contains a separate installable Python package (`logdetective-packit-message`) that provides:
- `LogDetectiveMessage` fedora-messaging schema class, and
- `LogDetectiveResult` enum.

Both this service and consumers (`packit-service`) should depend on this package
rather than duplicating these definitions.
To install it locally for development:

```bash
pip install -e ./schema
```

When using uv, this is handled automatically via `[tool.uv.sources]` in pyproject.toml.

### Testing

Tests should be executed with `uv`:

```bash
uv run pytest
```
