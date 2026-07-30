"""End-to-end tests for the user-scoped list views in anubis/.

Each of these views lists one user's proposals, grants, or reviews. They are
gated so that a user sees only their own lists (staff and admin see everyone's),
which is a confidentiality boundary with no regression net today.

All tests reuse the session-scoped populated_call fixture: testuser owns its
proposal and grant, and admin is the finalized reviewer.
"""

from playwright.sync_api import expect


def test_user_proposals_list_visible_to_owner_and_admin(settings, admin_page, user_page, populated_call):
    "The owner and admin can load a user's proposals list and see the proposal."
    base = settings["BASE_URL"]
    owner = settings["USER_USERNAME"]
    target = f"{base}/proposals/user/{owner}"

    for page in (user_page, admin_page):
        page.goto(target)
        expect(page).to_have_url(target)
        expect(page.get_by_role("link", name="Proposal").first).to_be_visible()


def test_user_proposals_list_denied_for_other_user(settings, user2_page, populated_call):
    "A different regular user may not view another user's proposals list."
    base = settings["BASE_URL"]
    target = f"{base}/proposals/user/{settings['USER_USERNAME']}"
    user2_page.goto(target)
    expect(user2_page).not_to_have_url(target)
