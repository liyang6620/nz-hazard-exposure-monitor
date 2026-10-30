from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from nzhem.adapters.local.geonet import GeoNetFdsnEventSource, NullEventSource
from nzhem.adapters.local.openai import OpenAILlmClient
from nzhem.adapters.local.secrets import EnvironmentSecretStore
from nzhem.adapters.local.smtp import SmtpMailer


def test_geonet_uses_updatedafter_and_normalises_events(monkeypatch: pytest.MonkeyPatch) -> None:
    text_response = Mock()
    text_response.text = (
        "#EventID | Time | Latitude | Longitude | Depth/km | Author | Catalog | "
        "Contributor | ContributorID | MagType | Magnitude | MagAuthor | "
        "EventLocationName | EventType\n"
        "event-1|2026-10-23T00:00:00|-41.0|174.0|10|GNS|GNS|GNS|event-1|M|4.2|GNS|NZ|earthquake\n"
    )
    xml_response = Mock()
    xml_response.text = """<?xml version="1.0"?>
    <q:quakeml xmlns:q="http://quakeml.org/xmlns/quakeml/1.2"
      xmlns="http://quakeml.org/xmlns/bed/1.2">
      <eventParameters><event publicID="event-1">
        <preferredOriginID>origin-1</preferredOriginID>
        <preferredMagnitudeID>magnitude-1</preferredMagnitudeID>
        <origin publicID="origin-1"><creationInfo>
          <creationTime>2026-10-23T00:05:00Z</creationTime>
        </creationInfo></origin>
        <magnitude publicID="magnitude-1">
          <mag><value>4.26</value></mag><type>M</type><creationInfo>
          <creationTime>2026-10-23T00:06:00Z</creationTime>
        </creationInfo></magnitude>
      </event></eventParameters>
    </q:quakeml>"""
    get = Mock(side_effect=[text_response, text_response, xml_response])
    monkeypatch.setattr("nzhem.adapters.local.geonet.requests.get", get)
    source = GeoNetFdsnEventSource("https://example.invalid/fdsn")

    events = source.fetch_updated_after(datetime(2026, 10, 22, tzinfo=UTC))

    assert events[0]["event_id"] == "event-1"
    assert events[0]["magnitude"] == 4.26
    assert events[0]["magnitude_type"] == "M"
    assert events[0]["magnitude_revision_time"] == "2026-10-23T00:06:00Z"
    assert events[0]["revision"] == "2026-10-23T00:06:00Z"
    assert events[0]["depth_km"] == 10
    assert events[0]["latitude"] == -41
    assert events[0]["longitude"] == 174
    assert events[0]["event_name"] == "NZ"
    assert get.call_count == 3
    call = get.call_args_list[0]
    assert call.kwargs["params"]["updatedafter"] == "2026-10-22T00:00:00Z"
    assert call.kwargs["params"]["format"] == "text"
    assert call.kwargs["params"]["minmagnitude"] == "4.0"
    assert "nz-hazard-exposure-monitor" in call.kwargs["headers"]["User-Agent"]
    assert text_response.raise_for_status.call_count == 2
    assert xml_response.raise_for_status.call_count == 1


def test_null_event_source_is_deterministic() -> None:
    assert NullEventSource().fetch_updated_after(datetime.now(UTC)) == []


def test_environment_secret_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_SECRET", "value")
    assert EnvironmentSecretStore().get_secret("TEST_SECRET") == "value"
    with pytest.raises(KeyError, match="MISSING_SECRET"):
        EnvironmentSecretStore().get_secret("MISSING_SECRET")


def test_smtp_mailer_sends_plain_text(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Mock()
    context = Mock()
    context.__enter__ = Mock(return_value=client)
    context.__exit__ = Mock(return_value=False)
    smtp = Mock(return_value=context)
    monkeypatch.setattr("nzhem.adapters.local.smtp.smtplib.SMTP", smtp)

    SmtpMailer("mailpit", 1025, "sender@example.invalid").send(
        "owner@example.invalid", "Subject", "Body"
    )

    smtp.assert_called_once_with("mailpit", 1025, timeout=10)
    message = client.send_message.call_args.args[0]
    assert message["To"] == "owner@example.invalid"
    assert "Body" in message.get_content()


def test_openai_adapter_enforces_configured_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock()
    response.json.return_value = {
        "output": [{"content": [{"type": "output_text", "text": "briefing"}]}],
        "usage": {
            "input_tokens": 100,
            "input_tokens_details": {"cached_tokens": 25},
            "output_tokens": 50,
            "total_tokens": 150,
        },
    }
    post = Mock(return_value=response)
    monkeypatch.setattr("nzhem.adapters.local.openai.requests.post", post)
    secrets = Mock()
    secrets.get_secret.return_value = "secret-value"

    client = OpenAILlmClient(secrets, api_key_name="OPENAI_API_KEY", model="gpt-5-mini")
    result = client.generate("prompt", max_output_tokens=1200)

    assert result == "briefing"
    assert post.call_args.kwargs["json"]["reasoning"] == {"effort": "minimal"}
    assert post.call_args.kwargs["json"]["max_output_tokens"] == 1200
    assert client.usage[0].cached_input_tokens == 25
    assert client.usage[0].total_tokens == 150
    response.raise_for_status.assert_called_once()
