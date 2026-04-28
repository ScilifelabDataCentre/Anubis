"""End-to-end coverage for the email-sending paths in Anubis.

Mailpit (http://localhost:8025 by default) is the SMTP sink. Each test wipes
the Mailpit inbox in `pretest_mailpit_cleanup`, then asserts on the message(s)
that arrive. Override `MAILPIT_BASE_URL` via env var when running against a
different mail catcher.
"""

import os
import time

import pytest
import requests
from playwright.sync_api import expect

MAILPIT_BASE_URL = os.environ.get("MAILPIT_BASE_URL", "http://localhost:8025").rstrip("/")


@pytest.fixture(autouse=True)
def pretest_mailpit_cleanup():
    "Empty the Mailpit inbox so each test only sees mail it produced."
    requests.delete(f"{MAILPIT_BASE_URL}/api/v1/messages")


def wait_for_email(predicate, timeout=5.0):
    "Poll Mailpit until a message satisfies predicate(msg), else fail the test."
    deadline = time.time() + timeout
    while time.time() < deadline:
        messages = requests.get(f"{MAILPIT_BASE_URL}/api/v1/messages").json()["messages"]
        for msg in messages:
            if predicate(msg):
                return msg
        time.sleep(0.1)
    pytest.fail(f"No matching email arrived within {timeout}s")


def to_addresses(msg):
    "Return the list of recipient addresses on a Mailpit message summary."
    return [r["Address"] for r in msg.get("To", [])]


@pytest.fixture
def user_cleanup(settings, admin_page):
    "Track usernames to delete at end of test. Tests append usernames they register."
    created = []
    yield created
    for username in created:
        _cleanup_user(settings, admin_page, username)


def _cleanup_user(settings, page, username):
    base = settings["BASE_URL"]
    page.goto(f"{base}/user/display/{username}")
    delete_btn = page.get_by_role("button", name="Delete")
    if delete_btn.is_visible():
        page.once("dialog", lambda d: d.accept())
        delete_btn.click()


def _public_register(browser, base, username, email):
    "Submit the public registration form from a fresh logged-out browser context."
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    page.goto(f"{base}/user/register")
    page.get_by_role("textbox", name="User name").fill(username)
    page.get_by_role("textbox", name="Email").fill(email)
    page.get_by_role("button", name="Register").click()
    context.close()


def test_user_registration_email(settings, admin_page, user_cleanup):
    "Admin registers a whitelisted user and a 'registered' email is sent to that user."
    base = settings["BASE_URL"]
    unique = str(int(time.time()))
    username = f"test_{unique}"
    email = f"test_{unique}@test.com"
    user_cleanup.append(username)

    admin_page.goto(base)
    admin_page.get_by_role("button", name="Users", exact=True).click()
    admin_page.get_by_role("link", name="Register user").click()
    admin_page.get_by_role("textbox", name="User name").fill(username)
    admin_page.get_by_role("textbox", name="Email").fill(email)
    admin_page.get_by_role("button", name="Register").click()
    expect(admin_page.get_by_text("Message: User account created")).to_be_visible()

    msg = wait_for_email(lambda m: email in to_addresses(m) and "registered" in m["Subject"].lower())
    assert email in to_addresses(msg)


def test_pending_registration_notifies_admins(settings, browser, user_cleanup):
    "Public self-registration creates a pending account and emails the admins."
    base = settings["BASE_URL"]
    unique = str(int(time.time()))
    username = f"pending_{unique}"
    email = f"pending_{unique}@test.com"
    user_cleanup.append(username)

    _public_register(browser, base, username, email)

    msg = wait_for_email(lambda m: "pending" in m["Subject"].lower())
    # The admin user is seeded in docker-compose as admin@test.com.
    assert "admin@test.com" in to_addresses(msg)


def test_admin_enable_sends_email_to_user(settings, browser, admin_page, user_cleanup):
    "Admin enabling a pending user account sends an 'enabled' email to the user."
    base = settings["BASE_URL"]
    unique = str(int(time.time()))
    username = f"toenable_{unique}"
    email = f"toenable_{unique}@test.com"
    user_cleanup.append(username)

    _public_register(browser, base, username, email)
    # Wait for the admin-notification mail so we know registration completed and then clear the inbox to isolate the enable email.
    wait_for_email(lambda m: "pending" in m["Subject"].lower())
    requests.delete(f"{MAILPIT_BASE_URL}/api/v1/messages")

    admin_page.goto(f"{base}/user/display/{username}")
    admin_page.get_by_role("button", name="Enable").click()

    msg = wait_for_email(
        lambda m: email in to_addresses(m) and "enabled" in m["Subject"].lower()
    )
    assert email in to_addresses(msg)


def test_password_reset_email(settings, browser, admin_page, user_cleanup):
    "Requesting a password reset for an enabled account emails the reset link."
    base = settings["BASE_URL"]
    unique = str(int(time.time()))
    username = f"reset_{unique}"
    email = f"reset_{unique}@test.com"
    user_cleanup.append(username)

    # Admin creates an enabled user so the reset endpoint can find them
    admin_page.goto(base)
    admin_page.get_by_role("button", name="Users", exact=True).click()
    admin_page.get_by_role("link", name="Register user").click()
    admin_page.get_by_role("textbox", name="User name").fill(username)
    admin_page.get_by_role("textbox", name="Email").fill(email)
    admin_page.get_by_role("button", name="Register").click()
    expect(admin_page.get_by_text("Message: User account created")).to_be_visible()
    requests.delete(f"{MAILPIT_BASE_URL}/api/v1/messages")

    # Reset is triggered from a logged-out context.
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    page.goto(f"{base}/user/reset")
    page.get_by_role("textbox", name="Email").fill(email)
    page.get_by_role("button", name="Reset").click()
    context.close()

    msg = wait_for_email(
        lambda m: email in to_addresses(m) and "password reset" in m["Subject"].lower()
    )
    assert email in to_addresses(msg)


def test_proposal_submission_email(settings, admin_page, seeded_call):
    """Submitting a proposal sends a confirmation email to the proposal owner.

    Uses admin_page rather than user_page because test_access_control.submitted_proposal
    is a session-scoped fixture that may have already created a testuser proposal in
    seeded_call (and is marked read-only). admin@test.com works as the recipient and
    admin has no pre-existing proposal in seeded_call.
    """
    base = settings["BASE_URL"]
    call_id = seeded_call

    admin_page.goto(f"{base}/call/{call_id}")
    admin_page.get_by_role("button", name="Create proposal").click()
    admin_page.get_by_role("textbox", name="Title", exact=True).fill("Mail test proposal")
    # seeded_call adds a required line field named project_title.
    admin_page.locator('input[name="project_title"]').fill("first line")
    admin_page.get_by_role("button", name="Save", exact=True).click()
    admin_page.get_by_role("button", name="Submit").click()
    expect(admin_page.locator(".alert-info", has_text="Proposal was submitted.")).to_be_visible()
    proposal_url = admin_page.url

    msg = wait_for_email(
        lambda m: "admin@test.com" in to_addresses(m) and "submitted" in m["Subject"].lower()
    )
    assert call_id in msg["Subject"]

    # Cleanup, deletes the proposal we just submitted so the seeded_call teardown can drop the call cleanly
    admin_page.goto(proposal_url)
    admin_page.once("dialog", lambda d: d.accept())
    admin_page.get_by_role("button", name="Delete").click()
