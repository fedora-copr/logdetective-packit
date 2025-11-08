import asyncio

import pytest

MINIMAL_BUILD_INFO = {"logs": {"dummy_log": "dummy_log_url"}, "build_id": "12345"}

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


DUMMY_MESSAGE_BODY = {"dummy_field": "dummy_value"}

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
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {"status": "success"}
    mock_response.raise_for_status = mocker.MagicMock()

    mock_async_client = mocker.AsyncMock()
    mock_async_client.post.return_value = mock_response

    # Return self instead of another mock, this simplifies assertions
    # placed on post
    mock_async_client.__aenter__.return_value = mock_async_client

    mocker.patch("logdetective_packit.main.AsyncClient", return_value=mock_async_client)
    mock_publish = mocker.patch("logdetective_packit.main.publish")

    return {"mock_publish": mock_publish, "mock_async_client": mock_async_client}


@pytest.fixture
def mock_publish_function(mocker):
    """Mock publish function"""
    mock_publish = mocker.patch("logdetective_packit.main.publish")

    return {"mock_publish": mock_publish}


@pytest.fixture()
def mock_server_logger(mocker):
    """Mock calls to server logger, this should not mock FastAPI logger,
    nor the fedora-messaging logger"""

    mock_logger = mocker.patch("logdetective_packit.main.LOG")

    return {"mock_logger": mock_logger}


class TaskCatcher:
    created_task = None

    def __init__(self, original_create_task) -> None:
        self.original_create_task = original_create_task

    def capture_task(self, coro):
        """Capture coroutine and task created by coroutine"""
        self.captured_coro = coro
        self.created_task = self.original_create_task(coro)
        return self.created_task


@pytest.fixture
def mock_create_task_call(mocker):
    original_create_task = asyncio.create_task
    task_catcher = TaskCatcher(original_create_task)
    mock_create_task = mocker.patch(
        "logdetective_packit.main.asyncio.create_task",
        side_effect=task_catcher.capture_task,
    )

    return {"mock_create_task": mock_create_task, "task_catcher": task_catcher}
