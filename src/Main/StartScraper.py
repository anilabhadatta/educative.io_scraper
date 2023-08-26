import time

from src.Logging.Logger import Logger
from src.Utility.BrowserUtility import BrowserUtility


class StartScraper:
    def __init__(self):
        self.logger = None
        self.browserUtil = None
        self.configJson = None
        self.browser = None


    def start(self, configJson):
        self.configJson = configJson
        self.browserUtil = BrowserUtility(self.configJson)
        self.logger = Logger(self.configJson, "StartScraper").logger
        self.logger.info("""StartScraper initiated...
                            To Terminate, Click on Stop Scraper Button
                        """)
        try:
            i = 0
            while True:
                self.logger.debug(f"Starting scraper... {i}")
                i += 1
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            self.logger.error(e)
        finally:
            self.logger.debug("Exiting...")
