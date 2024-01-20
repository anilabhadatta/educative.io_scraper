import os

from src.Logging.Logger import Logger
from src.Main.LoginAccount import LoginAccount
from src.ScraperType.CourseTopicScraper.ScraperModules.ApiUtility import ApiUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.CodeUtility import CodeUtility
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
    def __init__(self, configJson):
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
        self.browserUtils = BrowserUtility(configJson)
        self.loginUtils = LoginAccount(configJson)
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)
        self.removeUtils = RemoveUtility(configJson)
        self.showUtils = ShowUtility(configJson)
        self.singleFileUtils = SingleFileUtility(configJson)
        self.screenshotUtils = ScreenshotUtility(configJson)
        self.printFileUtils = PrintFileUtility(configJson)


    def start(self):
        self.logger.info("CourseTopicScraper initiated...")
        urlsTextFile = self.fileUtils.loadTextFile(self.configJson["courseUrlsFilePath"])
        for textFileUrl in urlsTextFile:
            try:
                if "?showContent=true" not in textFileUrl:
                    textFileUrl += "?showContent=true"
                self.logger.info(f"Started Scraping from Text File URL: {textFileUrl}")
                self.browser = self.browserUtils.loadBrowser()
                self.apiUtils.browser = self.browser
                self.loginUtils.browser = self.browser
                self.scrapeCourse(textFileUrl)
            except Exception as e:
                lineNumber = e.__traceback__.tb_lineno
                raise Exception(f"CourseTopicScraper:start: {lineNumber}: {e}")
            finally:
                if self.browser is not None:
                    self.browser.quit()
        self.logger.info("CourseTopicScraper completed.")


    def scrapeCourse(self, textFileUrl):
        try:
            courseUrl = self.apiUtils.getCourseUrl(textFileUrl)
            courseApiUrl = self.apiUtils.getNextData()
            topicUrlsList = self.apiUtils.getCourseTopicUrlsList(textFileUrl, courseUrl)
            startIndex = topicUrlsList.index(textFileUrl) if textFileUrl in topicUrlsList else 0
            self.loginUtils.checkIfLoggedIn()
            courseCollectionsJson = self.apiUtils.getCourseCollectionsJson(courseApiUrl, courseUrl)
            topicApiUrlList = courseCollectionsJson['topicApiUrlList']
            topicApiNameList = courseCollectionsJson["topicNameList"]
            topicApiUrlListLen = len(topicApiUrlList)
            topicUrlsListLen = len(topicUrlsList)

            self.logger.debug(f"Course Topic URLs: {topicUrlsList}")
            self.logger.debug(f"Course Api Topic Urls: {topicApiUrlList}")
            self.logger.debug(f"Course Collections JSON: {courseCollectionsJson}")
            self.logger.info(
                f"API Urls: {topicApiUrlListLen} == {topicUrlsListLen} :Topic Urls")
            if topicApiUrlListLen != topicUrlsListLen:
                raise Exception("CourseCollectionsJson and CourseTopicUrlsList Urls are not equal")

            courseTitle = self.fileUtils.filenameSlugify(courseCollectionsJson["courseTitle"])
            coursePath = os.path.join(self.outputFolderPath, courseTitle)
            self.fileUtils.createFolderIfNotExists(coursePath)
            TOCUtility.serializeTocAndStore(courseCollectionsJson["courseTitle"], courseUrl, coursePath,
                                            courseCollectionsJson["toc"], topicUrlsList)

            for topicIndex in range(startIndex, topicUrlsListLen):
                topicUrl = topicUrlsList[topicIndex]
                topicApiUrl = topicApiUrlList[topicIndex]
                filenameSlugified = self.fileUtils.filenameSlugify(topicApiNameList[topicIndex])
                topicName = f"{topicIndex:03}-{filenameSlugified}"
                self.logger.info(f"""----------------------------------------------------------------------------------
                Scraping Topic: {topicName}: {topicUrl}
                """)
                self.loginUtils.checkIfLoggedIn()
                topicApiContentJson = self.apiUtils.getCourseApiContentJson(topicApiUrl)
                self.osUtils.sleep(10)
                self.scrapeTopic(coursePath, topicName, topicApiContentJson, topicUrl)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"CourseTopicScraper:scrapeCourse: {lineNumber}: {e}")


    def scrapeTopic(self, coursePath, topicName, topicApiContentJson, topicUrl):
        try:
            self.seleniumBasicUtils.browser = self.browser
            self.removeUtils.browser = self.browser
            self.showUtils.browser = self.browser
            self.singleFileUtils.browser = self.browser
            self.screenshotUtils.browser = self.browser
            self.printFileUtils.browser = self.browser
            self.browser.get(topicUrl)
            self.seleniumBasicUtils.loadingPageAndCheckIfSomethingWentWrong()
            self.seleniumBasicUtils.waitWebdriverToLoadTopicPage()
            self.seleniumBasicUtils.addNameAttributeInNextBackButton()
            self.browserUtils.scrollPage()
            # self.browserUtils.setWindowSize()
            self.removeUtils.removeBlurWithCSS()
            self.removeUtils.removeMarkAsCompleted()
            self.removeUtils.removeUnwantedElements()
            self.showUtils.showSingleMarkDownQuizSolution()
            self.showUtils.showCodeSolutions()
            self.showUtils.showHints()
            self.showUtils.showSlides()
            pageData = None
            courseTopicPath = os.path.join(coursePath, topicName)
            topicFilePath = os.path.join(courseTopicPath, f"{topicName}.{self.configJson['fileType']}")
            self.fileUtils.createFolderIfNotExists(courseTopicPath)
            if self.configJson["scrapingMethod"] == "SingleFile-HTML":
                if self.configJson["fileType"] == "html":
                    self.singleFileUtils.fixAllObjectTags()
                    self.singleFileUtils.injectImportantScripts()
                    self.singleFileUtils.makeCodeSelectable()
                    pageData = self.singleFileUtils.getSingleFileHtml(topicName)
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
                codeTypes = ["CodeTest", "TabbedCode", "EditorCode", "Code", "WebpackBin", "RunJS"]
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
