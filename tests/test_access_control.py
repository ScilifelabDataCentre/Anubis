"""
Testing access control for admin, user, reviewer and non-user.
"""

import pytest
from playwright.sync_api import Browser
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
def user2_page(settings, admin_page, browser: Browser):

    user2_username = "testuser2"
    user2_email = "testuser2@test.com"
    user2_password = "testuserpass123"
    base = settings["BASE_URL"]

    # Register user2 and set password via admin
    admin_page.get_by_role("button", name="Users", exact=True).click()
    admin_page.get_by_role("link", name="Register user").click()
    admin_page.get_by_role("textbox", name="User name").fill(user2_username)
    admin_page.get_by_role("textbox", name="Email").fill(user2_email)
    admin_page.get_by_role("button", name="Register").click()
    admin_page.goto(f"{base}/user/all")
    admin_page.get_by_role("link", name="testuser2").click()
    admin_page.get_by_role("button", name="Set password", exact=True).click()
    admin_page.get_by_role("textbox", name="Password").click()
    admin_page.get_by_role("textbox", name="Password").fill(user2_password)
    admin_page.get_by_role("button", name="Set password").click()

    # Log in as user2
    context = browser.new_context()
    user2_page = context.new_page()
    user2_page.set_default_timeout(15_000)
    user2_page.goto(base)
    user2_page.click("text=Login")
    user2_page.fill('input[name="username"]', user2_username)
    user2_page.fill('input[name="password"]', user2_password)
    user2_page.click("id=login")
    assert user2_page.url.rstrip("/") == base

    yield user2_page

    # Teardown: delete user2
    context.close()
    admin_page.get_by_role("button", name="Users", exact=True).click()
    admin_page.get_by_role("link", name="All users").click()
    admin_page.get_by_role("link", name=user2_username).click()
    admin_page.once("dialog", lambda dialog: dialog.accept())
    admin_page.get_by_role("button", name="Delete").click()


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
