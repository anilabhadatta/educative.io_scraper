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
