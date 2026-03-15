import asyncio
import os
from urllib.parse import urlparse

from src.Logging.Logger import Logger
from src.Main.LoginAccount import LoginAccount
from src.ScraperType.CourseTopicScraper.ScraperModules.ApiUtility import ApiUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.CodeUtility import CodeUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.NetworkMonitor import NetworkMonitor
from src.ScraperType.CourseTopicScraper.ScraperModules.PrintFileUtility import PrintFileUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.QuizUtility import QuizUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.RemoveUtility import RemoveUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.ScreenshotUtility import ScreenshotUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.ShowUtility import ShowUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.SingleFileUtility import SingleFileUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.UrlUtility import UrlUtility
from src.Utility.TOCUtility import TOCUtility
from src.Utility.BrowserUtility import BrowserUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility

class CourseTopicScraper:
    def __init__(self, configJson, progressQueue):
        self.browser = None
        self.configJson = configJson
        self.outputFolderPath = self.configJson["saveDirectory"]
        self.logger = Logger(configJson, "CourseTopicScraper").logger
        self.fileUtils = FileUtility()
        self.osUtils = OSUtility(configJson)
        self.apiUtils = ApiUtility(configJson)
        self.urlUtils = UrlUtility()
        self.codeUtils = CodeUtility(configJson)
        self.quizUtils = QuizUtility(configJson)
        self.loginUtils = LoginAccount(configJson)
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)
        self.removeUtils = RemoveUtility(configJson)
        self.showUtils = ShowUtility(configJson)
        self.singleFileUtils = SingleFileUtility(configJson)
        self.screenshotUtils = ScreenshotUtility(configJson)
        self.printFileUtils = PrintFileUtility(configJson)
        self.browserUtils = BrowserUtility(self.configJson)
        self.networkMonitor = NetworkMonitor(self.configJson)
        selectorPath = os.path.join(os.path.dirname(__file__), "ScraperModules", "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["CourseTopicScraper"]
        self.progressQueue = progressQueue


    def start(self):
        self.logger.info("CourseTopicScraper initiated...")
        urlsTextFile = self.fileUtils.loadTextFile(self.configJson["courseUrlsFilePath"])
        self.progressQueue.put(("progress-topic", 0))
        self.progressQueue.put(("progress-course", 0))
        self.progressQueue.put(("max-course", len(urlsTextFile)))
        for textFileIdx, textFileUrl in enumerate(urlsTextFile):
            try:
                self.progressQueue.put(("progress-course", textFileIdx+1))
                if "?showContent=true" not in textFileUrl:
                    textFileUrl += "?showContent=true"
                self.logger.info(f"Started Scraping from Text File URL: {textFileUrl}")
                self.browser = self.browserUtils.loadBrowser()
                self.apiUtils.browser = self.browser
                self.loginUtils.browser = self.browser
                self.browser.set_window_size(1920, 1080)
                if self.configJson["moduleType"] == "COURSE-PATH":
                    self.scrapeCourseOrPath(textFileUrl)
                if self.configJson["moduleType"] in ("CLOUDLAB", "PROJECT"):
                    self.scrapeCloudLabOrProject(textFileUrl)
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
            except Exception as e:
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                lineNumber = e.__traceback__.tb_lineno
                raise Exception(f"CourseTopicScraper:start: {lineNumber}: {e}")
        self.logger.info("CourseTopicScraper completed.")


    def startManual(self):
        self.logger.info("CourseTopicScraper Manual initiated...")
        try:
            existingDevToolUrl = self.browserUtils.getDevToolsUrl()
            parsed_url = urlparse(existingDevToolUrl)
            self.logger.info(existingDevToolUrl)
            self.browserUtils.devToolUrl = f"{parsed_url.hostname}:{parsed_url.port}"
            self.browser = self.browserUtils.loadBrowser()
            self.browser.set_window_size(1920, 1080)
            self.scrapeTopicManual()
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CourseTopicScraper:startManual: {lineNumber}: {e}")
        self.logger.info("CourseTopicScraper Manual completed.")


    def scrapeCourseOrPath(self, textFileUrl):
        try:
            courseUrl = self.apiUtils.getCourseUrl(textFileUrl)

            self.networkMonitor.browser = self.browser
            self.apiUrls = self.networkMonitor.getAPIUrls()
            courseApiUrlV2 = self.apiUtils.getCourseApiUrlFromNetworkUrls(self.apiUrls, courseUrl)
            self.logger.info(f"Derived Course API URL from network capture: {courseApiUrlV2}")
            courseApiUrl = self.apiUtils.getAuthorAndCollectionId()
            if not courseApiUrlV2:
                self.logger.warning(
                    "Network capture did not yield a course API URL; "
                    "falling back to author/collection extraction."
                )
                self.logger.debug(f"Captured API URLs ({len(self.apiUrls)}): {self.apiUrls}")
                courseApiUrlV2 = courseApiUrl
            self.logger.info(f"Derived Course API URL from author/collection logic: {courseApiUrl}")

            topicUrlsList, pathFolderName = self.apiUtils.getCourseTopicUrlsList(textFileUrl, courseUrl)
            # Remove duplicates while preserving order
            originalLen = len(topicUrlsList)
            seen = set()
            topicUrlsList = [url for url in topicUrlsList if not (url in seen or seen.add(url))]
            if len(topicUrlsList) < originalLen:
                duplicatesRemoved = originalLen - len(topicUrlsList)
                self.logger.warning(f"Removed {duplicatesRemoved} duplicate URL(s) from topicUrlsList")
            startIndex = topicUrlsList.index(textFileUrl) if textFileUrl in topicUrlsList else 0
            self.loginUtils.checkIfLoggedIn()
            courseCollectionsJson = self.apiUtils.getCourseCollectionsJson(courseApiUrlV2, courseUrl)
            topicApiUrlList = courseCollectionsJson['topicApiUrlList']
            topicApiNameList = courseCollectionsJson["topicNameList"]
            topicApiUrlListLen = len(topicApiUrlList)
            topicUrlsListLen = len(topicUrlsList)

            self.logger.debug(f"Course Topic URLs: {topicUrlsList}")
            self.logger.debug(f"Course Api Topic Urls: {topicApiUrlList}")
            self.logger.debug(f"Course Collections JSON: {courseCollectionsJson}")
            self.logger.info(f"API Urls: {topicApiUrlListLen} == {topicUrlsListLen} :Topic Urls")
            if topicApiUrlListLen != topicUrlsListLen:
                self.logger.warning(
                    f"Primary collection API count mismatch ({topicApiUrlListLen} != {topicUrlsListLen}). "
                    f"Trying fallback endpoint for topic API URLs."
                )
                courseCollectionsJson = self.apiUtils.getCourseCollectionsJson(courseApiUrl, courseUrl)
                topicApiUrlList  = courseCollectionsJson["topicApiUrlList"]
                topicApiNameList = courseCollectionsJson["topicNameList"]
                topicApiUrlListLen = len(topicApiUrlList)

                self.logger.info( f"API Urls: {topicApiUrlListLen} == {topicUrlsListLen} :Topic Urls")
                self.logger.debug(f"Course Topic URLs: {topicUrlsList}")
                self.logger.debug(f"Course Api Topic Urls: {topicApiUrlList}")
                if topicApiUrlListLen != topicUrlsListLen:
                    apiUrlsSet = set(topicApiUrlList)
                    topicUrlsSet = set(topicUrlsList)
                    self.logger.debug(f"Extra API URLs (not in topic URLs): {apiUrlsSet - topicUrlsSet}")
                    self.logger.debug(f"Extra in Topic URLs (not API URLs): {topicUrlsSet - apiUrlsSet}")
                    raise Exception("CourseCollectionsJson and CourseTopicUrlsList Urls are not equal")

            courseTitle = self.fileUtils.filenameSlugify(courseCollectionsJson["courseTitle"])
            if pathFolderName:
                pathFolderName = self.fileUtils.filenameSlugify(pathFolderName)
                coursePath = os.path.join(self.outputFolderPath, pathFolderName, courseTitle)
            else:
                coursePath = os.path.join(self.outputFolderPath, courseTitle)
            self.fileUtils.createFolderIfNotExists(coursePath)
            TOCUtility.serializeTocAndStore(courseCollectionsJson["courseTitle"], courseUrl, coursePath,
                                            courseCollectionsJson["toc"], topicUrlsList)
            self.progressQueue.put(("max-topic", topicUrlsListLen))

            for topicIndex in range(startIndex, topicUrlsListLen):
                self.progressQueue.put(("progress-topic", topicIndex+1))
                topicUrl = topicUrlsList[topicIndex]
                topicApiUrl = topicApiUrlList[topicIndex]
                filenameSlugified = self.fileUtils.filenameSlugify(topicApiNameList[topicIndex])
                topicName = f"{topicIndex:03}-{filenameSlugified}"
                self.logger.info(f"""----------------------------------------------------------------------------------
                Scraping Topic: {topicName}: {topicUrl}
                """)
                self.loginUtils.checkIfLoggedIn()
                topicApiContentJson = self.apiUtils.getTopicApiContentJson(topicApiUrl)
                if not topicApiContentJson:
                    url = topicUrl.split("/")
                    if not (url[-1] in ["assessment?showContent=true", "cloudlab?showContent=true", "project?showContent=true", "mock-interview?showContent=true"]):
                        raise Exception("Cannot fetch content from Topic Api Url")
                self.osUtils.sleep(10)
                self.scrapeTopic(coursePath, topicName, topicApiContentJson, topicUrl)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CourseTopicScraper:scrapeCourse: {lineNumber}: {e}")
        

    def scrapeCloudLabOrProject(self, textFileUrl):
        try:
            self.browser.get(textFileUrl)
            self.osUtils.sleep(5)
            self.seleniumBasicUtils.browser = self.browser
            self.seleniumBasicUtils.clickStartCloudlabsOrProject()
            self.seleniumBasicUtils.clickEndLabForCloudlabs()
            
            self.logger.info("Finding Sidebar topics")
            sideBarTopicsSelector = self.selectors["sideBarTopics"][f'{self.configJson["moduleType"]}']
            sideBarTopicsJsScript = f"""return document.querySelectorAll("{sideBarTopicsSelector}");"""
            sideBarTopics = self.browser.execute_script(sideBarTopicsJsScript)
            
            highlightedTopicProp = self.selectors["highlightedTopic"][f'{self.configJson["moduleType"]}']
            self.progressQueue.put(("max-topic", len(sideBarTopics)))
            for highlightedTopicIdx in range(len(sideBarTopics)):
                self.progressQueue.put(("progress-topic", highlightedTopicIdx+1))
                sideBarTopics = self.browser.execute_script(sideBarTopicsJsScript)
                highlightedTopicJsScript = f"""return arguments[0].getAttribute("class").search("{highlightedTopicProp}") !== -1"""
                highlightedTopic = self.browser.execute_script(highlightedTopicJsScript, sideBarTopics[highlightedTopicIdx])

                if highlightedTopic:
                    courseHeaderSelector = self.selectors["courseHeader"][f'{self.configJson["moduleType"]}']
                    courseHeaderJsScript = f"""return document.querySelectorAll("{courseHeaderSelector}")[0].innerText;"""
                    courseName = self.browser.execute_script(courseHeaderJsScript)
                    folderNameSlugified = self.fileUtils.filenameSlugify(courseName)
                    currentPath = os.path.join(self.outputFolderPath, folderNameSlugified)

                    topicHeaderSelector = self.selectors["topicHeader"][f'{self.configJson["moduleType"]}']
                    topicHeaderJsScript = f"""return document.querySelectorAll("{topicHeaderSelector}")[0].innerText;"""
                    topicName = self.browser.execute_script(topicHeaderJsScript)
                    filenameSlugified = self.fileUtils.filenameSlugify(topicName)
                    topicName = f"{highlightedTopicIdx:03}-{filenameSlugified}"
                    self.logger.info(f"Scraping topic: {courseName}/{topicName}")

                    topicUrl = self.browser.current_url
                    self.logger.info(f"""----------------------------------------------------------------------------------
                                    Scraping Topic: {topicName}: {topicUrl}
                                    """)
                    extraArgs = {"removeVScodeProjectWindow" : True, "resizeHorizontalGlutter": True}
                    self.scrapeTopic(currentPath, topicName, None, topicUrl, extraArgs)

                    if highlightedTopicIdx + 1 < len(sideBarTopics):
                        clickNextTopicJSScript = f"""arguments[0].click()"""
                        sideBarTopics = self.browser.execute_script(sideBarTopicsJsScript)
                        self.browser.execute_script(clickNextTopicJSScript, sideBarTopics[highlightedTopicIdx + 1])
                        self.osUtils.sleep(10)
                    else:
                        break
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CourseTopicScraper:scrapeCloudLabOrProject: {lineNumber}: {e}")


    def scrapeTopicManual(self):
        try:
            sideBarTopicsSelector = self.selectors["sideBarTopics"][f'{self.configJson["moduleType"]}']
            sideBarTopicsJsScript = f"""return document.querySelectorAll("{sideBarTopicsSelector}");"""
            sideBarTopics = self.browser.execute_script(sideBarTopicsJsScript)

            highlightedTopicProp = self.selectors["highlightedTopic"][f'{self.configJson["moduleType"]}']
            for highlightedTopicIdx in range(len(sideBarTopics)):
                sideBarTopics = self.browser.execute_script(sideBarTopicsJsScript)
                highlightedTopicJsScript = f"""return arguments[0].getAttribute("class").search("{highlightedTopicProp}") !== -1"""
                highlightedTopic = self.browser.execute_script(highlightedTopicJsScript, sideBarTopics[highlightedTopicIdx])

                if highlightedTopic:
                    courseHeaderSelector = self.selectors["courseHeader"][f'{self.configJson["moduleType"]}']
                    courseHeaderJsScript = f"""return document.querySelectorAll("{courseHeaderSelector}")[0].innerText;"""
                    courseName = self.browser.execute_script(courseHeaderJsScript)
                    folderNameSlugified = self.fileUtils.filenameSlugify(courseName)
                    currentPath = os.path.join(self.outputFolderPath, folderNameSlugified)

                    topicHeaderSelector = self.selectors["topicHeader"][f'{self.configJson["moduleType"]}']
                    topicHeaderJsScript = f"""return document.querySelectorAll("{topicHeaderSelector}")[0].innerText;"""

                    topicName = self.browser.execute_script(topicHeaderJsScript)
                    filenameSlugified = self.fileUtils.filenameSlugify(topicName)
                    topicName = f"{highlightedTopicIdx:03}-{filenameSlugified}"
                    topicUrl = self.browser.current_url
                    self.logger.info(f"""----------------------------------------------------------------------------------
                                    Scraping Topic: {topicName}: {topicUrl}
                                    """)
                    extraArgs = {"removeVScodeProjectWindow" : True, "resizeHorizontalGlutter": True}
                    self.scrapeTopic(currentPath, topicName, None, topicUrl, extraArgs)

                    if self.configJson["autonext"] and highlightedTopicIdx + 1 < len(sideBarTopics):
                        clickNextTopicJSScript = f"""arguments[0].click()"""
                        sideBarTopics = self.browser.execute_script(sideBarTopicsJsScript)
                        self.browser.execute_script(clickNextTopicJSScript, sideBarTopics[highlightedTopicIdx + 1])
                        self.osUtils.sleep(10)
                    else:
                        break

        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CourseTopicScraper:scrapeTopicManual: {lineNumber}: {e}")
        

    def scrapeTopic(self, coursePath, topicName, topicApiContentJson, topicUrl, extraArgs=dict()):
        try:
            self.seleniumBasicUtils.browser = self.browser
            self.removeUtils.browser = self.browser
            self.showUtils.browser = self.browser
            self.singleFileUtils.browser = self.browser
            self.screenshotUtils.browser = self.browser
            self.printFileUtils.browser = self.browser
            courseTopicPath = os.path.join(coursePath, topicName)
            topicFilePath = os.path.join(courseTopicPath, f"{topicName}.{self.configJson['fileType']}")
            self.fileUtils.createFolderIfNotExists(courseTopicPath)
            pageData = None
            retries = 1

            while retries < 3:
                self.logger.info(f"Trying to load webpage {retries} of 2")
                try:
                    '''Creates new tab and closes the older tab'''
                    originalWindow = self.browser.current_window_handle
                    self.browser.switch_to.new_window('tab')
                    newWindow = self.browser.current_window_handle
                    self.logger.info(f"{originalWindow} {newWindow}")

                    self.browser.switch_to.window(originalWindow)
                    self.browser.close()

                    self.browser.switch_to.window(newWindow)
                    # self.singleFileUtils.injectSingleFileViaCDP()
                    self.browser.get(topicUrl)
                except:
                    self.logger.info("Page Loading Issue, pressing ESC to stop page load")
                    self.browser.execute_script("window.stop();")
                self.browser.set_window_size(1920, 1080)
                if self.seleniumBasicUtils.waitWebdriverToLoadTopicPage():
                    break
                retries += 1
                if retries == 3:
                    raise Exception("Exception Caused: due to captcha or page load issue")
            if "resizeHorizontalGlutter" in extraArgs and extraArgs["resizeHorizontalGlutter"]:
                self.seleniumBasicUtils.resizeHorizontalGlutter()
            if "removeVScodeProjectWindow" in extraArgs and extraArgs["removeVScodeProjectWindow"]:
                self.removeUtils.removeVScodeProjectWindow()
            self.seleniumBasicUtils.addNameAttributeInNextBackButton()
            self.browserUtils.scrollPage()
            self.removeUtils.removeDialogBoxIfVisible()
            self.removeUtils.removeBlurWithCSS()
            self.removeUtils.removeMarkAsCompleted()
            self.removeUtils.removeUnwantedElements()
            self.showUtils.showSingleMarkDownQuizSolution()
            self.showUtils.showCodeSolutions()
            self.showUtils.showHints()
            self.showUtils.showHintsV2()
            self.showUtils.showSlides()
            self.browserUtils.setWindowSize()
            self.browserUtils.scrollPage()

            if self.configJson["scrapingMethod"] == "SingleFile-HTML":
                if self.configJson["fileType"] == "html":
                    self.singleFileUtils.fixAllObjectTags()
                    self.singleFileUtils.makeCodeSelectable()
                    if not self.configJson["useExtension"]:
                        self.singleFileUtils.injectSingleFileScriptsV1()
                        pageData = self.singleFileUtils.getSingleFileHtmlV1()
                    if self.configJson["useExtension"]:
                        pageData = self.singleFileUtils.getSingleFileHtmlV2()
                elif self.configJson["fileType"] == "html2pdf":
                    pageData = self.printFileUtils.printPdfAsCdp(topicName)
            if not pageData:
                pageData = self.screenshotUtils.getFullPageScreenshot(topicName)
                if "html" in self.configJson["fileType"]:
                    pageData = self.fileUtils.getHtmlWithImage(pageData, topicName)

            if self.configJson["fileType"] == "html":
                self.fileUtils.createTopicHtml(topicFilePath, pageData)
            elif self.configJson["fileType"] == "png":
                self.fileUtils.createPngFile(topicFilePath, pageData)
            elif self.configJson["fileType"] == "png2pdf":
                self.fileUtils.createPng2PdfFile(topicFilePath, pageData)
            elif self.configJson["fileType"] == "html2pdf":
                self.fileUtils.createHtml2PdfFile(topicFilePath, pageData)
            self.logger.info("Topic File Successfully Created")

            if topicApiContentJson:
                self.logger.debug(f"Course API Content JSON: {topicApiContentJson}")
                self.logger.info(f"Downloading Code and Quiz Files if found...")
                quizComponentIndex = 0
                codeComponentIndex = 0
                codeTypes = ["CodeTest", "TabbedCode", "EditorCode", "Code", "WebpackBin", "RunJS", "Sandpack"]
                quizTypes = ["Quiz", "StructuredQuiz"]
                for componentIndex, component in enumerate(topicApiContentJson):
                    componentType = component["type"]
                    if any(item in componentType for item in codeTypes) and "content" in component:
                        self.codeUtils.downloadCodeFiles(courseTopicPath, component, codeComponentIndex)
                        codeComponentIndex += 1
                    elif any(item in componentType for item in quizTypes) and "content" in component:
                        self.quizUtils.downloadQuizFiles(courseTopicPath, component, quizComponentIndex)
                        quizComponentIndex += 1
                self.logger.info(f"Code and Quiz Files Downloaded if found.")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CourseTopicScraperMain:scrapeTopic: {lineNumber}: {e}")
