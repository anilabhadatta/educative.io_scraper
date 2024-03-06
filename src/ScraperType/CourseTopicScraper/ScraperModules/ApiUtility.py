import os

from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.ScraperType.CourseTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.UrlUtility import UrlUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


class ApiUtility:
    def __init__(self, configJson):
        self.browser = None
        self.timeout = 10
        self.osUtils = OSUtility(configJson)
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


    def getTopicApiContentJson(self, topicApiUrl):
        try:
            self.logger.info(f"Getting Topic API Content JSON from URL: {topicApiUrl}")
            retry = 1
            jsonDataToReturn = None
            while retry < 3:
                try:
                    jsonData = self.executeJsToGetJson(topicApiUrl)
                    if "components" in jsonData:
                        jsonDataToReturn = jsonData["components"]
                        self.logger.info("Successfully fetched JSON API data")
                        break
                except Exception:
                    pass
                retry += 1
                self.osUtils.sleep(2)
                self.logger.info(f"Found Error fetching Json, retrying {retry} out of 3: {topicApiUrl}")
            return jsonDataToReturn
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseApiContentJson: {lineNumber}: {e}")


    def getCourseApiContentJson(self, courseApiUrl):
        try:
            self.logger.info(f"Getting Course API Content JSON from URL: {courseApiUrl}")
            retry = 1
            jsonDataToReturn = None
            while retry < 3:
                try:
                    jsonData = self.executeJsToGetJson(courseApiUrl)
                    if "instance" in jsonData:
                        jsonDataToReturn = jsonData["instance"]
                        self.logger.info("Successfully fetched JSON API data")
                        break
                except Exception:
                    pass
                retry += 1
                self.osUtils.sleep(2)
                self.logger.info(f"Found Error fetching Json, retrying {retry} out of 3: {courseApiUrl}")
            return jsonDataToReturn
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseApiContentJson: {lineNumber}: {e}")


    def getCourseCollectionsJson(self, courseApiUrl, courseUrl):
        try:
            self.logger.info(f"Getting Course Collections JSON from URL: {courseApiUrl}")
            courseType = courseUrl.split('/')[3]
            if "module" in courseType:
                courseType = "module"
            else:
                courseType = "collection"
            jsonData = self.getCourseApiContentJson(courseApiUrl)
            jsonData = jsonData["details"]
            authorId = str(jsonData["author_id"])
            collectionId = str(jsonData["collection_id"])
            categories = jsonData["toc"]["categories"]
            courseTitle = jsonData["title"]
            topicApiUrlList = []
            topicNameList = []
            baseApiUrl = f"https://educative.io/api/collection/{authorId}/{collectionId}/page/"
            categoryType = ["COLLECTION_PROJECT", "COLLECTION_CATEGORY", "COLLECTION_ASSESSMENT", "PATH_EXTERNAL_PROJECT", "PATH_EXTERNAL_ASSESSMENT", "CLOUD_LAB"]
            topicIdx = 0
            toc = []
            for category in categories:
                if any(cType in category["type"] for cType in categoryType) and (
                        isinstance(category["id"], int) or len(category["id"]) <= 10):
                    if not category["pages"]:
                        topicApiUrl = baseApiUrl + str(category["id"]) + f"?work_type={courseType}"
                        topicApiUrlList.append(topicApiUrl)
                        topicNameList.append(category["title"])
                        category_topic = (topicIdx, category["title"], topicApiUrl)
                        toc.append(category_topic)
                        topicIdx += 1
                    else:
                        category_topic = {"category": category["title"], "topics": []}
                        toc.append(category_topic)

                        for page in category["pages"]:
                            topicApiUrl = baseApiUrl + str(page["id"]) + f"?work_type={courseType}"
                            topicApiUrlList.append(topicApiUrl)
                            topicNameList.append(page["title"])
                            category_topic["topics"].append((topicIdx, page["title"], topicApiUrl))
                            topicIdx += 1

            return {
                "courseTitle": courseTitle,
                "topicApiUrlList": topicApiUrlList,
                "topicNameList": topicNameList,
                "toc": toc
            }
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseCollectionsJson: {lineNumber}: {e}")


    def getCourseTopicUrlsList(self, topicUrl, courseUrl):
        try:
            self.logger.info(f"Getting Course Topic URLs List from Course URL: {courseUrl}")
            self.browser.get(courseUrl)
            self.logger.info(f"Topic URL: {topicUrl}")
            topicUrlSelector = self.urlUtils.getTopicUrlSelector(topicUrl)
            self.logger.info(f"Topic URL Selector: {topicUrlSelector}")
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, topicUrlSelector)))
            if "/module/" not in topicUrl:
                self.seleniumBasicUtils.browser = self.browser
                self.seleniumBasicUtils.expandAllSections()
            pathFolderName = None
            if "/module/" in topicUrl:
                pathFolderName = self.getPathFolderName()
            self.logger.info(f"Topic URL Selector: {topicUrlSelector}")
            topicUrlJsScript = f"""
            var topicUrls = document.evaluate("{topicUrlSelector}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
            var hrefData  = [];
            for (var i = 0; i < topicUrls.snapshotLength; i++) {{
                var element = topicUrls.snapshotItem(i);
                var href = 'https://www.educative.io' + element.getAttribute('href') + "?showContent=true";
                isButtonInsideHref = element.querySelector('button');
                if(isButtonInsideHref === null && href.indexOf("/certificate?") === -1) {{
                    hrefData.push(href);
                }}
            }}
            return hrefData;
            """
            topicUrls = self.browser.execute_script(topicUrlJsScript)
            return topicUrls, pathFolderName
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseTopicUrlsList: {lineNumber}: {e}")


    def getCourseUrl(self, topicUrl):
        try:
            self.logger.info("Getting Course url")
            try:
                self.browser.get(topicUrl)
            except TimeoutException:
                self.logger.info("Page Loading Issue, pressing ESC to stop page load")
                self.browser.execute_script("window.stop();")
            courseTypeSelector = f"//a[contains(@href, '/{topicUrl.split('/')[3]}/')]/span[contains(text(), 'Home')]/.."
            self.logger.info(f"Course Type Selector: {courseTypeSelector}")
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, courseTypeSelector)))
            courseUrlJsScript = f"""
            var anchorElement = document.evaluate(
                                "{courseTypeSelector}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                            ).singleNodeValue;
                            var hrefValue = "";
                            if (anchorElement) {{
                                hrefValue = anchorElement.getAttribute('href');
                            }}
            return "https://www.educative.io" + hrefValue + "?showContent=true";
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


    def getPathFolderName(self):
        try:
            self.logger.info("Module, getting path folder name")
            pathNameSelector = self.selectors["pathSelector"]
            pathScript = f"""
            var anchorElement = document.evaluate(
                    "{pathNameSelector}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            return anchorElement.text;
            """
            return self.browser.execute_script(pathScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getPathFolderName: {lineNumber}: {e}")