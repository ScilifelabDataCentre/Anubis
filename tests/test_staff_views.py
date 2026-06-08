"""End-to-end tests for staff/admin-gated list views in calls.py and user.py.

These routes guard data that should only be visible to staff or admins (lists
of unpublished calls, per-call reviews/grants summaries, pending and staff user
lists). The tests verify the auth gate on each: admin lands on the target URL,
non-admin user gets redirected away etc.
"""

from playwright.sync_api import expect


def test_calls_unpublished_staff_only(settings, admin_page, user_page):
    "Admin can load /calls/unpublished, non-admin user is redirected away."
    base = settings["BASE_URL"]
    target = f"{base}/calls/unpublished"

    admin_page.goto(target)
    expect(admin_page).to_have_url(target)

    user_page.goto(target)
    expect(user_page).not_to_have_url(target)


def test_calls_reviews_overview_staff_only(settings, admin_page, user_page):
    "Admin can load /calls/reviews, non-admin user is redirected away."
    base = settings["BASE_URL"]
    target = f"{base}/calls/reviews"

    admin_page.goto(target)
    expect(admin_page).to_have_url(target)

    user_page.goto(target)
    expect(user_page).not_to_have_url(target)


def test_calls_grants_overview_staff_only(settings, admin_page, user_page):
    "Admin can load /calls/grants. Non-admin user is redirected away."
    base = settings["BASE_URL"]
    target = f"{base}/calls/grants"

    admin_page.goto(target)
    expect(admin_page).to_have_url(target)

    user_page.goto(target)
    expect(user_page).not_to_have_url(target)


def test_user_pending_list_admin_only(settings, admin_page, user_page):
    "Admin can load /user/pending. Non-admin user is redirected away."
    base = settings["BASE_URL"]
    target = f"{base}/user/pending"

    admin_page.goto(target)
    expect(admin_page).to_have_url(target)

    user_page.goto(target)
    expect(user_page).not_to_have_url(target)


def test_user_staff_list_admin_only(settings, admin_page, user_page):
    "Admin can load /user/staff. Non-admin user is redirected away."
    base = settings["BASE_URL"]
    target = f"{base}/user/staff"

    admin_page.goto(target)
    expect(admin_page).to_have_url(target)

    user_page.goto(target)
    expect(user_page).not_to_have_url(target)
