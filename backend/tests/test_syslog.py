import socket
import time

import pytest

from models import SystemLog
from syslog_server import SyslogProtocol, parse_syslog_line


# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------

def test_parses_pri_and_rfc3164_fields():
    parsed = parse_syslog_line(
        "<38>Jul 15 00:20:01 web-01 sshd[1234]: Failed password for invalid user admin from 203.0.113.45"
    )
    assert parsed["facility"] == "auth"
    assert parsed["severity"] == "info"
    assert parsed["source_host"] == "web-01"
    assert parsed["tag"] == "sshd"
    assert "Failed password" in parsed["message"]
    assert parsed["flagged"] is True
    assert "failed password" in parsed["flag_reason"]


def test_pri_facility_and_severity_decode_correctly():
    # <11> = facility 1 (user) * 8 + severity 3 (err)
    parsed = parse_syslog_line("<11>Jul 15 00:20:04 fw-01 kernel: segfault at 0 ip 00007f")
    assert parsed["facility"] == "user"
    assert parsed["severity"] == "err"
    assert parsed["flagged"] is True
    assert "err" in parsed["flag_reason"]


def test_missing_pri_falls_back_to_reasonable_defaults():
    parsed = parse_syslog_line("just a bare log line with no structure at all")
    assert parsed["facility"] == "user"
    assert parsed["severity"] == "info"
    assert parsed["source_host"] == "unknown"
    assert parsed["tag"] is None
    assert parsed["message"] == "just a bare log line with no structure at all"
    assert parsed["flagged"] is False


def test_host_tag_message_without_timestamp():
    parsed = parse_syslog_line("<14>db-01 postgres[5678]: connection authorized: user=app")
    assert parsed["source_host"] == "db-01"
    assert parsed["tag"] == "postgres"
    assert parsed["message"] == "connection authorized: user=app"


def test_info_severity_clean_message_not_flagged():
    parsed = parse_syslog_line("<14>Jul 15 00:20:02 db-01 postgres[5678]: connection authorized: user=app")
    assert parsed["severity"] == "info"
    assert parsed["flagged"] is False
    assert parsed["flag_reason"] is None


@pytest.mark.parametrize(
    "keyword",
    ["authentication failure", "invalid user", "permission denied", "brute force", "sql injection", "port scan"],
)
def test_suspicious_keywords_are_flagged(keyword):
    parsed = parse_syslog_line(f"<14>host-01 app: something happened: {keyword} detected")
    assert parsed["flagged"] is True
    assert "matched pattern" in parsed["flag_reason"]


# ---------------------------------------------------------------------------
# Protocol wiring
# ---------------------------------------------------------------------------

def test_syslog_protocol_invokes_callback_with_parsed_message():
    received = []
    protocol = SyslogProtocol(on_message=received.append)
    protocol.datagram_received(b"<14>host-01 app: hello world", ("127.0.0.1", 5000))
    assert len(received) == 1
    assert received[0]["message"] == "hello world"
    assert "received_at" in received[0]


def test_syslog_protocol_swallows_bad_utf8_without_raising():
    received = []
    protocol = SyslogProtocol(on_message=received.append)
    protocol.datagram_received(b"<14>host-01 app: \xff\xfe binary garbage", ("127.0.0.1", 5000))
    assert len(received) == 1  # decoded with errors="replace", still processed


def test_syslog_protocol_does_not_raise_when_callback_fails():
    def _boom(parsed):
        raise RuntimeError("db is down")

    protocol = SyslogProtocol(on_message=_boom)
    protocol.datagram_received(b"<14>host-01 app: hello", ("127.0.0.1", 5000))  # must not raise


# ---------------------------------------------------------------------------
# Real UDP end-to-end: send actual packets to a live listener bound on an
# ephemeral port and confirm they land in the database.
# ---------------------------------------------------------------------------

def test_real_udp_packet_is_parsed_and_persisted(db_session):
    import asyncio

    received = []

    async def _run():
        loop = asyncio.get_event_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: SyslogProtocol(on_message=received.append),
            local_addr=("127.0.0.1", 0),
        )
        port = transport.get_extra_info("sockname")[1]

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b"<38>Jul 15 00:00:00 test-host sshd[1]: Failed password for root", ("127.0.0.1", port))
        sock.close()

        for _ in range(50):
            if received:
                break
            await asyncio.sleep(0.05)

        transport.close()

    asyncio.run(_run())

    assert len(received) == 1
    parsed = received[0]
    assert parsed["source_host"] == "test-host"
    assert parsed["flagged"] is True

    row = SystemLog(**parsed)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    assert row.id is not None


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

def _seed_log(db_session, **overrides):
    defaults = dict(
        source_host="web-01",
        facility="auth",
        severity="err",
        tag="sshd",
        message="Failed password for invalid user admin",
        raw="<38>Jul 15 00:20:01 web-01 sshd[1234]: Failed password for invalid user admin",
        flagged=True,
        flag_reason="matched pattern: failed password",
    )
    defaults.update(overrides)
    row = SystemLog(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def test_list_logs_requires_auth(client, db_session):
    _seed_log(db_session)
    assert client.get("/logs").status_code == 401


def test_list_logs_returns_seeded_rows(authed_client, db_session):
    _seed_log(db_session, source_host="web-01")
    _seed_log(db_session, source_host="db-01", severity="info", flagged=False, flag_reason=None)

    resp = authed_client.get("/logs")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2


def test_list_logs_filters_by_severity(authed_client, db_session):
    _seed_log(db_session, severity="err")
    _seed_log(db_session, severity="info", flagged=False, flag_reason=None)

    resp = authed_client.get("/logs?severity=err")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["severity"] == "err"


def test_list_logs_filters_flagged_only(authed_client, db_session):
    _seed_log(db_session, flagged=True)
    _seed_log(db_session, flagged=False, flag_reason=None, severity="info")

    resp = authed_client.get("/logs?flagged_only=true")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["flagged"] is True


def test_list_logs_search_matches_message_text(authed_client, db_session):
    _seed_log(db_session, message="Failed password for invalid user admin")
    _seed_log(db_session, message="connection authorized", flagged=False, flag_reason=None, severity="info")

    resp = authed_client.get("/logs?search=authorized")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert "authorized" in body[0]["message"]


def test_log_stats_aggregates_correctly(authed_client, db_session):
    _seed_log(db_session, source_host="web-01", facility="auth", severity="err", flagged=True)
    _seed_log(db_session, source_host="db-01", facility="daemon", severity="info", flagged=False, flag_reason=None)
    _seed_log(db_session, source_host="web-01", facility="auth", severity="info", flagged=False, flag_reason=None)

    resp = authed_client.get("/logs/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_logs"] == 3
    assert body["flagged_logs"] == 1
    assert body["unique_hosts"] == 2
    assert body["by_severity"] == {"err": 1, "info": 2}
    assert body["by_facility"] == {"auth": 2, "daemon": 1}
    assert body["listening_port"] == 0  # SYSLOG_PORT=0 in test env


def test_log_stats_requires_auth(client):
    assert client.get("/logs/stats").status_code == 401
