from pydantic import BaseModel, Field


class BuildInfo(BaseModel):
    """ID of the build being analyzed and URL to and all logs."""

    logs: dict[str, str] = Field(description="Dictionary of logs and their URLs", min_length=1)
    build_id: str = Field(
        description="Unique identifier of the build so the result can be reported"
    )
