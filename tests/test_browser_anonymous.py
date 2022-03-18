"""Test browser anonymous access.

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


def test_about(settings, page):  # 'page' fixture from 'pytest-playwright'
    "Test access to 'About' pages."
    page.goto(settings["BASE_URL"])
    page.click("text=About")
    page.click("text=Contact")
    assert page.url == f"{settings['BASE_URL']}/about/contact"

    page.go_back()
    page.click("text=About")
    page.click("text=Personal data policy")
    assert page.url == f"{settings['BASE_URL']}/about/gdpr"

    page.go_back()
    page.click("text=About")
    page.click("text=Software")
    assert page.url == f"{settings['BASE_URL']}/about/software"


def test_calls(settings, page):
    "Test access to calls pages."
    page.goto(settings["BASE_URL"])
    page.click("text=Calls")
    page.click("text=Open calls")
    assert page.url == f"{settings['BASE_URL']}/calls/open"

    page.go_back()
    page.click("text=Calls")
    page.click("text=Closed calls")
    assert page.url == f"{settings['BASE_URL']}/calls/closed"


def test_documentation(settings, page):
    "Test access to documentation pages."
    page.goto(settings["BASE_URL"])
    page.click("text=Documentation")
    page.click("text=Overview")
    assert page.url == f"{settings['BASE_URL']}/documentation/overview"

    page.go_back()
    page.click("text=Documentation")
    page.click("text=URL endpoints")
    assert (
        page.url == f"{settings['BASE_URL']}/documentation/endpoints"
    )

    # page.wait_for_timeout(3000)
