import os

from selenium.webdriver.common.by import By

from src.Utility.OSUtility import OSUtility
from src.Logging.Logger import Logger
from src.ScraperType.CourseTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.Utility.FileUtility import FileUtility


class ScreenshotUtility:
    def __init__(self, configJson):
        self.browser = None
        self.fileUtils = FileUtility()
        self.osUtils = OSUtility(configJson)
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["ScreenshotHtmlUtility"]
        self.logger = Logger(configJson, "ScreenshotHtmlUtility").logger


    def getFullPageScreenshot(self, topicName):
        self.logger.info(f"getFullPageScreenshot: Getting full page screenshot for {topicName}")
        articlePageSelector = self.selectors["articlePage"]
        generalPageSelector = self.selectors["generalPage"]
        self.seleniumBasicUtils.browser = self.browser
        try:
            canvas = (self.browser.find_elements(By.XPATH, articlePageSelector) or
                      self.browser.find_elements(By.XPATH, generalPageSelector))
            base64Png = self.seleniumBasicUtils.screenshotAsCdp(canvas[0], 1)
            self.osUtils.sleep(2)
            self.logger.info("getFullPageScreenshot: Successfully Received Full Page Screenshot...")
            return base64Png
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ScreenshotHtmlUtility:getFullPageScreenshot: {lineNumber}: {e}")