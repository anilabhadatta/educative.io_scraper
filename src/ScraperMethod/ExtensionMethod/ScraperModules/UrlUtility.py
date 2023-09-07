import json


class UrlUtility:
    def __init__(self):
        pass


    def getTopicUrlSelector(self, url):
        modifiedCourseUrl = "/".join(url.split("/")[3:-1]) + "/"
        return f"//a[contains(@href, '{modifiedCourseUrl}')]"


    def getCourseApiCollectionListUrl(self, nextData):
        try:
            nextData = json.loads(nextData.get_attribute('innerHTML'))
            moduleNextData = nextData["props"]["pageProps"]
            courseNextData1 = nextData["query"]
            courseNextData2 = nextData["props"]["pageProps"]
            if "moduleAuthorId" in moduleNextData and "moduleCollectionId" in moduleNextData:
                return f"https://educative.io/api/collection/{moduleNextData['moduleAuthorId']}/{moduleNextData['moduleCollectionId']}?work_type=collection"
            if "authorId" in moduleNextData and "collectionId" in moduleNextData:
                return f"https://educative.io/api/collection/{moduleNextData['authorId']}/{moduleNextData['collectionId']}?work_type=collection"
            if "moduleAuthorId" in courseNextData1 and "moduleCollectionId" in courseNextData1:
                return f"https://educative.io/api/collection/{courseNextData1['moduleAuthorId']}/{courseNextData1['moduleCollectionId']}?work_type=collection"
            if "authorId" in courseNextData1 and "collectionId" in courseNextData1:
                return f"https://educative.io/api/collection/{courseNextData1['authorId']}/{courseNextData1['collectionId']}?work_type=collection"
            if "moduleAuthorId" in courseNextData2 and "moduleCollectionId" in courseNextData2:
                return f"https://educative.io/api/collection/{courseNextData2['moduleAuthorId']}/{courseNextData2['moduleCollectionId']}?work_type=collection"
            if "authorId" in courseNextData2 and "collectionId" in courseNextData2:
                return f"https://educative.io/api/collection/{courseNextData2['authorId']}/{courseNextData2['collectionId']}?work_type=collection"
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"UrlUtility:getCourseApiCollectionListUrl: {lineNumber}: {e}")
