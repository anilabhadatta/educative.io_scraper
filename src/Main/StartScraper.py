from src.Logging.Logger import Logger
from src.ScraperType.AllCourseUrlsScraper.AllCourseUrlsScraperMain import AllCourseUrlsScraper
from src.ScraperType.CourseTopicScraper.CourseTopicScraperMain import CourseTopicScraper


class StartScraper:
    def __init__(self):
        self.logger = None


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
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"start: {lineNumber}: {e}")
        finally:
            self.logger.debug("Exiting ScraperType...")
