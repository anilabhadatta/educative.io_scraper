"""
ApiScraperMain.py

Mirrors CourseTopicScraper exactly — same browser init, login checks,
course/topic URL resolution — but instead of rendering pages to files,
it fetches each topic's raw API JSON and stores it in SQLite via DatabaseManager.
"""

import asyncio
import shutil

from slugify import slugify

from src.ScraperType.ApiScraper.ScraperModules.ProjectModule import ProjectModule
from src.ScraperType.ApiScraper.APIScraperConstants import (
    HTTP_PREFIX,
    SHOW_CONTENT_QUERY,
    SPECIAL_TOPIC_TYPES,
    WORK_TYPE_COLLECTION,
    WORK_TYPE_MODULE,
)
from src.ScraperType.ApiScraper.Database.DatabaseManager import DatabaseManager
from src.Logging.Logger import Logger
from src.Main.LoginAccount import LoginAccount
from src.Utility.NetworkMonitor import NetworkMonitor
from src.ScraperType.ApiScraper.ScraperModules.ApiUtility import ApiUtility
from src.ScraperType.ApiScraper.ScraperModules.CommonUtility import CommonUtility
from src.ScraperType.ApiScraper.ScraperModules.ResolveComponent import ResolveComponent
from src.Utility.BrowserUtility import BrowserUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


class ApiScraperMain:
    def __init__(self, configJson, progressQueue=None):
        self.browser = None
        self.configJson = configJson
        self.progressQueue = progressQueue
        self.totalCourseUnits = 0
        self.completedCourseUnits = 0

        self.logger = Logger(configJson, "ApiScraperMain").logger
        self.fileUtils = FileUtility()
        self.osUtils = OSUtility(configJson)
        self.apiUtils = ApiUtility(configJson)
        self.loginUtils = LoginAccount(configJson)
        self.resolveComponent = ResolveComponent(self.apiUtils, self.loginUtils, self.logger)
        self.browserUtils = BrowserUtility(configJson)
        self.db = DatabaseManager(configJson)
        self.pathTable = self.db.paths
        self.courseTable = self.db.courses
        self.projectTable = self.db.projects
        self.topicTable = self.db.topics
        self.componentTable = self.db.components
        self.progressTable = self.db.progress
        self.networkMonitor = NetworkMonitor(configJson)
        self.projectModule = ProjectModule(configJson)

    # ------------------------------------------------------------------ #
    #  Entry points (mirrors CourseTopicScraper.start / startManual)
    # ------------------------------------------------------------------ #

    def _removeUrlFromFile(self, courseUrl: str):
        """Remove courseUrl (and everything before it) from the URLs text file.
        Mirrors UpdateTxtFileFromLog.updateUrlsFile — keeps only lines *after*
        the first occurrence of the URL so the file auto-advances on resume.
        A .bak copy is made before any write.
        Only runs when autofixtextfile=true in config.
        """
        if not self.configJson.get("autofixtextfile", False):
            return
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
        self.totalCourseUnits = len(urlsTextFile)
        self.completedCourseUnits = 0
        self.progressQueue.put(("progress-topic", 0))
        self.progressQueue.put(("progress-course", 0))
        self.progressQueue.put(("max-course", self.totalCourseUnits))

        for textFileIdx, topicUrl in enumerate(urlsTextFile):
            try:
                if SHOW_CONTENT_QUERY not in topicUrl:
                    topicUrl += SHOW_CONTENT_QUERY
                self.logger.info(f"Started Scraping from Text File URL: {topicUrl}")
                self.browser = self.browserUtils.loadBrowser()
                self.apiUtils.browser = self.browser
                self.loginUtils.browser = self.browser
                self.networkMonitor.browser = self.browser
                self.projectModule.browser = self.browser
                self.browser.set_window_size(1920, 1080)
                self.scrapeCourseOrPath(topicUrl)
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                self._removeUrlFromFile(topicUrl)
            except KeyboardInterrupt:
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                raise
            except Exception as e:
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                lineNumber = e.__traceback__.tb_lineno
                raise Exception(f"ApiScraperMain:start: {lineNumber}: {e}")

        self.logger.info("ApiScraperMain completed.")

    # ------------------------------------------------------------------ #
    #  Core: resolve course structure, then store each topic JSON in DB
    # ------------------------------------------------------------------ #

    def scrapeCourseOrPath(self, topicUrl):
        try:
            courseUrl = self.apiUtils.getCourseUrl(topicUrl)
            workType = WORK_TYPE_MODULE if ("/module/" in courseUrl or "/pal/" in courseUrl) else WORK_TYPE_COLLECTION
            self.apiUrls = self.networkMonitor.getAPIUrls()

            courseApiUrls = self.apiUtils.getCourseApiUrlFromNetworkUrls(self.apiUrls, workType) or []
            try:
                courseApiUrlFallback = self.apiUtils.getAuthorAndCollectionId(workType)
                courseApiUrls += courseApiUrlFallback
            except Exception as e:
                self.logger.warning(f"Could not derive fallback course API URL from author/collection logic: {e}")
            
            if not courseApiUrls:
                raise Exception("Could not derive course API URL from both network capture and author/collection extraction")
            
            seenApiUrls = set()
            courseApiUrls = [url for url in courseApiUrls if not (url in seenApiUrls or seenApiUrls.add(url))]
            courseType = (
                "Project" if any("/api/project/" in url for url in courseApiUrls)
                else "Path" if "/module/" in courseUrl
                else "Course"
            )
            courseApiUrls = courseApiUrls[::-1]
            self.logger.info(f"Determined course type: {courseType}")
            self.logger.info(f"Derived course API URLs: {courseApiUrls}")

            self.loginUtils.checkIfLoggedIn()
            courseCollectionsJsonList = self.apiUtils.getCollectionsJson(courseApiUrls, courseType, workType, topicUrl)

            # One input URL can expand to multiple course units (e.g., PAL + COLLECTION).
            extraCourseUnits = max(0, len(courseCollectionsJsonList) - 1)
            if extraCourseUnits:
                self.totalCourseUnits += extraCourseUnits
                self.progressQueue.put(("max-course", self.totalCourseUnits))

            for courseCollectionsJson in courseCollectionsJsonList:
                self.completedCourseUnits += 1
                self.progressQueue.put(("progress-course", self.completedCourseUnits))

                topicApiUrlList = courseCollectionsJson["topicApiUrlList"]
                topicNameList = courseCollectionsJson["topicNameList"]
                topicUrlList = courseCollectionsJson["topicUrlList"]
                topicTypeList = courseCollectionsJson["topicTypeList"]
                authorId = courseCollectionsJson["authorId"]
                collectionId = courseCollectionsJson["collectionId"]
                title = courseCollectionsJson["title"]
                toc = courseCollectionsJson["toc"]
                topicSlugs = courseCollectionsJson["topicSlugList"]

                slug = slugify(title)
                projectId = courseCollectionsJson.get("projectId", None)
                pathMeta = courseCollectionsJson.get("pathMeta", {})

                path_id = None
                if courseType == "Path":
                    path_id = self.pathTable.upsert_path(
                        path_author_id = pathMeta["path_author_id"],
                        path_collection_id = pathMeta["path_collection_id"],
                        path_url_slug = pathMeta["path_url_slug"],
                        path_title = pathMeta["path_title"]
                    )

                project_id = None
                if courseType == "Project":
                    project_id = self.projectTable.upsert_project(
                        project_author_id=authorId,
                        project_collection_id=collectionId,
                        project_work_id=projectId,
                        project_title=title,
                        project_url_slug=slug,
                    )

                course_id = self.courseTable.upsert_course(
                    url           = courseUrl,
                    slug          = slug,
                    author_id     = authorId,
                    collection_id = collectionId,
                    title         = title,
                    toc           = toc,
                    course_type   = courseType,
                    path_id       = path_id,
                    project_id    = project_id,
                    topic_slugs   = topicSlugs,
                )
            
                self.topicTable.upsert_topics_for_course(
                    course_id    = course_id,
                    topic_names  = topicNameList,
                    topic_slugs  = topicSlugs,
                    topic_urls   = topicUrlList,
                    api_urls     = topicApiUrlList,
                )
                # Enrich toc_json with DB-sourced course_id + topic_index now that topics exist
                self.courseTable.finalize_course_toc(course_id)

                self.progressQueue.put(("max-topic", len(topicUrlList)))
                overwrite = self.configJson["overwrite"]

                # ── Determine start index ──────────────────────────────────────────
                # When overwrite=True the caller expects scraping to resume from the
                # URL that was passed in (textFileUrl), not from the very first topic.
                # Strip the query string for matching since topicUrlsList entries may
                # or may not include ?showContent=true.
                startIndex = 0
                if overwrite:
                    baseTextFileUrl = topicUrl.split("?")[0]
                    for idx, url in enumerate(topicUrlList):
                        if url.split("?")[0] == baseTextFileUrl:
                            startIndex = idx
                            break
                    if startIndex:
                        self.logger.info(
                            f"overwrite=True: starting from topic index {startIndex} "
                            f"matching URL: {baseTextFileUrl}"
                        )

                if courseType == "Project":
                    self.projectModule.clickOnStartProject()

                # ── Fetch & store each topic JSON ──────────────────────────────────
                for topicIndex in range(startIndex, len(topicApiUrlList)):
                    self.progressQueue.put(("progress-topic", topicIndex + 1))
                    topicApiUrl = topicApiUrlList[topicIndex]
                    topicPageUrl = topicUrlList[topicIndex]
                    topicName = topicNameList[topicIndex]
                    topicType = topicTypeList[topicIndex]
                    parsedAuthorId, parsedCollectionId, parsedPageId = CommonUtility.extract_ids_from_topic_api_url(topicApiUrl)
                    topicAuthorId = parsedAuthorId or authorId
                    topicCollectionId = parsedCollectionId or collectionId

                    self.logger.info(
                        f"----------------------------------------------------------------------------------\n"
                        f"Scraping Topic: {topicIndex}: {topicName}: {topicPageUrl}"
                    )

                    # DB-based resume: skip done topics only when not in overwrite mode.
                    # In overwrite mode we started from the matching URL index, so every
                    # topic from that point onwards is intentionally re-scraped.
                    topicRow = self.topicTable.get_topic_by_api_url(course_id, topicApiUrl)
                    if not overwrite and topicRow and topicRow["status"] == "done":
                        self.logger.info(f"Skipping already-done topic: {topicName}")
                        continue

                    isSpecialTopic = topicType in SPECIAL_TOPIC_TYPES

                    # Re-check session before every fetch (same as original scraper)
                    self.loginUtils.checkIfLoggedIn()

                    # Fetch the raw full JSON response from the topic API.
                    # executeJsToGetJson runs a browser-side fetch() so auth cookies
                    # are sent automatically — no manual cookie handling needed.
                    topicRawJson = self.apiUtils.executeJsToGetJson(topicApiUrl)

                    # Any non-200 HTTP response on a special topic is not an error —
                    # content simply isn't available; mark done and proceed.
                    # On a normal topic, any non-200 is a real error — raise immediately.
                    if isinstance(topicRawJson, str) and topicRawJson.startswith(HTTP_PREFIX):
                        httpCode = topicRawJson.split("_")[1]
                        if isSpecialTopic:
                            if topicRow:
                                self.topicTable.mark_topic_done(course_id, topicRow["topic_index"])
                            self.logger.info(f"HTTP {httpCode} on special topic — marking done and skipping: {topicName}")
                            self.osUtils.sleep(2)
                            continue
                        else:
                            raise Exception(f"HTTP {httpCode} fetching topic API URL: {topicApiUrl}")

                    if topicRawJson:
                        topicRawJson = self.resolveComponent.resolveLazyLoadPlaceholders(
                            topicRawJson, topicAuthorId, topicCollectionId, workType
                        )
                        page_id = topicRow["page_id"]
                        topicRawJson = self.resolveComponent.resolveDrawIOSlides(
                            topicRawJson, topicAuthorId, topicCollectionId, page_id
                        )
                        topicComponents = CommonUtility.extract_topic_components_for_persistence(
                            topicRawJson=topicRawJson,
                            isProjectCourse=(courseType == "Project"),
                        )

                        # Normal topics must have persistable content.
                        if not isSpecialTopic and not topicComponents:
                            if topicRow:
                                self.topicTable.mark_topic_error(
                                    course_id   = course_id,
                                    topic_index = topicRow["topic_index"],
                                    error_msg   = "API returned JSON with no components/widgets",
                                )
                            raise Exception(f"Topic JSON missing persistable content: {topicApiUrl}")

                        if topicRow:
                            self.componentTable.save_topic_content(
                                course_id     = course_id,
                                topic_index   = topicRow["topic_index"],
                                components    = topicComponents,
                                author_id     = topicAuthorId,
                                collection_id = topicCollectionId,
                                topic_api_url = topicApiUrl,
                            )
                        self.logger.info(f"Saved JSON for: {topicName}")
                    else:
                        if topicRow:
                            self.topicTable.mark_topic_error(
                                course_id   = course_id,
                                topic_index = topicRow["topic_index"],
                                error_msg   = "API returned empty response",
                            )
                        if not isSpecialTopic:
                            raise Exception(f"Cannot fetch content from Topic API Url: {topicApiUrl}")
                        self.logger.warning(f"Empty response for special topic (skipping): {topicName}")

                    self.osUtils.sleep(2)

                progress = self.progressTable.get_scrape_progress(course_id)
                self.logger.info(f"Course '{title}' done. Progress: {progress}")

        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiScraperMain:scrapeCourseOrPath: {lineNumber}: {e}")

