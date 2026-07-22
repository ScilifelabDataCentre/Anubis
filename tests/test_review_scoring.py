"""End-to-end tests for review score aggregation in anubis/proposals.py.

The staff proposals list shows, per proposal, the mean and standard deviation of
the reviewers' scores. These numbers feed funding decisions, so a regression in
the aggregation is the kind that passes every unit test but produces the wrong
ranking in production. Reviews flagged as a conflict of interest must be left out
of the aggregate (covered in the COI test).

Two reviewers are needed for a standard deviation, so the fixture adds the admin
as a second reviewer alongside the shared reviewer user. Each test builds its own
reviews on a fresh proposal and relies on proposal deletion cascading to reviews
for cleanup.
"""

from datetime import datetime, timedelta

import pytest
from playwright.sync_api import expect
from conftest import _create_call, _cleanup_call, _submit_proposal, _delete_proposal

SCORING_CALL_ID = "CI_SCORING_CALL"


@pytest.fixture(scope="session")
def scoring_call(settings, browser, admin_page):
    "Open call with the quality_score review field and two reviewers (revieweruser and admin)."
    base = settings["BASE_URL"]
    admin_username = settings["ADMIN_USERNAME"]

    # Clear any stale call, then build fresh. revieweruser and the required
    # quality_score review field are both set up by _create_call.
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    _cleanup_call(settings, page, SCORING_CALL_ID)
    context.close()

    now = datetime.now()
    opens = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    closes = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    cid = _create_call(browser, settings, SCORING_CALL_ID, opens, closes)

    # Add admin as a second reviewer so a proposal can carry two finalized reviews.
    admin_page.goto(f"{base}/call/{cid}/reviewers")
    admin_page.locator("#reviewer").fill(admin_username)
    admin_page.get_by_role("button", name="Add", exact=True).click()
    expect(admin_page.get_by_role("link", name=admin_username)).to_be_visible()

    # The proposals list only aggregates score fields flagged as banner, so promote
    # quality_score to a banner field via its edit modal.
    admin_page.goto(f"{base}/call/{cid}/review")
    admin_page.locator("tr", has_text="quality_score").get_by_role("button", name="Edit").click()
    modal = admin_page.locator("#quality_score-Modal")
    modal.locator("#quality_score-banner").check()
    modal.get_by_role("button", name="Save").click()

    yield cid

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    _cleanup_call(settings, page, SCORING_CALL_ID)
    context.close()


@pytest.fixture
def fresh_proposal(settings, scoring_call, user_page, admin_page):
    "A submitted proposal in the scoring call. Deleted (cascading its reviews) after each test."
    url = _submit_proposal(settings, scoring_call, user_page, "Proposal")
    yield url
    _delete_proposal(admin_page, url)


def _create_finalize_review(admin_page, filler_page, base, cid, reviewer_username, score, coi):
    """Admin assigns a review to reviewer_username, then filler_page answers the
    conflict-of-interest field, sets the score, and finalizes. filler_page is the
    page logged in as reviewer_username (admin_page when the reviewer is admin).
    Navigation is by direct review URL so it never depends on the "My reviews" list.
    """
    admin_page.goto(f"{base}/reviews/call/{cid}/reviewer/{reviewer_username}")
    admin_page.get_by_role("checkbox", name="Create").check()
    admin_page.get_by_role("button", name="Create checked reviews").click()
    review_url = base + admin_page.get_by_role("link", name="Review", exact=True).get_attribute("href")

    filler_page.goto(review_url)
    filler_page.get_by_role("button", name="Edit").click()
    filler_page.get_by_text("Yes" if coi else "No", exact=True).click()
    filler_page.locator(f'label[for="quality_score_{score}"]').click()
    filler_page.get_by_role("button", name="Save").click()
    filler_page.get_by_role("button", name="Finalize").click()
    expect(filler_page.locator(".badge-success", has_text="Finalized")).to_be_visible()


def test_score_mean_and_stdev(settings, scoring_call, fresh_proposal, admin_page, reviewer_page):
    "Two finalized non-COI reviews produce the score mean and stdev in the proposals list."
    base = settings["BASE_URL"]
    admin_username = settings["ADMIN_USERNAME"]
    reviewer_username = settings["REVIEWER_USERNAME"]

    _create_finalize_review(admin_page, reviewer_page, base, scoring_call, reviewer_username, 4, False)
    _create_finalize_review(admin_page, admin_page, base, scoring_call, admin_username, 2, False)

    admin_page.goto(f"{base}/proposals/call/{scoring_call}")
    row = admin_page.locator("tbody.table-borderless tr")
    expect(row).to_contain_text("3.0")  # mean of 4 and 2
    expect(row).to_contain_text("1.4")  # stdev of 4 and 2
