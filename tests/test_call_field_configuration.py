"""End-to-end tests for call field configuration in anubis/call.py.

Covers the decision and grant field-definition sub-pages
(/call/<cid>/decision and /call/<cid>/grant). These edit the call's
schema, so a regression here corrupts the data structures that
decisions and grants are built from.

Each mutating test adds a uniquely-named field and removes it again in
a finally block, leaving the session-scoped seeded_call as it was found.
"""

from playwright.sync_api import expect


def _add_line_field(page, base, cid, sub, field_id, title):
    "Add a required 'line' field on the given call sub-page (decision or grant)."
    page.goto(f"{base}/call/{cid}/{sub}")
    page.get_by_role("button", name="Add line field").click()
    page.locator("#_lineModal input[name='identifier']").fill(field_id)
    page.locator("#_lineModal input[name='title']").fill(title)
    page.locator("#_lineModal input[name='required']").check()
    page.locator("#_lineModal").get_by_role("button", name="Save").click()
    expect(page).to_have_url(f"{base}/call/{cid}/{sub}")


def _delete_field(page, base, cid, sub, field_id):
    "Delete the field row identified by field_id, accepting the confirm dialog."
    page.goto(f"{base}/call/{cid}/{sub}")
    row = page.locator("tr", has_text=field_id)
    if row.count() == 0:
        return
    page.once("dialog", lambda d: d.accept())
    row.get_by_role("button", name="Delete").click()
    page.wait_for_load_state("load")


def test_decision_field_config(settings, admin_page, seeded_call):
    "Admin adds a required decision field; it renders in the config table; delete removes it."
    base = settings["BASE_URL"]
    cid = seeded_call
    field_id = "ci_decision_note"
    try:
        _add_line_field(admin_page, base, cid, "decision", field_id, "Decision note")
        admin_page.goto(f"{base}/call/{cid}/decision")
        expect(admin_page.locator("tr", has_text=field_id)).to_be_visible()
    finally:
        _delete_field(admin_page, base, cid, "decision", field_id)
    expect(admin_page.locator("tr", has_text=field_id)).to_have_count(0)


def test_grant_field_config(settings, admin_page, seeded_call):
    "Admin adds a required grant field; it renders in the config table; delete removes it."
    base = settings["BASE_URL"]
    cid = seeded_call
    field_id = "ci_grant_budget"
    try:
        _add_line_field(admin_page, base, cid, "grant", field_id, "Grant budget")
        admin_page.goto(f"{base}/call/{cid}/grant")
        expect(admin_page.locator("tr", has_text=field_id)).to_be_visible()
    finally:
        _delete_field(admin_page, base, cid, "grant", field_id)
    expect(admin_page.locator("tr", has_text=field_id)).to_have_count(0)


def test_field_config_pages_admin_only(settings, admin_page, user_page, seeded_call):
    "Admin can load the decision/grant config pages; a non-admin user is denied and redirected away."
    base = settings["BASE_URL"]
    cid = seeded_call
    for sub in ("decision", "grant"):
        target = f"{base}/call/{cid}/{sub}"
        admin_page.goto(target)
        expect(admin_page).to_have_url(target)

        user_page.goto(target)
        expect(user_page).not_to_have_url(target)
