class UrlUtility:
    def __init__(self):
        pass


    def getCourseUrlSelector(self, url):
        modifiedCourseUrl = "/".join(url.split("/")[3:]) + "/"
        return f"//a[contains(@href, '{modifiedCourseUrl}')]"


    def getCourseApiCollectionListUrl(self, url):
        url = url.split("/")
        return "/".join(url[:3]) + "/api/collection/" + "/".join(url[4:]) + "?work_type=collection"
