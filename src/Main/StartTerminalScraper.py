import asyncio
from queue import Queue
from src.Utility.BrowserUtility import BrowserUtility
from src.Main.UpdateTxtFileFromLog import UpdateTxtFileFromLog
from src.Logging.Logger import Logger
from src.Main.MailNotify import MailNotify
from src.ScraperType.AllCourseUrlsScraper.AllCourseUrlsScraperMain import AllCourseUrlsScraper
from src.ScraperType.CourseTopicScraper.CourseTopicScraperMain import CourseTopicScraper
from src.ScraperType.ApiScraper.ApiScraperMain import ApiScraperMain
from src.Utility.StaticAssetExtractor import run_from_config as run_static_asset_extractor
from src.Utility.StaticAssetDownloader import run_from_config as run_static_asset_downloader


class StartTerminalScraper:
    def __init__(self, configJson):
        self.logger = None
        self.mailNotify = MailNotify()
        self.configJson = configJson
        self.updateTextFromLog = UpdateTxtFileFromLog(self.configJson)
        self.browserUtil = BrowserUtility(self.configJson)


    def startScraper(self):
        return self.startAutoScraper()


    def startAutoScraper(self, progressQueue=None):
        self.logger = Logger(self.configJson, "StartTerminal").logger
        self.logger.info("""StartTerminal Initiated...
                            To Terminate, Click on Stop ScraperType Button
                        """)
        try:
            progressQueue = progressQueue or Queue()
            if self.configJson['autofixtextfile'] and not self.updateTextFromLog.updateTextFileFromLogMain():
                self.logger.info("No URL found in log file. Starting Scraper from first url...")
            if self.configJson["scraperType"] == "All-Course-Urls-Text-File-Generator":
                AllCourseUrlsScraper(self.configJson, progressQueue).start()
            elif self.configJson["scraperType"] == "API-JSON-Scraper":
                ApiScraperMain(self.configJson, progressQueue).start()
            else:
                CourseTopicScraper(self.configJson, progressQueue).start()
            self.mailNotify.send_email("Scraping Complete")
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"start: {lineNumber}: {e}")
            self.mailNotify.send_email(f"Exception occured in line number {lineNumber}, {e}")
        finally:
            asyncio.get_event_loop().run_until_complete(self.browserUtil.shutdownChromeViaWebsocket())
            self.logger.info("Exiting Scraper...")


    def extractAssets(self, progressQueue=None):
        self.logger = Logger(self.configJson, "StartTerminal").logger
        self.logger.info("Starting static asset extraction...")
        try:
            run_static_asset_extractor(config_json=self.configJson, progress_queue=progressQueue)
            self.mailNotify.send_email("Static Asset Extraction Complete")
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"extractAssets: {lineNumber}: {e}")
            self.mailNotify.send_email(f"Exception occured in line number {lineNumber}, {e}")


    def downloadAssets(self, progressQueue=None):
        self.logger = Logger(self.configJson, "StartTerminal").logger
        self.logger.info("Starting static asset download...")
        try:
            run_static_asset_downloader(config_json=self.configJson, progress_queue=progressQueue)
            self.mailNotify.send_email("Static Asset Download Complete")
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"downloadAssets: {lineNumber}: {e}")
            self.mailNotify.send_email(f"Exception occured in line number {lineNumber}, {e}")


    def extractAndDownloadAssets(self, progressQueue=None):
        self.extractAssets(progressQueue=progressQueue)
        self.downloadAssets(progressQueue=progressQueue)

