import hashlib
import hmac

import pytest

import notifications


class FakeResponse:
    def __init__(self, text="ok", status_code=200, ok=True):
        self.text = text
        self.status_code = status_code
        self.ok = ok


def test_send_slack_accepts_ok_response(mocker):
    post = mocker.patch("notifications.requests.post", return_value=FakeResponse(text="ok"))
    notifications.send_slack("https://hooks.slack.example/x", "hello")
    post.assert_called_once()
    assert post.call_args.kwargs["json"] == {"text": "hello"}


def test_send_slack_raises_on_non_ok_response(mocker):
    mocker.patch("notifications.requests.post", return_value=FakeResponse(text="invalid_payload", status_code=400))
    with pytest.raises(notifications.NotificationError):
        notifications.send_slack("https://hooks.slack.example/x", "hello")


def test_send_webhook_signs_payload_when_secret_given(mocker):
    post = mocker.patch("notifications.requests.post", return_value=FakeResponse(ok=True))
    payload = {"a": 1}
    notifications.send_webhook("https://example.com/hook", payload, secret="s3cret")

    body = post.call_args.kwargs["data"]
    sent_headers = post.call_args.kwargs["headers"]
    expected_sig = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert sent_headers["X-CyberGuard-Signature"] == expected_sig


def test_send_webhook_omits_signature_header_without_secret(mocker):
    post = mocker.patch("notifications.requests.post", return_value=FakeResponse(ok=True))
    notifications.send_webhook("https://example.com/hook", {"a": 1})
    assert "X-CyberGuard-Signature" not in post.call_args.kwargs["headers"]


def test_send_webhook_raises_on_failed_delivery(mocker):
    mocker.patch("notifications.requests.post", return_value=FakeResponse(ok=False, status_code=500))
    with pytest.raises(notifications.NotificationError):
        notifications.send_webhook("https://example.com/hook", {"a": 1})


def test_send_email_without_credentials_raises_clear_error(mocker):
    mocker.patch.object(notifications, "SMTP_USERNAME", None)
    mocker.patch.object(notifications, "SMTP_PASSWORD", None)
    with pytest.raises(notifications.NotificationError, match="SMTP_USERNAME"):
        notifications.send_email(["a@example.com"], "subject", "body")
