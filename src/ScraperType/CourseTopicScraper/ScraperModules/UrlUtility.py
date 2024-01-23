class UrlUtility:
    def __init__(self):
        pass


    @staticmethod
    def getTopicUrlSelector(url):
        url = url.split("/")
        if "project?showContent=true" == url[-1] or "assessment?showContent=true" == url[-1]:
            url = url[:-1]
        modifiedCourseUrl = "/".join(url[3:-1]) + "/"
        return f"//a[contains(@href, '{modifiedCourseUrl}')]"


    @staticmethod
    def getCourseApiCollectionListUrl(nextData):
        try:
            nextData = nextData["query"]
            return f"https://educative.io/api/collection/{nextData['authorId']}/{nextData['collectionId']}?work_type=collection"
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"UrlUtility:getCourseApiCollectionListUrl: {lineNumber}: {e}")
