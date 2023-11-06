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
            base64Png = self.screenshotAsCdp(canvas[0], 1)
            self.osUtils.sleep(2)
            self.logger.info("getFullPageScreenshot: Successfully Received Full Page Screenshot...")
            return base64Png
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ScreenshotHtmlUtility:getFullPageScreenshot: {lineNumber}: {e}")


    def screenshotAsCdp(self, canvas, scale=1, shiftx=0, shifty=0, padwidth=0, padheight=0):
        try:
            self.logger.info("Taking screenshot as CDP")

            try:
                size = canvas.size
                location = canvas.location
                width, height = size['width'], size['height']
                x, y = location['x'], location['y']
            except:
                rect = self.browser.execute_script("return arguments[0].getBoundingClientRect();", canvas)
                width, height = rect['width'], rect['height']
                x, y = rect['left'], rect['top']

            params = {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {
                    "width": round(width + padwidth),
                    "height": round(height + padheight),
                    "x": round(x + shiftx),
                    "y": round(y + shifty),
                    "scale": scale
                }
            }
            screenshot = self.seleniumBasicUtils.sendCommand("Page.captureScreenshot", params)
            return screenshot['data']
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ScreenshotUtility:screenshotAsCdp: {lineNumber}: {e}")
