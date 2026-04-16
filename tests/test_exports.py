from utils import get_admin_session
import requests
import json

def test_api_calls_open(settings):
    base = settings["BASE_URL"]
    resp = requests.get(f"{base}/api/calls/open")
    assert resp.status_code == 200
    j = json.loads(resp.content)
    assert "calls" in j
    assert resp.headers["Access-Control-Allow-Origin"] == "*"


def test_api_calls_closed(settings):
    base = settings["BASE_URL"]
    resp = requests.get(f"{base}/api/calls/closed")
    assert resp.status_code == 200
    j = json.loads(resp.content)
    assert "calls" in j
    assert resp.headers["Access-Control-Allow-Origin"] == "*"


def test_calls_open_xlsx(settings):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    resp = session.get(f"{base}/calls/open_xlsx")
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers["Content-Type"]
    assert len(resp.content) > 0


def test_call_zip(settings, seeded_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    resp = session.get(f"{base}/call/{seeded_call}.zip")
    assert resp.status_code == 200
    assert "application/zip" in resp.headers["Content-Type"]
    assert len(resp.content) > 0