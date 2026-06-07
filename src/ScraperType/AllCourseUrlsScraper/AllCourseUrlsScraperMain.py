import json
import os

import cloudscraper
from bs4 import BeautifulSoup
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.CourseLinkLogger import CourseLinkLogger
from src.Logging.Logger import Logger
from src.Logging.TopicLinkLogger import TopicLinkLogger
from src.Logging.CloudLabLinkLogger import CloudLabLinkLogger
from src.Logging.ProjectLinkLogger import ProjectLinkLogger
from src.Utility.BrowserUtility import BrowserUtility
from selenium.webdriver.support import expected_conditions as EC

from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


class AllCourseUrlsScraper:
    def __init__(self, configJson, progressQueue):
        self.browser = None
        self.proxies = None
        self.cloudscraper = cloudscraper.create_scraper()
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
        self.cloudLabLinkLogger = CloudLabLinkLogger(configJson).logger
        self.cloudLabLinkLogData = CloudLabLinkLogger(configJson).loadDataFromLinkLogger()
        self.projectLinkLogger = ProjectLinkLogger(configJson).logger
        self.projectLinkLogData = ProjectLinkLogger(configJson).loadDataFromLinkLogger()

        if self.configJson["isProxy"]:
            self.proxies = {
                'http': "http://" + self.configJson["proxy"],
                'https': "http://" + self.configJson["proxy"],
            }
        self.logger.info(f"Current IP: {self.cloudscraper.get('https://httpbin.org/ip', proxies=self.proxies).content}")

        categories_raw = self.configJson.get('excelCategories', ['courses', 'path', 'cloudlabs', 'projects', 'answers', 'blog', 'newsletter'])
        if isinstance(categories_raw, str):
            import ast
            try:
                self.valid_categories = ast.literal_eval(categories_raw)
            except:
                self.valid_categories = ['courses', 'path', 'cloudlabs', 'projects', 'answers', 'blog', 'newsletter']
        else:
            self.valid_categories = categories_raw


    def start(self):
        self.logger.info("Started All Course Urls scraper.")
        try:
            allDataFromEducative = json.loads(
                self.cloudscraper.get("https://www.educative.io/api/reader/featured_items").content)
            allCoursesData = allDataFromEducative["works"]
            allPathsData = allDataFromEducative["tracks"]
            allCloudLabData = allDataFromEducative["standalone_cloudlabs"]
            allProjectData = allDataFromEducative["standalone_projects"]
            allCourseLinks = self.generateLinks(allCoursesData, "courses") if 'courses' in self.valid_categories else []
            allPathsLinks = self.generateLinks(allPathsData, "paths") if 'path' in self.valid_categories else []
            allCloudLabLinks = self.generateLinks(allCloudLabData, "cloudlabs") if 'cloudlabs' in self.valid_categories else []
            allProjectLinks = self.generateLinks(allProjectData, "projects") if 'projects' in self.valid_categories else []
            self.logger.debug(allCourseLinks)
            self.logger.debug(allPathsLinks)
            self.logger.debug(allCloudLabLinks)
            self.logger.debug(allProjectLinks)
            self.logger.info(f"Received Course Links {len(allCourseLinks)} and Path Links {len(allPathsLinks)} and CloudLab Links {len(allCloudLabLinks)} and Project Links {len(allProjectLinks)}")
            
            if 'courses' in self.valid_categories:
                self.generateCourseTopicLinks(allCourseLinks)
            if 'path' in self.valid_categories:
                self.generatePathTopicLinks(allPathsLinks)
            if 'cloudlabs' in self.valid_categories:
                self.generateCloudLabLinks(allCloudLabLinks)
            if 'projects' in self.valid_categories:
                self.generateProjectLinks(allProjectLinks)
                
            self.logger.info("Completed Scraping Topic Urls")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"AllCourseUrlsScraper:start: {lineNumber}: {e}")


    def generateLinks(self, allData, type):
        links = []
        for idx, data in enumerate(allData):
            title = data.get("title") or "<unknown>"
            self.logger.info(f"Generating link for {type} {idx + 1}/{len(allData)}: {title}")
            parent_pal = data.get("parent_pal")
            if parent_pal == "CODING_INTERVIEW_PREP":
                self.logger.info(
                    f"Skipping {type} with title {title} as it is part of parent pal {parent_pal}"
                )
                continue
            if type == "courses":
                url = "courses/" + data["course_url_slug"] if ("course_url_slug" in data and
                       data["course_url_slug"]) else "collection/" + str(data["author_id"]) + "/" + str(data["id"])
                url = ["https://www.educative.io/" + url]
            elif type == "paths":
                url = "path/" + data["course_url_slug"] if ("course_url_slug" in data and
                       data["course_url_slug"]) else "collection/" + str(data["author_id"]) + "/" + str(data["id"])
                url = ["https://www.educative.io/" + url, data['module_count'], data['work_titles']]
            else:
                url = ["https://www.educative.io/" + type + "/" + data["url_slug"]]
                
            self.logger.debug(url)
            links.append(url)
        return links


    def generateCourseTopicLinks(self, allCourseLinks):
        try:
            for idx, courseLink in enumerate(allCourseLinks):
                self.logger.info(f"Processing Course url {idx + 1}/{len(allCourseLinks)}: {courseLink[0]}")
                if courseLink[0] in self.courseLinkLogData:
                    self.logger.info(f"Skipping {courseLink[0]}")
                    continue
                self.logger.info(f"Getting Topic url for Course url: {courseLink[0]}")
                response = self.cloudscraper.get(courseLink[0], proxies=self.proxies)
                if response.status_code == 200:
                    if 'Page Not Found!' in response.text or "Looks like there's been a glitch..." in response.text:
                        raise Exception(f"Page not Found Error on course url: {courseLink[0]}")
                    soup = BeautifulSoup(response.content, 'html.parser')
                    topicLinks = soup.find_all('a', class_=lambda x: x and 'Lesson_' in x)
                    self.logger.debug(f"TopicLinks: {topicLinks}")
                    if not topicLinks:
                        self.logger.warning(
                            f"No lesson links found for course url: {courseLink[0]}; skipping for now"
                        )
                        continue
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
    

    def generateCloudLabLinks(self, allCloudLabLinks):
        try:
            for cloudLabLink in allCloudLabLinks:
                if cloudLabLink[0] in self.cloudLabLinkLogData:
                    self.logger.info(f"Skipping {cloudLabLink[0]}")
                    continue
                self.cloudLabLinkLogger.info(cloudLabLink[0])
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"generateCloudLabLinks: {lineNumber}: {e}")

        
    def generateProjectLinks(self, allProjectLinks):
        try:
            for projectLink in allProjectLinks:
                if projectLink[0] in self.projectLinkLogData:
                    self.logger.info(f"Skipping {projectLink[0]}")
                    continue
                self.projectLinkLogger.info(projectLink[0])
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"generateProjectLinks: {lineNumber}: {e}")


    def generatePathTopicLinks(self, allPathsLinks):
        xPathForModules = "//a[contains(@href,'/module/') and contains(@href,'module/lesson/')=false]"
        try:
            self.browser = self.browserUtils.loadBrowser()
            for pathLink in allPathsLinks:
                if pathLink[0] in self.courseLinkLogData or "become-a-python-developer" in pathLink[0]:
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