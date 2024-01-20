import json
import os

import requests
from bs4 import BeautifulSoup
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.CourseLinkLogger import CourseLinkLogger
from src.Logging.Logger import Logger
from src.Logging.TopicLinkLogger import TopicLinkLogger
from src.Utility.BrowserUtility import BrowserUtility
from selenium.webdriver.support import expected_conditions as EC

from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


class AllCourseUrlsScraper:
    def __init__(self, configJson):
        self.browser = None
        self.proxies = None
        self.configJson = configJson
        self.logger = Logger(configJson, "ScrapeAllTopicUrls").logger
        self.browserUtils = BrowserUtility(configJson)
        self.fileUtils = FileUtility()
        self.osUtils = OSUtility(configJson)
        self.outputFolderPath = self.configJson["saveDirectory"]
        self.courseLinkLogger = CourseLinkLogger(configJson).logger
        self.courseLinkLogData = CourseLinkLogger(configJson).loadDataFromLinkLogger()
        self.topicLinkLogger = TopicLinkLogger(configJson).logger
        self.topicLinkLogData = TopicLinkLogger(configJson).loadDataFromLinkLogger()
        if self.configJson["isProxy"]:
            self.proxies = {
                'http': "http://" + self.configJson["proxy"],
                'https': "http://" + self.configJson["proxy"],
            }
        self.logger.info(f"Current IP: {requests.get("https://httpbin.org/ip", proxies=self.proxies).content}")


    def start(self):
        self.logger.info("Started All Course Urls scraper.")
        try:
            allDataFromEducative = json.loads(
                requests.get("https://www.educative.io/api/reader/featured_items").content)
            allCoursesData = allDataFromEducative["works"]
            allPathsData = allDataFromEducative["tracks"]
            allCourseLinks = self.generateLinks(allCoursesData, "courses")
            allPathsLinks = self.generateLinks(allPathsData, "paths")
            self.logger.debug(allCourseLinks)
            self.logger.debug(allPathsLinks)
            self.logger.info(f"Received Course Links {len(allCourseLinks)} and Path Links {len(allPathsLinks)}")
            self.generateCourseTopicLinks(allCourseLinks)
            self.generatePathTopicLinks(allPathsLinks)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CourseTopicScraper:start: {lineNumber}: {e}")


    def generateLinks(self, allData, type):
        links = []
        for data in allData:
            if type == "courses":
                url = "courses/" + data["course_url_slug"] if ("course_url_slug" in data and
                       data["course_url_slug"]) else "collection/" + str(data["author_id"]) + "/" + str(data["id"])
                url = ["https://www.educative.io/" + url]
            else:
                url = "path/" + data["course_url_slug"] if ("course_url_slug" in data and
                       data["course_url_slug"]) else "collection/" + str(data["author_id"]) + "/" + str(data["id"])
                url = ["https://www.educative.io/" + url, data['module_count'], data['work_titles']]
            self.logger.debug(url)
            links.append(url)
        return links


    def generateCourseTopicLinks(self, allCourseLinks):
        try:
            for courseLink in allCourseLinks:
                if courseLink[0] in self.courseLinkLogData:
                    self.logger.info(f"Skipping {courseLink[0]}")
                    continue
                self.logger.info(f"Getting Topic url for Course url: {courseLink[0]}")
                response = requests.get(courseLink[0], proxies=self.proxies)
                if response.status_code == 200:
                    if 'Page Not Found!' in response.text or "Looks like there's been a glitch..." in response.text:
                        raise Exception(f"Page not Found Error on course url: {courseLink[0]}")
                    soup = BeautifulSoup(response.content, 'html.parser')
                    topicLinks = soup.find_all('a', id=lambda x: x and 'lesson-title' in x)
                    firstTopicLink = "https://www.educative.io" + topicLinks[0].get('href')
                    self.logger.info(firstTopicLink)
                    if firstTopicLink not in self.topicLinkLogData:
                        self.topicLinkLogger.info(firstTopicLink)
                    self.courseLinkLogger.info(courseLink[0])
                else:
                    raise Exception(f"Error 404 on course url: {courseLink[0]}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"generateCourseTopicLinks: {lineNumber}: {e}")


    def generatePathTopicLinks(self, allPathsLinks):
        xPathForModules = "//a[contains(@href,'/module/') and contains(@href,'module/lesson/')=false]"
        self.browser = self.browserUtils.loadBrowser()
        try:
            for pathLink in allPathsLinks:
                if pathLink[0] in self.courseLinkLogData:
                    self.logger.info(f"Skipping {pathLink[0]}")
                    continue
                self.logger.info(f"Getting Module urls for Path url: {pathLink[0]}")
                self.browser.get(pathLink[0])
                try:
                    self.osUtils.sleep(2)
                    WebDriverWait(self.browser, 10).until(EC.presence_of_element_located(
                        (By.XPATH, xPathForModules + "/following-sibling::div[2]")))
                except TimeoutException:
                    raise Exception("Timeout as the element not located")
                self.logger.info("Page loaded successfully")

                clickOnShowContentJsScript = f"""
                var showButton = document.evaluate("{xPathForModules}/following-sibling::div[1]", 
                                        document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                for (var i = 0; i < showButton.snapshotLength; i++) {{
                    var element = showButton.snapshotItem(i);
                    if (element.textContent.trim() === "Show Content") {{
                        element.click();
                    }}
                }}"""
                retryExpand = 0
                while retryExpand < 3:
                    self.logger.info("Expanding all sections")
                    self.osUtils.sleep(2)
                    self.browser.execute_script(clickOnShowContentJsScript)
                    retryExpand += 1

                getTopicUrlsJsScript = f"""
                var urlContainer = document.evaluate("{xPathForModules}/following-sibling::div[2]", 
                                        document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                var hrefData = []
                for (var i = 0; i < urlContainer.snapshotLength; i++) {{
                    var element = urlContainer.snapshotItem(i);
                    var link = "https://www.educative.io" + element.querySelector("a").getAttribute('href');
                    hrefData.push(link);
                }}
                return hrefData"""
                firstTopicLinks = self.browser.execute_script(getTopicUrlsJsScript)
                if len(firstTopicLinks) != pathLink[1]:
                    raise Exception(f"{len(firstTopicLinks)} != {pathLink[1]} Not Matching Path url: {pathLink[0]}")
                for firstTopicLink in firstTopicLinks:
                    if firstTopicLink not in self.topicLinkLogData:
                        self.logger.info(firstTopicLink)
                        self.topicLinkLogger.info(firstTopicLink)
                self.courseLinkLogger.info(pathLink[0])
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"generatePathTopicLinks: {lineNumber}: {e}")
        finally:
            if self.browser is not None:
                self.browser.quit()