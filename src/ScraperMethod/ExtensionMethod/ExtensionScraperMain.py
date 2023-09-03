from src.Logging.Logger import Logger
from src.ScraperMethod.ExtensionMethod.ScraperModules.ApiUtility import ApiUtility
from src.ScraperMethod.ExtensionMethod.ScraperModules.UrlUtility import UrlUtility
from src.Utility.FileUtility import FileUtility


class ExtensionScraper:
    def __init__(self, configJson, browser):
        self.configJson = configJson
        self.browser = browser
        self.logger = Logger(configJson, "ExtensionScraper").logger
        self.fileUtils = FileUtility()
        self.apiUtils = ApiUtility(browser, configJson)
        self.urlUtils = UrlUtility(configJson)


    def start(self):
        self.logger.info("ExtensionScraper initiated...")
        urlsTextFile = self.fileUtils.loadTextFile(self.configJson["courseUrlsFilePath"])
        for url in urlsTextFile:
            try:
                self.logger.info(f"Scraping URL: {url}")
                courseCollectionsData = self.apiUtils.getCourseCollectionsData(url)
                courseTopicUrls = self.apiUtils.getCourseTopicUrls(url)
                with open("courseTopicUrls.txt", "w") as f:
                    f.write(str(courseTopicUrls))
                with open("courseCollectionsData.txt", "w") as f:
                    f.write(str(courseCollectionsData))
                while True:
                    pass
            except Exception as e:
                raise Exception(e)
        self.logger.info("ExtensionScraper completed.")
