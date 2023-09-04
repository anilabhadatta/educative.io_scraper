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


    def executeJsToGetJson(self, url):
        script = f"""
            return new Promise((resolve, reject) => {{
                fetch("{url}")
                    .then(response => response.json())
                    .then(data => {{
                        resolve(data);
                    }})
                    .catch(error => {{
                        reject(error);
                    }});
            }});
        """
        return self.browser.execute_script(script)


    def getCourseApiContentJson(self, courseApiUrl):
        try:
            jsonData = self.executeJsToGetJson(courseApiUrl)
            jsonData = jsonData["components"]
            return jsonData
        except Exception as e:
            self.logger.error(f"getCourseApiContentJson {e}")


    def getCourseCollectionsJson(self, topicUrl):
        try:
            courseApiUrl = self.urlUtils.getCourseApiCollectionListUrl(topicUrl)
            self.browser.get("https://www.educative.io/api/")
            jsonData = self.executeJsToGetJson(courseApiUrl)
            jsonData = jsonData["instance"]["details"]
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
            self.logger.error(f"getCourseCollectionsJson {e}")


    def getCourseTopicUrlsList(self, topicUrl):
        try:
            courseUrlSelector = self.urlUtils.getCourseUrlSelector(topicUrl)
            self.browser.get(topicUrl)
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, courseUrlSelector)))
            topicUrlElements = self.browser.find_elements(By.XPATH, courseUrlSelector)
            topicUrls = []
            for topicUrlElement in topicUrlElements:
                topicUrls.append(topicUrlElement.get_attribute("href"))
            return topicUrls
        except Exception as e:
            self.logger.error(f"getCourseTopicUrlsList {e}")
