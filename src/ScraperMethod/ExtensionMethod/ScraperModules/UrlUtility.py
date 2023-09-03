from src.Logging.Logger import Logger


class UrlUtility:
    def __init__(self, configJson):
        self.logger = Logger(configJson, "UrlUtility").logger


    def getCourseUrl(self, url):
        return "/".join(url.split("/")[:-1])


    def getCourseUrlSelector(self, url):
        modifiedCourseUrl = "/".join(url.split("/")[3:-1]) + "/"
        return f"//a[contains(@href, '{modifiedCourseUrl}')]"


    def getCourseApiCollectionListUrl(self, url):
        url = url.split("/")
        if url[3] is "module":
            return "/".join(url[:3]) + "/api/collection/" + "/".join(url[6:-1]) + "?work_type=collection"
        return "/".join(url[:3]) + "/api/collection/" + "/".join(url[4:-1]) + "?work_type=collection"
