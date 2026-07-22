"""End-to-end test for the password set flow in anubis/user.py.

Requesting a reset sets a one-time code on the account and emails a
/user/password link carrying it. The user opens that link, sets a new password,
and is logged in. This closes the loop that test_browser_mail only starts (it
asserts the reset email is sent, not that the code actually sets a password).

The one-time code is never shown in the UI, only in the email, so the test reads
it back from Mailpit via the shared helpers in utils.
"""

import re

import pytest
import requests
from playwright.sync_api import expect

import utils

PWSET_USERNAME = "test_pwset_user"
PWSET_EMAIL = "test_pwset_user@test.com"


def _delete_user_if_exists(settings, admin_page, username):
    "Delete the user via its admin display page, tolerating a missing account."
    base = settings["BASE_URL"]
    admin_page.goto(f"{base}/user/display/{username}")
    delete_btn = admin_page.get_by_role("button", name="Delete")
    if delete_btn.is_visible():
        admin_page.once("dialog", lambda d: d.accept())
        delete_btn.click()
        admin_page.wait_for_load_state("load")


@pytest.fixture
def enabled_user(settings, admin_page):
    "Admin registers a fresh enabled user. Yields dict(username, email). Deleted on teardown."
    base = settings["BASE_URL"]
    _delete_user_if_exists(settings, admin_page, PWSET_USERNAME)

    admin_page.goto(base)
    admin_page.get_by_role("button", name="Users", exact=True).click()
    admin_page.get_by_role("link", name="Register user").click()
    admin_page.get_by_role("textbox", name="User name").fill(PWSET_USERNAME)
    admin_page.get_by_role("textbox", name="Email").fill(PWSET_EMAIL)
    admin_page.get_by_role("button", name="Register").click()
    expect(admin_page.get_by_text("Message: User account created")).to_be_visible()

    yield {"username": PWSET_USERNAME, "email": PWSET_EMAIL}

    _delete_user_if_exists(settings, admin_page, PWSET_USERNAME)


def _trigger_reset_get_url(browser, settings, email):
    "Reset from a logged-out context and return the set-password URL from the email."
    base = settings["BASE_URL"]
    # Clear the inbox first so only the reset email is matched.
    requests.delete(f"{utils.MAILPIT_BASE_URL}/api/v1/messages")

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    page.goto(f"{base}/user/reset")
    page.get_by_role("textbox", name="Email").fill(email)
    page.get_by_role("button", name="Reset").click()
    context.close()

    msg = utils.wait_for_email(
        lambda m: email in utils.to_addresses(m) and "password reset" in m["Subject"].lower()
    )
    body = utils.get_message_text(msg)
    match = re.search(r"go to (\S+)", body)
    assert match, f"No set-password URL found in email body: {body!r}"
    return match.group(1)


def test_reset_set_password_and_login(settings, browser, enabled_user):
    "Reset emails a code, the user sets a new password via it, is logged in, and can log in again."
    base = settings["BASE_URL"]
    username = enabled_user["username"]
    new_password = "newpass123"

    url = _trigger_reset_get_url(browser, settings, enabled_user["email"])

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)

    # The emailed link prefills the username and code on the set-password form.
    page.goto(url)
    page.locator("#password").fill(new_password)
    page.get_by_role("button", name="Set password").click()

    # On success the user is sent home, logged in, with a confirmation flash.
    expect(page.get_by_text("Message: Password set.")).to_be_visible()
    expect(page.get_by_role("button", name=username)).to_be_visible()

    # Log out and back in to prove the new password works for a fresh login.
    utils.logout(settings, page, username)
    page.click("text=Login")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', new_password)
    page.click("id=login")
    assert page.url.rstrip("/") == base
    expect(page.get_by_role("button", name=username)).to_be_visible()
    context.close()


def test_password_set_rejects_wrong_code(settings, browser, enabled_user):
    "Setting a password with a wrong one-time code is rejected."
    base = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)

    page.goto(f"{base}/user/password?username={enabled_user['username']}&code=wrongcode")
    page.locator("#password").fill("newpass123")
    page.get_by_role("button", name="Set password").click()

    expect(page.get_by_text("No such user or wrong code.")).to_be_visible()
    context.close()


def test_password_set_rejects_short_password(settings, browser, enabled_user):
    "A password shorter than the minimum length is rejected even with a valid code."
    # The code check precedes the length check, so a real emailed code is needed
    # to reach the length validation.
    url = _trigger_reset_get_url(browser, settings, enabled_user["email"])

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    page.goto(url)
    page.locator("#password").fill("abc")
    page.get_by_role("button", name="Set password").click()

    expect(page.get_by_text("Too short password.")).to_be_visible()
    context.close()
