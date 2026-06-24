"""End-to-end tests for the download/export endpoints.

Covers the JSON API, the XLSX spreadsheet exports, the ZIP bundles, and the
DOCX proposal export. Each download test asserts the status, the Content-Type,
and a non-empty body: enough to catch a format generator silently breaking on a
library upgrade, which stays invisible until a user clicks download.

The object-level exports (proposal/review/grant) need real documents to export,
so they use the session-scoped `populated_call` fixture from conftest.
"""

import json

import requests
from utils import get_admin_session

# Content-Type substrings sent by the download endpoints (anubis/__init__.py).
XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_MIMETYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ZIP_MIMETYPE = "application/zip"


def _assert_download(session, url, content_type):
    "Assert the URL returns 200, the expected Content-Type, and a non-empty body."
    resp = session.get(url)
    assert resp.status_code == 200
    assert content_type in resp.headers["Content-Type"]
    assert len(resp.content) > 0


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


# Calls-level exports: a workbook of calls, needing only an admin session.
# seeded_call guarantees at least one call exists in the listings.

def test_calls_open_xlsx(settings):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/calls/open_xlsx", XLSX_MIMETYPE)


def test_calls_closed_xlsx(settings):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/calls/closed_xlsx", XLSX_MIMETYPE)


def test_calls_all_xlsx(settings, seeded_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/calls/all_xlsx", XLSX_MIMETYPE)


def test_calls_owner_xlsx(settings, seeded_call):
    "The seeded calls are created by admin, so admin is their owner."
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    url = f"{base}/calls/owner/{settings['ADMIN_USERNAME']}.xlsx"
    _assert_download(session, url, XLSX_MIMETYPE)


def test_calls_unpublished_xlsx(settings, seeded_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/calls/unpublished.xlsx", XLSX_MIMETYPE)


def test_calls_reviews_xlsx(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/calls/reviews_xlsx", XLSX_MIMETYPE)


def test_calls_grants_xlsx(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/calls/grants_xlsx", XLSX_MIMETYPE)


# Object-level exports: export a specific call/proposal/review/grant, so they
# need the fully populated call (admin is its reviewer; see the fixture).

def test_call_zip(settings, seeded_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/call/{seeded_call}.zip", ZIP_MIMETYPE)


def test_proposal_docx(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/proposal/{populated_call['proposal']}.docx", DOCX_MIMETYPE)


def test_proposal_xlsx(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/proposal/{populated_call['proposal']}.xlsx", XLSX_MIMETYPE)


def test_proposals_call_xlsx(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/proposals/call/{populated_call['call']}.xlsx", XLSX_MIMETYPE)


def test_reviews_call_xlsx(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/reviews/call/{populated_call['call']}.xlsx", XLSX_MIMETYPE)


def test_reviews_call_reviewer_xlsx(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    reviewer = settings["ADMIN_USERNAME"]
    url = f"{base}/reviews/call/{populated_call['call']}/reviewer/{reviewer}.xlsx"
    _assert_download(session, url, XLSX_MIMETYPE)


def test_reviews_call_reviewer_zip(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    reviewer = settings["ADMIN_USERNAME"]
    url = f"{base}/reviews/call/{populated_call['call']}/reviewer/{reviewer}.zip"
    _assert_download(session, url, ZIP_MIMETYPE)


def test_reviews_proposal_xlsx(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/reviews/proposal/{populated_call['proposal']}.xlsx", XLSX_MIMETYPE)


def test_grant_zip(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/grant/{populated_call['grant']}.zip", ZIP_MIMETYPE)


def test_grants_call_xlsx(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/grants/call/{populated_call['call']}.xlsx", XLSX_MIMETYPE)


def test_grants_call_zip(settings, populated_call):
    base = settings["BASE_URL"]
    session = get_admin_session(settings)
    _assert_download(session, f"{base}/grants/call/{populated_call['call']}.zip", ZIP_MIMETYPE)
