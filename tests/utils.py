import pytest

MINIMAL_BUILD_INFO = {
    "logs": {
        "dummy_log": "dummy_log_url"
        },
    "build_id": "12345"}

MULTILOG_BUILD_INFO = {
    "logs": {
        "builder-live.log": "http://example.com/builder-live.log",
        "backend.log": "http://example.com/backend.log",
    },
    "build_id": "12345",
}

INVALID_BUILD_INFO_EMPTY_LOGS = {
    "build_id": "12345",
    "logs": {},
}

INVALID_BUILD_INFO_NO_BUILD_ID = {
    "logs": {"builder-live.log": "http://example.com/builder-live.log"}
    # 'build_id' is missing
}


DUMMY_MESSAGE_BODY = {
    "dummy_field": "dummy_value"
}

# Mock utilities

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set environment variables for server tests"""
    monkeypatch.setenv("LD_URL", "http://mock-ld-server.com/api")
    monkeypatch.setenv("LD_TOKEN", "test-token-123")
    monkeypatch.setenv("PUBLISH_TIMEOUT", "10")
    monkeypatch.setenv("MESSAGE_EXCHANGE", "test-exchange")


@pytest.fixture
def mock_external_calls(mocker):
    """Mock external calls to prevent real network/messaging,

    fedora_messaging.api.publish function is mocked at main module
    """

    mock_requests_post = mocker.patch("requests.post")
    mock_publish = mocker.patch("logdetective_packit.main.publish")

    return {"mock_publish": mock_publish, "mock_requests_post": mock_requests_post}


@pytest.fixture
def mock_server_logger(mocker):
    """Mock calls to server logger, this should not mock FastAPI logger,
    nor the fedora-messaging logger"""

    mock_logger = mocker.patch("logdetective_packit.main.LOG")

    return {"mock_logger": mock_logger}