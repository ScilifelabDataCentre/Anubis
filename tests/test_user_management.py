import pytest


@pytest.fixture(scope="function")
def new_user(settings, browser, admin_page):
    "Goes through the signup-flow as a new user. On teardown the user is deleted."
    base = settings["BASE_URL"]
    new_username = "testnewuser"
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    page.goto(base)
    page.get_by_role("link", name="Register a new user account").click()
    page.get_by_role("textbox", name="User name").fill(new_username)
    page.get_by_role("textbox", name="Email").fill("testnewuser@test.com")
    page.get_by_role("textbox", name="Given name").fill("Test")
    page.get_by_role("textbox", name="Family name").fill("Test")
    page.locator("div").filter(has_text="Male").nth(5).click()
    page.get_by_role("textbox", name="Birth date").fill("1900-01-01")
    page.get_by_role("radio", name="PhD").check()
    page.locator("#affiliation_other").fill("Karolinska institutet")
    page.get_by_role("textbox", name="ORCID").fill("0000-0002-1825-0097")
    page.get_by_role("button", name="Register").click()
    
    yield page

    admin_page.goto(f"{base}/user/display/{new_username}")
    admin_page.once("dialog", lambda d: d.accept())
    admin_page.get_by_role("button", name="Delete").click()
    context.close()


def test_new_user_registration(settings, admin_page, new_user):
    base = settings["BASE_URL"]
    assert new_user.get_by_text("Message: User account created").is_visible()
    admin_page.goto(base)
    admin_page.get_by_role("button", name="Users", exact=True).click()
    admin_page.get_by_role("link", name="Pending users").click()
    assert admin_page.get_by_role("gridcell", name="testnewuser", exact=True).is_visible()


def test_disable_user(settings, admin_page):
    base = settings["BASE_URL"]
    new_username = "testtestnewuser"
    try:
        admin_page.goto(base)
        admin_page.get_by_role("button", name="Users", exact=True).click()
        admin_page.get_by_role("link", name="Register user").click()
        admin_page.get_by_role("textbox", name="User name").fill(new_username)
        admin_page.get_by_role("textbox", name="Email").fill("testnewuser@test.com")
        admin_page.get_by_role("button", name="Register").click()
        admin_page.get_by_role("link", name=new_username).click()
        assert admin_page.get_by_role("button", name="Disable").is_visible()
        admin_page.get_by_role("button", name="Disable").click()
        assert admin_page.get_by_role("button", name="Enable").is_visible()

    finally:
        admin_page.goto(f"{base}/user/display/{new_username}")
        admin_page.once("dialog", lambda d: d.accept())
        admin_page.get_by_role("button", name="Delete").click()


def test_profile_editing(settings, browser, admin_page):
    new_username = "newtestuseredit"
    new_password = "testpass123"
    base = settings["BASE_URL"]
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(15_000)
    try:
        admin_page.goto(base)
        admin_page.get_by_role("button", name="Users", exact=True).click()
        admin_page.get_by_role("link", name="Register user").click()
        admin_page.get_by_role("textbox", name="User name").fill(new_username)
        admin_page.get_by_role("textbox", name="Email").fill("testnewuseredit@test.com")
        admin_page.get_by_role("button", name="Register").click()
        admin_page.get_by_role("link", name=new_username).click()
        admin_page.get_by_role("button", name="Set password", exact=True).click()
        admin_page.get_by_role("textbox", name="Password").fill(new_password)
        admin_page.get_by_role("button", name="Set password").click()
        assert admin_page.get_by_text("Message: Password set.").is_visible()

        page.goto(base)
        page.get_by_role("button", name="Login").click()
        page.get_by_role("textbox", name="User name or email address").fill(new_username)
        page.locator("#password").fill(new_password)
        page.locator("#login").click()
        page.get_by_role("button", name=new_username).click()
        page.get_by_role("button", name="Edit", exact=True).click()
        page.get_by_role("textbox", name="Given name").fill("newgivenname")
        page.get_by_role("textbox", name="Family name").fill("newfamilyname")
        page.get_by_text("Male", exact=True).click()
        page.get_by_text("MSc").click()
        page.get_by_role("button", name="Save").click()
        assert page.url.rstrip("/") == f"{base}/user/display/{new_username}"
        assert page.get_by_role("cell", name="newgivenname").is_visible()
        assert page.get_by_role("cell", name="newfamilyname").is_visible()
        assert page.get_by_role("cell", name="Male").is_visible()
        assert page.get_by_role("cell", name="MSc").is_visible()
    finally:
        admin_page.goto(f"{base}/user/display/{new_username}")
        admin_page.once("dialog", lambda dialog: dialog.accept())
        admin_page.get_by_role("button", name="Delete").click()
        context.close()