# logdetective-packit-message

Message schema package for the logdetective-packit service.

## Provides:
- `LogDetectiveMessage` — a fedora-messaging schema class for Log Detective analysis results, published on the `logdetective.analysis` topic
- `LogDetectiveResult` — an enum of possible analysis outcomes (complete, running, unknown, error)

## Usage

```py
from logdetective_packit_message import LogDetectiveMessage, LogDetectiveResult
```

## Installation

```bash
pip install "logdetective-packit-message @ git+https://github.com/fedora-copr/logdetective-packit.git#subdirectory=schema"
```

For local development from this repo:
```bash
pip install -e ./schema
```
