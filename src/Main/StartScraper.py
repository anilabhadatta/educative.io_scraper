from src.Logging.Logger import Logger
from src.ScraperMethod.ApiMethod.ApiScraperMain import ApiScraper
from src.ScraperMethod.ExtensionMethod.ExtensionScraperMain import ExtensionScraper
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
        self.logger.info("""StartScraper Initiated...
                            To Terminate, Click on Stop Scraper Button
                        """)
        try:
            self.browser = self.browserUtil.loadBrowser()
            if configJson["apiToHtml"]:
                ApiScraper(configJson, self.browser).start()
            else:
                ExtensionScraper(configJson, self.browser).start()
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            self.logger.error(e)
        finally:
            self.logger.debug("Exiting Scraper...")
            self.browser.quit()
