import json
import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.Utility.FileUtility import FileUtility


class SeleniumBasicUtility:
    """
    A class that provides basic utility functions for Selenium web scraping.

    Attributes:
        fileUtils (FileUtility): An instance of the FileUtility class.
        browser: The Selenium webdriver instance.
        timeout (int): The timeout value for waiting for elements to load.
        selectors (dict): A dictionary of CSS selectors for various elements.
        logger (Logger): An instance of the Logger class.
    """

    def __init__(self, configJson):
        """
        Initializes a new instance of the SeleniumBasicUtility class.

        Args:
            configJson (dict): A dictionary of configuration settings.
        """
        self.fileUtils = FileUtility()
        self.browser = None
        self.timeout = 10 # todo chooose a user configured timeout, too slow for fast internet, better replace with programatic check instead?
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["SeleniumBasicUtility"]
        self.logger = Logger(configJson, "SeleniumBasicUtility").logger


    def expandAllSections(self):
        """
        Expands all sections on the current page.
        """
        try:
            self.logger.debug("Expanding all sections function")
            expandAllButtonSelector = self.selectors["expandAllButton"]
            expandButtonJsScript = f"""
            try {{
                var expandButton = document.evaluate("{expandAllButtonSelector}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                if (expandButton.snapshotLength > 0) {{
                    expandButton.snapshotItem(0).click();
                }}
            }} catch (e) {{
                console.log(e);
            }}
            """
            retryExpand = 0
            while retryExpand < 3:
                self.logger.info("Expanding all sections")
                time.sleep(2)
                self.browser.execute_script(expandButtonJsScript)
                retryExpand += 1
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SeleniumBasicUtility:expandAllSections: {lineNumber}: {e}")


    def waitWebdriverToLoadTopicPage(self):
        """
        Waits for the webdriver to load the topic page.
        """
        try:
            self.logger.info("Waiting for webdriver to load topic page")
            articlePageSelector = self.selectors["articlePage"]
            generalPageSelector = self.selectors["generalPage"]
            try:
                WebDriverWait(self.browser, self.timeout).until(
                    EC.visibility_of_element_located((By.XPATH, articlePageSelector)))
            except Exception as e:
                WebDriverWait(self.browser, self.timeout).until(
                    EC.visibility_of_element_located((By.XPATH, generalPageSelector)))
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SeleniumBasicUtility:waitWebdriverToLoadTopicPage: {lineNumber}: {e}")


    def loadingPageAndCheckIfSomethingWentWrong(self):
        """
        Loads the page and checks if something went wrong.
        """
        self.logger.info("Loading page and checking if something went wrong")
        time.sleep(self.timeout)
        if "Something Went Wrong" in self.browser.page_source:
            raise Exception(f"SeleniumBasicUtility:checkSomethingWentWrong: Something Went Wrong")


    def addNameAttributeInNextBackButton(self):
        """
        Adds a name attribute to the next/back button.
        """
        try:
            self.logger.info("Adding name attribute in next/back button")
            nextButtonSelector = self.selectors["nextButton"]
            backButtonSelector = self.selectors["backButton"]
            addNameAttributeJsScript = f"""
            const buttons = document.querySelectorAll('button');
            buttons.forEach(button => {{
                if (button.textContent.trim() === "{nextButtonSelector}") {{
                    button.setAttribute('name', 'next');
                }}
                if (button.textContent.trim() === "{backButtonSelector}") {{
                    button.setAttribute('name', 'back');
                }}
            }});
            """
            self.browser.execute_script(addNameAttributeJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SeleniumBasicUtility:addNameAttributeInNextBackButton: {lineNumber}: {e}")


    def screenshotAsCdp(self, canvas, scale=1):
        """
        Takes a screenshot of the current page using Chrome DevTools Protocol.

        Args:
            canvas: The canvas element to take a screenshot of.
            scale (float): The scale factor for the screenshot.

        Returns:
            The screenshot data as a byte string.
        """
        self.logger.info("Taking screenshot as CDP")
        
        self.logger.info("Taking screenshot as CDP")
        size, location = canvas.size, canvas.location
        width, height = size['width'], size['height']
        x, y = location['x'], location['y']

        params = {
            "format": "png",
            "captureBeyondViewport": True,
            "clip": {
                "width": width,
                "height": height,
                "x": x,
                "y": y,
                "scale": scale
            }
        }
        screenshot = self.sendCommand("Page.captureScreenshot", params)
        return screenshot['data']


    def sendCommand(self, command, params):
        """
        Sends a command to the Chrome DevTools Protocol.

        Args:
            command (str): The name of the command to send.
            params (dict): A dictionary of parameters for the command.

        Returns:
            The response value from the command.
        """
        self.logger.debug(f"Sending command: {command} with params: {params}")
        resource = "/session/%s/chromium/send_command_and_get_result" % self.browser.session_id
        url = self.browser.command_executor._url + resource
        body = json.dumps({'cmd': command, 'params': params})
        response = self.browser.command_executor._request('POST', url, body)
        return response.get('value')
    