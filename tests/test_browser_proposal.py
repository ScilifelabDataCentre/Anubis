"""Test browser call and proposal creation. Requires admin and ordinary user account.

After installing from PyPi using the 'requirements.txt' file, one must do:
$ playwright install

To run while displaying browser window:
$ pytest --headed

Much of the code below was created using the playwright code generation feature:
$ playwright codegen http://localhost:5002/
"""

import datetime
import json
import urllib.parse

import pytest
import playwright.sync_api


@pytest.fixture(scope="module")
def settings():
    """Get the settings from
    1) defaults
    2) file 'settings.json' in this directory
    """
    result = {"BASE_URL": "http://localhost:5002"}  # Default values

    try:
        with open("settings.json", "rb") as infile:
            result.update(json.load(infile))
    except IOError:
        pass
    for key in ["BASE_URL"]:
        if result.get(key) is None:
            raise KeyError(f"Missing {key} value in settings.")
    # Remove any trailing slash.
    result["BASE_URL"] = result["BASE_URL"].rstrip("/")
    return result


def login_admin(settings, page):
    "Login to the system as admin."
    page.goto(settings["BASE_URL"])
    page.click("text=Login")
    assert page.url.split("?")[0] == f"{settings['BASE_URL']}/user/login"
    page.click('input[name="username"]')
    page.fill('input[name="username"]', settings["ADMIN_USERNAME"])
    page.press('input[name="username"]', "Tab")
    page.fill('input[name="password"]', settings["ADMIN_PASSWORD"])
    page.click("id=login")
    assert page.url.rstrip("/") == settings["BASE_URL"]


def login_user(settings, page):
    "Login to the system as ordinary user."
    page.goto(settings["BASE_URL"])
    page.click("text=Login")
    assert page.url.split("?")[0] == f"{settings['BASE_URL']}/user/login"
    page.click('input[name="username"]')
    page.fill('input[name="username"]', settings["USER_USERNAME"])
    page.press('input[name="username"]', "Tab")
    page.fill('input[name="password"]', settings["USER_PASSWORD"])
    page.click("id=login")
    assert page.url.rstrip("/") == settings["BASE_URL"]


def logout(settings, page, username):
    "Logout from the current account."
    page.goto(f"{settings['BASE_URL']}/user/display/{username}")
    page.click("text=Logout")
    assert page.url.rstrip("/") == settings["BASE_URL"]


def test_create_proposal(settings, page):
    "Test login, create, delete a call, and a proposal in that call."
    login_admin(settings, page)

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
    logout(settings, page, settings["ADMIN_USERNAME"])
    login_user(settings, page)

    # Logout from ordinary user, login as admin user.
    logout(settings, page, settings["USER_USERNAME"])
    login_admin(settings, page)

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

