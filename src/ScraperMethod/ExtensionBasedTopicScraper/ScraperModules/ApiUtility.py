import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.UrlUtility import UrlUtility
from src.Utility.FileUtility import FileUtility


class ApiUtility:
    """
    A class that provides utility functions for interacting with the Educative.io website's API.

    Attributes:
        browser: A Selenium WebDriver object.
        timeout: An integer representing the timeout duration for waiting for elements to load.
        urlUtils: An instance of the UrlUtility class.
        fileUtils: An instance of the FileUtility class.
        seleniumBasicUtils: An instance of the SeleniumBasicUtility class.
        selectors: A dictionary containing CSS selectors for various elements on the website.
        logger: An instance of the Logger class.

    Methods:
        __init__(self, configJson):
            Initializes the ApiUtility class with the given configJson object.
        executeJsToGetJson(self, url):
            Executes JavaScript code to fetch JSON data from the given url.
        getCourseApiContentJson(self, courseApiUrl):
            Fetches the JSON data for the course API content from the given courseApiUrl.
        getCourseCollectionsJson(self, courseApiUrl, courseUrl):
            Fetches the JSON data for the course collections from the given courseApiUrl and courseUrl.
        getCourseTopicUrlsList(self, topicUrl, courseUrl):
            Fetches the list of topic URLs for the given topicUrl and courseUrl.
        getCourseUrl(self, topicUrl):
            Fetches the URL of the course for the given topicUrl.
        getNextData(self):
            Fetches the next data from the website.
    """

    def __init__(self, configJson):
        """
        Initializes the ApiUtility class with the given configJson object.

        Args:
            configJson: A dictionary containing configuration information for the scraper.

        Returns:
            None.
        """
        self.browser = None
        self.timeout = 10
        self.urlUtils = UrlUtility()
        self.fileUtils = FileUtility()
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["ApiUtility"]
        self.logger = Logger(configJson, "ApiUtility").logger


    def executeJsToGetJson(self, url):
        """
        Executes JavaScript code to fetch JSON data from the given url.

        Args:
            url: A string representing the URL to fetch JSON data from.

        Returns:
            The fetched JSON data.
        """
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
        """
        Fetches the JSON data for the course API content from the given courseApiUrl.

        Args:
            courseApiUrl: A string representing the URL of the course API content.

        Returns:
            The fetched JSON data.
        """
        try:
            self.logger.info(f"Getting Course API Content JSON from URL: {courseApiUrl}")
            retry = 1
            jsonDataToReturn = None
            while retry < 3:
                jsonData = self.executeJsToGetJson(courseApiUrl)
                if "components" in jsonData:
                    jsonDataToReturn = jsonData["components"]
                    self.logger.info("Successfully fetched JSON API data")
                    break
                retry += 1
                self.logger.info(f"Found Error fetching Json, retrying {retry} out of 3: {courseApiUrl}")
            return jsonDataToReturn
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseApiContentJson: {lineNumber}: {e}")


    def getCourseCollectionsJson(self, courseApiUrl, courseUrl):
        """
        Fetches the JSON data for the course collections from the given courseApiUrl and courseUrl.

        Args:
            courseApiUrl: A string representing the URL of the course API content.
            courseUrl: A string representing the URL of the course.

        Returns:
            A dictionary containing the course title, topic API URL list, and topic name list.
        """
        try:
            self.logger.info(f"Getting Course Collections JSON from URL: {courseApiUrl}")
            courseType = courseUrl.split('/')[3]
            if "module" in courseType:
                courseType = "module"
            else:
                courseType = "collection"
            jsonData = self.executeJsToGetJson(courseApiUrl)
            self.logger.debug(f"Course API JSON: {jsonData}")
            jsonData = jsonData["instance"]["details"]
            authorId = str(jsonData["author_id"])
            collectionId = str(jsonData["collection_id"])
            # todo store pages by categories
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
                        topicApiUrlList.append(baseApiUrl + str(category["id"]) + f"?work_type={courseType}")
                        topicNameList.append(category["title"])
                    for page in category["pages"]:
                        topicApiUrlList.append(baseApiUrl + str(page["id"]) + f"?work_type={courseType}")
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
        """
        Fetches the list of topic URLs for the given topicUrl and courseUrl.

        Args:
            topicUrl: A string representing the URL of the topic.
            courseUrl: A string representing the URL of the course.

        Returns:
            The list of topic URLs.
        """
        try:
            self.logger.info(f"Getting Course Topic URLs List from URL: {courseUrl}")
            # TODO scrape the index page too, why are we scrolling to this page?
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
                var href = 'https://www.educative.io' + element.getAttribute('href') + "?showContent=true";
                isButtonInsideHref = element.querySelector('button');
                if(isButtonInsideHref === null && href.indexOf("/certificate?") === -1) {{
                    hrefData.push(href);
                }}
            }}
            return hrefData;
            """
            topicUrls = self.browser.execute_script(topicUrlJsScript)
            # this seems messed up, sometime only 25 links of total 32
            return topicUrls
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseTopicUrlsList: {lineNumber}: {e}")


    def getCourseUrl(self, topicUrl):
        """
        Fetches the URL of the course for the given topicUrl.

        Args:
            topicUrl: A string representing the URL of the topic.

        Returns:
            The URL of the course.
        """
        try:
            self.browser.get(topicUrl)
            courseTypeSelector = f"a[href*='/{topicUrl.split('/')[3]}/']"
            self.logger.info(f"Course Type Selector: {courseTypeSelector}")
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, courseTypeSelector)))
            courseUrlJsScript = f"""
            var courseUrl = "https://www.educative.io" + document.querySelector("{courseTypeSelector}").getAttribute('href') + "?showContent=true";
            return courseUrl;
            """
            courseUrl = self.browser.execute_script(courseUrlJsScript)
            return courseUrl
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseUrl: {lineNumber}: {e}")


    def getNextData(self):
        """
        Fetches the next data from the website.

        Returns:
            The URL of the course API collection list.
        """
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
