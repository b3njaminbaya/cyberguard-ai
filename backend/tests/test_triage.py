import pytest
import requests

import triage


class FakeResponse:
    def __init__(self, json_body, status_code=200):
        self._json = json_body
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def test_generate_triage_returns_model_content(mocker):
    mocker.patch(
        "triage.requests.post",
        return_value=FakeResponse({"message": {"role": "assistant", "content": "  Isolate the host.  "}}),
    )
    result = triage.generate_triage(
        label="DoS",
        severity="critical",
        score=0.9,
        source_ip="10.0.0.1",
        dest_ip="10.0.0.2",
        protocol="tcp",
        bytes_transferred=1000,
        raw_features={"dur": 1.2, "service": "http", "state": "FIN"},
    )
    assert result == "Isolate the host."


def test_generate_triage_only_includes_interesting_fields_in_prompt(mocker):
    post = mocker.patch(
        "triage.requests.post",
        return_value=FakeResponse({"message": {"content": "ok"}}),
    )
    triage.generate_triage(
        label="Exploits",
        severity="high",
        score=0.5,
        source_ip="10.0.0.1",
        dest_ip="10.0.0.2",
        protocol="tcp",
        bytes_transferred=1,
        raw_features={"dur": 1.2, "totally_irrelevant_field": 42},
    )
    user_message = post.call_args.kwargs["json"]["messages"][1]["content"]
    assert "dur" in user_message
    assert "totally_irrelevant_field" not in user_message


def test_generate_triage_raises_when_ollama_unreachable(mocker):
    mocker.patch("triage.requests.post", side_effect=requests.ConnectionError("refused"))
    with pytest.raises(triage.TriageError, match="Couldn't reach Ollama"):
        triage.generate_triage(
            label="DoS", severity="critical", score=0.9,
            source_ip="a", dest_ip="b", protocol="tcp",
            bytes_transferred=1, raw_features={},
        )


def test_generate_triage_raises_on_empty_response(mocker):
    mocker.patch("triage.requests.post", return_value=FakeResponse({"message": {"content": ""}}))
    with pytest.raises(triage.TriageError, match="no content"):
        triage.generate_triage(
            label="DoS", severity="critical", score=0.9,
            source_ip="a", dest_ip="b", protocol="tcp",
            bytes_transferred=1, raw_features={},
        )
