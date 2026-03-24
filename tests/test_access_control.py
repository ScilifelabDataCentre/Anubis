"""
Testing access control for admin, user, reviewer and non-user.
"""

import pytest

@pytest.fixture(scope="session")
def submitted_proposal(settings, seeded_call, user_page):
    
    base = settings["BASE_URL"]

    user_page.goto(f"{base}/call/{seeded_call}")
    user_page.locator("text=Create proposal").click()

    user_page.locator("#_title").fill("Proposal")
    user_page.locator("#project_title").fill("Proposal Title")
    user_page.locator("text=Save & submit").click()

    yield user_page.url


def test_proposal_access_admin(admin_page, submitted_proposal):

    admin_page.goto(submitted_proposal)
    assert admin_page.url == submitted_proposal


def test_proposal_access_reviewer(reviewer_page, submitted_proposal):
    
    reviewer_page.goto(submitted_proposal)
    assert reviewer_page.url == submitted_proposal


def test_proposal_access_user(user_page, submitted_proposal):
    
    user_page.goto(submitted_proposal)
    assert user_page.url == submitted_proposal

def test_proposal_access_anonymous(settings, browser, submitted_proposal):
    base_url = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    
    page.goto(submitted_proposal)
    assert page.url.startswith(f"{base_url}/user/login")
    context.close()