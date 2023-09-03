import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.ScraperMethod.ExtensionMethod.ScraperModules.UrlUtility import UrlUtility


class ApiUtility:
    def __init__(self, browser, configJson):
        self.browser = browser
        self.timeout = 10
        self.logger = Logger(configJson, "ApiUtility").logger
        self.urlUtils = UrlUtility(configJson)


    def getCourseCollectionsData(self, url):
        try:
            courseApiUrl = self.urlUtils.getCourseApiCollectionListUrl(url)
            self.browser.get(courseApiUrl)
            WebDriverWait(self.browser, self.timeout).until(EC.presence_of_element_located((By.XPATH, "//pre")))
            jsonData = self.browser.find_elements(By.XPATH, "//pre")[0].text
            jsonData = json.loads(jsonData)["instance"]["details"]
            authorId = str(jsonData["author_id"])
            collectionId = str(jsonData["collection_id"])
            categories = jsonData["toc"]["categories"]
            courseTitle = jsonData["title"]
            topicApiUrlList = []
            baseApiUrl = f"https://educative.io/api/collection/{authorId}/{collectionId}/page/"
            for category in categories:
                for page in category["pages"]:
                    topicApiUrlList.append(baseApiUrl + str(page["id"]))
            return {
                "courseTitle": courseTitle,
                "topicApiUrlList": topicApiUrlList
            }
        except Exception as e:
            self.logger.error(e)
            raise Exception(e)


    def getCourseTopicUrls(self, url):
        self.browser.get(url)
        courseUrlSelector = self.urlUtils.getCourseUrlSelector(url)
        WebDriverWait(self.browser, self.timeout).until(
            EC.presence_of_element_located((By.XPATH, courseUrlSelector)))
        topicUrlElements = self.browser.find_elements(By.XPATH, courseUrlSelector)
        topicUrls = []
        for topicUrlElement in topicUrlElements:
            topicUrls.append(topicUrlElement.get_attribute("href"))
        return topicUrls
