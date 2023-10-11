from src.Logging.Logger import Logger
from src.Utility.CourseUtil import CourseUtil

class ScrapeAllTopicUrls:
    def __init__(self, configJson):
        self.configJson = configJson
        self.logger = Logger(configJson, "ScrapeAllTopicUrls").logger
        self.browser = None
        self.courseUtil = CourseUtil(configJson)

    def start(self):
        self.logger.info("AllTopicUrls scraper executing!.")
        # todo, pass url for scraping
        self.courseUtil.get_course_api_url("https://www.educative.io/collection/6226925030735872/6693327303868416?work_type=collection")
        # self.courseUtil.get_course_api_url("https://www.educative.io/collection/dynamodb-from-basic-to-advance?work_type=collection")

if __name__ == "__main__":
    scrapeAllTopicUrls = ScrapeAllTopicUrls()
    scrapeAllTopicUrls.start()
