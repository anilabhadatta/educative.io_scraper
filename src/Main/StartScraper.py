import time

from src.Utility.BrowserUtility import BrowserUtility


class StartScraper:
    def __init__(self, configJson):
        self.configJson = configJson
        self.browserUtil = BrowserUtility(configJson)
        self.browser = None


    def start(self):
        i = 0
        while True:
            print("Starting scraper...", i)
            i += 1
            time.sleep(1)
