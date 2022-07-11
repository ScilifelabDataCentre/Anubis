"Utility functions for the tests."

import json


def get_settings(**defaults):
    "Update the default settings by the contents of the 'settings.json' file."
    result = defaults.copy()
    with open("settings.json", "rb") as infile:
        data = json.load(infile)
    for key in result:
        try:
            result[key] = data[key]
        except KeyError:
            pass
        if result.get(key) is None:
            raise KeyError(f"Missing {key} value in settings.")
    # Remove any trailing slash in the base URL.
    result["BASE_URL"] = result["BASE_URL"].rstrip("/")
    return result


def login(settings, page, admin=False):
    "Login to the system, admin or ordinary user."
    page.goto(settings["BASE_URL"])
    page.click("text=Login")
    assert page.url.split("?")[0] == f"{settings['BASE_URL']}/user/login"
    page.click('input[name="username"]')
    username = admin and settings["ADMIN_USERNAME"] or settings["USER_USERNAME"]
    page.fill('input[name="username"]', username)
    page.press('input[name="username"]', "Tab")
    password = admin and settings["ADMIN_PASSWORD"] or settings["USER_PASSWORD"]
    page.fill('input[name="password"]', password)
    page.click("id=login")
    assert page.url.rstrip("/") == settings["BASE_URL"]


def logout(settings, page, username):
    "Logout from the current account."
    page.goto(f"{settings['BASE_URL']}/user/display/{username}")
    page.click("text=Logout")
    assert page.url.rstrip("/") == settings["BASE_URL"]
