import os
import time

from selenium.webdriver.common.by import By

from src.Logging.Logger import Logger
from src.ScraperMethod.ExtensionMethod.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.Utility.FileUtility import FileUtility


class ScreenshotHtmlUtility:
    def __init__(self, configJson):
        self.browser = None
        self.fileUtils = FileUtility()
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["ScreenshotHtmlUtility"]
        self.logger = Logger(configJson, "ScreenshotHtmlUtility").logger


    def getFullPageScreenshotHtml(self, topicName):
        self.logger.info(f"Getting full page screenshot html for {topicName}")
        articlePageSelector = self.selectors["articlePage"]
        generalPageSelector = self.selectors["generalPage"]
        self.seleniumBasicUtils.browser = self.browser
        try:
            canvas = (self.browser.find_elements(By.XPATH, articlePageSelector) or
                      self.browser.find_elements(By.XPATH, generalPageSelector))
            base64Png = self.seleniumBasicUtils.screenshotAsCdp(canvas[0], 1)
            time.sleep(2)
            return self.getHtmlWithImage(base64Png, topicName)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ScreenshotHtmlUtility:getFullPageScreenshotHtml: {lineNumber}: {e}")


    def getHtmlWithImage(self, base64Png, topicName):
        self.logger.debug(f"Attaching image with the html")
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>{topicName}</title>
        </head>
        <body background-color: rgb(21 21 30); style="zoom: 80%">
            <div style="text-align: center">
                <img style="display: block;margin-left: auto; margin-right: auto;" src="data:image/png;base64,{base64Png}" alt="">
            </div>
        </body>
        </html>
        """
