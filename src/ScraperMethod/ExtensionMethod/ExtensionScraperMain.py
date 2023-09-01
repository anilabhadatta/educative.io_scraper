from src.Logging.Logger import Logger
from src.Utility.FileUtility import FileUtility


class ExtensionScraper:
    def __init__(self, configJson, browser):
        self.configJson = configJson
        self.browser = browser
        self.logger = Logger(configJson, "ExtensionScraper").logger
        self.fileUtil = FileUtility()


    def start(self):
        self.logger.info("ExtensionScraper initiated...")
        urlsTextFile = self.fileUtil.loadTextFile(self.configJson["courseUrlsFilePath"])
        for url in urlsTextFile:
            try:
                self.logger.info(f"Scraping URL: {url}")
                self.browser.get(url)
                while True:
                    pass
            except Exception as e:
                raise Exception(e)
        self.logger.info("ExtensionScraper completed.")
