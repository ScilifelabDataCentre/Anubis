import utils
import pytest
from conftest import _create_call, _cleanup_call, SEEDED_TRANSITION_CALL_ID
from datetime import datetime, timedelta


@pytest.fixture(scope="session")
def transition_call(settings, browser, pre_session_cleanup):
    "Open call used exclusively by state transition tests. Cleaned up after the session ends."
    call_id = SEEDED_TRANSITION_CALL_ID
    now = datetime.now()
    opens = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    closes = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    
    yield _create_call(browser, settings, call_id, opens, closes)

    td_context = browser.new_context()
    td_page = td_context.new_page()
    _cleanup_call(settings, td_page, call_id)
    td_context.close()

@pytest.fixture(autouse=True)
def pre_test_cleanup(settings, browser, transition_call):
    "Delete any stale proposal and review for transition_call before each test."
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "admin")

    base = settings["BASE_URL"]
    page.goto(f"{base}/proposals/call/{transition_call}")
    proposal_links = [link.get_attribute("href") for link in page.locator("a[title='Proposal']").all()]
    for prop_link in proposal_links:
        page.goto(base+prop_link)
        page.once("dialog", lambda d: d.accept())
        page.get_by_role("button", name="Delete").click()
        page.wait_for_load_state("load")

    utils.logout(settings, page, settings["ADMIN_USERNAME"])
    context.close()
    yield


@pytest.fixture(scope="function")
def review_assignment(settings, browser, transition_call):
    "Submit a proposal as testuser and create a review assignment via admin. Yields the review URL. Cleaned up after each test."
    base = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)

    # Submit proposal as testuser
    utils.login(settings, page, "user")
    page.goto(f"{base}/call/{transition_call}")
    page.locator("text=Create proposal").click()
    page.locator("#_title").fill("Proposal")
    page.locator("#project_title").fill("Proposal Title")
    page.locator("text=Save & submit").click()

    # Create review assignment as admin
    utils.logout(settings, page, settings["USER_USERNAME"])
    context.close()
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "admin")
    page.goto(f"{base}/reviews/call/{transition_call}/reviewer/{settings['REVIEWER_USERNAME']}")
    page.locator("text=Create every review").click()
    review_url = base + page.get_by_role("link", name="Review", exact=True).get_attribute("href")

    yield review_url

    # Teardown: delete review
    page.goto(review_url)
    page.wait_for_load_state("load")
    delete_btn = page.get_by_role("button", name="Delete")
    if delete_btn.is_visible():
        page.once("dialog", lambda d: d.accept())
        delete_btn.click()
        page.wait_for_load_state("load")

    context.close()


def test_missing_required_proposal_fields(settings, transition_call, browser):
    base = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "user")

    page.goto(f"{base}/call/{transition_call}")
    page.get_by_role("button", name="Create proposal").click()
    page.get_by_role("button", name="Save & submit").click()

    assert page.url == f"{base}/proposal/{transition_call}:001"
    assert page.get_by_text("Submit cannot be done; proposal is incomplete, or call is closed.").is_visible()
    assert page.get_by_text("Missing value.").is_visible()
    assert page.get_by_text("A proposal that contains errors cannot be submitted.").is_visible()

    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Delete").click()
    page.wait_for_load_state("load")
    context.close()


def test_missing_review_fields(settings, browser, review_assignment):
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "reviewer")
    page.goto(review_assignment)
    assert not page.locator("button").filter(has_text="Finalize").is_visible()
    assert page.get_by_text("Missing value.").first.is_visible()
    assert page.get_by_text("Not finalized").is_visible()

    context.close()


def test_create_grant_without_finalized_decision(settings, browser, transition_call):
    base = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)

    utils.login(settings, page, "user")
    page.goto(f"{base}/call/{transition_call}")
    page.locator("text=Create proposal").click()
    page.locator("#_title").fill("Proposal")
    page.locator("#project_title").fill("Proposal Title")
    page.locator("text=Save & submit").click()
    proposal_url = page.url

    utils.logout(settings, page, settings["USER_USERNAME"])
    context.close()

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "admin")
    page.goto(proposal_url)
    page.wait_for_load_state("load")
    assert not page.locator("button").filter(has_text="Create grant dossier").is_visible()

    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Delete").click()
    page.wait_for_load_state("load")
    context.close()


def test_deletion_of_call_with_proposals(settings, browser, transition_call):

    base = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)

    utils.login(settings, page, "user")

    page.goto(f"{base}/call/{transition_call}")
    page.locator("text=Create proposal").click()
    page.locator("#_title").fill("Proposal")
    page.locator("#project_title").fill("Proposal Title")
    page.locator("text=Save & submit").click()

    utils.logout(settings, page, settings["USER_USERNAME"])
    context.close()

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    utils.login(settings, page, "admin")

    page.goto(f"{base}/call/{transition_call}")
    assert not page.get_by_role("button", name="Delete").is_visible()