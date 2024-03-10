import os

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
        self.seleniumBasicUtils.browser = self.browser
        try:
            # completeBase64Png = self.browser.get_screenshot_as_base64()
            # completeBase64ImgTag = f'''<img style="max-width: 140%; display: block; margin-left: auto; margin-right: auto;" src="data:image/png;base64,{completeBase64Png}">'''
            canvas = self.browser.execute_cdp_cmd("Page.getLayoutMetrics", {})
            height = canvas["contentSize"]["height"]
            completeBase64ImgTag = ""
            if height >= 25000:
                for counter, maxImgH in enumerate(range(25000, height, 25000), start=0):
                    canvas["contentSize"]["height"] = min(height-maxImgH, 25000)
                    completeBase64ImgTag += self.screenshotAsCdp(canvas, counter)
            else:
                completeBase64ImgTag = self.screenshotAsCdp(canvas)
            self.logger.info("getFullPageScreenshot: Successfully Received Full Page Screenshot...")
            return completeBase64ImgTag
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ScreenshotHtmlUtility:getFullPageScreenshot: {lineNumber}: {e}")


    def screenshotAsCdp(self, canvas, counter=0):
        try:
            self.logger.info("Taking screenshot as CDP")
            width = canvas["contentSize"]["width"]
            height = canvas["contentSize"]["height"]
            self.logger.info(f"width {width}, height {height}")
            params = {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {
                    "width": width,
                    "height": height,
                    "x": 0,
                    "y": counter*25000,
                    "scale": 0.8
                }
            }
            retry = 0
            while retry < 2:
                try:
                    screenshot = self.seleniumBasicUtils.sendCommand("Page.captureScreenshot", params)
                    base64ImgTag = f'''<img style="max-width: 140%; display: block; margin-left: auto; margin-right: auto;" src="data:image/png;base64,{screenshot["data"]}">'''
                    self.logger.info("Successfully captured Screenshot")
                    self.osUtils.sleep(2)
                    return base64ImgTag
                except Exception as e:
                    retry += 1
                    self.logger.info(f"Found Error taking Screenshot, retrying {retry} out of 2: {e}")
                    if retry == 2:
                        raise Exception("Problem taking screenshot")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ScreenshotUtility:screenshotAsCdp: {lineNumber}: {e}")