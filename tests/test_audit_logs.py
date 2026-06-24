"""
End-to-end tests for the audit-log views.

Every major category (call, proposal, review, grant, user) exposes a /logs page
that renders its change history. Each test loads the page against the fully
populated call and asserts the heading, the log table, and (for the entities
that the fixture demonstrably edited) at least one log row.
"""

from playwright.sync_api import expect


def _assert_logs_render(page, base, url, heading, expect_rows=True):
    "Load a /logs page; assert its heading and the log table render."
    page.goto(f"{base}{url}")
    expect(page.get_by_role("heading", name=heading)).to_be_visible()
    expect(page.get_by_role("columnheader", name="Timestamp")).to_be_visible()
    if expect_rows:
        expect(page.locator("table.table-sm tbody tr").first).to_be_visible()


def test_call_logs(settings, admin_page, populated_call):
    "The call has been created and edited, so its log has entries."
    base = settings["BASE_URL"]
    cid = populated_call["call"]
    _assert_logs_render(admin_page, base, f"/call/{cid}/logs", f"Logs for Call {cid}")


def test_proposal_logs(settings, admin_page, populated_call):
    base = settings["BASE_URL"]
    pid = populated_call["proposal"]
    _assert_logs_render(admin_page, base, f"/proposal/{pid}/logs", f"Logs for Proposal {pid}")


def test_review_logs(settings, admin_page, populated_call):
    "The review heading is 'Logs for Review of <proposal> by <reviewer>'."
    base = settings["BASE_URL"]
    iuid = populated_call["review"]
    _assert_logs_render(admin_page, base, f"/review/{iuid}/logs", "Logs for Review of")


def test_grant_logs(settings, admin_page, populated_call):
    base = settings["BASE_URL"]
    gid = populated_call["grant"]
    _assert_logs_render(admin_page, base, f"/grant/{gid}/logs", f"Logs for Grant {gid}")


def test_user_logs(settings, admin_page, populated_call):
    "Admin's own audit log. The user document may have no edits, so don't require rows."
    base = settings["BASE_URL"]
    admin_username = settings["ADMIN_USERNAME"]
    _assert_logs_render(
        admin_page, base, f"/user/logs/{admin_username}", f"Logs for User {admin_username}", expect_rows=False
    )
