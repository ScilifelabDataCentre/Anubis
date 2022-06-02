"""Test browser proposal creation. Requires admin and ordinary user account.

After installing from PyPi using the 'requirements.txt' file, one must do:
$ playwright install

To run while displaying browser window:
$ pytest --headed

Much of the code below was created using the playwright code generation feature:
$ playwright codegen http://localhost:5002/
"""

import datetime
import urllib.parse

import pytest
import playwright.sync_api

import utils


@pytest.fixture(scope="module")
def settings():
    "Get the settings from the file 'settings.json' in this directory."
    result = utils.get_settings(BASE_URL="http://localhost:5002",
                                ADMIN_USERNAME=None,
                                ADMIN_PASSWORD=None,
                                USER_USERNAME=None,
                                USER_PASSWORD=None)
    # Remove any trailing slash.
    result["BASE_URL"] = result["BASE_URL"].rstrip("/")
    return result


def test_create_proposal(settings, page):
    "Test login, create, delete a call, and a proposal in that call."
    utils.login(settings, page, admin=True)

    # Create a call.
    page.goto(settings["BASE_URL"])
    page.click("text=Calls")
    page.click("text=My calls")
    assert page.url == f"{settings['BASE_URL']}/calls/owner/{settings['ADMIN_USERNAME']}"
    page.click("text=Create")
    assert page.url == f"{settings['BASE_URL']}/call/"
    page.click('input[name="identifier"]')
    page.fill('input[name="identifier"]', "TEST")
    page.click('input[name="title"]')
    page.fill('input[name="title"]', "Test call")
    page.click("#create")
    assert page.url == f"{settings['BASE_URL']}/call/TEST/edit"
    page.click('textarea[name="description"]')
    page.fill('textarea[name="description"]', "This is a test call.")
    page.locator("input[name=\"opens\"]").click()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    page.locator("input[name=\"opens\"]").fill(today.isoformat())
    page.locator("input[name=\"closes\"]").click()
    page.locator("input[name=\"closes\"]").fill(tomorrow.isoformat())
    page.click("text=Save")
    assert page.url == f"{settings['BASE_URL']}/call/TEST"

    # Click text=Edit proposal fields
    page.locator("text=Edit proposal fields").click()
    assert page.url == f"{settings['BASE_URL']}/call/TEST/proposal"
    page.locator("button:has-text(\"Add line field\")").click()
    page.locator("text=Add line field × Identifier Required! Identifier for the field. It cannot be cha >> input[name=\"identifier\"]").click()
    page.locator("text=Add line field × Identifier Required! Identifier for the field. It cannot be cha >> input[name=\"identifier\"]").fill("short_description")
    page.locator("text=Add line field × Identifier Required! Identifier for the field. It cannot be cha >> input[name=\"required\"]").check()
    page.locator("[id=\"_lineModal\"] >> text=Save").click()
    assert page.url == f"{settings['BASE_URL']}/call/TEST/proposal"
    page.locator("button:has-text(\"Add text field\")").click()
    page.locator("text=Add text field × Identifier Required! Identifier for the field. It cannot be cha >> input[name=\"identifier\"]").click()
    page.locator("text=Add text field × Identifier Required! Identifier for the field. It cannot be cha >> input[name=\"identifier\"]").fill("long_description")
    page.locator("[id=\"_textModal\"] >> text=Save").click()
    assert page.url == f"{settings['BASE_URL']}/call/TEST/proposal"
    page.locator("text=Back").click()
    assert page.url == f"{settings['BASE_URL']}/call/TEST"

    # Logout from admin user, login as ordinary user.
    utils.logout(settings, page, settings["ADMIN_USERNAME"])
    utils.login(settings, page, admin=False)

    # Create a proposal.
    page.locator("a:has-text(\"Test call\")").click()
    assert page.url == f"{settings['BASE_URL']}/call/TEST"
    page.locator("text=Create proposal").click()
    assert page.url == f"{settings['BASE_URL']}/proposal/TEST:001/edit"
    page.locator("input[name=\"_title\"]").click()
    page.locator("input[name=\"_title\"]").fill("A test proposal")
    page.locator("input[name=\"short_description\"]").click()
    page.locator("input[name=\"short_description\"]").fill("A brief description")
    page.locator("textarea[name=\"long_description\"]").click()
    page.locator("textarea[name=\"long_description\"]").fill("A longer description.")
    page.locator("text=Save").first.click()
    assert page.url == f"{settings['BASE_URL']}/proposal/TEST:001"
    page.locator("button:has-text(\"Submit\")").click()
    assert page.url == f"{settings['BASE_URL']}/proposal/TEST:001"

    # Logout from ordinary user, login as admin user.
    utils.logout(settings, page, settings["USER_USERNAME"])
    utils.login(settings, page, admin=True)

    # Delete the proposal.
    page.locator("a:has-text(\"Test call\")").click()
    assert page.url == f"{settings['BASE_URL']}/call/TEST"
    page.locator("text=1 proposals").click()
    assert page.url == f"{settings['BASE_URL']}/proposals/call/TEST"
    page.locator("text=TEST:001 A test proposal").click()
    assert page.url == f"{settings['BASE_URL']}/proposal/TEST:001"
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("text=Delete").click()
    assert page.url == f"{settings['BASE_URL']}/proposals/call/TEST"

    # page.wait_for_timeout(3000)

    # Delete the call.
    page.goto(settings["BASE_URL"])
    page.click("text=Calls")
    page.click("text=My calls")
    assert page.url == f"{settings['BASE_URL']}/calls/owner/{settings['ADMIN_USERNAME']}"
    page.click("text=TEST")
    assert page.url == f"{settings['BASE_URL']}/call/TEST"
    page.once("dialog", lambda dialog: dialog.accept())  # Callback for next click.
    page.click("text=Delete")
    assert page.url == f"{settings['BASE_URL']}/calls/owner/{settings['ADMIN_USERNAME']}"
