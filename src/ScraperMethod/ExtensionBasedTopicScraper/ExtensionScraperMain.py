import os

from src.Logging.Logger import Logger
from src.Main.LoginAccount import LoginAccount
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.ApiUtility import ApiUtility
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.CodeUtility import CodeUtility
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.QuizUtility import QuizUtility
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.RemoveUtility import RemoveUtility
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.ScreenshotHtmlUtility import ScreenshotHtmlUtility
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.ShowUtility import ShowUtility
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.SingleFileUtility import SingleFileUtility
from src.ScraperMethod.ExtensionBasedTopicScraper.ScraperModules.UrlUtility import UrlUtility
from src.Utility.BrowserUtility import BrowserUtility
from src.Utility.FileUtility import FileUtility


class ExtensionScraper:
    def __init__(self, configJson):
        self.browser = None
        self.configJson = configJson
        self.outputFolderPath = self.configJson["saveDirectory"]
        self.logger = Logger(configJson, "ExtensionScraper").logger
        self.fileUtils = FileUtility()
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
        self.screenshotHtmlUtils = ScreenshotHtmlUtility(configJson)


    def start(self):
        self.logger.info("ExtensionScraper initiated...")
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
                raise Exception(f"ExtensionScraper:start: {lineNumber}: {e}")
            finally:
                if self.browser is not None:
                    self.browser.quit()
        self.logger.info("ExtensionScraper completed.")


    def scrapeCourse(self, textFileUrl):
        try:
            courseUrl = self.apiUtils.getCourseUrl(textFileUrl)
            courseApiUrl = self.apiUtils.getNextData()
            courseTopicUrlsList = self.apiUtils.getCourseTopicUrlsList(textFileUrl, courseUrl)
            startIndex = courseTopicUrlsList.index(textFileUrl) if textFileUrl in courseTopicUrlsList else 0
            self.loginUtils.checkIfLoggedIn()
            courseCollectionsJson = self.apiUtils.getCourseCollectionsJson(courseApiUrl, courseUrl)

            self.logger.debug(f"Course Topic URLs: {courseTopicUrlsList}")
            self.logger.debug(f"Course Collections JSON: {courseCollectionsJson}")
            self.logger.info(
                f"API Urls: {len(courseCollectionsJson['topicApiUrlList'])} == {len(courseTopicUrlsList)} :Topic Urls")
            if len(courseCollectionsJson["topicApiUrlList"]) != len(courseTopicUrlsList):
                raise Exception("CourseCollectionsJson and CourseTopicUrlsList Urls are not equal")

            courseTitle = self.fileUtils.filenameSlugify(courseCollectionsJson["courseTitle"])
            coursePath = os.path.join(self.outputFolderPath, courseTitle)
            self.fileUtils.createFolderIfNotExists(coursePath)

            for topicIndex in range(startIndex, len(courseTopicUrlsList)):
                courseTopicUrl = courseTopicUrlsList[topicIndex] + "?showContent=true"
                courseApiUrl = courseCollectionsJson["topicApiUrlList"][topicIndex]
                topicName = str(topicIndex) + "-" + self.fileUtils.filenameSlugify(
                    courseCollectionsJson["topicNameList"][topicIndex])
                self.logger.info(f"Scraping {topicName}: {courseTopicUrl}")
                self.loginUtils.checkIfLoggedIn()
                courseApiContentJson = self.apiUtils.getCourseApiContentJson(courseApiUrl)
                self.scrapeTopic(coursePath, topicName, courseApiContentJson, courseTopicUrl)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ExtensionScraper:scrapeCourse: {lineNumber}: {e}")


    def scrapeTopic(self, coursePath, topicName, courseApiContentJson, courseTopicUrl):
        try:
            self.seleniumBasicUtils.browser = self.browser
            self.removeUtils.browser = self.browser
            self.showUtils.browser = self.browser
            self.singleFileUtils.browser = self.browser
            self.screenshotHtmlUtils.browser = self.browser
            self.browser.get(courseTopicUrl)
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
            self.singleFileUtils.fixAllObjectTags()
            self.singleFileUtils.injectImportantScripts()
            self.singleFileUtils.makeCodeSelectable()
            courseTopicPath = os.path.join(coursePath, topicName)
            self.fileUtils.createFolderIfNotExists(courseTopicPath)
            if self.configJson["singleFileHTML"]:
                htmlPageData = self.singleFileUtils.getSingleFileHtml(topicName)
            else:
                htmlPageData = self.screenshotHtmlUtils.getFullPageScreenshotHtml(topicName)
            htmlFilePath = os.path.join(courseTopicPath, f"{topicName}.html")
            self.fileUtils.createTopicHtml(htmlFilePath, htmlPageData)
            if courseApiContentJson:
                self.logger.debug(f"Course API Content JSON: {courseApiContentJson}")
                self.logger.info(f"Downloading Code and Quiz Files if found...")
                quizComponentIndex = 0
                codeComponentIndex = 0
                codeTypes = ["CodeTest", "TabbedCode", "Code", "WebpackBin", "RunJS"]
                quizTypes = ["Quiz", "StructuredQuiz"]
                for componentIndex, component in enumerate(courseApiContentJson):
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
            raise Exception(f"ExtensionScraper:scrapeTopic: {lineNumber}: {e}")
