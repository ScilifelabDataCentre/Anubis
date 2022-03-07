"""Test browser call creation. Requires admin user account.

After installing from PyPi using the 'requirements.txt' file, one must do:
$ playwright install

To run while displaying browser window:
$ pytest --headed

Much of the code below was created using the playwright code generation feature:
$ playwright codegen http://localhost:5002/
"""

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


def login(settings, page):
    "Login to the system."
    page.goto(settings["BASE_URL"])
    page.click("text=Login")
    assert page.url.split("?")[0] == f"{settings['BASE_URL']}/user/login"
    page.click('input[name="username"]')
    page.fill('input[name="username"]', settings["ADMIN_USERNAME"])
    page.press('input[name="username"]', "Tab")
    page.fill('input[name="password"]', settings["ADMIN_PASSWORD"])
    page.click("id=login")
    assert page.url.rstrip("/") == settings["BASE_URL"]


def test_create_call(settings, page):
    "Test login, create, delete a call."
    login(settings, page)

    # Create a call.
    page.goto(settings["BASE_URL"])
    page.click("text=Calls")
    page.click("text=My calls")
    assert page.url == f"http://localhost:5002/calls/owner/{settings['ADMIN_USERNAME']}"
    page.click("text=Create")
    assert page.url == "http://localhost:5002/call/"
    page.click('input[name="identifier"]')
    page.fill('input[name="identifier"]', "TEST")
    page.click('input[name="title"]')
    page.fill('input[name="title"]', "Test call")
    page.click("#create")
    assert page.url == "http://localhost:5002/call/TEST/edit"
    page.click('textarea[name="description"]')
    page.fill('textarea[name="description"]', "This is a test call.")
    page.click("text=Save")
    assert page.url == "http://localhost:5002/call/TEST"

    # Delete the call.
    page.goto(settings["BASE_URL"])
    page.click("text=Calls")
    page.click("text=My calls")
    assert page.url == f"http://localhost:5002/calls/owner/{settings['ADMIN_USERNAME']}"
    page.click("text=TEST")
    assert page.url == "http://localhost:5002/call/TEST"
    page.once("dialog", lambda dialog: dialog.accept())  # Callback for next click.
    page.click("text=Delete")
    assert page.url == f"http://localhost:5002/calls/owner/{settings['ADMIN_USERNAME']}"

    # page.wait_for_timeout(3000)
