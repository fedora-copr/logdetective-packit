import pytest
from logdetective_packit.models import BuildInfo
from pydantic import ValidationError

from tests.utils import (
    MULTILOG_BUILD_INFO,
    INVALID_BUILD_INFO_EMPTY_LOGS,
    INVALID_BUILD_INFO_NO_TARGET_BUILD,
)
from tests.utils import mock_env_vars, mock_external_calls


def test_buildinfo_model_creation():
    """Test successful creation of the BuildInfo model.
    This is a basic skeleton test to ensure the model loads and validates.
    """

    # Try creating the model
    info = BuildInfo(**MULTILOG_BUILD_INFO)

    # Basic assertions to check if data was loaded correctly
    assert info.target_build == "12345"
    assert info.logs["builder-live.log"] == "http://example.com/builder-live.log"
    assert info.logs == MULTILOG_BUILD_INFO["logs"]


def test_buildinfo_model_validation_error():
    """Test that the model raises a ValidationError for missing required fields,
    or if there are no logs in the `logs` field.
    """

    with pytest.raises(ValidationError):
        BuildInfo(**INVALID_BUILD_INFO_NO_TARGET_BUILD)

    with pytest.raises(ValidationError):
        BuildInfo(**INVALID_BUILD_INFO_EMPTY_LOGS)
