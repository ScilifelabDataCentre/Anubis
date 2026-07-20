"""End-to-end tests for archiving/unarchiving finalized reviews (anubis/review.py).

Archiving a finalized review removes it from the active reviews and moves it to
the call's archived list (so it no longer counts toward ranking). Unarchiving
restores it. Only an admin may archive/unarchive a finalized review.

The review is created for the admin user (added as a reviewer) rather than the
shared reviewer, so navigation never depends on the reviewer's "My reviews" list.
Uses a dedicated call (a user may hold only one proposal per call).
"""

import pytest
from playwright.sync_api import expect
from conftest import (
    _cleanup_call_fresh_context,
    _create_call,
    _open_call_dates,
    _submit_proposal,
)

ARCHIVE_CALL_ID = "CI_REVIEW_ARCHIVE_CALL"


@pytest.fixture(scope="session")
def finalized_review(settings, browser, admin_page, user_page):
    "Dedicated call with a submitted proposal and one finalized review by the admin."
    base = settings["BASE_URL"]
    admin_username = settings["ADMIN_USERNAME"]

    # Clear any call left behind by a prior failed run, then build fresh.
    _cleanup_call_fresh_context(browser, settings, ARCHIVE_CALL_ID)
    opens, closes = _open_call_dates()
    cid = _create_call(browser, settings, ARCHIVE_CALL_ID, opens, closes)

    # Add admin as a reviewer so the review is created and finalized without
    # touching the shared reviewer's "My reviews" navigation.
    admin_page.goto(f"{base}/call/{cid}/reviewers")
    admin_page.locator("#reviewer").fill(admin_username)
    admin_page.get_by_role("button", name="Add", exact=True).click()
    expect(admin_page.get_by_role("link", name=admin_username)).to_be_visible()

    # Title must be exactly "Proposal" so _cleanup_call's a[title='Proposal'] finds it.
    _submit_proposal(settings, cid, user_page, "Proposal")

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

    yield {"cid": cid, "review_url": review_url}

    # Teardown
    _cleanup_call_fresh_context(browser, settings, ARCHIVE_CALL_ID)


def test_archive_unarchive_round_trip(settings, admin_page, finalized_review):
    "Admin archives a finalized review then unarchives it. The review page reflects each state."
    review_url = finalized_review["review_url"]
    # exact=True matters: name="Archive" would otherwise substring-match "Unarchive".
    archive_btn = admin_page.get_by_role("button", name="Archive", exact=True)
    unarchive_btn = admin_page.get_by_role("button", name="Unarchive", exact=True)

    # Starts active: only the Archive control is shown.
    admin_page.goto(review_url)
    expect(archive_btn).to_be_visible()
    expect(unarchive_btn).to_have_count(0)

    # Archive it (confirm dialog) -> the review reloads showing Unarchive.
    admin_page.once("dialog", lambda d: d.accept())
    archive_btn.click()
    expect(unarchive_btn).to_be_visible()
    expect(archive_btn).to_have_count(0)

    # Unarchive restores the active state.
    unarchive_btn.click()
    expect(archive_btn).to_be_visible()
    expect(unarchive_btn).to_have_count(0)


def test_archive_denied_for_submitter(settings, user_page, finalized_review):
    "The proposal submitter cannot view the review, so the archive control is unreachable."
    user_page.goto(finalized_review["review_url"])
    expect(user_page).not_to_have_url(finalized_review["review_url"])
