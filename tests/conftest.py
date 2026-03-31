"""Shared fixtures for the Anubis e2e test suite.

Session-scoped page convention: every test that uses admin_page, user_page, or
reviewer_page must call page.goto() to its starting URL at the top of the test
body. Never assume the page is on any particular URL.
"""

from datetime import datetime, timedelta

import pytest
import utils


SEEDED_CALL_ID = "CI_SEEDED_CALL"
SEEDED_TRANSITION_CALL_ID = "CI_TRANSITION_CALL_ID"
CALL_ID = "CI_LIFECYCLE_TEST"
SEEDED_CLOSED_CALL_ID = "CI_CLOSED_CALL_ID"

@pytest.fixture(scope="session")
def settings():
    return utils.get_settings(
        BASE_URL="http://localhost:5002",
        ADMIN_USERNAME=None,
        ADMIN_PASSWORD=None,
        USER_USERNAME=None,
        USER_PASSWORD=None,
        REVIEWER_USERNAME=None,
        REVIEWER_PASSWORD=None,
    )


def _cleanup_call(settings, page, call_id):
    "Delete all artifacts for call_id (grant -> decision -> review -> proposal -> call), tolerating missing items."
    base = settings["BASE_URL"]
    utils.login(settings, page, "admin")

    # Grant: unlock if locked, then delete
    page.goto(f"{base}/grant/{call_id}:G:001")
    if page.url.startswith(f"{base}/grant/"):
        unlock_btn = page.get_by_role("button", name="Unlock")
        if unlock_btn.is_visible():
            unlock_btn.click()
        delete_btn = page.get_by_role("button", name="Delete")
        if delete_btn.is_visible():
            page.once("dialog", lambda d: d.accept())
            delete_btn.click()

    # Decision: reached via the proposal page
    page.goto(f"{base}/proposal/{call_id}:001")
    if page.url.startswith(f"{base}/proposal/"):
        accepted_btn = page.get_by_role("button", name="Accepted")
        if accepted_btn.is_visible():
            accepted_btn.click()
            unfinalize_btn = page.get_by_role("button", name="Unfinalize")
            if unfinalize_btn.is_visible():
                unfinalize_btn.click()
            delete_btn = page.get_by_role("button", name="Delete")
            if delete_btn.is_visible():
                page.once("dialog", lambda d: d.accept())
                delete_btn.click()

    # Review
    page.goto(f"{base}/reviews/call/{call_id}")
    if page.url.startswith(f"{base}/reviews/call/"):
        review_link = page.get_by_role("link", name="Review", exact=True)
        if review_link.is_visible():
            review_link.click()
            unfinalize_btn = page.get_by_role("button", name="Unfinalize")
            if unfinalize_btn.is_visible():
                unfinalize_btn.click()
            delete_btn = page.get_by_role("button", name="Delete")
            if delete_btn.is_visible():
                page.once("dialog", lambda d: d.accept())
                delete_btn.click()

    # Proposal
    page.goto(f"{base}/proposal/{call_id}:001")
    if page.url.startswith(f"{base}/proposal/"):
        delete_btn = page.get_by_role("button", name="Delete")
        if delete_btn.is_visible():
            page.once("dialog", lambda d: d.accept())
            delete_btn.click()

    # Call
    page.goto(f"{base}/call/{call_id}")
    if page.url.startswith(f"{base}/call/"):
        delete_btn = page.get_by_role("button", name="Delete")
        if delete_btn.is_visible():
            page.once("dialog", lambda d: d.accept())
            delete_btn.click()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


@pytest.fixture(scope="session", autouse=True)
def pre_session_cleanup(settings, browser):
    "Remove stale test artifacts at session start. Handles cases where teardown did not run (CI kill, hard crash)."
    context = browser.new_context()
    page = context.new_page()
    _cleanup_call(settings, page, SEEDED_CALL_ID)
    _cleanup_call(settings, page, SEEDED_CLOSED_CALL_ID)
    _cleanup_call(settings, page, SEEDED_TRANSITION_CALL_ID)
    context.close()
    yield


@pytest.fixture(scope="session")
def admin_page(settings, browser):
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "admin")
    yield page
    context.close()


@pytest.fixture(scope="session")
def user_page(settings, browser):
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "user")
    yield page
    context.close()


@pytest.fixture(scope="session")
def reviewer_page(settings, browser):
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    base = settings["BASE_URL"]
    page.goto(base)
    page.click("text=Login")
    page.fill('input[name="username"]', settings["REVIEWER_USERNAME"])
    page.press('input[name="username"]', "Tab")
    page.fill('input[name="password"]', settings["REVIEWER_PASSWORD"])
    page.click("id=login")
    assert page.url.rstrip("/") == base
    yield page
    context.close()


@pytest.fixture(scope="session")
def seeded_call(settings, browser, pre_session_cleanup):
    """Create a fully configured open call shared across test modules.

    The call has a required line proposal field, a required score review field,
    the reviewer user assigned, and dates set so it is currently open.
    Yields the call identifier string. Cleaned up after the session ends.
    """
    call_id = SEEDED_CALL_ID
    # Set dates so the call is open
    now = datetime.now()
    opens = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    closes = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    yield _create_call(browser, settings, call_id, opens, closes)


    # Teardown
    td_context = browser.new_context()
    td_page = td_context.new_page()
    _cleanup_call(settings, td_page, call_id)
    td_context.close()


def _create_call(browser, settings, call_id, opening_date, closing_date):
    base = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "admin")

    # Create call
    page.get_by_role("button", name="Calls", exact=True).click()
    page.get_by_role("link", name="Create a new call").click()
    page.fill('input[name="identifier"]', call_id)
    page.fill('input[name="title"]', "Seeded test call")
    page.click("#create")
    assert page.url == f"{base}/call/{call_id}/edit"
    page.get_by_role("button", name="Save").click()
    assert page.url == f"{base}/call/{call_id}"

    # Add proposal field
    page.locator("text=Edit proposal fields").click()
    assert page.url == f"{base}/call/{call_id}/proposal"
    page.get_by_role("button", name="Add line field").click()
    page.locator("#_lineModal input[name='identifier']").fill("project_title")
    page.locator("#_lineModal input[name='required']").check()
    page.locator("#_lineModal").get_by_role("button", name="Save").click()
    assert page.url == f"{base}/call/{call_id}/proposal"

    # Add review field
    page.goto(f"{base}/call/{call_id}/review")
    page.get_by_role("button", name="Add score field").click()
    page.locator("#_score-identifier").fill("quality_score")
    page.locator("#_score-title").fill("Scientific quality")
    page.locator("#_score-required").check()
    page.get_by_role("button", name="Save").click()
    assert page.locator("text=quality_score").is_visible()

    # Add reviewer
    page.goto(f"{base}/call/{call_id}/reviewers")
    page.locator("#reviewer").fill(settings["REVIEWER_USERNAME"])
    page.get_by_role("button", name="Add", exact=True).click()
    assert page.get_by_role("link", name=settings["REVIEWER_USERNAME"]).is_visible()

    page.goto(f"{base}/call/{call_id}/edit")
    page.get_by_role("textbox", name="Labels Opens").fill(opening_date)
    page.get_by_role("textbox", name="Closes").fill(closing_date)
    page.get_by_role("button", name="Save").click()
    assert page.url == f"{base}/call/{call_id}"

    utils.logout(settings, page, settings["ADMIN_USERNAME"])
    context.close()

    return call_id

