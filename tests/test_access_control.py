"""
Testing access control for admin, user, reviewer and non-user.
"""

import pytest
from conftest import _create_call, _cleanup_call, SEEDED_CLOSED_CALL_ID


@pytest.fixture(scope="session")
def submitted_proposal(settings, seeded_call, user_page):
    """Submit a proposal to the seeded call as testuser. Read-only — tests must not modify it."""
    base = settings["BASE_URL"]

    user_page.goto(f"{base}/call/{seeded_call}")
    user_page.locator("text=Create proposal").click()

    user_page.locator("#_title").fill("Proposal")
    user_page.locator("#project_title").fill("Proposal Title")
    user_page.locator("text=Save & submit").click()

    yield user_page.url


@pytest.fixture(scope="session")
def create_closed_call(settings, browser, pre_session_cleanup):
    call_id = SEEDED_CLOSED_CALL_ID
    opens = "1926-12-24 10:00"
    closes = "1926-12-24 10:01"
    
    yield _create_call(browser, settings, call_id, opens, closes)

    td_context = browser.new_context()
    td_page = td_context.new_page()
    _cleanup_call(settings, td_page, call_id)
    td_context.close()


def test_proposal_access_admin(admin_page, submitted_proposal):

    admin_page.goto(submitted_proposal)
    assert admin_page.url == submitted_proposal


def test_proposal_access_reviewer(reviewer_page, submitted_proposal):
    
    reviewer_page.goto(submitted_proposal)
    assert reviewer_page.url == submitted_proposal


def test_proposal_access_user(user_page, submitted_proposal):
    
    user_page.goto(submitted_proposal)
    assert user_page.url == submitted_proposal

def test_proposal_access_anonymous(settings, browser, submitted_proposal):
    base_url = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    
    page.goto(submitted_proposal)
    assert page.url.startswith(f"{base_url}/user/login")
    context.close()

def test_edit_submitted_proposal(settings, user_page, submitted_proposal):
    user_page.goto(f"{submitted_proposal}/edit")
    assert user_page.url.rstrip("/") == settings["BASE_URL"].rstrip("/")
    assert user_page.get_by_text("You are not allowed to edit this proposal.").is_visible()

def test_user2_proposal_access(settings, user2_page, submitted_proposal):
    user2_page.goto(f"{submitted_proposal}")
    assert user2_page.url.rstrip("/") == settings["BASE_URL"].rstrip("/")
    assert user2_page.get_by_text("You are not allowed to view this proposal.").is_visible()

def test_create_proposal_for_closed_call(settings, create_closed_call, user_page):
    base = settings["BASE_URL"]
    user_page.goto(f"{base}/call/{create_closed_call}")
    assert user_page.get_by_text("Call is closed; a proposal cannot be created.").is_visible()
    assert not user_page.locator("button").filter(has_text="Create proposal").is_visible()
