"Test the web site pages using Selenium. Not logged in."

import unittest

import selenium
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

import utils


class LoginUser(utils.BrowserTestCase):
    "Test login as a user."

    def test_1_login(self):
        "Starting from home page, login to a user account."
        elem = self.driver.get(self.settings["BASE_URL"])
        elem = self.driver.find_element_by_xpath("//form[@id='login-form']")
        elem = elem.find_element_by_tag_name("button")
        elem.click()

        # Login page; fill in user name and password in form.
        self.assertIn("Login", self.driver.title)
        elem = self.driver.find_element_by_name("username")
        elem.clear()
        elem.send_keys(self.settings["USERNAME"])
        elem = self.driver.find_element_by_name("password")
        elem.clear()
        elem.send_keys(self.settings["PASSWORD"])
        elem = self.driver.find_element_by_id("login-form-submit")
        elem.send_keys(Keys.RETURN)


if __name__ == "__main__":
    unittest.main()
