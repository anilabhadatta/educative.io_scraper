import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.ScraperMethod.ExtensionMethod.ScraperModules.UrlUtility import UrlUtility
from src.Utility.FileUtility import FileUtility


class ApiUtility:
    def __init__(self, configJson):
        self.browser = None
        self.timeout = 10
        self.urlUtils = UrlUtility()
        self.fileUtils = FileUtility()
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["ApiUtility"]
        self.logger = Logger(configJson, "ApiUtility").logger


    def executeJsToGetJson(self, url):
        self.logger.info(f"Executing JS to get JSON from URL")
        apiJsonScript = f"""
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
        return self.browser.execute_script(apiJsonScript)


    def getCourseApiContentJson(self, courseApiUrl):
        try:
            self.logger.info(f"Getting Course API Content JSON from URL: {courseApiUrl}")
            jsonData = self.executeJsToGetJson(courseApiUrl)
            if "components" in jsonData:
                jsonData = jsonData["components"]
                return jsonData
            return None
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseApiContentJson: {lineNumber}: {e}")


    def getCourseCollectionsJson(self, courseUrl):
        try:
            courseApiUrl = self.urlUtils.getCourseApiCollectionListUrl(courseUrl)
            self.logger.info(f"Getting Course Collections JSON from URL: {courseApiUrl}")
            jsonData = self.executeJsToGetJson(courseApiUrl)
            jsonData = jsonData["instance"]["details"]
            authorId = str(jsonData["author_id"])
            collectionId = str(jsonData["collection_id"])
            categories = jsonData["toc"]["categories"]
            courseTitle = jsonData["title"]
            topicApiUrlList = []
            topicNameList = []
            baseApiUrl = f"https://educative.io/api/collection/{authorId}/{collectionId}/page/"
            for category in categories:
                if not category["pages"]:
                    topicApiUrlList.append(baseApiUrl + str(category["id"]))
                    topicNameList.append(category["title"])
                for page in category["pages"]:
                    topicApiUrlList.append(baseApiUrl + str(page["id"]))
                    topicNameList.append(page["title"])
            return {
                "courseTitle": courseTitle,
                "topicApiUrlList": topicApiUrlList,
                "topicNameList": topicNameList
            }
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseCollectionsJson: {lineNumber}: {e}")


    def getCourseTopicUrlsList(self, courseUrl):
        try:
            self.logger.info(f"Getting Course Topic URLs List from URL: {courseUrl}")
            courseUrlSelector = self.urlUtils.getCourseUrlSelector(courseUrl)
            self.logger.info(f"Course URL Selector: {courseUrlSelector}")
            self.browser.get(courseUrl)
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, courseUrlSelector)))
            expandAllButtonSelector = self.selectors["expandAllButton"]
            self.browser.find_element(By.XPATH, expandAllButtonSelector).click()
            time.sleep(2)
            topicUrlElements = self.browser.find_elements(By.XPATH, courseUrlSelector)
            topicUrls = []
            for topicUrlElement in topicUrlElements:
                topicUrls.append(topicUrlElement.get_attribute("href"))
            return topicUrls
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseTopicUrlsList: {lineNumber}: {e}")


    def getCourseUrl(self, topicUrl):
        try:
            self.browser.get(topicUrl)
            courseTypeSelector = f"a[href*='{topicUrl.split('/')[3]}']"
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, courseTypeSelector)))
            return self.browser.find_element(By.CSS_SELECTOR, courseTypeSelector).get_attribute("href")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseUrl: {lineNumber}: {e}")
