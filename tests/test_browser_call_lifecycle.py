from datetime import datetime, timedelta
import pytest
import utils



@pytest.fixture(scope="module")
def settings():
    "Get the settings from the file 'settings.json' in this directory."
    result = utils.get_settings(
        BASE_URL="http://localhost:5002",
        ADMIN_USERNAME=None,
        ADMIN_PASSWORD=None,
        USER_USERNAME=None,
        USER_PASSWORD=None,
        REVIEWER_USERNAME=None,
        REVIEWER_PASSWORD=None,
    )
    return result


def test_call_lifecycle(settings, page):
    """
    Test the full lifecycle of a call: create call -> add review fields ->
    add reviewer -> set dates to open -> create and submit proposal ->
    create and finalize review -> create and finalize decision ->
    create grant -> lock grant -> cleanup
    """
    call_id = "CI_LIFECYCLE_TEST"
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
    utils.login(settings, page, admin=True)

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
    utils.login(settings, page, admin=True)

    page.goto(f"{settings['BASE_URL']}/call/{call_id}/reviewers")
    page.locator("#reviewer").fill(settings["REVIEWER_USERNAME"])
    page.get_by_role("button", name="Add", exact=True).click()
    assert page.locator(f"text={settings['REVIEWER_USERNAME']}").is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def set_call_dates_to_open(settings, page, call_id):
    """Admin sets the call open/close dates so the call is open."""
    utils.login(settings, page, admin=True)

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
    utils.login(settings, page, admin=False)

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
    utils.login(settings, page, admin=True)

    page.goto(f"{settings['BASE_URL']}/reviews/call/{call_id}/reviewer/{settings['REVIEWER_USERNAME']}")
    page.get_by_role("checkbox", name="Create").check()
    page.get_by_role("button", name="Create checked reviews").click()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])

    # Reviewer fills and finalizes the review
    page.goto(settings["BASE_URL"])
    page.click("text=Login")
    page.click('input[name="username"]')
    page.fill('input[name="username"]', settings["REVIEWER_USERNAME"])
    page.press('input[name="username"]', "Tab")
    page.fill('input[name="password"]', settings["REVIEWER_PASSWORD"])
    page.click("id=login")

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
    utils.login(settings, page, admin=True)

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
    utils.login(settings, page, admin=True)

    page.goto(f"{settings['BASE_URL']}/proposal/{call_id}:001")
    page.get_by_role("button", name="Create grant dossier").click()
    assert page.locator("text=Grant dossier").is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def lock_grant(settings, page, call_id):
    """Admin locks the grant dossier."""
    utils.login(settings, page, admin=True)

    page.goto(f"{settings['BASE_URL']}/grant/{call_id}:G:001")
    page.get_by_role("button", name="Lock").click()
    assert page.locator("text=Locked").is_visible()

    utils.logout(settings, page, settings["ADMIN_USERNAME"])


def cleanup(settings, page, call_id):
    "Admin deletes everything created during the test (in reverse order)."
    utils.login(settings, page, admin=True)

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
