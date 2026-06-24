"""Test browser anonymous access."""

def test_about(settings, page):  # 'page' fixture from 'pytest-playwright'
    page.set_default_timeout(15_000)
    page.goto(settings["BASE_URL"])
    page.click("text=About")
    page.click("text=Contact")
    assert page.url == f"{settings['BASE_URL']}/about/contact"

    page.go_back()
    page.click("text=About")
    page.click("text=Data policy")
    assert page.url == f"{settings['BASE_URL']}/about/data_policy"

    page.go_back()
    page.click("text=About")
    page.click("text=Software")
    assert page.url == f"{settings['BASE_URL']}/about/software"


def test_calls(settings, page):
    page.set_default_timeout(15_000)
    page.goto(settings["BASE_URL"])
    page.click("text=Calls")
    page.click("text=Open calls")
    assert page.url == f"{settings['BASE_URL']}/calls/open"

    page.go_back()
    page.click("text=Calls")
    page.click("text=Closed calls")
    assert page.url == f"{settings['BASE_URL']}/calls/closed"


def test_documentation(settings, page):
    page.set_default_timeout(15_000)
    page.goto(f"{settings['BASE_URL']}/documentation")
    assert page.url == f"{settings['BASE_URL']}/documentation"


def test_status_endpoint(settings, page):
    "The /status health endpoint returns ok plus the database counts (SMOKE_TESTS #1)."
    resp = page.request.get(f"{settings['BASE_URL']}/status")
    assert resp.status == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "n_calls" in body


def test_sitemap(settings, page):
    "The /sitemap endpoint returns an XML document that includes the home URL."
    resp = page.request.get(f"{settings['BASE_URL']}/sitemap")
    assert resp.status == 200
    assert "xml" in resp.headers["content-type"]
    body = resp.text()
    assert "<url>" in body
    assert settings["BASE_URL"] in body