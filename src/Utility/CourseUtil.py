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
            # todo return both flavours of course API URL, by collect id and course name
            courAPIUrl = f"https://educative.io/api/collection/{author_id}/{collection_id}?work_type=collection"

            # todo remove this
            self.get_content_json(courAPIUrl)
            
            return courAPIUrl
        
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"""Error fetching course API URL for {course_url}. 
                            CourseUtil:get_course_api_url: {lineNumber}: {e}""")

    def get_content_json(self, url):
        payload = {}
        headers = {
        'Cookie': '__cf_bm=.wtp5ObyDOogpMxWGpJkrtG968hQvNs5_hRZU7snWDg-1697046430-0-AZdHhts20natzJvhprYhRY6D1fHA/C3HahVh0AfDJZiXnLJm+732kL2AyN2SCy8xbyOO3M4BxXnk8B12YMfxdac=; flask-session=eyJfcGVybWFuZW50Ijp0cnVlfQ.ZSbgvQ.dxEhIPUBHVhaEVg55cXRZE75eXo'
        }

        self.logger.info(f"Fetching course Json: {url}")    
        response = requests.request("GET", url, headers=headers, data=payload)
        jsonData = json.loads(response.text)["instance"]["details"]
        formattedResponse = json.dumps(jsonData, indent=4, sort_keys=True)
        self.logger.debug(f"Course Json: {formattedResponse}")

        # Extracting the desired fields
        filteredData = {
            "title": jsonData.get("title"),
            "summary": jsonData.get("summary"),
            "page_titles": jsonData.get("page_titles"),
            "is_priced": jsonData.get("is_priced"),
            "sections": self.extractPages(jsonData),
        }

        self.logger.info(f"Filtered Course Json: {json.dumps(filteredData, indent=4, sort_keys=True)}")
        return filteredData

    def extractPages(self, json_data):
        extracted_data = []
    
        for item in json_data.get("toc").get("categories"):
            extracted_item = {
                "title": item.get("title"),
                "type": item.get("type"),
                "pages": [{"id": page["id"], "slug": page["slug"], "title": page["title"], "type": page["type"]} for page in item.get("pages", [])]
            }
            extracted_data.append(extracted_item)
        
        return extracted_data
        

if __name__ == "__main__":
    courseUtil = CourseUtil()
    
    # todo pass url even for main call
    #success
    success_course_url = "https://www.educative.io/collection/6226925030735872/6693327303868416?work_type=collection"
    course_api_url = courseUtil.get_course_api_url(success_course_url)
    print(course_api_url)

    #failure
    failure_course_url = "https://www.educative.io/collection/dynamodb-from-basic-to-advance?work_type=collection"
    course_api_url = courseUtil.get_course_api_url(failure_course_url)
    print(course_api_url)
