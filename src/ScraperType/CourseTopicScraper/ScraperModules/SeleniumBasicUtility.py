import json
import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility

class SeleniumBasicUtility:
    def __init__(self, configJson):
        self.fileUtils = FileUtility()
        self.osUtils = OSUtility(configJson)
        self.browser = None
        self.timeout = 5
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["SeleniumBasicUtility"]
        self.logger = Logger(configJson, "SeleniumBasicUtility").logger
        self.configJson = configJson


    def expandAllSections(self):
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
                self.osUtils.sleep(2)
                self.browser.execute_script(expandButtonJsScript)
                retryExpand += 1
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SeleniumBasicUtility:expandAllSections: {lineNumber}: {e}")


    def waitWebdriverToLoadTopicPage(self):
        try:
            self.logger.info("Waiting for webdriver to load topic page")
            articlePageSelector = self.selectors["articlePage"]
            generalPageSelector = self.selectors["generalPage"]
            cloudLabOrProjectSelector = self.selectors[f'{self.configJson["moduleType"]}']
            mockInterviewSelector = self.selectors["mockInterviewPage"]
            try:
                try:
                    try:
                        WebDriverWait(self.browser, self.timeout+5).until(
                            EC.visibility_of_element_located((By.XPATH, articlePageSelector)))
                    except Exception as e:
                        self.browser.save_screenshot("image.png")
                        WebDriverWait(self.browser, self.timeout+5).until(
                            EC.visibility_of_element_located((By.XPATH, generalPageSelector)))
                except Exception as e:
                    try:
                        WebDriverWait(self.browser, self.timeout + 5).until(
                            EC.visibility_of_element_located((By.XPATH, cloudLabOrProjectSelector)))
                    except Exception as e:
                        WebDriverWait(self.browser, self.timeout + 5).until(
                            EC.visibility_of_element_located((By.XPATH, mockInterviewSelector)))
            except Exception as e:
                lineNumber = e.__traceback__.tb_lineno
                self.logger.error(f"SeleniumBasicUtility:waitWebdriverToLoadTopicPage: {lineNumber}: {e}")
                return False
            return True
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SeleniumBasicUtility:waitWebdriverToLoadTopicPage: {lineNumber}: {e}")


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


    def sendCommand(self, command, params):
        self.logger.debug(f"Sending command: {command} with params: {params}")
        resource = "/session/%s/chromium/send_command_and_get_result" % self.browser.session_id
        url = self.browser.command_executor._url + resource
        body = json.dumps({'cmd': command, 'params': params})
        response = self.browser.command_executor._request('POST', url, body)
        return response.get('value')


    def resizeHorizontalGlutter(self):
        self.logger.info("resizeHorizontalGlutter")
        try:
            horizonWidthSelector = self.selectors["resizeHorizontalGlutter"]
            horizonWidthJsScript = f"""document.querySelectorAll("{horizonWidthSelector}")[0].removeAttribute('style');"""
            self.browser.execute_script(horizonWidthJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"SeleniumBasicUtility:resizeHorizontalGlutter: {lineNumber}: {e}")

    
    def clickEndLabForCloudlabs(self):
        try:
            if self.configJson["moduleType"] in ("CLOUDLAB"):
                self.logger.info("Inside clickEndLabForCloudlabs")
                self.osUtils.sleep(2)
                endLabButtonSelector = self.selectors["endLabButton"][f'{self.configJson["moduleType"]}']
                endLabButtonJsScript = f"""
                try {{
                    var endLabButton = document.evaluate("{endLabButtonSelector}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    if (endLabButton.snapshotLength > 0) {{
                        endLabButton.snapshotItem(0).click();
                    }}
                }} catch (e) {{
                    console.log(e);
                }}
                """
                self.browser.execute_script(endLabButtonJsScript)
            self.osUtils.sleep(10)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"SeleniumBasicUtility:clickEndLabForCloudlabs: {lineNumber}: {e}")
    

    def clickStartCloudlabsOrProject(self):
        try:
            self.logger.info("Inside clickStartCloudlabsOrProject")
            startButtonSelector = self.selectors["startButton"][f'{self.configJson["moduleType"]}']
            startButtonJsScript = f"""
            try {{
                var startButton = document.evaluate("{startButtonSelector}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                if (startButton.snapshotLength > 0) {{
                    startButton.snapshotItem(0).click();
                }}
            }} catch (e) {{
                console.log(e);
            }}
            """
            self.browser.execute_script(startButtonJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"SeleniumBasicUtility:clickStartCloudlabsOrProject: {lineNumber}: {e}")

