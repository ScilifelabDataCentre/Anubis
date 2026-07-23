"""End-to-end tests for reviewer rank validation in anubis/reviews.py.

A reviewer ranks the proposals in a call using a rank review field. The ranks of
a reviewer's finalized reviews must form a consecutive run from 1, otherwise the
review page warns of a rank error (get_rank_error). A broken ranking that slips
through would corrupt the ranking factor the funding decisions build on.

The rank field must be flagged as a banner field for get_rank_error to consider
it, so the fixture sets that. Three proposals are submitted (by testuser, admin,
and testuser2) so the reviewer can produce both a consecutive ranking and one
with a gap. Each test builds its own reviews and relies on proposal deletion
cascading to reviews for cleanup.
"""

import pytest
from playwright.sync_api import expect
from conftest import (
    _cleanup_call_fresh_context,
    _create_call,
    _delete_proposal,
    _open_call_dates,
    _submit_proposal,
)

RANK_CALL_ID = "CI_RANK_CALL"


@pytest.fixture(scope="session")
def rank_call(settings, browser, admin_page):
    "Open call with a banner rank review field (plus the reviewer set up by _create_call)."
    base = settings["BASE_URL"]
    _cleanup_call_fresh_context(browser, settings, RANK_CALL_ID)
    opens, closes = _open_call_dates()
    cid = _create_call(browser, settings, RANK_CALL_ID, opens, closes)

    # Add a rank review field, flagged as banner so get_rank_error considers it.
    admin_page.goto(f"{base}/call/{cid}/review")
    admin_page.get_by_role("button", name="Add rank field").click()
    admin_page.locator("#_rank-identifier").fill("rank")
    admin_page.locator("#_rank-banner").check()
    admin_page.locator("#_rankModal").get_by_role("button", name="Save").click()

    yield cid

    _cleanup_call_fresh_context(browser, settings, RANK_CALL_ID)


@pytest.fixture
def three_proposals(settings, rank_call, user_page, admin_page, user2_page):
    "Three submitted proposals (testuser, admin, testuser2). Deleted (cascading reviews) after each test."
    urls = [
        _submit_proposal(settings, rank_call, user_page, "Proposal"),
        _submit_proposal(settings, rank_call, admin_page, "Proposal"),
        _submit_proposal(settings, rank_call, user2_page, "Proposal"),
    ]
    yield urls
    for url in urls:
        _delete_proposal(admin_page, url)


def _create_reviewer_reviews(admin_page, base, cid, reviewer_username):
    "Admin creates a review for the reviewer on every proposal. Returns the review URLs."
    admin_page.goto(f"{base}/reviews/call/{cid}/reviewer/{reviewer_username}")
    for checkbox in admin_page.get_by_role("checkbox", name="Create").all():
        checkbox.check()
    admin_page.get_by_role("button", name="Create checked reviews").click()
    return [
        base + link.get_attribute("href")
        for link in admin_page.get_by_role("link", name="Review", exact=True).all()
    ]


def _rank_and_finalize(reviewer_page, review_url, rank, score=4):
    "Reviewer fills the conflict field, a score, and the rank, then finalizes the review."
    reviewer_page.goto(review_url)
    reviewer_page.get_by_role("button", name="Edit").click()
    reviewer_page.get_by_text("No", exact=True).click()
    reviewer_page.locator(f'label[for="quality_score_{score}"]').click()
    reviewer_page.locator("#rank").fill(str(rank))
    reviewer_page.get_by_role("button", name="Save").click()
    reviewer_page.get_by_role("button", name="Finalize").click()
    expect(reviewer_page.locator(".badge-success", has_text="Finalized")).to_be_visible()


def test_consecutive_ranks_accepted(settings, rank_call, three_proposals, admin_page, reviewer_page):
    "A reviewer whose finalized ranks are consecutive (1, 2, 3) triggers no rank error."
    base = settings["BASE_URL"]
    reviewer_username = settings["REVIEWER_USERNAME"]

    review_urls = _create_reviewer_reviews(admin_page, base, rank_call, reviewer_username)
    for rank, url in enumerate(review_urls, start=1):
        _rank_and_finalize(reviewer_page, url, rank)

    reviewer_page.goto(review_urls[0])
    expect(reviewer_page.get_by_text("non-consecutive values")).to_have_count(0)
