import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.ScraperMethod.ExtensionMethod.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.ScraperMethod.ExtensionMethod.ScraperModules.UrlUtility import UrlUtility
from src.Utility.FileUtility import FileUtility


class ApiUtility:
    def __init__(self, configJson):
        self.browser = None
        self.timeout = 10
        self.urlUtils = UrlUtility()
        self.fileUtils = FileUtility()
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)
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


    def getCourseCollectionsJson(self, courseApiUrl):
        try:
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
            categoryType = ["COLLECTION_PROJECT", "COLLECTION_CATEGORY", "COLLECTION_ASSESSMENT"]
            for category in categories:
                if any(cType in category["type"] for cType in categoryType) and (
                        isinstance(category["id"], int) or len(category["id"]) <= 10):
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


    def getCourseTopicUrlsList(self, topicUrl, courseUrl):
        try:
            self.logger.info(f"Getting Course Topic URLs List from URL: {courseUrl}")
            self.browser.get(courseUrl)
            topicUrlSelector = self.urlUtils.getTopicUrlSelector(topicUrl)
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, topicUrlSelector)))
            if "/module/" not in topicUrl:
                self.seleniumBasicUtils.browser = self.browser
                self.seleniumBasicUtils.expandAllSections()
            self.logger.info(f"Course URL Selector: {topicUrlSelector}")
            topicUrlJsScript = f"""
            var topicUrls = document.evaluate("{topicUrlSelector}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
            var hrefData  = [];
            for (var i = 0; i < topicUrls.snapshotLength; i++) {{
                var element = topicUrls.snapshotItem(i);
                var href = 'https://www.educative.io' + element.getAttribute('href');
                hrefData.push(href);
            }}
            return hrefData;
            """
            topicUrls = self.browser.execute_script(topicUrlJsScript)
            return topicUrls
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseTopicUrlsList: {lineNumber}: {e}")


    def getCourseUrl(self, topicUrl):
        try:
            self.browser.get(topicUrl)
            courseTypeSelector = f"a[href*='/{topicUrl.split('/')[3]}/']"
            self.logger.info(f"Course Type Selector: {courseTypeSelector}")
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, courseTypeSelector)))
            courseUrlJsScript = f"""
            var courseUrl = "https://www.educative.io" + document.querySelector("{courseTypeSelector}").getAttribute('href');
            return courseUrl;
            """
            courseUrl = self.browser.execute_script(courseUrlJsScript)
            return courseUrl
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseUrl: {lineNumber}: {e}")


    def getNextData(self):
        try:
            self.logger.info(f"Getting Next Data")
            nextDataSelector = self.selectors["nextData"]
            nextDataScript = f"""
            return JSON.parse(document.querySelectorAll("{nextDataSelector}")[0].textContent);
            """
            nextData = self.browser.execute_script(nextDataScript)
            courseApiUrl = self.urlUtils.getCourseApiCollectionListUrl(nextData)
            return courseApiUrl
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getNextData: {lineNumber}: {e}")
