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


def test_user_grants_list_visible_to_owner_and_admin(settings, admin_page, user_page, populated_call):
    "The owner and admin can load a user's grants list and see the grant."
    base = settings["BASE_URL"]
    owner = settings["USER_USERNAME"]
    gid = populated_call["grant"]
    target = f"{base}/grants/user/{owner}"

    for page in (user_page, admin_page):
        page.goto(target)
        expect(page).to_have_url(target)
        expect(page.locator(f'a[href$="/grant/{gid}"]')).to_be_visible()


def test_user_grants_list_denied_for_other_user(settings, user2_page, populated_call):
    "A different regular user may not view another user's grants list."
    base = settings["BASE_URL"]
    target = f"{base}/grants/user/{settings['USER_USERNAME']}"
    user2_page.goto(target)
    expect(user2_page).not_to_have_url(target)


def test_proposal_reviews_visible_to_admin_denied_to_submitter(settings, admin_page, user_page, populated_call):
    "Admin sees the reviews listed for a proposal; the submitter (non-reviewer) is denied."
    base = settings["BASE_URL"]
    pid = populated_call["proposal"]
    iuid = populated_call["review"]
    target = f"{base}/reviews/proposal/{pid}"

    admin_page.goto(target)
    expect(admin_page.locator(f'a[href$="/review/{iuid}"]')).to_be_visible()

    user_page.goto(target)
    expect(user_page.get_by_text("You may not view the reviews of the call.")).to_be_visible()


def test_reviewer_reviews_denied_to_other_user(settings, admin_page, user_page, populated_call):
    "A reviewer's reviews page is reachable by that reviewer but denied to a regular user."
    base = settings["BASE_URL"]
    reviewer = settings["ADMIN_USERNAME"]
    target = f"{base}/reviews/reviewer/{reviewer}"

    # The reviewer (admin) is allowed. A single-call reviewer is redirected to the
    # call reviews page, so assert absence of the denial rather than an exact URL.
    admin_page.goto(target)
    expect(admin_page.get_by_text("You may not view the user's reviews.")).to_have_count(0)

    user_page.goto(target)
    expect(user_page.get_by_text("You may not view the user's reviews.")).to_be_visible()
