import pytest
from fastapi.testclient import TestClient

def test_analyze_build_skeleton(monkeypatch, mocker):
    """Test for the /analyze endpoint.
    """

    monkeypatch.setenv("LD_URL", "http://mock-ld-server.com/api")
    monkeypatch.setenv("LD_TOKEN", "test-token-123")
    monkeypatch.setenv("PUBLISH_TIMEOUT", "10")
    monkeypatch.setenv("MESSAGE_EXCHANGE", "test-exchange")

    # Mock external calls to prevent real network/messaging
    mock_requests_post = mocker.patch("requests.post")
    mock_publish = mocker.patch("fedora_messaging.api.publish")
    
    # Mock the return value of requests.post().json()
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"status": "analysis_started", "id": "fake-id"}
    mock_requests_post.return_value = mock_response

    # Import the app *after* environment and mocks are in place
    from logdetective_packit.main import app

    # TestClient requires 'httpx' to be installed
    client = TestClient(app)

    # Based on BuildInfo model
    payload = {
        "logs": {
            "builder-live.log": "http://example.com/builder-live.log"
        },
        "build_id": "12345"
    }

    # Make the request to the endpoint
    response = client.post("/analyze", json=payload)

    # The endpoint returns None on success, so a 200 OK is expected
    assert response.status_code == 200
    
    # Check that requests.post was called correctly
    expected_headers = {"Authorization": "Bearer test-token-123"}
    # The code only takes the first log URL
    expected_data = {
        "url": "http://example.com/builder-live.log"}
    mock_requests_post.assert_called_once_with(
        url="http://mock-ld-server.com/api",
        data=expected_data,
        headers=expected_headers
    )
    
    # Check that fedora-messaging.api.publish was called
    mock_publish.assert_called_once()
    
    # Further assertions on calls to publish function
    args, kwargs = mock_publish.call_args
    assert "message" in kwargs
    message_body = kwargs["message"].body
    assert message_body["target_build"] == "12345"
    assert message_body["log_detective_response"]["status"] == "analysis_started"