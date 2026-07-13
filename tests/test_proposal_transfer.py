"""End-to-end tests for proposal ownership transfer (anubis/proposal.py).

Transfer reassigns a proposal to another user; the new owner gains access
and the previous owner loses it. Only admin/staff/call-owner may transfer.
There is no regression net for this today, and ownership change is high impact.
"""

import pytest
from playwright.sync_api import expect
from conftest import _submit_proposal, _delete_proposal


@pytest.fixture
def transferable_proposal(settings, seeded_call, user_page, admin_page):
    "A fresh submitted proposal in the seeded call (mutable, function-scoped). Admin deletes it after."
    url = _submit_proposal(settings, seeded_call, user_page, "Transfer test proposal")
    yield url
    _delete_proposal(admin_page, url)


def test_transfer_changes_owner(settings, admin_page, user_page, user2_page, transferable_proposal):
    "Admin transfers a proposal to testuser2; user2 gains view access, the original owner loses it."
    base = settings["BASE_URL"]
    pid = transferable_proposal.rstrip("/").split("/")[-1]
    purl = f"{base}/proposal/{pid}"

    # Admin performs the transfer to testuser2
    admin_page.goto(f"{purl}/transfer")
    admin_page.locator("#user").fill("testuser2")
    admin_page.get_by_role("button", name="Transfer").click()
    expect(admin_page).to_have_url(purl)

    # New owner can view it
    user2_page.goto(purl)
    expect(user2_page).to_have_url(purl)

    # Original owner can no longer view it (redirected away with a denial)
    user_page.goto(purl)
    expect(user_page).not_to_have_url(purl)
    expect(user_page.get_by_text("not allowed to view this proposal")).to_be_visible()


def test_transfer_denied_for_submitter(settings, user_page, transferable_proposal):
    "The submitter (not owner/staff/admin) cannot transfer their own proposal."
    base = settings["BASE_URL"]
    pid = transferable_proposal.rstrip("/").split("/")[-1]

    user_page.goto(f"{base}/proposal/{pid}/transfer")
    expect(user_page).not_to_have_url(f"{base}/proposal/{pid}/transfer")
    expect(user_page.get_by_text("not allowed to transfer")).to_be_visible()
