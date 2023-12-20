from src.Logging.Logger import Logger


class AllCourseUrlsScraper:
    def __init__(self, configJson):
        self.configJson = configJson
        self.logger = Logger(configJson, "ScrapeAllTopicUrls").logger
        self.browser = None


    def start(self):
        self.logger.info("All Course Urls scraper Not implemented.")
