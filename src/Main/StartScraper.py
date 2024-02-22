from src.Logging.Logger import Logger
from src.Main.MailNotify import MailNotify
from src.ScraperType.AllCourseUrlsScraper.AllCourseUrlsScraperMain import AllCourseUrlsScraper
from src.ScraperType.CourseTopicScraper.CourseTopicScraperMain import CourseTopicScraper


class StartScraper:
    def __init__(self):
        self.logger = None
        self.mailNotify = MailNotify()


    def start(self, configJson):
        self.logger = Logger(configJson, "StartScraper").logger
        self.logger.info("""StartScraper Initiated...
                            To Terminate, Click on Stop ScraperType Button
                        """)
        try:
            if configJson["scraperType"] == "All-Course-Urls-Text-File-Generator":
                AllCourseUrlsScraper(configJson).start()
            else:
                CourseTopicScraper(configJson).start()
            self.mailNotify.send_email("Scraping Complete")
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"start: {lineNumber}: {e}")
            self.mailNotify.send_email(f"Exception occured in line number {lineNumber}, {e}")
        finally:
            self.logger.debug("Exiting Scraper...")
