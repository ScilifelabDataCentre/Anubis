"""End-to-end tests for call management operations in anubis/call.py.

Covers the call-lifecycle actions beyond field-schema editing: cloning a call,
resetting its proposal counter, managing attached documents, and adding/removing
reviewers. A regression in any of these silently corrupts or leaks call state
(clone dropping fields, a counter reset wiping numbering, a stuck reviewer).

Uses a dedicated session-scoped call (CI_CALL_CONFIG_CALL) so the mutating tests
never disturb the shared seeded_call; the clone test reads seeded_call read-only.
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest
from playwright.sync_api import expect
from conftest import _create_call, _cleanup_call

CONFIG_CALL_ID = "CI_CALL_CONFIG_CALL"
CLONE_TARGET_ID = "CI_CLONE_TARGET"


@pytest.fixture(scope="session")
def config_call(settings, browser):
    "A dedicated open call for the management tests, isolated from seeded_call."
    now = datetime.now()
    opens = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    closes = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")

    # Clear any call left behind by a prior failed run, then build fresh.
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    _cleanup_call(settings, page, CONFIG_CALL_ID)
    context.close()

    yield _create_call(browser, settings, CONFIG_CALL_ID, opens, closes)

    # Teardown
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    _cleanup_call(settings, page, CONFIG_CALL_ID)
    context.close()


@pytest.fixture
def temp_text_file():
    "A temp .txt file with known bytes. Returns (path, content); removed on test exit."
    content = b"e2e call document content\n"
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        yield path, content
    finally:
        os.unlink(path)


def test_clone_copies_fields_not_reviewers_or_dates(settings, browser, admin_page, seeded_call):
    "Cloning copies the proposal field definitions but not the reviewers or the dates."
    base = settings["BASE_URL"]
    reviewer = settings["REVIEWER_USERNAME"]
    try:
        admin_page.goto(f"{base}/call/{seeded_call}/clone")
        admin_page.locator("#identifier").fill(CLONE_TARGET_ID)
        admin_page.locator("#title").fill("Cloned call")
        admin_page.get_by_role("button", name="Create").click()
        # Clone succeeds by redirecting to the new call's edit page.
        expect(admin_page).to_have_url(f"{base}/call/{CLONE_TARGET_ID}/edit")

        # Proposal field definition is copied.
        admin_page.goto(f"{base}/call/{CLONE_TARGET_ID}/proposal")
        expect(admin_page.locator("tr", has_text="project_title")).to_be_visible()

        # Reviewers are not copied.
        admin_page.goto(f"{base}/call/{CLONE_TARGET_ID}/reviewers")
        expect(admin_page.get_by_role("link", name=reviewer)).to_have_count(0)

        # Dates are not copied.
        admin_page.goto(f"{base}/call/{CLONE_TARGET_ID}/edit")
        expect(admin_page.get_by_role("textbox", name="Labels Opens")).to_have_value("")
        expect(admin_page.get_by_role("textbox", name="Closes")).to_have_value("")
    finally:
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(15_000)
        _cleanup_call(settings, page, CLONE_TARGET_ID)
        context.close()


def test_reset_counter_succeeds_when_empty(settings, admin_page, config_call):
    "With no proposals in the call, resetting the proposal counter succeeds."
    base = settings["BASE_URL"]
    admin_page.goto(f"{base}/call/{config_call}")
    admin_page.get_by_role("button", name="Reset proposals counter").click()
    expect(admin_page.get_by_text("Counter for proposals in call reset.")).to_be_visible()


def test_reset_counter_hidden_with_proposals(settings, admin_page, populated_call):
    "A call that holds a proposal does not expose the reset-counter control."
    base = settings["BASE_URL"]
    admin_page.goto(f"{base}/call/{populated_call['call']}")
    expect(admin_page.get_by_role("button", name="Reset proposals counter")).to_have_count(0)


def test_call_documents_round_trip(settings, admin_page, config_call, temp_text_file):
    "Admin uploads a call document; the same content downloads; deleting removes it."
    base = settings["BASE_URL"]
    path, content = temp_text_file
    filename = os.path.basename(path)

    admin_page.goto(f"{base}/call/{config_call}/documents")
    admin_page.locator("#document").set_input_files(path)
    admin_page.get_by_role("button", name="Add document").click()
    expect(admin_page.locator("tr", has_text=filename)).to_be_visible()

    # The stored bytes download unchanged.
    resp = admin_page.context.request.get(f"{base}/call/{config_call}/documents/{filename}")
    assert resp.status == 200
    assert resp.body() == content

    # Delete removes the row (confirm dialog).
    admin_page.once("dialog", lambda d: d.accept())
    admin_page.locator("tr", has_text=filename).get_by_role("button", name="Delete").click()
    expect(admin_page.locator("tr", has_text=filename)).to_have_count(0)


def test_add_remove_reviewer(settings, admin_page, config_call, user2_page):
    "Admin adds a reviewer (with no reviews) and can remove it again."
    base = settings["BASE_URL"]
    admin_page.goto(f"{base}/call/{config_call}/reviewers")
    admin_page.locator("#reviewer").fill("testuser2")
    admin_page.get_by_role("button", name="Add", exact=True).click()
    expect(admin_page.get_by_role("link", name="testuser2")).to_be_visible()

    # Remove has no confirm dialog; the reviewer has no reviews so it is enabled.
    admin_page.locator("tr", has_text="testuser2").get_by_role("button", name="Remove").click()
    expect(admin_page.get_by_role("link", name="testuser2")).to_have_count(0)


def test_call_management_pages_admin_only(settings, admin_page, user_page, config_call):
    "Admin can load the documents/reviewers/clone pages; a non-admin user is denied."
    base = settings["BASE_URL"]
    for sub in ("documents", "reviewers", "clone"):
        target = f"{base}/call/{config_call}/{sub}"
        admin_page.goto(target)
        expect(admin_page).to_have_url(target)

        user_page.goto(target)
        expect(user_page).not_to_have_url(target)
