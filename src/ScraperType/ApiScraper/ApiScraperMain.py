"""
ApiScraperMain.py

Mirrors CourseTopicScraper exactly — same browser init, login checks,
course/topic URL resolution — but instead of rendering pages to files,
it fetches each topic's raw API JSON and stores it in SQLite via DatabaseManager.
"""

import asyncio
import shutil
from urllib.parse import urlparse

from slugify import slugify

from src.Database.DatabaseManager import DatabaseManager
from src.Logging.Logger import Logger
from src.Main.LoginAccount import LoginAccount
from src.ScraperType.CourseTopicScraper.ScraperModules.ApiUtility import ApiUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.Utility.BrowserUtility import BrowserUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


class ApiScraperMain:
    def __init__(self, configJson, progressQueue=None):
        self.browser = None
        self.configJson = configJson
        self.progressQueue = progressQueue

        self.logger = Logger(configJson, "ApiScraperMain").logger
        self.fileUtils = FileUtility()
        self.osUtils = OSUtility(configJson)
        self.apiUtils = ApiUtility(configJson)
        self.loginUtils = LoginAccount(configJson)
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)
        self.browserUtils = BrowserUtility(configJson)
        self.db = DatabaseManager(configJson)

    # ------------------------------------------------------------------ #
    #  Entry points (mirrors CourseTopicScraper.start / startManual)
    # ------------------------------------------------------------------ #

    def _removeUrlFromFile(self, courseUrl: str):
        """Remove courseUrl (and everything before it) from the URLs text file.
        Mirrors UpdateTxtFileFromLog.updateUrlsFile — keeps only lines *after*
        the first occurrence of the URL so the file auto-advances on resume.
        A .bak copy is made before any write.
        """
        try:
            urlFilePath = self.configJson.get("courseUrlsFilePath", "")
            if not urlFilePath:
                return
            baseCourseUrl = courseUrl.split("?")[0]
            lines = self.fileUtils.loadTextFileNonStrip(urlFilePath)
            foundIndex = next((i for i, line in enumerate(lines) if baseCourseUrl in line), None)
            if foundIndex is None:
                self.logger.warning(f"_removeUrlFromFile: URL not found in file: {baseCourseUrl}")
                return
            shutil.copy2(urlFilePath, urlFilePath + ".bak")
            remainingLines = lines[foundIndex + 1:]
            self.fileUtils.writeLines(urlFilePath, remainingLines)
            self.logger.info(f"Removed URL and all preceding lines from file (index {foundIndex}): {baseCourseUrl}")
        except Exception as e:
            self.logger.error(f"_removeUrlFromFile failed: {e}")

    def start(self):
        self.logger.info("ApiScraperMain initiated...")
        urlsTextFile = self.fileUtils.loadTextFile(self.configJson["courseUrlsFilePath"])
        self.progressQueue.put(("progress-topic", 0))
        self.progressQueue.put(("progress-course", 0))
        self.progressQueue.put(("max-course", len(urlsTextFile)))

        for textFileIdx, textFileUrl in enumerate(urlsTextFile):
            try:
                self.progressQueue.put(("progress-course", textFileIdx + 1))
                if "?showContent=true" not in textFileUrl:
                    textFileUrl += "?showContent=true"
                self.logger.info(f"Started Scraping from Text File URL: {textFileUrl}")
                self.browser = self.browserUtils.loadBrowser()
                self.apiUtils.browser = self.browser
                self.loginUtils.browser = self.browser
                self.browser.set_window_size(1920, 1080)
                self.scrapeCourseOrPath(textFileUrl)
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                self._removeUrlFromFile(textFileUrl)
            except KeyboardInterrupt:
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                self._removeUrlFromFile(textFileUrl)
                raise
            except Exception as e:
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                self._removeUrlFromFile(textFileUrl)
                lineNumber = e.__traceback__.tb_lineno
                raise Exception(f"ApiScraperMain:start: {lineNumber}: {e}")

        self.logger.info("ApiScraperMain completed.")

    # ------------------------------------------------------------------ #
    #  Core: resolve course structure, then store each topic JSON in DB
    # ------------------------------------------------------------------ #

    def scrapeCourseOrPath(self, textFileUrl):
        try:
            # ── Resolve course & topic URL lists (identical to CourseTopicScraper) ──
            courseUrl    = self.apiUtils.getCourseUrl(textFileUrl)
            courseApiUrl = self.apiUtils.getAuthorAndCollectionId()
            topicUrlsList, pathFolderName = self.apiUtils.getCourseTopicUrlsList(textFileUrl, courseUrl)

            # Remove duplicates while preserving order
            originalLen = len(topicUrlsList)
            seen = set()
            topicUrlsList = [url for url in topicUrlsList if not (url in seen or seen.add(url))]
            if len(topicUrlsList) < originalLen:
                self.logger.warning(f"Removed {originalLen - len(topicUrlsList)} duplicate URL(s)")

            self.loginUtils.checkIfLoggedIn()
            courseCollectionsJson = self.apiUtils.getCourseCollectionsJson(courseApiUrl, courseUrl)
            topicApiUrlList  = courseCollectionsJson["topicApiUrlList"]
            topicApiNameList = courseCollectionsJson["topicNameList"]
            topicApiUrlListLen = len(topicApiUrlList)
            topicUrlsListLen   = len(topicUrlsList)

            self.logger.debug(f"Course Topic URLs: {topicUrlsList}")
            self.logger.debug(f"Course Api Topic Urls: {topicApiUrlList}")
            self.logger.info(f"API Urls: {topicApiUrlListLen} == {topicUrlsListLen} :Topic Urls")
            if topicApiUrlListLen != topicUrlsListLen:
                apiUrlsSet   = set(topicApiUrlList)
                topicUrlsSet = set(topicUrlsList)
                self.logger.info(f"Extra in API URLs (not in topic URLs): {apiUrlsSet - topicUrlsSet}")
                self.logger.info(f"Extra in Topic URLs (not in API URLs): {topicUrlsSet - apiUrlsSet}")
                raise Exception("CourseCollectionsJson and CourseTopicUrlsList Urls are not equal")

            # ── Persist course + all topic stubs to DB ─────────────────────────
            courseTitle = courseCollectionsJson["courseTitle"]
            toc         = courseCollectionsJson["toc"]
            topicSlugs  = courseCollectionsJson["topicSlugList"]

            # Parse authorId / collectionId from the collection API URL
            # e.g. https://www.educative.io/api/collection/123/456?work_type=collection
            apiParts      = courseApiUrl.split("?")[0].split("/")
            author_id     = apiParts[-2] if len(apiParts) >= 2 else ""
            collection_id = apiParts[-1] if len(apiParts) >= 1 else ""

            # Detect type using the same two-level logic as CourseTopicScraper:
            #   Level 1 – moduleType: COURSE-PATH | CLOUDLAB | PROJECT
            #   Level 2 – within COURSE-PATH, "/module/" in the URL means it is
            #              a Path (getCourseTopicUrlsList uses the same check).
            module_type = self.configJson.get("moduleType", "COURSE-PATH")
            if module_type == "CLOUDLAB":
                course_type = "Cloudlab"
            elif module_type == "PROJECT":
                course_type = "Project"
            elif "/module/" in courseUrl:
                course_type = "Path"
            else:
                course_type = "Course"

            # work_type mirrors ApiUtility.getCourseCollectionsJson:
            # "module" for paths, "collection" for everything else.
            work_type = "module" if course_type == "Path" else "collection"

            course_slug = slugify(courseTitle)

            path_id = None
            if course_type == "Path":
                path_id = self.db.upsert_path(
                    url   = courseUrl,
                    slug  = course_slug,
                    title = courseTitle,
                    toc   = toc,
                )

            course_id = self.db.upsert_course(
                url           = courseUrl,
                slug          = course_slug,
                author_id     = author_id,
                collection_id = collection_id,
                title         = courseTitle,
                toc           = toc,
                course_type   = course_type,
                path_id       = path_id,
            )
            self.db.upsert_topics_for_course(
                course_id    = course_id,
                topic_names  = topicApiNameList,
                topic_slugs  = topicSlugs,
                topic_urls   = topicUrlsList,
                api_urls     = topicApiUrlList,
            )

            self.progressQueue.put(("max-topic", topicUrlsListLen))
            overwrite = self.configJson.get("overwrite", False)

            # ── Fetch & store each topic JSON ──────────────────────────────────
            for topicIndex in range(0, topicUrlsListLen):
                self.progressQueue.put(("progress-topic", topicIndex + 1))
                topicUrl    = topicUrlsList[topicIndex]
                topicApiUrl = topicApiUrlList[topicIndex]
                topicName   = f"{topicIndex:03}-{self.fileUtils.filenameSlugify(topicApiNameList[topicIndex])}"

                self.logger.info(
                    f"----------------------------------------------------------------------------------\n"
                    f"Scraping Topic: {topicName}: {topicUrl}"
                )

                # DB-based resume: skip done topics unless overwrite=True
                topicRow = self.db.get_topic_by_api_url(course_id, topicApiUrl)
                if not overwrite and topicRow and topicRow["status"] == "done":
                    self.logger.info(f"Skipping already-done topic: {topicName}")
                    continue

                # Re-check session before every fetch (same as original scraper)
                self.loginUtils.checkIfLoggedIn()

                # Fetch the raw full JSON response from the topic API.
                # executeJsToGetJson runs a browser-side fetch() so auth cookies
                # are sent automatically — no manual cookie handling needed.
                topicRawJson = self.apiUtils.executeJsToGetJson(topicApiUrl)

                if topicRawJson:
                    topicRawJson = self.resolveLazyLoadPlaceholders(
                        topicRawJson, author_id, collection_id, work_type
                    )
                    if topicRow:
                        self.db.save_topic_content(
                            course_id   = course_id,
                            topic_index = topicRow["topic_index"],
                            components  = topicRawJson.get("components", []),
                        )
                    self.logger.info(f"Saved JSON for: {topicName}")
                else:
                    url = topicUrl.split("/")
                    isSpecialTopic = url[-1] in [
                        "assessment?showContent=true",
                        "cloudlab?showContent=true",
                        "project?showContent=true",
                        "mock-interview?showContent=true",
                    ]
                    if topicRow:
                        self.db.mark_topic_error(
                            course_id   = course_id,
                            topic_index = topicRow["topic_index"],
                            error_msg   = "API returned empty response",
                        )
                    if not isSpecialTopic:
                        raise Exception(f"Cannot fetch content from Topic API Url: {topicApiUrl}")
                    self.logger.warning(f"Empty response for special topic (skipping): {topicName}")

                self.osUtils.sleep(2)

            progress = self.db.get_scrape_progress(course_id)
            self.logger.info(f"Course '{courseTitle}' done. Progress: {progress}")

        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiScraperMain:scrapeCourseOrPath: {lineNumber}: {e}")

    # ------------------------------------------------------------------ #
    #  Lazy load placeholder resolution
    # ------------------------------------------------------------------ #

    def resolveLazyLoadPlaceholders(self, topicJson: dict, collectionId: str, courseId: str, workType: str) -> dict:
        try:
            components = topicJson.get("components", [])
            for component in components:
                if component.get("type") != "LazyLoadPlaceholder":
                    continue
                content = component.get("content", {})
                pageId          = content.get("pageId")
                widgetIndex     = content.get("widgetIndex")
                contentRevision = content.get("contentRevision")

                if pageId is None or widgetIndex is None or contentRevision is None:
                    self.logger.warning(f"Skipping LazyLoadPlaceholder — missing params: {content}")
                    continue

                lazyApiUrl = (
                    f"https://www.educative.io/api/collection/{collectionId}/{courseId}"
                    f"/page/{pageId}/{contentRevision}/{widgetIndex}?work_type={workType}"
                )
                self.logger.info(f"Fetching LazyLoad widget {widgetIndex}: {lazyApiUrl}")
                self.loginUtils.checkIfLoggedIn()
                lazyJson = self.apiUtils.executeJsToGetJson(lazyApiUrl)

                if lazyJson:
                    component["content"]["lazyLoadData"] = lazyJson
                    self.logger.info(f"Stored lazyLoadData for widget {widgetIndex}")
                else:
                    self.logger.warning(f"Empty response for LazyLoad widget {widgetIndex}")

            return topicJson
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"resolveLazyLoadPlaceholders: {lineNumber}: {e}")
            return topicJson
