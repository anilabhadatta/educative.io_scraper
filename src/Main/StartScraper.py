from src.Logging.Logger import Logger
from src.ScraperMethod.AllTopicUrlsScraper.ScrapeAllTopicUrls import ScrapeAllTopicUrls
from src.ScraperMethod.ExtensionBasedTopicScraper.ExtensionScraperMain import ExtensionScraper


class StartScraper:
    def __init__(self):
        self.logger = None


    def start(self, configJson):
        self.logger = Logger(configJson, "StartScraper").logger
        self.logger.info("""StartScraper Initiated...
                            To Terminate, Click on Stop Scraper Button
                        """)
        try:
            if configJson["scrapeAllTopicUrls"]:
                ScrapeAllTopicUrls(configJson).start()
            else:
                ExtensionScraper(configJson).start()
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"start: {lineNumber}: {e}")
        finally:
            self.logger.debug("Exiting Scraper...")
