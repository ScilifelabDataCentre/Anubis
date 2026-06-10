"""End-to-end tests for admin lifecycle inverse actions.

Forward lifecycle actions (submit, finalize, lock) all have inverse counterparts
(unsubmit, unfinalize, unlock). These are easy to forget in refactors and
regressing one leaves users stuck in a terminal state. Each test
exercises the forward + inverse together to guard against that.

Uses its own call (CI_ACTIONS_CALL) rather than the shared `seeded_call` so the
read-only session-scoped proposal in test_access_control.py does not block the
"Create proposal" link these tests need.
"""

from datetime import datetime, timedelta

import pytest
from conftest import _cleanup_call, _create_call
from playwright.sync_api import expect


ACTIONS_CALL_ID = "CI_ACTIONS_CALL"


@pytest.fixture(scope="session")
def actions_call(settings, browser, pre_session_cleanup):
    "Session-scoped call dedicated to the inverse-action tests, isolated from other test files' state."
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    _cleanup_call(settings, page, ACTIONS_CALL_ID)
    context.close()

    now = datetime.now()
    opens = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    closes = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    yield _create_call(browser, settings, ACTIONS_CALL_ID, opens, closes)

    td_context = browser.new_context()
    td_page = td_context.new_page()
    td_page.set_default_timeout(15_000)
    _cleanup_call(settings, td_page, ACTIONS_CALL_ID)
    td_context.close()


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


def test_proposal_unsubmit(settings, actions_call, user_page, admin_page):
    "Admin unsubmits a submitted proposal and user can edit it again."
    proposal_url = _submit_proposal(settings, actions_call, user_page, "Proposal for unsubmit test")

    try:
        # Admin sees the Unsubmit button on the submitted proposal
        admin_page.goto(proposal_url)
        expect(admin_page.get_by_role("button", name="Unsubmit")).to_be_visible()
        admin_page.get_by_role("button", name="Unsubmit").click()

        # After unsubmit, the Submit button is back (proposal returned to editable state)
        expect(admin_page.get_by_role("button", name="Submit")).to_be_visible()

        # User sees their own proposal as editable again
        user_page.goto(proposal_url)
        expect(user_page.get_by_role("button", name="Submit")).to_be_visible()
    finally:
        _delete_proposal(admin_page, proposal_url)


def test_review_unfinalize(settings, actions_call, user_page, admin_page, reviewer_page):
    "Admin unfinalizes a finalized review and reviewer can edit it again."
    proposal_url = _submit_proposal(settings, actions_call, user_page, "Proposal for review unfinalize")

    try:
        review_url = _create_and_finalize_review(settings, actions_call, admin_page, reviewer_page)

        # Admin unfinalizes the review
        admin_page.goto(review_url)
        expect(admin_page.get_by_role("button", name="Unfinalize")).to_be_visible()
        admin_page.get_by_role("button", name="Unfinalize").click()

        # Verify Finalize button is back (review is editable again)
        expect(admin_page.get_by_role("button", name="Finalize")).to_be_visible()
    finally:
        _delete_proposal(admin_page, proposal_url)


def test_decision_unfinalize(settings, actions_call, user_page, admin_page, reviewer_page):
    "Admin unfinalizes a finalized decision and admin can edit it again."
    proposal_url = _submit_proposal(settings, actions_call, user_page, "Proposal for decision unfinalize")

    try:
        _create_and_finalize_review(settings, actions_call, admin_page, reviewer_page)
        _create_and_finalize_decision(proposal_url, admin_page)

        # Admin unfinalizes the decision, still on the decision page after finalize
        expect(admin_page.get_by_role("button", name="Unfinalize")).to_be_visible()
        admin_page.get_by_role("button", name="Unfinalize").click()

        # Verify that the Finalize button is back so decision is editable again
        expect(admin_page.get_by_role("button", name="Finalize")).to_be_visible()
    finally:
        _delete_proposal(admin_page, proposal_url)


def test_grant_lock_unlock(settings, actions_call, user_page, admin_page, reviewer_page):
    "Admin locks a grant so user cannot edit, then unlocks so user can edit again."
    proposal_url = _submit_proposal(settings, actions_call, user_page, "Proposal for grant lock test")
    grant_url = None

    try:
        _create_and_finalize_review(settings, actions_call, admin_page, reviewer_page)
        _create_and_finalize_decision(proposal_url, admin_page)

        # Admin creates the grant dossier from the accepted proposal
        admin_page.goto(proposal_url)
        admin_page.get_by_role("button", name="Create grant dossier").click()
        grant_url = admin_page.url

        # Admin locks the grant
        admin_page.get_by_role("button", name="Lock").click()
        expect(admin_page.locator("text=Locked")).to_be_visible()

        # User cannot edit the locked grant
        user_page.goto(grant_url)
        expect(user_page.get_by_role("button", name="Edit")).not_to_be_visible()

        # Admin unlocks the grant
        admin_page.goto(grant_url)
        admin_page.get_by_role("button", name="Unlock").click()
        expect(admin_page.locator("text=Unlocked")).to_be_visible()

        # User can edit the grant again
        user_page.goto(grant_url)
        expect(user_page.get_by_role("button", name="Edit")).to_be_visible()
    finally:
        # Cleanup: unlock the grant if still locked, then delete it before the proposal
        # since proposal delete does not cascade to grant
        if grant_url is not None:
            admin_page.goto(grant_url)
            unlock_btn = admin_page.get_by_role("button", name="Unlock")
            if unlock_btn.is_visible():
                unlock_btn.click()
                admin_page.wait_for_load_state("load")
            admin_page.once("dialog", lambda d: d.accept())
            admin_page.get_by_role("button", name="Delete").click()
            admin_page.wait_for_load_state("load")
        _delete_proposal(admin_page, proposal_url)
