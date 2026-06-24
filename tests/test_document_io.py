"""End-to-end tests for document field upload + download paths.

These tests confirm the full upload -> storage -> download round-trip works at every level: proposal, review,
decision, grant.
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest
import utils
from conftest import (
    _cleanup_call,
    _create_and_finalize_decision,
    _create_and_finalize_review,
    _delete_proposal,
    _submit_proposal,
)
from playwright.sync_api import expect


DOC_CALL_ID = "CI_DOC_IO_CALL"


@pytest.fixture(scope="session")
def doc_io_call(settings, browser, pre_session_cleanup):
    """Create a call with document fields at every level + the supporting fields
    needed by the shared lifecycle helpers (project_title proposal field,
    quality_score review field, reviewer assignment).
    """
    base = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)

    # Remove any stale call left behind by a prior failed run
    _cleanup_call(settings, page, DOC_CALL_ID)

    utils.login(settings, page, "admin")

    page.get_by_role("button", name="Calls", exact=True).click()
    page.get_by_role("link", name="Create a new call").click()
    page.fill('input[name="identifier"]', DOC_CALL_ID)
    page.fill('input[name="title"]', "Doc IO test call")
    page.click("#create")
    assert page.url == f"{base}/call/{DOC_CALL_ID}/edit"

    now = datetime.now()
    opens = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    closes = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    page.get_by_role("textbox", name="Labels Opens").fill(opens)
    page.get_by_role("textbox", name="Closes").fill(closes)
    page.get_by_role("button", name="Save").click()
    assert page.url == f"{base}/call/{DOC_CALL_ID}"

    # Proposal fields: required line (matches the shared _submit_proposal helper)
    # + optional document
    page.locator("text=Edit proposal fields").click()
    assert page.url == f"{base}/call/{DOC_CALL_ID}/proposal"
    page.get_by_role("button", name="Add line field").click()
    page.locator("#_lineModal input[name='identifier']").fill("project_title")
    page.locator("#_lineModal input[name='required']").check()
    page.locator("#_lineModal").get_by_role("button", name="Save").click()
    expect(page.get_by_role("rowheader", name="project_title")).to_be_visible()
    page.get_by_role("button", name="Add document field").click()
    page.locator("#_documentModal input[name='identifier']").fill("attachment")
    page.locator("#_documentModal").get_by_role("button", name="Save").click()
    expect(page.get_by_role("rowheader", name="attachment")).to_be_visible()

    # Review fields: required score (matches _create_and_finalize_review) + optional document
    page.goto(f"{base}/call/{DOC_CALL_ID}/review")
    page.get_by_role("button", name="Add score field").click()
    page.locator("#_score-identifier").fill("quality_score")
    page.locator("#_score-title").fill("Scientific quality")
    page.locator("#_score-required").check()
    page.get_by_role("button", name="Save").click()
    expect(page.get_by_role("rowheader", name="quality_score")).to_be_visible()
    page.get_by_role("button", name="Add document field").click()
    page.locator("#_documentModal input[name='identifier']").fill("attachment")
    page.locator("#_documentModal").get_by_role("button", name="Save").click()
    expect(page.get_by_role("rowheader", name="attachment")).to_be_visible()

    # Decision: optional document (verdict is built-in)
    page.goto(f"{base}/call/{DOC_CALL_ID}/decision")
    page.get_by_role("button", name="Add document field").click()
    page.locator("#_documentModal input[name='identifier']").fill("attachment")
    page.locator("#_documentModal").get_by_role("button", name="Save").click()
    expect(page.get_by_role("rowheader", name="attachment")).to_be_visible()

    # Grant: optional document
    page.goto(f"{base}/call/{DOC_CALL_ID}/grant")
    page.get_by_role("button", name="Add document field").click()
    page.locator("#_documentModal input[name='identifier']").fill("attachment")
    page.locator("#_documentModal").get_by_role("button", name="Save").click()
    expect(page.get_by_role("rowheader", name="attachment")).to_be_visible()

    # Assign reviewer so reviews can be created
    page.goto(f"{base}/call/{DOC_CALL_ID}/reviewers")
    page.locator("#reviewer").fill(settings["REVIEWER_USERNAME"])
    page.get_by_role("button", name="Add", exact=True).click()
    assert page.get_by_role("link", name=settings["REVIEWER_USERNAME"]).is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])
    context.close()

    yield DOC_CALL_ID

    # Teardown
    td_context = browser.new_context()
    td_page = td_context.new_page()
    td_page.set_default_timeout(15_000)
    _cleanup_call(settings, td_page, DOC_CALL_ID)
    td_context.close()


@pytest.fixture
def temp_text_file():
    "Create a temp .txt file with known bytes. Clean up on test exit. Returns (path, content)."
    content = b"e2e test document content\n"
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        yield path, content
    finally:
        os.unlink(path)


def test_proposal_document_field_upload_download(settings, doc_io_call, user_page, admin_page, temp_text_file):
    "User uploads a document on a proposal. The same content downloads via /proposal/<pid>/document/<fid>."
    base = settings["BASE_URL"]
    tmp_path, file_content = temp_text_file
    proposal_url = None

    try:
        # User creates a proposal with the document attached
        user_page.goto(f"{base}/call/{doc_io_call}")
        user_page.locator("text=Create proposal").click()
        user_page.locator("#_title").fill("Proposal with attachment")
        user_page.locator("#project_title").fill("Project title")
        user_page.locator('input[type="file"][name="attachment"]').set_input_files(tmp_path)
        user_page.locator("text=Save & submit").click()
        proposal_url = user_page.url

        pid = proposal_url.rstrip("/").rsplit("/", 1)[-1]
        doc_url = f"{base}/proposal/{pid}/document/attachment"

        resp = user_page.context.request.get(doc_url)
        assert resp.status == 200
        assert resp.body() == file_content
        assert "text/plain" in resp.headers["content-type"]
    finally:
        if proposal_url is not None:
            _delete_proposal(admin_page, proposal_url)


def test_review_document_field_upload_download(settings, doc_io_call, user_page, admin_page, reviewer_page, temp_text_file):
    "Reviewer uploads a document on a review, the same content downloads via /review/<iuid>/document/<fid>."
    base = settings["BASE_URL"]
    reviewer_username = settings["REVIEWER_USERNAME"]
    tmp_path, file_content = temp_text_file
    proposal_url = None

    try:
        proposal_url = _submit_proposal(settings, doc_io_call, user_page, "Proposal for review doc test")

        # Admin creates the review assignment for the reviewer
        admin_page.goto(f"{base}/reviews/call/{doc_io_call}/reviewer/{reviewer_username}")
        admin_page.get_by_role("checkbox", name="Create").check()
        admin_page.get_by_role("button", name="Create checked reviews").click()

        # Reviewer opens the review, uploads doc + fills required score, saves
        reviewer_page.goto(base)
        reviewer_page.get_by_role("link", name="My reviews").click()
        reviewer_page.get_by_role("link", name="Review", exact=True).click()
        review_url = reviewer_page.url
        reviewer_page.get_by_role("button", name="Edit").click()
        reviewer_page.locator('input[type="file"][name="attachment"]').set_input_files(tmp_path)
        reviewer_page.get_by_text("No", exact=True).click()
        reviewer_page.locator('label[for="quality_score_4"]').click()
        reviewer_page.get_by_role("button", name="Save").click()

        iuid = review_url.rstrip("/").rsplit("/", 1)[-1]
        doc_url = f"{base}/review/{iuid}/document/attachment"

        resp = reviewer_page.context.request.get(doc_url)
        assert resp.status == 200
        assert resp.body() == file_content
        assert "text/plain" in resp.headers["content-type"]
    finally:
        if proposal_url is not None:
            _delete_proposal(admin_page, proposal_url)


def test_decision_document_field_upload_download(settings, doc_io_call, user_page, admin_page, reviewer_page, temp_text_file):
    "Admin uploads a document on a decision. The same content downloads via /decision/<iuid>/document/<fid>."
    base = settings["BASE_URL"]
    tmp_path, file_content = temp_text_file
    proposal_url = None

    try:
        proposal_url = _submit_proposal(settings, doc_io_call, user_page, "Proposal for decision doc test")
        _create_and_finalize_review(settings, doc_io_call, admin_page, reviewer_page)

        # Admin creates a decision with the document attached
        admin_page.goto(proposal_url)
        admin_page.get_by_role("button", name="Create decision").click()
        decision_url = admin_page.url
        admin_page.get_by_role("button", name="Edit").click()
        admin_page.locator('input[type="file"][name="attachment"]').set_input_files(tmp_path)
        admin_page.get_by_text("Accepted").click()
        admin_page.get_by_role("button", name="Save").click()

        iuid = decision_url.rstrip("/").rsplit("/", 1)[-1]
        doc_url = f"{base}/decision/{iuid}/document/attachment"

        resp = admin_page.context.request.get(doc_url)
        assert resp.status == 200
        assert resp.body() == file_content
        assert "text/plain" in resp.headers["content-type"]
    finally:
        if proposal_url is not None:
            _delete_proposal(admin_page, proposal_url)


def test_grant_document_field_upload_download(settings, doc_io_call, user_page, admin_page, reviewer_page, temp_text_file):
    "Admin uploads a document on a grant. The same content downloads via /grant/<gid>/document/<fid>."
    base = settings["BASE_URL"]
    tmp_path, file_content = temp_text_file
    proposal_url = None
    grant_url = None

    try:
        proposal_url = _submit_proposal(settings, doc_io_call, user_page, "Proposal for grant doc test")
        _create_and_finalize_review(settings, doc_io_call, admin_page, reviewer_page)
        _create_and_finalize_decision(proposal_url, admin_page)

        # Admin creates the grant dossier with the document attached
        admin_page.goto(proposal_url)
        admin_page.get_by_role("button", name="Create grant dossier").click()
        grant_url = admin_page.url
        admin_page.get_by_role("button", name="Edit").click()
        admin_page.locator('input[type="file"][name="attachment"]').set_input_files(tmp_path)
        admin_page.get_by_role("button", name="Save").click()

        gid = grant_url.rstrip("/").rsplit("/", 1)[-1]
        doc_url = f"{base}/grant/{gid}/document/attachment"

        resp = admin_page.context.request.get(doc_url)
        assert resp.status == 200
        assert resp.body() == file_content
        assert "text/plain" in resp.headers["content-type"]
    finally:
        # Grants don't cascade from proposal delete - unlock if needed, then delete grant first
        if grant_url is not None:
            admin_page.goto(grant_url)
            unlock_btn = admin_page.get_by_role("button", name="Unlock")
            if unlock_btn.is_visible():
                unlock_btn.click()
                admin_page.wait_for_load_state("load")
            admin_page.once("dialog", lambda d: d.accept())
            admin_page.get_by_role("button", name="Delete").click()
            admin_page.wait_for_load_state("load")
        if proposal_url is not None:
            _delete_proposal(admin_page, proposal_url)
