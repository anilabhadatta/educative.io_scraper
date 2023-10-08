class UrlUtility:
    """
    A class that provides utility functions for working with URLs.

    Methods:
        get_topic_url_selector(url):
            Returns an XPath selector for the given topic URL.
        get_course_api_collection_list_url(next_data):
            Returns the URL for the course API collection list for the given `next_data` object.
    """

    def __init__(self):
        pass


    @staticmethod
    def getTopicUrlSelector(url):
        """
        Returns an XPath selector for the given topic URL.

        Args:
            url: A string representing the URL of the topic.

        Returns:
            An XPath selector for the given topic URL.
        """
        url = url.split("/")
        if "project" in url[-1] or "assessment" in url[-1]:
            url = url[:-1]
        modifiedCourseUrl = "/".join(url[3:-1]) + "/"
        return f"//a[contains(@href, '{modifiedCourseUrl}')]"


    @staticmethod
    def getCourseApiCollectionListUrl(nextData):
        """
        Returns the URL for the course API collection list for the given `next_data` object.

        Args:
            next_data: A dictionary containing the `query` parameter for the course API collection list.

        Returns:
            The URL for the course API collection list.
        """
        try:
            authorID = nextData["query"]["authorId"]
            collectionID = nextData["query"]["collectionId"]
            return f"https://educative.io/api/collection/{authorID}/{collectionID}?work_type=collection"
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"UrlUtility:getCourseApiCollectionListUrl: {lineNumber}: {e}")
