import json
import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.Utility.FileUtility import FileUtility


class SeleniumBasicUtility:
    def __init__(self, configJson):
        self.fileUtils = FileUtility()
        self.browser = None
        self.timeout = 10
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["SeleniumBasicUtility"]
        self.logger = Logger(configJson, "SeleniumBasicUtility").logger


    def expandAllSections(self):
        try:
            self.logger.debug("Expanding all sections function")
            expandAllButtonSelector = self.selectors["expandAllButton"]
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, expandAllButtonSelector)))
            expandButton = self.browser.find_elements(By.XPATH, expandAllButtonSelector)
            while expandButton:
                self.logger.info("Expanding all sections")
                expandButton[0].click()
                time.sleep(2)
                expandButton = self.browser.find_elements(By.XPATH, expandAllButtonSelector)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SeleniumBasicUtility:expandAllSections: {lineNumber}: {e}")


    def waitWebdriverToLoadTopicPage(self):
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
        self.logger.info("Loading page and checking if something went wrong")
        time.sleep(self.timeout)
        if "Something Went Wrong" in self.browser.page_source:
            raise Exception(f"SeleniumBasicUtility:checkSomethingWentWrong: Something Went Wrong")


    def addNameAttributeInNextBackButton(self):
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
        self.logger.debug(f"Sending command: {command} with params: {params}")
        resource = "/session/%s/chromium/send_command_and_get_result" % self.browser.session_id
        url = self.browser.command_executor._url + resource
        body = json.dumps({'cmd': command, 'params': params})
        response = self.browser.command_executor._request('POST', url, body)
        return response.get('value')
