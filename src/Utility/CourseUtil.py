import json
import requests
from bs4 import BeautifulSoup

from src.Logging.Logger import Logger

class CourseUtil:
    """
    A class that provides utility functions for working with URLs.

    Methods:
        get_course_api_url():
            Returns the URL for the course API for the given course URL.
    """

    def __init__(self, configJson):
        """
        Initializes the CourseUtil class with the given course URL.

        Args:
            configJson: The JSON object containing the configuration.
        """
        self.logger = None
        if configJson:
            self.logger = Logger(configJson, "CourseUtility").logger

    def get_course_api_url(self, course_url):
        """
        Returns the URL for the course API for the given course URL.

        Returns:
            The URL for the course API collection list.
        """
        try:
            self.logger.info(f"Fetching course API URL for {course_url}")
            response = requests.get(course_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            json_data = soup.find('script', {'id': '__NEXT_DATA__'}).string
            query = json.loads(json_data)["query"]
            author_id = query["authorId"]
            collection_id = query["collectionId"]
            self.logger.info(f"author_id: {author_id}, collection_id: {collection_id}")
            # todo give both flavours of course API URL
            courAPIUrl = f"https://educative.io/api/collection/{author_id}/{collection_id}?work_type=collection"
            return courAPIUrl
        
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"""Error fetching course API URL for {course_url}. 
                            CourseUtil:get_course_api_url: {lineNumber}: {e}""")

if __name__ == "__main__":
    courseUtil = CourseUtil()
    
    #success
    success_course_url = "https://www.educative.io/collection/6226925030735872/6693327303868416?work_type=collection"
    course_api_url = courseUtil.get_course_api_url(success_course_url)
    print(course_api_url)

    #failure
    failure_course_url = "https://www.educative.io/collection/dynamodb-from-basic-to-advance?work_type=collection"
    course_api_url = courseUtil.get_course_api_url(failure_course_url)
    print(course_api_url)
