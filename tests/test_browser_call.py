"""Test browser call creation. Requires admin user account.

After installing from PyPi using the 'requirements.txt' file, one must do:
$ playwright install

To run while displaying browser window:
$ pytest --headed

Much of the code below was created using the playwright code generation feature:
$ playwright codegen http://localhost:5002/
"""

import urllib.parse

import pytest
import playwright.sync_api

import utils


@pytest.fixture(scope="module")
def settings():
    "Get the settings from the file 'settings.json' in this directory."
    result = utils.get_settings(BASE_URL="http://localhost:5002",
                                ADMIN_USERNAME=None,
                                ADMIN_PASSWORD=None)
    # Remove any trailing slash.
    result["BASE_URL"] = result["BASE_URL"].rstrip("/")
    return result


def test_create_call(settings, page):
    "Test login, create, delete a call."
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
    page.click("text=Save")
    assert page.url == f"{settings['BASE_URL']}/call/TEST"

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

    # page.wait_for_timeout(3000)
