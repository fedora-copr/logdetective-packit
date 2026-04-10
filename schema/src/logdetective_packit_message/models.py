import enum

from fedora_messaging import message


class LogDetectiveMessage(message.Message):
    """Message schema for Log Detective response for Packit Service"""

    body_schema = {
        "id": "http://fedoraproject.org/message-schema/logdetective-analysis#",
        "$schema": "http://json-schema.org/draft-04/schema#",
        "description": "Result of a Log Detective build log analysis",
        "type": "object",
        "required": [
            "status",
            "target_build",
            "build_system",
            "log_detective_analysis_id",
            "log_detective_analysis_start",
        ],
        "properties": {
            "status": {"type": "string", "enum": ["complete", "running", "unknown", "error"]},
            "target_build": {"type": "string"},
            "build_system": {"type": "string"},
            "log_detective_analysis_id": {"type": "string"},
            "log_detective_analysis_start": {"type": "string"},
            "project_url": {"type": ["string", "null"]},
            "pr_id": {"type": ["integer", "null"]},
            "commit_sha": {"type": ["string", "null"]},
            "log_detective_response": {"type": "object"},
            "error_msg": {"type": "string"},
        },
    }

    topic = "logdetective.analysis"

    def __str__(self):
        return (
            f"Log Detective analysis {self.body['log_detective_analysis_id']}: "
            f"{self.body['status']} for {self.body['target_build']} "
            f"({self.body['build_system']})"
        )

    @property
    def summary(self):
        return (
            f"Log Detective {self.body['status']} for {self.body['target_build']}"
        )

    @property
    def app_name(self):
        return "Log Detective"


class LogDetectiveResult(str, enum.Enum):
    """Possible results of Log Detective analysis."""

    __test__ = False

    complete = "complete"
    running = "running"
    unknown = "unknown"
    error = "error"

    @classmethod
    def from_string(cls, value):
        try:
            return cls(value)
        except ValueError:
            return cls.unknown
