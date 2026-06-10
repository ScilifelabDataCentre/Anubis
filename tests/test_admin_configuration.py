"""End-to-end tests for admin configuration endpoints in anubis/admin.py."""

from playwright.sync_api import expect


def test_site_configuration_edit(settings, admin_page):
    "Admin changes site name, change renders on home. Original name restored after."
    base = settings["BASE_URL"]
    new_name = "Site under e2e test"

    admin_page.goto(f"{base}/admin/site_configuration")
    original_name = admin_page.locator('input[name="name"]').input_value()

    try:
        admin_page.locator('input[name="name"]').fill(new_name)
        admin_page.get_by_role("button", name="Save").click()
        expect(admin_page).to_have_url(f"{base}/admin/site_configuration")

        # Site name renders as the home page <h1>
        admin_page.goto(base)
        expect(admin_page.locator("h1", has_text=new_name)).to_be_visible()
    finally:
        # Restore original name regardless of test outcome
        admin_page.goto(f"{base}/admin/site_configuration")
        admin_page.locator('input[name="name"]').fill(original_name)
        admin_page.get_by_role("button", name="Save").click()


def test_database_view_admin_only(settings, admin_page, user_page):
    "Admin can load /admin/database, non-admin user is redirected away."
    base = settings["BASE_URL"]
    target = f"{base}/admin/database"

    admin_page.goto(target)
    expect(admin_page).to_have_url(target)

    user_page.goto(target)
    expect(user_page).not_to_have_url(target)


def test_settings_view_admin_only(settings, admin_page, user_page):
    "Admin can load /admin/settings, non-admin user is redirected away."
    base = settings["BASE_URL"]
    target = f"{base}/admin/settings"

    admin_page.goto(target)
    expect(admin_page).to_have_url(target)

    user_page.goto(target)
    expect(user_page).not_to_have_url(target)
