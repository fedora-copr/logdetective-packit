import pytest

from fedora_messaging.api import Message
from fedora_messaging.exceptions import (
    ValidationError,
    PublishForbidden,
    PublishTimeout,
    PublishReturned,
)
from httpx import HTTPStatusError, AsyncClient, ASGITransport

from logdetective_packit.models import BuildInfo

from tests.utils import (
    MINIMAL_BUILD_INFO,
    DUMMY_MESSAGE_BODY,
    mock_env_vars,
    mock_external_calls,
    mock_server_logger,
    mock_create_task_call,
)


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
    from logdetective_packit.main import publish_message, PUBLISH_TIMEOUT

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
    from logdetective_packit.main import call_log_detective

    build_info = BuildInfo(**MINIMAL_BUILD_INFO)
    await call_log_detective(build_info=build_info)

    mock_external_calls["mock_publish"].assert_called_once()


@pytest.mark.asyncio
async def test_call_log_detective_request_exception(
    mock_env_vars, mock_external_calls, mock_server_logger, mocker
):
    """Test calls to Log Detective if the exception is raised by request"""

    from logdetective_packit.main import call_log_detective

    build_info = BuildInfo(**MINIMAL_BUILD_INFO)

    mock_external_calls["mock_async_client"].post.side_effect = HTTPStatusError(
        "Exception", request=mocker.Mock(), response=mocker.Mock()
    )

    with pytest.raises(HTTPStatusError):
        await call_log_detective(build_info=build_info)
        mock_server_logger["mock_logger"].assert_called_once()
        mock_external_calls["mock_async_client"].post.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_build_skeleton(
    monkeypatch, mocker, mock_env_vars, mock_external_calls, mock_create_task_call
):
    """Test for the entire /analyze endpoint."""

    # Mock the return value of requests.post().json()
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"status": "analysis_started", "id": "fake-id"}

    mock_response.raise_for_status = mocker.Mock()
    mock_external_calls["mock_async_client"].post.return_value = mock_response

    # Import the app *after* environment and mocks are in place
    from logdetective_packit.main import app

    # Based on BuildInfo model
    payload = {
        "logs": {"builder-live.log": "http://example.com/builder-live.log"},
        "build_id": "12345",
    }

    # Make the request to the endpoint
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/analyze", json=payload)

    # The endpoint returns None on success, so a 200 OK is expected
    assert response.status_code == 200

    assert mock_create_task_call["task_catcher"].created_task is not None
    await mock_create_task_call["task_catcher"].created_task

    # Check that requests.post was called correctly
    expected_headers = {"Authorization": "Bearer test-token-123"}
    # The code only takes the first log URL
    expected_data = {"url": "http://example.com/builder-live.log"}

    mock_external_calls["mock_async_client"].post.assert_called_once_with(
        url="http://mock-ld-server.com/api",
        json=expected_data,
        headers=expected_headers,
    )

    # Check that fedora-messaging.api.publish was called
    mock_external_calls["mock_publish"].assert_called_once()
