import pytest

from datetime import datetime
from fedora_messaging.api import Message
from fedora_messaging.exceptions import (
    ValidationError,
    PublishForbidden,
    PublishTimeout,
    PublishReturned,
)
from httpx import HTTPStatusError, AsyncClient, ASGITransport
from logdetective_packit_message import LogDetectiveResult, LogDetectiveMessage

from logdetective_packit.models import BuildInfo
from logdetective_packit.main import (
    build_error_message,
    call_log_detective,
    publish_message,
    PUBLISH_TIMEOUT,
)
from logdetective_packit.utils import is_url


from tests.utils import (
    MINIMAL_BUILD_INFO,
    DUMMY_MESSAGE_BODY,
    mock_env_vars,
    mock_external_calls,
    mock_server_logger,
    mock_create_task_call,
)


def test_build_error_message_content(mock_env_vars):
    """Test that build_error_message constructs the LogDetectiveMessage body correctly."""
    analysis_id = "test-uuid-123"
    start_time = datetime.fromisoformat("2024-03-20T12:00:00Z")
    error_text = "Analysis failed due to timeout"
    build_info = BuildInfo(**MINIMAL_BUILD_INFO)

    message = build_error_message(
        log_detective_analysis_id=analysis_id,
        log_detective_analysis_start=start_time,
        build_info=build_info,
        error_msg=error_text,
    )

    assert isinstance(message, LogDetectiveMessage)
    assert message.topic == LogDetectiveMessage.topic

    body = message.body
    assert body["status"] == LogDetectiveResult.error
    assert body["log_detective_analysis_id"] == analysis_id
    assert datetime.fromisoformat(body["log_detective_analysis_start"]) == start_time
    assert body["error_msg"] == error_text

    assert body["target_build"] == build_info.target_build
    assert body["build_system"] == build_info.build_system
    assert body["project_url"] == build_info.project_url
    assert body["pr_id"] == build_info.pr_id
    assert body["commit_sha"] == build_info.commit_sha


def test_build_error_message_default_error(mock_env_vars):
    """Test build_error_message with the default empty error message."""
    build_info = BuildInfo(**MINIMAL_BUILD_INFO)

    message = build_error_message(
        log_detective_analysis_id="id",
        log_detective_analysis_start="start",
        build_info=build_info,
    )

    assert message.body["error_msg"] == ""


@pytest.mark.asyncio
async def test_publish_message(mock_env_vars, mocker, mock_external_calls):
    from logdetective_packit.main import publish_message, PUBLISH_TIMEOUT

    message = Message(body=DUMMY_MESSAGE_BODY)

    await publish_message(message)
    mock_external_calls["mock_publish"].assert_called_once_with(
        message=message, timeout=PUBLISH_TIMEOUT
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception",
    [
        ValidationError,
        PublishForbidden,
        PublishTimeout,
        PublishReturned,
    ],
)
async def test_publish_message_exceptions(
    mock_env_vars, mock_external_calls, mock_server_logger, exception
):
    """Test behavior of `publish_mesage` when encountering exceptions"""

    message = Message(body=DUMMY_MESSAGE_BODY)
    mock_publish = mock_external_calls["mock_publish"]

    mock_publish.side_effect = exception

    with pytest.raises(expected_exception=exception):
        await publish_message(message)
        mock_server_logger["mock_logger"].assert_called_once()
        mock_external_calls["mock_publish"].assert_called_once_with(
            message=message, timeout=PUBLISH_TIMEOUT
        )


@pytest.mark.asyncio
async def test_call_log_detective(
    mock_env_vars, mock_external_calls, mock_server_logger
):
    log_detective_analysis_id = "8052517e-cf69-11f0-9b27-9a478821d0e2"
    log_detective_build_analysis_start = datetime.fromisoformat(
        "2025-12-10 10:57:57.341695+00:00"
    )
    build_info = BuildInfo(**MINIMAL_BUILD_INFO)
    await call_log_detective(
        build_info=build_info,
        log_detective_analysis_id=log_detective_analysis_id,
        log_detective_analysis_start=log_detective_build_analysis_start,
    )

    mock_external_calls["mock_publish"].assert_called_once()


@pytest.mark.asyncio
async def test_call_log_detective_request_exception(
    mock_env_vars, mock_external_calls, mock_server_logger, mocker
):
    """Test calls to Log Detective if the exception is raised by request"""

    build_info = BuildInfo(**MINIMAL_BUILD_INFO)

    mock_external_calls["mock_async_client"].post.side_effect = HTTPStatusError(
        "Exception", request=mocker.Mock(), response=mocker.Mock()
    )

    with pytest.raises(HTTPStatusError):
        log_detective_build_analysis_id = "8052517e-cf69-11f0-9b27-9a478821d0e2"
        log_detective_build_analysis_start = datetime.fromisoformat(
            "2025-12-10 10:57:57.341695+00:00"
        )
        await call_log_detective(
            build_info=build_info,
            log_detective_analysis_id=log_detective_build_analysis_id,
            log_detective_analysis_start=log_detective_build_analysis_start,
        )
        mock_server_logger["mock_logger"].assert_called_once()
        mock_external_calls["mock_async_client"].post.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_build_skeleton(
    monkeypatch, mocker, mock_env_vars, mock_external_calls, mock_create_task_call
):
    """Test for the entire /analyze endpoint."""

    # Mock is_url to test calls
    mock_is_url = mocker.patch("logdetective_packit.main.is_url", side_effect=is_url)

    # Mock the return value of requests.post().json()
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"status": "analysis_started", "id": "fake-id"}
    mock_response.raise_for_status = mocker.Mock()
    mock_external_calls["mock_async_client"].post.return_value = mock_response

    monkeypatch.setattr(
        "logdetective_packit.main.LD_URL", "http://mock-ld-server.com/api"
    )
    monkeypatch.setattr("logdetective_packit.main.LD_TOKEN", "test-token-123")
    monkeypatch.setattr("logdetective_packit.main.LD_PACKIT_TOKEN", "secret-123")

    # Import the app *after* environment and mocks are in place
    from logdetective_packit.main import app

    # Based on BuildInfo model
    payload = MINIMAL_BUILD_INFO

    # Make the request to the endpoint
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/analyze", json=payload, headers={"Authorization": "Bearer secret-123"}
        )

    # The endpoint returns None on success, so a 200 OK is expected
    assert response.status_code == 200

    assert mock_create_task_call["task_catcher"].created_task is not None
    await mock_create_task_call["task_catcher"].created_task

    # Check that requests.post was called correctly
    expected_headers = {"Authorization": "Bearer test-token-123"}
    # The code only takes the first log URL
    expected_data = {
        "files": [
            {
                "name": "builder-live.log",
                "url": "http://example.com/builder-live.log",
            }
        ]
    }

    mock_is_url.assert_called_once_with("http://example.com/builder-live.log")
    mock_external_calls["mock_async_client"].post.assert_called_once_with(
        url="http://mock-ld-server.com/api",
        json=expected_data,
        headers=expected_headers,
    )

    # Check that fedora-messaging.api.publish was called
    mock_external_calls["mock_publish"].assert_called_once()


@pytest.mark.asyncio
async def test_analyze_build_skeleton_no_token(
    monkeypatch, mocker, mock_env_vars, mock_external_calls, mock_create_task_call
):
    """Test for the entire /analyze endpoint. Authentication token is not provided."""

    # Import the app *after* environment and mocks are in place
    from logdetective_packit.main import app

    # Based on BuildInfo model
    payload = MINIMAL_BUILD_INFO

    # Make the request to the endpoint
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/analyze", json=payload)

    # The endpoint returns None on success, so a 403 Forbidden is expected
    assert response.status_code == 403

    assert mock_create_task_call["task_catcher"].created_task is None

    # Check that requests.post was not called
    mock_external_calls["mock_async_client"].post.assert_not_called()

    # Check that fedora-messaging.api.publish was not called
    mock_external_calls["mock_publish"].assert_not_called()
