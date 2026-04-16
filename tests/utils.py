"Utility functions for the tests."

import json
import os
from typing import Literal
import requests
import re

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
    # Allow BASE_URL to be overridden by environment variable
    if os.environ.get("BASE_URL"):
        result["BASE_URL"] = os.environ.get("BASE_URL")
    # Remove any trailing slash in the base URL.
    result["BASE_URL"] = result["BASE_URL"].rstrip("/")
    return result


def login(settings, page, role: Literal["admin", "user", "reviewer"]):
    "Login to the system, admin or ordinary user."
    credentials = {
        "admin": ("ADMIN_USERNAME", "ADMIN_PASSWORD"),
        "user": ("USER_USERNAME", "USER_PASSWORD"),
        "reviewer": ("REVIEWER_USERNAME", "REVIEWER_PASSWORD")
    }
    if role not in credentials:
        raise ValueError(f"Invalid role: {role!r}. Must be one of {list(credentials)}")

    page.goto(settings["BASE_URL"])
    page.click("text=Login")
    assert page.url.split("?")[0] == f"{settings['BASE_URL']}/user/login"
    page.click('input[name="username"]')
    username = settings[credentials[role][0]]
    page.fill('input[name="username"]', username)
    page.press('input[name="username"]', "Tab")
    password = settings[credentials[role][1]]
    page.fill('input[name="password"]', password)
    page.click("id=login")
    assert page.url.rstrip("/") == settings["BASE_URL"]


def logout(settings, page, username):
    "Logout from the current account."
    page.goto(f"{settings['BASE_URL']}/user/display/{username}")
    page.click("text=Logout")
    assert page.url.rstrip("/") == settings["BASE_URL"]


def get_admin_session(settings):
    "Returns an authenticated requests.Session for admin."
    base = settings["BASE_URL"]
    s = requests.Session()
    resp = s.get(f"{base}/user/login")
    pattern = 'name="_csrf_token" value="([^"]+)'
    csrf_token = re.search(pattern, resp.text).group(1)

    s.post(f"{base}/user/login", data={
        "username": settings["ADMIN_USERNAME"],
        "password": settings["ADMIN_PASSWORD"],
        "_csrf_token": csrf_token
    })

    return s