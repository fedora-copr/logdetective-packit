import pytest
from logdetective_packit.models import BuildInfo
from pydantic import ValidationError


def test_buildinfo_model_creation():
    """Test successful creation of the BuildInfo model.
    This is a basic skeleton test to ensure the model loads and validates.
    """
    data = {
        "logs": {
            "builder-live.log": "http://example.com/builder-live.log",
            "backend.log": "http://example.com/backend.log",
        },
        "build_id": "12345",
    }

    # Try creating the model
    info = BuildInfo(**data)

    # Basic assertions to check if data was loaded correctly
    assert info.build_id == "12345"
    assert info.logs["builder-live.log"] == "http://example.com/builder-live.log"
    assert info.logs == data["logs"]


def test_buildinfo_model_validation_error():
    """Test that the model raises a ValidationError for missing required fields.
    Or if there are no logs in the `logs` field.
    """
    invalid_data = {
        "logs": {"builder-live.log": "http://example.com/builder-live.log"}
        # 'build_id' is missing
    }

    with pytest.raises(ValidationError):
        BuildInfo(**invalid_data)
    
    invalid_data = {
        "build_id": "12345",
        "logs": {},
    }

    with pytest.raises(ValidationError):
        BuildInfo(**invalid_data)

