import json
import logging
import os
import re
import requests
import time

from bs4 import BeautifulSoup
from src.Logging.Logger import Logger


class CourseUtil:
    """
    A class that provides utility functions for working with URLs.

    Methods:
        get_course_api_url():
            Returns the URL for the course API for the given course URL.
        get_filtered_content_json():
            Returns the filtered JSON data for the given course API URL.
    """

    def __init__(self, configJson):
        """
        Initializes the CourseUtil class with the given course URL.

        Args:
        """
        self.configJson = configJson
        self.logger = Logger(configJson, "CourseUtil").logger

    def get_course_api_url(self, course_url, named_api=False):
        """
        Returns the URL for the course API for the given course URL.

        Returns:
            The URL for the course API collection list.
        """
        try:
            self.logger.info(f"Fetching course API URL for {course_url}")

            course_name = self.get_course_name(course_url)

            response = requests.get(course_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            json_data = soup.find('script', {'id': '__NEXT_DATA__'}).string
            query = json.loads(json_data)["query"]

            author_id = query["authorId"]
            collection_id = query["collectionId"]
            courseAPIUrl = f"https://www.educative.io/api/collection/{author_id}/{collection_id}?work_type=collection"
            courseNameAPIUrl = f"https://www.educative.io/api/collection/{course_name}?work_type=collection"

            self.logger.info(
                f"author_id: {author_id}, collection_id: {collection_id}, courseAPIUrl: {courseAPIUrl}, courseNameAPIUrl: {courseNameAPIUrl}")

            return courseNameAPIUrl if named_api else courseAPIUrl

        except Exception as e:
            self._handle_exception(e, "get_course_api_url")

    def get_index_filtered_content(self, url, filter_data=False):
        """
        Returns the filtered JSON data for the given course API URL.

        Returns:
            The filtered JSON data.
        """
        try:
            self.logger.info(f"Fetching course content JSON: {url}")

            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()

            api_data = json.loads(response.text)

            filtered_data = api_data["instance"]["details"]
            if filter_data:
                filtered_data = {
                    "title": filtered_data.get("title"),
                    "summary": filtered_data.get("summary"),
                    "url_slug": filtered_data.get("url_slug"),
                    "author_id": filtered_data.get("author_id"),
                    "collection_id": filtered_data.get("collection_id"),
                    "page_titles": filtered_data.get("page_titles"),
                    "page_slugs": filtered_data.get("page_slugs"),
                    "is_priced": filtered_data.get("is_priced"),
                    "sections": self._extract_pages(filtered_data.get("toc").get("categories")),
                    "collection_type": filtered_data.get("collection_type"),
                    "work_type": filtered_data.get("work_type")
                }

            self.logger.debug(
                f"Filtered course content JSON: {json.dumps(filtered_data, indent=4, sort_keys=True)}")

            return filtered_data

        except Exception as e:
            self._handle_exception(e, "get_filtered_content_json")

    def get_course_name(self, course_url):
        """
        Returns the name of the course from the given course URL.

        Returns:
            The name of the course.
        """
        try:
            self.logger.info(f"Fetching course name for {course_url}")

            match = re.search(r"/courses/([^/]+)/", course_url)
            if match:
                course_name = match.group(1)
                self.logger.info(f"Course name: {course_name}")
                return course_name
            else:
                raise Exception(
                    f"Error extracting course name from {course_url}")

        except Exception as e:
            self._handle_exception(e, "get_course_name")

    def _extract_pages(self, json_data):
        """
        Extracts the pages from the given JSON data.

        Returns:
            The extracted pages.
        """
        extracted_data = []

        for item in json_data:
            extracted_item = {
                "title": item.get("title"),
                "type": item.get("type"),
                "pages": [{"id": page["id"], "slug": page["slug"], "title": page["title"], "type": page["type"]} for page in item.get("pages", [])]
            }
            extracted_data.append(extracted_item)

        return extracted_data

    def scrape_course_content(self, course_url, filter_data=False):
        course_api_url = self.get_course_api_url(course_url)
        course_data = self.get_index_filtered_content(
            course_api_url, filter_data=filter_data)

        author_id = course_data["author_id"]
        collection_id = course_data["collection_id"]
        course_dir = course_data["url_slug"]

        course_dir = f"./courses/{course_dir}"
        index_data_path = f"{course_dir}/index.json"

        # write course data to index file in course directory
        os.makedirs(os.path.dirname(index_data_path), exist_ok=True)
        with open(index_data_path, "w") as f:
            json.dump(course_data, f)

        sections = enumerate(course_data["sections"]) if filter_data else enumerate(
            course_data.get("toc").get("categories"))

        for section_number, section in sections:
            section_dir = section['title'].lower().replace(' ', '-')
            for page_number, page in enumerate(section["pages"]):
                page_slug = page["slug"]
                page_id = page["id"]
                page_url = f"https://www.educative.io/api/collection/{author_id}/{collection_id}/page/{page_id}?work_type=collection"
                page_data = self.get_page_data(page_url)

                # save to file with nesting of sections
                file_path = f"{course_dir}/{section_number:02d}-{section_dir}/{page_number:02d}-{page_slug}.json"
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    json.dump(page_data, f)

        self.logger.info(f"Course content saved to {course_dir}")

    def get_page_data(self, page_url):
        """
        Returns the page content for the given page URL.

        Returns:
            The page content.
        """
        try:
            self.logger.info(f"Fetching page content for {page_url}")

            response = requests.get(page_url, headers=self._get_headers())
            response.raise_for_status()

            page_data = json.loads(response.text)

            self.logger.debug(
                f"Page content: {json.dumps(page_data, indent=4, sort_keys=True)}")

            return page_data

        except Exception as e:
            self._handle_exception(e, "get_course_api_url")

    def _get_headers(self):
        """
        Returns the headers for the HTTP request.

        Returns:
            The headers.
        """
        return {
            'Cookie': 'OptanonConsent=isGpcEnabled=0&datestamp=Sun+Oct+08+2023+07%3A34%3A41+GMT%2B0530+(India+Standard+Time)&version=202308.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=300e900f-3794-4bb0-b33f-e3b727cbde53&interactionCount=0&landingPath=https%3A%2F%2Fwww.educative.io%2Fcourses%2Fgrokking-the-engineering-management-and-leadership-interviews%2F1-1s-with-team-members%3FshowContent%3Dtrue&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1;flask-auth=.eJyLNjMwNjU3NTIEYnNDS2MzHUMdJT-L1IJkt_zkQNdE86Sc0ojcXPfcvHQlHUMzS3NjCxNTAwMY08TSXEcpJbXMKLFML9MhPTcxM0cvOT9XCbtgSVFpqk5aYk5xqk5eaU6OjjGEQhgbCwA-iynd;font-family-body-lesson-markdown=Droid Serif;editor-auth=eyJ1c2VyX2lkIjogIjYwMzU3NTIxNzUyNzE5MzYiLCAidG9rZW4iOiAieXoxOEVSOUFCOXJsWXFybzF6T29UOCIsICJ0b2tlbl90cyI6IDE2OTczODQ0OTgwMDB9;enterprise_nav=false;theme=dark;subscribed=false;flask-session=.eJxtT00LgkAU_C_v_BDXXV311MW6Bd2CiGXTlwi7q-iuFNF_T4vo0mGYYQ7z8QA10Gi1I-eh9GMgBBUmGqE8ZTFPZZqwBZIVPEOGsM9pqLd9fai0vJhwtHZnXQvIskLyXKRx_JWikAgNzYmeo27TWt2ZqO4t_DffzVdtJkIXjEH-oV_sGcHqm9ItQclyJsTSBOtQ5e_D4sHkQ7OeeL4Adn9Atw.ZSwIlg.akPPwdEmwvRbtXBOSvXRXGvOr3U;visited-explore-page=false;font-family-heading-lesson-markdown=Droid Serif;__cf_bm=YUlp.HQgqRGhAJVrpoNdlN..Sqv2TWUrCrtTNonfo6U-1697384385-0-ARzXHbNSNIdHHqEMdDeQXQecerwSS+ztuquD0FJK1tWQkARHEfcH3CDD2DuVfOjOZjLA78UCSr6UzHKDiicCYnI=;__stripe_mid=afc5d014-6ce6-422d-95b4-7bb6b7afa322be79a2;_gcl_au=1.1.1097530599.1696730682;cache_token=1697384598-Girs8WcuX/p2v7wNNyywFRerRAhVEemuqoWRfY4SxoE%3D;content-width-lesson-markdown=1024px;enterprise_new_sidebar=true;ext_name=ojplmecpdpgccookcobabopnaifgidhf;font-size-lesson-markdown=20px;g_state={"i_p":1696901350366,"i_l":2};line-height-lesson-markdown=175%;logged_in=;recommendations=true;trial_availed=false;use_system_preference=system_preference;usprivacy=1---'
        }

    def _handle_exception(self, e, method_name):
        """
        Handles the given exception.

        Args:
            e: The exception.
            method_name: The name of the method where the exception occurred.
        """
        line_number = e.__traceback__.tb_lineno
        self.logger.exception(
            f"Error in {method_name} (line {line_number}): {e}")
        raise e
