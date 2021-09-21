"Test the web site pages using Selenium. Not logged in."

import unittest

import selenium
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

import utils


class Homepage(utils.BrowserTestCase):
    "Test the home page."

    def test_home(self):
        "Test presence of table in home page and version indicator."
        self.driver.get(self.settings["BASE_URL"])

        # Software versions displayed in footer in every page.
        elem = self.driver.find_element_by_id("version")
        self.assertGreaterEqual(elem.text, "1.3.17")


if __name__ == "__main__":
    unittest.main()
