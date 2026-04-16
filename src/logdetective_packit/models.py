from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BuildMetadata(BaseModel):
    """Model of additional information provided about the build."""

    specfile: Optional[str] = Field(
        description="Contents of package spec file as a string.", default=None
    )
    last_patch: Optional[str] = Field(
        description="Contents of last patch applied as a string.", default=None
    )
    commentary: Optional[str] = Field(
        description="Comment attached to the triggered build, such as PR description.",
        default=None,
    )
    infra_status: Optional[str] = Field(
        description="State of build infrastructure as a string.", default=None
    )


class BuildInfo(BaseModel):
    """ID of the build being analyzed and URL to and all artifacts."""

    artifacts: dict[str, str] = Field(
        description="Dictionary of build artifacts, such as logs and their URLs",
        min_length=1,
    )
    target_build: str = Field(
        description="Unique identifier of the build so the result can be reported"
    )
    build_system: str = Field(description="System where the build was launched")
    project_url: Optional[str] = Field(
        description="URL of the project being analyzed", default=None
    )
    commit_sha: Optional[str] = Field(
        description="SHA of the commit used as basis of the build", default=None
    )
    pr_id: Optional[int] = Field(
        description="ID of the pull request, or equivalent of the given forge",
        default=None,
    )
    build_metadata: Optional[BuildMetadata] = Field(
        description="Optional build metadata.", default=None
    )


class Response(BaseModel):
    log_detective_analysis_id: str = Field(
        description="UUID of the analysis which will be used to retrieve the results from messages"
    )
    creation_time: datetime = Field(description="Time of Log Detective analysis start")
