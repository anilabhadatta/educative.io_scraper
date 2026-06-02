class UrlUtility:
    def __init__(self):
        pass


    @staticmethod
    def appendShowContentQuery(url):
        if not url:
            return url
        if "showContent=true" not in url:
            if "?" in url:
                return url + "&showContent=true"
            else:
                return url + "?showContent=true"
        return url


    @staticmethod
    def getTopicUrlSelector(url):
        url = url.split("/")
        if url[-1] in ["assessment?showContent=true", "cloudlab?showContent=true", "project?showContent=true", "mock-interview?showContent=true"]:
            url = url[:-1]
        modifiedCourseUrl = "/".join(url[3:-1]) + "/"
        return f"//a[contains(@href, '{modifiedCourseUrl}')]"


    @staticmethod
    def getCourseApiCollectionListUrl(resMap, workType="collection"):
        try:
            return f"https://www.educative.io/api/collection/{resMap['authorId']}/{resMap['collectionId']}?work_type={workType}"
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"UrlUtility:getCourseApiCollectionListUrl: {lineNumber}: {e}")


    @staticmethod
    def getCourseApiPalUrl(authorId, collectionId, workType="collection"):
        try:
            return f"https://www.educative.io/api/pal/{authorId}/{collectionId}?work_type={workType}"
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"UrlUtility:getCourseApiPalUrl: {lineNumber}: {e}")


    @staticmethod
    def getCourseApiProjectUrl(authorId, collectionId, projectId, workType="collection"):
        try:
            return f"https://www.educative.io/api/project/{authorId}/{collectionId}/{projectId}?work_type={workType}"
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"UrlUtility:getCourseApiProjectUrl: {lineNumber}: {e}")


    @staticmethod
    def getCollectionTopicApiUrl(authorId, collectionId, pageId, workType="collection"):
        try:
            return f"https://www.educative.io/api/collection/{authorId}/{collectionId}/page/{pageId}?work_type={workType}"
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"UrlUtility:getCollectionTopicApiUrl: {lineNumber}: {e}")


    @staticmethod
    def getProjectTopicApiUrl(authorId, collectionId, projectId, pageId, workType="collection"):
        try:
            return f"https://www.educative.io/api/project/{authorId}/{collectionId}/{projectId}/{pageId}?work_type={workType}"
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"UrlUtility:getProjectTopicApiUrl: {lineNumber}: {e}")


    @staticmethod
    def isCourseUrl(url):
        clean_url = url.split("?")[0].rstrip("/")
        parts = clean_url.split("/")
        for keyword in ["courses"]:
            if keyword in parts:
                try:
                    idx = parts.index(keyword)
                    return len(parts) == idx + 2
                except ValueError:
                    pass
        return False


    @staticmethod
    def getCollectionTopicPageUrl(topicUrl, page):
        try:
            base = str(topicUrl).split("?", 1)[0].rstrip("/")
            if UrlUtility.isCourseUrl(topicUrl):
                course_url = base
            else:
                course_url = base.rsplit("/", 1)[0]
            slug = page.get("slug") or page.get("id")
            return f"{course_url}/{slug}?showContent=true"
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"UrlUtility:getCollectionTopicPageUrl: {lineNumber}: {e}")
