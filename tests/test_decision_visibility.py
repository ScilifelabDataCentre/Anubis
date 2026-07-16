"""End-to-end tests for submitter visibility of a finalized decision (anubis/decision.py).

A proposal submitter sees the decision inline on their proposal only when the call
privilege 'allow_submitter_view_decision' is set and the decision is finalized.
Staff/admin see it regardless (via the decision link), so these assertions run as
the submitter (user_page).

Uses a dedicated call: a user may hold only one proposal per call, so this must not
collide with seeded_call's read-only submitted_proposal.
"""

from datetime import datetime, timedelta

import pytest
from playwright.sync_api import expect
from conftest import _create_call, _cleanup_call, _submit_proposal, _create_and_finalize_decision

DECISION_CALL_ID = "CI_DECISION_VIS_CALL"


@pytest.fixture(scope="session")
def decision_call(settings, browser, admin_page, user_page):
    "Dedicated call with a submitted proposal and a finalized (Accepted) decision."
    now = datetime.now()
    opens = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    closes = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")

    # Clear any call left behind by a prior failed run, then build fresh.
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    _cleanup_call(settings, page, DECISION_CALL_ID)
    context.close()

    cid = _create_call(browser, settings, DECISION_CALL_ID, opens, closes)
    # Title must be exactly "Proposal": _cleanup_call finds proposals to delete via
    # a[title='Proposal'] (the link's title attribute is the proposal title), so any
    # other title would leak the proposal and block the call's teardown.
    proposal_url = _submit_proposal(settings, cid, user_page, "Proposal")
    _create_and_finalize_decision(proposal_url, admin_page)

    yield {"cid": cid, "proposal_url": proposal_url}

    # Teardown
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    _cleanup_call(settings, page, DECISION_CALL_ID)
    context.close()


def _set_submitter_view_decision(settings, admin_page, cid, enabled):
    "Toggle the call's allow_submitter_view_decision privilege via the edit form."
    base = settings["BASE_URL"]
    admin_page.goto(f"{base}/call/{cid}/edit")
    box = admin_page.locator("#allow_submitter_view_decision")
    box.check() if enabled else box.uncheck()
    admin_page.get_by_role("button", name="Save").click()
    expect(admin_page).to_have_url(f"{base}/call/{cid}")


def test_submitter_sees_decision_when_privilege_set(settings, admin_page, user_page, decision_call):
    "With the privilege set, the submitter sees the finalized decision on their proposal."
    _set_submitter_view_decision(settings, admin_page, decision_call["cid"], True)

    user_page.goto(decision_call["proposal_url"])
    expect(user_page.get_by_text("Accepted", exact=True)).to_be_visible()


def test_submitter_blind_when_privilege_unset(settings, admin_page, user_page, decision_call):
    "Without the privilege, the submitter does not see the decision inline."
    _set_submitter_view_decision(settings, admin_page, decision_call["cid"], False)

    user_page.goto(decision_call["proposal_url"])
    expect(user_page.get_by_text("Accepted", exact=True)).to_have_count(0)
