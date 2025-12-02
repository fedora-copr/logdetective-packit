from pydantic import BaseModel, Field


class BuildInfo(BaseModel):
    """ID of the build being analyzed and URL to and all logs."""

    logs: dict[str, str] = Field(
        description="Dictionary of logs and their URLs", min_length=1
    )
    target_build: str = Field(
        description="Unique identifier of the build so the result can be reported"
    )
    build_system: str = Field(description="System where the build was launched")


class Response(BaseModel):
    log_detective_analysis_id: str = Field(
        description="UUID of the analysis which will be used to retrieve the results from messages"
    )
