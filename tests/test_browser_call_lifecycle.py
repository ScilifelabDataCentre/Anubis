from datetime import datetime, timedelta
import pytest
import utils
from conftest import CALL_ID



@pytest.fixture(autouse=True)
def pre_test_cleanup(settings, browser):
    """Delete any leftover test data before the test runs."""
    context = browser.new_context()
    page = context.new_page()
    _cleanup_leftovers(settings, page, CALL_ID)
    context.close()
    yield


def _cleanup_leftovers(settings, page, call_id):
    """Delete leftover test artifacts, tolerating missing items."""
    base = settings["BASE_URL"]
    utils.login(settings, page, "admin")

    # Grant: unlock if locked, then delete
    page.goto(f"{base}/grant/{call_id}:G:001")
    if page.url.startswith(f"{base}/grant/"):
        if page.get_by_role("button", name="Unlock").is_visible():
            page.get_by_role("button", name="Unlock").click()
            page.wait_for_load_state("load")
        delete_btn = page.get_by_role("button", name="Delete")
        if delete_btn.is_visible():
            page.once("dialog", lambda dialog: dialog.accept())
            delete_btn.click()

    # Proposal
    page.goto(f"{base}/proposals/call/{call_id}")
    proposals_links = [link.get_attribute("href") for link in page.locator("a[title='Proposal']").all()]
    for prop_link in proposals_links:
        page.goto(base + prop_link)
        page.once("dialog", lambda d: d.accept())
        page.get_by_role("button", name="Delete").click()
        page.wait_for_load_state("load")

    # Call
    page.goto(f"{base}/call/{call_id}")
    if page.url.startswith(f"{base}/call/"):
        delete_btn = page.get_by_role("button", name="Delete")
        if delete_btn.is_visible():
            page.once("dialog", lambda dialog: dialog.accept())
            delete_btn.click()



def test_call_lifecycle(settings, page):
    """
    Test the full lifecycle of a call: create call -> add review fields ->
    add reviewer -> set dates to open -> create and submit proposal ->
    create and finalize review -> create and finalize decision ->
    create grant -> lock grant -> cleanup
    """
    call_id = CALL_ID
    proposal_title = "CI Lifecycle test proposal"

    create_call_with_review_fields(settings, page, call_id)
    add_reviewer(settings, page, call_id)
    set_call_dates_to_open(settings, page, call_id)
    create_and_submit_proposal(settings, page, call_id, proposal_title)
    fill_and_finalize_review(settings, page, call_id)
    create_and_finalize_decision(settings, page, call_id)
    create_grant(settings, page, call_id)
    lock_grant(settings, page, call_id)
    cleanup(settings, page, call_id)


def create_call_with_review_fields(settings, page, call_id):
    """Admin creates a call and adds a score review field."""
    utils.login(settings, page, "admin")

    # Create the call
    page.get_by_role("button", name="Calls", exact=True).click()
    page.get_by_role("link", name="Create a new call").click()
    page.click('input[name="identifier"]')
    page.fill('input[name="identifier"]', call_id)
    page.click('input[name="title"]')
    page.fill('input[name="title"]', "Lifecycle test call")
    page.click("#create")
    assert page.url == f"{settings['BASE_URL']}/call/{call_id}/edit"
    page.get_by_role("button", name="Save").click()
    assert page.url == f"{settings['BASE_URL']}/call/{call_id}"

    # Add a score review field
    page.get_by_role("button", name="Edit review fields").click()
    assert page.url == f"{settings['BASE_URL']}/call/{call_id}/review"
    page.get_by_role("button", name="Add score field").click()
    page.locator("#_score-identifier").fill("quality_score")
    page.locator("#_score-title").fill("Scientific quality")
    page.locator("#_score-required").check()
    page.get_by_role("button", name="Save").click()
    assert page.locator("text=quality_score").is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def add_reviewer(settings, page, call_id):
    """Admin adds the reviewer to the call."""
    utils.login(settings, page, "admin")

    page.goto(f"{settings['BASE_URL']}/call/{call_id}/reviewers")
    page.locator("#reviewer").fill(settings["REVIEWER_USERNAME"])
    page.get_by_role("button", name="Add", exact=True).click()
    assert page.get_by_role("link", name=settings["REVIEWER_USERNAME"]).is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def set_call_dates_to_open(settings, page, call_id):
    """Admin sets the call open/close dates so the call is open."""
    utils.login(settings, page, "admin")

    now = datetime.now()
    opens = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    closes = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")

    page.goto(f"{settings['BASE_URL']}/call/{call_id}/edit")
    page.get_by_role("textbox", name="Labels Opens").fill(opens)
    page.get_by_role("textbox", name="Closes").fill(closes)
    page.get_by_role("button", name="Save").click()
    assert page.url == f"{settings['BASE_URL']}/call/{call_id}"
    assert page.locator(".badge-success", has_text="Open.").is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def create_and_submit_proposal(settings, page, call_id, proposal_title):
    """User creates and submits a proposal."""
    utils.login(settings, page, "user")

    page.goto(f"{settings['BASE_URL']}/call/{call_id}")
    page.get_by_role("button", name="Create proposal").click()
    # Now on the proposal edit page
    page.get_by_role("textbox", name="Title").fill(proposal_title)
    page.get_by_role("button", name="Save", exact=True).click()
    page.get_by_role("button", name="Submit").click()
    assert page.locator(".alert-info", has_text="Proposal was submitted.").is_visible()

    utils.logout(settings, page, settings["USER_USERNAME"])


def fill_and_finalize_review(settings, page, call_id):
    """Admin creates a review assignment, then reviewer fills and finalizes it."""
    
    
    # Admin creates the review assignment
    utils.login(settings, page, "admin")

    page.goto(f"{settings['BASE_URL']}/reviews/call/{call_id}/reviewer/{settings['REVIEWER_USERNAME']}")
    page.get_by_role("checkbox", name="Create").check()
    page.get_by_role("button", name="Create checked reviews").click()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])

    # Reviewer fills and finalizes the review
    utils.login(settings, page, "reviewer")

    page.get_by_role("link", name="My reviews").click()
    page.get_by_role("link", name="Review", exact=True).click()
    page.get_by_role("button", name="Edit").click()
    page.get_by_text("No", exact=True).click()
    page.get_by_text("4").first.click()
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Finalize").click()
    assert page.locator(".badge-success", has_text="Finalized").is_visible()

    utils.logout(settings, page, settings["REVIEWER_USERNAME"])


def create_and_finalize_decision(settings, page, call_id):
    """Admin creates a decision, sets verdict to accepted, and finalizes."""
    utils.login(settings, page, "admin")

    page.goto(f"{settings['BASE_URL']}/proposal/{call_id}:001")
    page.get_by_role("button", name="Create decision").click()
    # Now on the decision page: editing it
    page.get_by_role("button", name="Edit").click()
    page.get_by_text("Accepted").click()
    page.get_by_role("button", name="Save").click()
    page.get_by_role("button", name="Finalize").click()
    assert page.locator(".badge-success", has_text="Finalized").is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def create_grant(settings, page, call_id):
    """Admin creates a grant dossier from the accepted proposal."""
    utils.login(settings, page, "admin")

    page.goto(f"{settings['BASE_URL']}/proposal/{call_id}:001")
    page.get_by_role("button", name="Create grant dossier").click()
    assert page.locator("text=Grant dossier").is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def lock_grant(settings, page, call_id):
    """Admin locks the grant dossier."""
    utils.login(settings, page, "admin")

    page.goto(f"{settings['BASE_URL']}/grant/{call_id}:G:001")
    page.get_by_role("button", name="Lock").click()
    assert page.locator("text=Locked").is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def cleanup(settings, page, call_id):
    "Admin deletes everything created during the test (in reverse order)."
    utils.login(settings, page, "admin")

    # Unlock and delete the grant
    page.goto(f"{settings['BASE_URL']}/grant/{call_id}:G:001")
    page.get_by_role("button", name="Unlock").click()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete").click()

    # Unfinalize and delete the decision
    page.goto(f"{settings['BASE_URL']}/proposal/{call_id}:001")
    page.get_by_role("button", name="Accepted").click()
    page.get_by_role("button", name="Unfinalize").click()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete").click()

    # Unfinalize and delete the review
    page.goto(f"{settings['BASE_URL']}/reviews/call/{call_id}")
    page.get_by_role("link", name="Review", exact=True).click()
    page.get_by_role("button", name="Unfinalize").click()
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete").click()

    # Delete the proposal
    page.goto(f"{settings['BASE_URL']}/proposal/{call_id}:001")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete").click()

    # Delete the call
    page.goto(f"{settings['BASE_URL']}/call/{call_id}")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Delete").click()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])
