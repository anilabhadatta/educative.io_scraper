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
        # pass course index page with trailing /
        self.courseUtil.scrape_course_content(
            "https://www.educative.io/courses/ds-and-algorithms-in-python/")


if __name__ == "__main__":
    scrapeAllTopicUrls = ScrapeAllTopicUrls({})
    scrapeAllTopicUrls.start()
