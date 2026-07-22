"""Shared fixtures for the Anubis e2e test suite.

Session-scoped page convention: every test that uses admin_page, user_page, or
reviewer_page must call page.goto() to its starting URL at the top of the test
body. Never assume the page is on any particular URL.
"""

from datetime import datetime, timedelta

import pytest
from playwright.sync_api import expect
import utils


SEEDED_CALL_ID = "CI_SEEDED_CALL"
SEEDED_TRANSITION_CALL_ID = "CI_TRANSITION_CALL_ID"
CALL_ID = "CI_LIFECYCLE_TEST"
SEEDED_CLOSED_CALL_ID = "CI_CLOSED_CALL_ID"
EXPORT_CALL_ID = "CI_EXPORT_CALL"

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
            page.wait_for_load_state("load")
        delete_btn = page.get_by_role("button", name="Delete")
        if delete_btn.is_visible():
            page.once("dialog", lambda d: d.accept())
            delete_btn.click()
            page.wait_for_load_state("load")

    # Proposal
    page.goto(f"{base}/proposals/call/{call_id}")
    proposal_links = [link.get_attribute("href") for link in page.locator("a[title='Proposal']").all()]
    for prop_link in proposal_links:
        page.goto(base + prop_link)
        page.once("dialog", lambda d: d.accept())
        page.get_by_role("button", name="Delete").click()
        page.wait_for_load_state("load")

    # Call
    page.goto(f"{base}/call/{call_id}")
    if page.url.startswith(f"{base}/call/"):
        delete_btn = page.get_by_role("button", name="Delete")
        if delete_btn.is_visible():
            page.once("dialog", lambda d: d.accept())
            delete_btn.click()
            page.wait_for_load_state("load")

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def _open_call_dates():
    "Return (opens, closes) strings for a call that is currently open for ~30 days."
    now = datetime.now()
    opens = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    closes = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    return opens, closes


def _cleanup_call_fresh_context(browser, settings, call_id):
    "Run _cleanup_call in a throwaway browser context, for fixture setup or teardown."
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    _cleanup_call(settings, page, call_id)
    context.close()


def _dedicated_call(browser, settings, call_id, opens=None, closes=None):
    """Generator backing the isolated-call fixtures: remove any stale copy, create
    the call fresh, yield its identifier, then clean up on teardown. A fixture that
    only needs the call delegates with `yield from _dedicated_call(...)`. The ones
    that build extra state (proposals, reviews) call the two helpers above directly.
    Defaults to an open call. Pass opens/closes for a closed one.
    """
    if opens is None or closes is None:
        opens, closes = _open_call_dates()
    _cleanup_call_fresh_context(browser, settings, call_id)
    yield _create_call(browser, settings, call_id, opens, closes)
    _cleanup_call_fresh_context(browser, settings, call_id)


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
    base = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "reviewer")
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
    yield from _dedicated_call(browser, settings, SEEDED_CALL_ID)


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


@pytest.fixture(scope="session")
def user2_page(settings, admin_page, browser):
    "A second regular user (testuser2), registered and logged in. Deleted at session end."
    user2_username = "testuser2"
    user2_email = "testuser2@test.com"
    user2_password = "testuserpass123"
    base = settings["BASE_URL"]

    # Register user2 and set its password via admin
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

    # Log in as user2 in its own context
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    page.goto(base)
    page.click("text=Login")
    page.fill('input[name="username"]', user2_username)
    page.fill('input[name="password"]', user2_password)
    page.click("id=login")
    assert page.url.rstrip("/") == base

    yield page

    # Teardown: delete user2
    context.close()
    admin_page.get_by_role("button", name="Users", exact=True).click()
    admin_page.get_by_role("link", name="All users").click()
    admin_page.get_by_role("link", name=user2_username).click()
    admin_page.once("dialog", lambda dialog: dialog.accept())
    admin_page.get_by_role("button", name="Delete").click()


# Lifecycle helpers shared across the state-mutating test modules. Each "forward"
# action (submit, finalize) lives here so test_admin_actions, test_document_io,
# the exports and the audit-log tests can reuse one proven implementation.

def _submit_proposal(settings, call_id, user_page, title):
    "Submit a proposal as user to the given call. Returns the proposal URL."
    base = settings["BASE_URL"]
    user_page.goto(f"{base}/call/{call_id}")
    user_page.locator("text=Create proposal").click()
    user_page.locator("#_title").fill(title)
    user_page.locator("#project_title").fill("Project title")
    user_page.locator("text=Save & submit").click()
    return user_page.url


def _create_and_finalize_review(settings, call_id, admin_page, reviewer_page):
    "Admin creates the review assignment, reviewer fills the score and finalizes. Returns review URL."
    base = settings["BASE_URL"]
    reviewer_username = settings["REVIEWER_USERNAME"]

    admin_page.goto(f"{base}/reviews/call/{call_id}/reviewer/{reviewer_username}")
    admin_page.get_by_role("checkbox", name="Create").check()
    admin_page.get_by_role("button", name="Create checked reviews").click()

    reviewer_page.goto(base)
    reviewer_page.get_by_role("link", name="My reviews").click()
    reviewer_page.get_by_role("link", name="Review", exact=True).click()
    review_url = reviewer_page.url
    reviewer_page.get_by_role("button", name="Edit").click()
    reviewer_page.get_by_text("No", exact=True).click()
    reviewer_page.locator('label[for="quality_score_4"]').click()
    reviewer_page.get_by_role("button", name="Save").click()
    reviewer_page.get_by_role("button", name="Finalize").click()
    expect(reviewer_page.locator(".badge-success", has_text="Finalized")).to_be_visible()
    return review_url


def _create_and_finalize_decision(proposal_url, admin_page):
    "Admin creates a decision, sets verdict to Accepted, and finalizes. Returns decision URL."
    admin_page.goto(proposal_url)
    admin_page.get_by_role("button", name="Create decision").click()
    decision_url = admin_page.url
    admin_page.get_by_role("button", name="Edit").click()
    admin_page.get_by_text("Accepted").click()
    admin_page.get_by_role("button", name="Save").click()
    admin_page.get_by_role("button", name="Finalize").click()
    expect(admin_page.locator(".badge-success", has_text="Finalized")).to_be_visible()
    return decision_url


def _delete_proposal(admin_page, proposal_url):
    "Admin deletes a proposal. Cascades to its reviews and decisions."
    admin_page.goto(proposal_url)
    admin_page.once("dialog", lambda d: d.accept())
    admin_page.get_by_role("button", name="Delete").click()
    admin_page.wait_for_load_state("load")


@pytest.fixture(scope="session")
def populated_call(settings, browser, admin_page, user_page, pre_session_cleanup):
    """Create an isolated call carried through the full lifecycle: one submitted
    proposal, one finalized review, one finalized (accepted) decision, and a
    grant dossier. Yields a dict of identifiers for the export and audit-log
    tests to build download URLs from.

    The review is created for the admin user, who is added as a reviewer here,
    not for the shared reviewer user. A finalized review still appears in the
    reviewer's list, so a persistent review for the shared reviewer would leave
    them with reviews in more than one call and break the "My reviews"
    navigation that _create_and_finalize_review relies on in other modules.
    """
    base = settings["BASE_URL"]
    admin_username = settings["ADMIN_USERNAME"]
    cid = EXPORT_CALL_ID

    # Remove any stale call left behind by a prior failed run, then build fresh.
    _cleanup_call_fresh_context(browser, settings, cid)
    opens, closes = _open_call_dates()
    _create_call(browser, settings, cid, opens, closes)

    # Add admin as a reviewer so a review can be created and finalized without
    # touching the shared reviewer user's "My reviews" list.
    admin_page.goto(f"{base}/call/{cid}/reviewers")
    admin_page.locator("#reviewer").fill(admin_username)
    admin_page.get_by_role("button", name="Add", exact=True).click()
    expect(admin_page.get_by_role("link", name=admin_username)).to_be_visible()

    # Title must be exactly "Proposal": _cleanup_call finds proposals to delete
    # with the selector a[title='Proposal'] (the title attribute carries the
    # proposal title), so any other title would leak the call past teardown.
    proposal_url = _submit_proposal(settings, cid, user_page, "Proposal")
    pid = proposal_url.rstrip("/").rsplit("/", 1)[-1]

    # Admin creates its own review for this call, then fills and finalizes it.
    # Navigation is scoped to this call so it never depends on "My reviews".
    admin_page.goto(f"{base}/reviews/call/{cid}/reviewer/{admin_username}")
    admin_page.get_by_role("checkbox", name="Create").check()
    admin_page.get_by_role("button", name="Create checked reviews").click()
    admin_page.get_by_role("link", name="Review", exact=True).click()
    review_url = admin_page.url
    admin_page.get_by_role("button", name="Edit").click()
    admin_page.get_by_text("No", exact=True).click()
    admin_page.locator('label[for="quality_score_4"]').click()
    admin_page.get_by_role("button", name="Save").click()
    admin_page.get_by_role("button", name="Finalize").click()
    expect(admin_page.locator(".badge-success", has_text="Finalized")).to_be_visible()
    review_iuid = review_url.rstrip("/").rsplit("/", 1)[-1]

    decision_url = _create_and_finalize_decision(proposal_url, admin_page)
    decision_iuid = decision_url.rstrip("/").rsplit("/", 1)[-1]

    admin_page.goto(proposal_url)
    admin_page.get_by_role("button", name="Create grant dossier").click()
    gid = admin_page.url.rstrip("/").rsplit("/", 1)[-1]

    yield {
        "call": cid,
        "proposal": pid,
        "review": review_iuid,
        "decision": decision_iuid,
        "grant": gid,
    }

    # Teardown: _cleanup_call removes grant -> proposals (cascading reviews and
    # decisions) -> call.
    _cleanup_call_fresh_context(browser, settings, cid)

