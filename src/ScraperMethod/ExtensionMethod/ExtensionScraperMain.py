import json

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
        for textFileUrl in urlsTextFile:
            try:
                self.logger.info(f"Started Scraping from Text File URL: {textFileUrl}")
                courseTopicUrlsList = self.apiUtils.getCourseTopicUrlsList(textFileUrl)
                courseCollectionsJson = self.apiUtils.getCourseCollectionsJson(textFileUrl)
                for index in range(len(courseTopicUrlsList)):
                    courseTopicUrl = courseTopicUrlsList[index]
                    courseApiUrl = courseCollectionsJson["topicApiUrlList"][index]
                    courseTitle = courseCollectionsJson["courseTitle"]
                    self.logger.info(f"Scraping {index}-{courseTitle}: {courseTopicUrl}")

                    courseApiContentJson = self.apiUtils.getCourseApiContentJson(courseApiUrl)
                    with open(f"courseApiContentJson{index}.json", "w") as f:
                        f.write(json.dumps(courseApiContentJson))
                    if index == 2:
                        break
                with open("courseTopicUrls.txt", "w") as f:
                    f.write(str(courseTopicUrlsList))
                with open("courseCollectionsData.json", "w") as f:
                    f.write(json.dumps(courseCollectionsJson))
                print("Complete")
                while True:
                    pass
            except Exception as e:
                self.logger.error(f"start {e}")
                raise Exception(f"ExtensionScraper:start {e}")
        self.logger.info("ExtensionScraper completed.")
