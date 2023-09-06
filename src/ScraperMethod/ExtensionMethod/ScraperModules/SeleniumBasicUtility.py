import json
import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Utility.FileUtility import FileUtility


class SeleniumBasicUtility:
    def __init__(self):
        self.fileUtils = FileUtility()
        self.browser = None
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["SeleniumBasicUtility"]


    def waitWebdriverToLoadTopicPage(self):
        try:
            articlePageSelector = self.selectors["articlePage"]
            WebDriverWait(self.browser, 10).until(EC.visibility_of_element_located((By.XPATH, articlePageSelector)))
            time.sleep(10)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SeleniumBasicUtility:waitWebdriverToLoadTopicPage: {lineNumber}: {e}")


    def checkSomethingWentWrong(self):
        if "Something Went Wrong" in self.browser.page_source:
            raise Exception(f"SeleniumBasicUtility:checkSomethingWentWrong: Something Went Wrong")


    def addNameAttributeInNextBackButton(self):
        try:
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
        resource = "/session/%s/chromium/send_command_and_get_result" % self.browser.session_id
        url = self.browser.command_executor._url + resource
        body = json.dumps({'cmd': command, 'params': params})
        response = self.browser.command_executor._request('POST', url, body)
        return response.get('value')
