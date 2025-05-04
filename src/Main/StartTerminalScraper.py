import asyncio
from queue import Queue
from src.Utility.BrowserUtility import BrowserUtility
from src.Main.UpdateTxtFileFromLog import UpdateTxtFileFromLog
from src.Logging.Logger import Logger
from src.Main.MailNotify import MailNotify
from src.ScraperType.AllCourseUrlsScraper.AllCourseUrlsScraperMain import AllCourseUrlsScraper
from src.ScraperType.CourseTopicScraper.CourseTopicScraperMain import CourseTopicScraper


class StartTerminalScraper:
    def __init__(self, configJson):
        self.logger = None
        self.mailNotify = MailNotify()
        self.configJson = configJson
        self.updateTextFromLog = UpdateTxtFileFromLog(self.configJson)
        self.browserUtil = BrowserUtility(self.configJson)


    def startScraper(self):
        self.logger = Logger(self.configJson, "StartTerminal").logger
        self.logger.info("""StartTerminal Initiated...
                            To Terminate, Click on Stop ScraperType Button
                        """)
        try:
            progressQueue = Queue()
            if self.configJson['autofixtextfile'] and not self.updateTextFromLog.updateTextFileFromLogMain():
                self.logger.info("No URL found in log file. Starting Scraper from first url...")
            if self.configJson["scraperType"] == "All-Course-Urls-Text-File-Generator":
                AllCourseUrlsScraper(self.configJson, progressQueue).start()
            else:
                CourseTopicScraper(self.configJson, progressQueue).start()
            self.mailNotify.send_email("Scraping Complete")
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
            asyncio.get_event_loop().run_until_complete(self.browserUtil.shutdownChromeViaWebsocket())
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"start: {lineNumber}: {e}")
            asyncio.get_event_loop().run_until_complete(self.browserUtil.shutdownChromeViaWebsocket())
            self.mailNotify.send_email(f"Exception occured in line number {lineNumber}, {e}")
        finally:
            self.logger.debug("Exiting Scraper...")

