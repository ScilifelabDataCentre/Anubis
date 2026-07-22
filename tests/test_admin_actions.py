"""
End-to-end tests for admin lifecycle inverse actions.

Forward lifecycle actions (submit, finalize, lock) all have inverse counterparts
(unsubmit, unfinalize, unlock). These are easy to forget in refactors and
regressing one leaves users stuck in a terminal state. Each test
exercises the forward + inverse together to guard against that.

Uses its own call (CI_ACTIONS_CALL) rather than the shared `seeded_call` so the
read-only session-scoped proposal in test_access_control.py does not block the
"Create proposal" link these tests need.
"""

import pytest
from conftest import (
    _create_and_finalize_decision,
    _create_and_finalize_review,
    _dedicated_call,
    _delete_proposal,
    _submit_proposal,
)
from playwright.sync_api import expect


ACTIONS_CALL_ID = "CI_ACTIONS_CALL"


@pytest.fixture(scope="session")
def actions_call(settings, browser, pre_session_cleanup):
    "Session-scoped call dedicated to the inverse-action tests, isolated from other test files' state."
    yield from _dedicated_call(browser, settings, ACTIONS_CALL_ID)


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
