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
from src.ScraperType.CourseTopicScraper.ScraperModules.NetworkMonitor import NetworkMonitor
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
        self.networkMonitor = NetworkMonitor(self.configJson)

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
                raise
            except Exception as e:
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                lineNumber = e.__traceback__.tb_lineno
                raise Exception(f"ApiScraperMain:start: {lineNumber}: {e}")

        self.logger.info("ApiScraperMain completed.")

    # ------------------------------------------------------------------ #
    #  Core: resolve course structure, then store each topic JSON in DB
    # ------------------------------------------------------------------ #

    def scrapeCourseOrPath(self, textFileUrl):
        try:
            # ── Resolve course & topic URL lists (identical to CourseTopicScraper) ──
            courseUrl = self.apiUtils.getCourseUrl(textFileUrl)

            # Navigate to courseUrl and read author/collection IDs while window.__next_f
            # is freshly populated, BEFORE getCourseTopicUrlsList's expandAllSections()
            # alters the page's Next.js flight data and makes the IDs undetectable.
            self.browser.get(textFileUrl)
            self.osUtils.sleep(3)
            self.networkMonitor.browser = self.browser
            self.apiUrls = self.networkMonitor.getAPIUrls()
            self.logger.debug(f"Captured API URLs from browser: {self.apiUrls}")
            courseApiUrlV2 = self.apiUtils.getCourseApiUrlFromNetworkUrls(self.apiUrls, courseUrl)
            self.logger.info(f"Derived Course API URL from network capture: {courseApiUrlV2}")
            courseApiUrl = self.apiUtils.getAuthorAndCollectionId()
            if not courseApiUrlV2:
                self.logger.warning(
                    "Network capture did not yield a course API URL; "
                    "falling back to author/collection extraction."
                )
                self.logger.debug(f"Captured API URLs ({len(self.apiUrls)}): {self.apiUrls}")
                courseApiUrlV2 = courseApiUrl
            self.logger.info(f"Derived Course API URL from author/collection logic: {courseApiUrl}")

            # getCourseTopicUrlsList independently navigates to courseUrl again, expands
            # all sidebar sections, then collects the topic hrefs — this double-load is
            # intentional and necessary for reliability.
            topicUrlsList, pathFolderName = self.apiUtils.getCourseTopicUrlsList(textFileUrl, courseUrl)

            # Remove duplicates while preserving order
            originalLen = len(topicUrlsList)
            seen = set()
            topicUrlsList = [url for url in topicUrlsList if not (url in seen or seen.add(url))]
            if len(topicUrlsList) < originalLen:
                self.logger.warning(f"Removed {originalLen - len(topicUrlsList)} duplicate URL(s)")

            self.loginUtils.checkIfLoggedIn()
            courseCollectionsJson = self.apiUtils.getCourseCollectionsJson(courseApiUrlV2, courseUrl)
            topicApiUrlList  = courseCollectionsJson["topicApiUrlList"]
            topicApiNameList = courseCollectionsJson["topicNameList"]
            topicApiUrlListLen = len(topicApiUrlList)
            topicUrlsListLen   = len(topicUrlsList)

            self.logger.debug(f"Course Topic URLs: {topicUrlsList}")
            self.logger.debug(f"Course Api Topic Urls: {topicApiUrlList}")
            self.logger.info(f"API Urls: {topicApiUrlListLen} == {topicUrlsListLen} :Topic Urls")
            if topicApiUrlListLen != topicUrlsListLen:
                self.logger.warning(
                    f"Primary collection API count mismatch ({topicApiUrlListLen} != {topicUrlsListLen}). "
                    f"Trying fallback endpoint for topic API URLs."
                )
                courseCollectionsJson = self.apiUtils.getCourseCollectionsJson(courseApiUrl, courseUrl)
                topicApiUrlList  = courseCollectionsJson["topicApiUrlList"]
                topicApiNameList = courseCollectionsJson["topicNameList"]
                topicApiUrlListLen = len(topicApiUrlList)

                self.logger.info( f"API Urls: {topicApiUrlListLen} == {topicUrlsListLen} :Topic Urls")
                self.logger.debug(f"Course Topic URLs: {topicUrlsList}")
                self.logger.debug(f"Course Api Topic Urls: {topicApiUrlList}")
                if topicApiUrlListLen != topicUrlsListLen:
                    apiUrlsSet = set(topicApiUrlList)
                    topicUrlsSet = set(topicUrlsList)
                    self.logger.debug(f"Extra API URLs (not in topic URLs): {apiUrlsSet - topicUrlsSet}")
                    self.logger.debug(f"Extra in Topic URLs (not API URLs): {topicUrlsSet - apiUrlsSet}")
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
            # Enrich toc_json with DB-sourced course_id + topic_index now that topics exist
            self.db.finalize_course_toc(course_id)

            self.progressQueue.put(("max-topic", topicUrlsListLen))
            overwrite = self.configJson.get("overwrite", False)

            # ── Determine start index ──────────────────────────────────────────
            # When overwrite=True the caller expects scraping to resume from the
            # URL that was passed in (textFileUrl), not from the very first topic.
            # Strip the query string for matching since topicUrlsList entries may
            # or may not include ?showContent=true.
            startIndex = 0
            if overwrite:
                baseTextFileUrl = textFileUrl.split("?")[0]
                for idx, url in enumerate(topicUrlsList):
                    if url.split("?")[0] == baseTextFileUrl:
                        startIndex = idx
                        break
                if startIndex:
                    self.logger.info(
                        f"overwrite=True: starting from topic index {startIndex} "
                        f"matching URL: {baseTextFileUrl}"
                    )

            # ── Fetch & store each topic JSON ──────────────────────────────────
            for topicIndex in range(startIndex, topicUrlsListLen):
                self.progressQueue.put(("progress-topic", topicIndex + 1))
                topicUrl    = topicUrlsList[topicIndex]
                topicApiUrl = topicApiUrlList[topicIndex]
                topicName   = f"{topicIndex:03}-{self.fileUtils.filenameSlugify(topicApiNameList[topicIndex])}"

                self.logger.info(
                    f"----------------------------------------------------------------------------------\n"
                    f"Scraping Topic: {topicName}: {topicUrl}"
                )

                # DB-based resume: skip done topics only when not in overwrite mode.
                # In overwrite mode we started from the matching URL index, so every
                # topic from that point onwards is intentionally re-scraped.
                topicRow = self.db.get_topic_by_api_url(course_id, topicApiUrl)
                if not overwrite and topicRow and topicRow["status"] == "done":
                    self.logger.info(f"Skipping already-done topic: {topicName}")
                    continue

                isSpecialTopic = topicUrl.split("/")[-1] in [
                    "assessment?showContent=true",
                    "cloudlab?showContent=true",
                    "project?showContent=true",
                    "mock-interview?showContent=true",
                ]

                # Re-check session before every fetch (same as original scraper)
                self.loginUtils.checkIfLoggedIn()

                # Fetch the raw full JSON response from the topic API.
                # executeJsToGetJson runs a browser-side fetch() so auth cookies
                # are sent automatically — no manual cookie handling needed.
                topicRawJson = self.apiUtils.executeJsToGetJson(topicApiUrl)

                # Any non-200 HTTP response on a special topic is not an error —
                # content simply isn't available; mark done and proceed.
                # On a normal topic, any non-200 is a real error — raise immediately.
                if isinstance(topicRawJson, str) and topicRawJson.startswith("HTTP_"):
                    httpCode = topicRawJson.split("_")[1]
                    if isSpecialTopic:
                        if topicRow:
                            self.db.mark_topic_done(course_id, topicRow["topic_index"])
                        self.logger.info(f"HTTP {httpCode} on special topic — marking done and skipping: {topicName}")
                        self.osUtils.sleep(2)
                        continue
                    else:
                        raise Exception(f"HTTP {httpCode} fetching topic API URL: {topicApiUrl}")

                if topicRawJson:
                    # Normal topics must have components data — empty components indicates a problem.
                    if not isSpecialTopic and not topicRawJson.get("components"):
                        if topicRow:
                            self.db.mark_topic_error(
                                course_id   = course_id,
                                topic_index = topicRow["topic_index"],
                                error_msg   = "API returned JSON with no components",
                            )
                        raise Exception(f"Topic JSON missing 'components' data: {topicApiUrl}")
                    topicRawJson = self.resolveLazyLoadPlaceholders(
                        topicRawJson, author_id, collection_id, work_type
                    )
                    page_id = topicRow["page_id"] if topicRow else ""
                    topicRawJson = self.resolveDrawIOSlides(
                        topicRawJson, author_id, collection_id, page_id
                    )
                    if topicRow:
                        self.db.save_topic_content(
                            course_id     = course_id,
                            topic_index   = topicRow["topic_index"],
                            components    = topicRawJson.get("components", []),
                            author_id     = author_id,
                            collection_id = collection_id,
                            topic_api_url = topicApiUrl,
                        )
                    self.logger.info(f"Saved JSON for: {topicName}")
                else:
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
    #  DrawIO slides resolution
    # ------------------------------------------------------------------ #

    def resolveDrawIOSlides(self, topicJson: dict, author_id: str, collection_id: str, page_id: str) -> dict:
        """
        For DrawIOWidget components that carry slide data (slidesEnabled=True,
        isSlides=True, slidesId present), fetch
          GET /api/slides/data?slides_id=<slidesId>
        and enrich the component content with:
          slidesApiData  – raw API response
          slidesImages   – list of image URLs in the form:
                           /api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}

        Plain DrawIOWidget components (no slides fields) are left untouched.
        """
        try:
            components = topicJson.get("components", [])
            for component in components:
                if component.get("type") != "DrawIOWidget":
                    continue
                content = component.get("content", {})
                # Only handle the slides variant — plain DrawIO has no slidesId
                slides_id = content.get("slidesId")
                if not (content.get("slidesEnabled") and content.get("isSlides") and slides_id):
                    continue

                slides_api_url = f"https://www.educative.io/api/slides/data?slides_id={slides_id}"
                self.logger.info(f"Fetching slides data for DrawIOWidget slidesId={slides_id}")
                self.loginUtils.checkIfLoggedIn()
                slides_data = self.apiUtils.executeJsToGetJson(slides_api_url)

                if not slides_data or isinstance(slides_data, str):
                    self.logger.warning(
                        f"No slides data for slidesId={slides_id} — response: {slides_data}"
                    )
                    continue

                # Store the full raw API response so nothing is lost
                component["content"]["slidesApiData"] = slides_data

                # Best-effort: extract image URLs from common response shapes.
                # Educative's slides API may return a list directly, or nest under
                # a key such as "slides", "images", or "data".
                image_urls = self._extractSlidesImageUrls(slides_data, author_id, collection_id, page_id)
                if image_urls:
                    component["content"]["slidesImages"] = image_urls
                    self.logger.info(
                        f"Stored {len(image_urls)} slidesImages for DrawIOWidget slidesId={slides_id}"
                    )
                else:
                    self.logger.warning(
                        f"Could not extract image URLs from slides response for slidesId={slides_id}. "
                        f"Raw data stored in slidesApiData for manual inspection."
                    )
            return topicJson
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"resolveDrawIOSlides: {lineNumber}: {e}")
            return topicJson

    def _extractSlidesImageUrls(self, slides_data: dict, author_id: str, collection_id: str, page_id: str) -> list:
        """
        Build image URLs from a slides API response.
        Known response format:
          { "status": 4002, "image_ids": [5505347740106752, ...], "error_msg": "" }
        Image URLs use the collection image format:
          /api/collection/{author_id}/{collection_id}/page/{page_id}/image/{image_id}
        Returns an empty list when no image IDs can be found — caller will
        log a warning so the raw slidesApiData can be inspected.
        """
        BASE = f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image"

        def _url_from_id(image_id) -> str:
            return f"{BASE}/{image_id}"

        if not isinstance(slides_data, dict):
            return []

        # Primary: { "image_ids": [...] }  — confirmed response format
        image_ids = slides_data.get("image_ids")
        if isinstance(image_ids, list):
            return [_url_from_id(img_id) for img_id in image_ids if img_id]

        return []

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
