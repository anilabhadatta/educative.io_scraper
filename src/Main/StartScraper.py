import multiprocessing
from src.Main.UpdateTxtFileFromLog import UpdateTxtFileFromLog
from src.Logging.Logger import Logger
from src.Main.MailNotify import MailNotify
from src.ScraperType.AllCourseUrlsScraper.AllCourseUrlsScraperMain import AllCourseUrlsScraper
from src.ScraperType.CourseTopicScraper.CourseTopicScraperMain import CourseTopicScraper
from src.ScraperType.ApiScraper.ApiScraperMain import ApiScraperMain


class StartScraper:
    def __init__(self):
        self.logger = None
        self.mailNotify = MailNotify()


    def start(self, configJson, updateTextFromLog: UpdateTxtFileFromLog, progressQueue: multiprocessing.Queue):
        self.logger = Logger(configJson, "StartScraper").logger
        self.logger.info("""StartScraper Initiated...
                            To Terminate, Click on Stop ScraperType Button
                        """)
        try:
            progressQueue.put(("color", "green"))
            if configJson["scraperType"] == "All-Course-Urls-Text-File-Generator":
                AllCourseUrlsScraper(configJson, progressQueue).start()
            elif configJson["scraperType"] == "API-JSON-Scraper":
                ApiScraperMain(configJson, progressQueue).start()
            else:
                CourseTopicScraper(configJson, progressQueue).start()
            self.mailNotify.send_email("Scraping Complete")
            updateTextFromLog.setBlockScraper(True)
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"start: {lineNumber}: {e}")
            self.mailNotify.send_email(f"Exception occured in line number {lineNumber}, {e}")
            progressQueue.put(("color", "red"))
        finally:
            self.logger.debug("Exiting Scraper...")


    def startManual(self, configJson):
        self.logger = Logger(configJson, "StartScraper").logger
        self.logger.info("""StartScraper Initiated Manually...
                            To Terminate, Click on Stop ScraperType Button
                        """)
        try:
            if configJson.get("scraperType") == "API-JSON-Scraper":
                ApiScraperMain(configJson).startManual()
            else:
                CourseTopicScraper(configJson).startManual()
            # self.mailNotify.send_email("Scraping Complete")
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"startManual: {lineNumber}: {e}")
            self.mailNotify.send_email(f"Exception occured in line number {lineNumber}, {e}")
        finally:
            self.logger.debug("Exiting Scraper...")
