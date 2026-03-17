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

    def _getConfigBool(self, key: str, default: bool = False) -> bool:
        value = self.configJson.get(key, self.configJson.get(key.lower(), default))
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)

    def _resolveTopicUrls(self, textFileUrl: str, courseUrl: str,
                          topicApiUrlList: list, isProjectCourse: bool) -> list:
        if isProjectCourse:
            return self._resolveProjectTopicUrls(topicApiUrlList)
        return self._resolveStandardTopicUrls(textFileUrl, courseUrl)

    def _resolveProjectTopicUrls(self, topicApiUrlList: list) -> list:
        topicUrlsList = list(topicApiUrlList)
        self.logger.info(
            f"Project flow detected: using {len(topicUrlsList)} topic API URL(s) as topic URL values."
        )
        return topicUrlsList

    def _resolveStandardTopicUrls(self, textFileUrl: str, courseUrl: str) -> list:
        # getCourseTopicUrlsList independently navigates to courseUrl again,
        # expands all sidebar sections, then collects topic hrefs.
        topicUrlsList, _ = self.apiUtils.getCourseTopicUrlsList(textFileUrl, courseUrl)

        # Remove duplicates while preserving order.
        originalLen = len(topicUrlsList)
        seen = set()
        topicUrlsList = [url for url in topicUrlsList if not (url in seen or seen.add(url))]
        if len(topicUrlsList) < originalLen:
            self.logger.warning(f"Removed {originalLen - len(topicUrlsList)} duplicate URL(s)")

        return topicUrlsList

    def _parseResolvedApiIdentity(self, resolvedApiUrl: str, projectMeta: dict):
        resolvedApiPath = str(resolvedApiUrl or "").split("?")[0]
        apiParts = resolvedApiPath.split("/")

        projectWorkId = str(projectMeta.get("project_id", "") or "")
        projectAuthorId = str(projectMeta.get("project_author_id", "") or "")
        projectCollectionId = str(projectMeta.get("project_collection_id", "") or "")

        author_id = ""
        collection_id = ""
        if "/api/project/" in resolvedApiPath and len(apiParts) >= 8:
            author_id = apiParts[-3]
            collection_id = apiParts[-2]
            if not projectWorkId:
                projectWorkId = apiParts[-1]
        else:
            author_id = apiParts[-2] if len(apiParts) >= 2 else ""
            collection_id = apiParts[-1] if len(apiParts) >= 1 else ""

        if projectAuthorId:
            author_id = projectAuthorId
        if projectCollectionId:
            collection_id = projectCollectionId

        return author_id, collection_id, projectWorkId, resolvedApiPath

    def _extractTopicComponentsForPersistence(self, topicRawJson: dict,
                                              isProjectCourse: bool) -> list:
        if not isinstance(topicRawJson, dict):
            return []

        if isProjectCourse:
            projectComponents = self._extractProjectTopicComponents(topicRawJson)
            if projectComponents:
                return projectComponents

        components = topicRawJson.get("components", [])
        return components if isinstance(components, list) else []

    def _extractProjectTopicComponents(self, topicRawJson: dict) -> list:
        content = topicRawJson.get("content", {})
        if not isinstance(content, dict):
            return []

        projectComponents = []
        for groupName in ("descriptionWidgets", "hintWidgets", "solutionWidgets"):
            widgets = content.get(groupName, [])
            if not isinstance(widgets, list):
                continue
            for widgetIndex, widget in enumerate(widgets):
                if not isinstance(widget, dict):
                    continue

                component = {
                    "type": str(widget.get("type") or "ProjectWidget"),
                    "content": widget.get("content", {}),
                    "project_widget_group": groupName,
                    "project_widget_index": widgetIndex,
                }
                extraWidgetData = {
                    key: value for key, value in widget.items()
                    if key not in ("type", "content")
                }
                if extraWidgetData:
                    component["project_widget_meta"] = extraWidgetData
                projectComponents.append(component)

        codeContent = content.get("codeContent")
        if isinstance(codeContent, dict):
            projectComponents.append({
                "type": "ProjectCodeContent",
                "content": codeContent,
                "project_widget_group": "codeContent",
                "project_widget_index": 0,
            })

        if projectComponents:
            return projectComponents

        if content:
            return [{
                "type": "ProjectContent",
                "content": content,
                "project_widget_group": "content",
                "project_widget_index": 0,
            }]

        return []

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
            overrideTopicUrlCheck = self._getConfigBool("overrideTopicUrlCheck", False)

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
            courseApiUrl = None
            try:
                courseApiUrl = self.apiUtils.getAuthorAndCollectionId()
                self.logger.info(f"Derived Course API URL from author/collection logic: {courseApiUrl}")
            except Exception as e:
                self.logger.warning(f"Could not derive fallback course API URL from author/collection logic: {e}")
            if not courseApiUrlV2:
                self.logger.warning(
                    "Network capture did not yield a course API URL; "
                    "falling back to author/collection extraction."
                )
                self.logger.debug(f"Captured API URLs ({len(self.apiUrls)}): {self.apiUrls}")
                if not courseApiUrl:
                    raise Exception("Could not derive course API URL from both network capture and author/collection extraction")
                courseApiUrlV2 = courseApiUrl

            self.loginUtils.checkIfLoggedIn()
            courseCollectionsJson = self.apiUtils.getCourseCollectionsJson(
                courseApiUrlV2,
                courseApiUrl,
                courseUrl,
                self.apiUrls,
            )
            topicApiUrlList  = courseCollectionsJson["topicApiUrlList"]
            topicApiNameList = courseCollectionsJson["topicNameList"]
            topicApiUrlListLen = len(topicApiUrlList)

            projectMeta = courseCollectionsJson.get("projectMeta", {})
            resolvedApiUrl = str((courseApiUrlV2 or courseApiUrl) or "")
            isProjectCourse = bool(projectMeta.get("project_id")) or "/api/project/" in resolvedApiUrl

            topicUrlsList = self._resolveTopicUrls(
                textFileUrl=textFileUrl,
                courseUrl=courseUrl,
                topicApiUrlList=topicApiUrlList,
                isProjectCourse=isProjectCourse,
            )

            topicUrlsListLen = len(topicUrlsList)

            self.logger.debug(f"Course Topic URLs: {topicUrlsList}")
            self.logger.debug(f"Course Api Topic Urls: {topicApiUrlList}")
            self.logger.info(f"API Urls: {topicApiUrlListLen} == {topicUrlsListLen} :Topic Urls")
            if topicApiUrlListLen != topicUrlsListLen and not overrideTopicUrlCheck:
                apiUrlsSet = set(topicApiUrlList)
                topicUrlsSet = set(topicUrlsList)
                self.logger.debug(f"Extra API URLs (not in topic URLs): {apiUrlsSet - topicUrlsSet}")
                self.logger.debug(f"Extra in Topic URLs (not API URLs): {topicUrlsSet - apiUrlsSet}")
                raise Exception("CourseCollectionsJson and CourseTopicUrlsList Urls are not equal")   

            if topicApiUrlListLen != topicUrlsListLen and overrideTopicUrlCheck:
                if topicUrlsListLen < topicApiUrlListLen:
                    missingCount = topicApiUrlListLen - topicUrlsListLen
                    self.logger.warning(
                        f"Override(Topic URL Check) enabled: adding {missingCount} placeholder topic URL(s) to match API URL count."
                    )
                    for missingIdx in range(missingCount):
                        placeholderIndex = topicUrlsListLen + missingIdx + 1
                        placeholderUrl = (
                            f"https://topic-url-mismatch.invalid/"
                            f"gibberish-topic-{placeholderIndex:04}?showContent=true"
                        )
                        topicUrlsList.append(placeholderUrl)
                else:
                    self.logger.warning(
                        f"Override(Topic URL Check) enabled: trimming {topicUrlsListLen - topicApiUrlListLen} extra topic URL(s) to prioritize API URL list."
                    )
                    topicUrlsList = topicUrlsList[:topicApiUrlListLen]

                topicUrlsListLen = len(topicUrlsList)
                self.logger.info(f"Override aligned counts: API Urls: {topicApiUrlListLen} == {topicUrlsListLen} :Topic Urls")

            # ── Persist course + all topic stubs to DB ─────────────────────────
            courseTitle = courseCollectionsJson["courseTitle"]
            toc         = courseCollectionsJson["toc"]
            topicSlugs  = courseCollectionsJson["topicSlugList"]

            # Parse IDs from the resolved API endpoint.
            # collection/pal: /api/{collection|pal}/{author}/{collection}
            # project:        /api/project/{author}/{collection}/{project}
            author_id, collection_id, projectWorkId, resolvedApiPath = self._parseResolvedApiIdentity(
                resolvedApiUrl=resolvedApiUrl,
                projectMeta=projectMeta,
            )

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

            if projectWorkId or "/api/project/" in resolvedApiPath:
                course_type = "Project"

            # work_type mirrors ApiUtility.getCourseCollectionsJson:
            # "module" for paths, "collection" for everything else.
            work_type = "module" if course_type == "Path" else "collection"

            course_slug = slugify(courseTitle)
            pathMeta = courseCollectionsJson.get("pathMeta", {})
            pathAuthorId = str(pathMeta.get("path_author_id", "") or "")
            pathCollectionId = str(pathMeta.get("path_collection_id", "") or "")
            pathUrlSlug = str(pathMeta.get("path_url_slug", "") or "")
            pathTitle = str(pathMeta.get("path_title", "") or "")
            projectTitle = str(projectMeta.get("project_title", "") or "")
            projectUrlSlug = str(projectMeta.get("project_url_slug", "") or "")

            if course_type == "Project":
                if not projectWorkId:
                    projectWorkId = str(collection_id)
                if not projectTitle:
                    projectTitle = courseTitle
                if not projectUrlSlug:
                    projectUrlSlug = slugify(projectTitle)

            path_id = None
            if course_type == "Path":
                if not pathAuthorId:
                    pathAuthorId = str(author_id)
                if not pathCollectionId:
                    pathCollectionId = str(collection_id)
                if not pathTitle:
                    pathTitle = courseTitle
                if not pathUrlSlug:
                    pathUrlSlug = slugify(pathTitle)
                path_id = self.db.upsert_path(
                    path_author_id = pathAuthorId,
                    path_collection_id = pathCollectionId,
                    path_url_slug = pathUrlSlug,
                    path_title = pathTitle
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
                project_id    = projectWorkId if course_type == "Project" else None,
            )
            if course_type == "Project":
                self.db.upsert_project(
                    course_id=course_id,
                    project_author_id=str(author_id),
                    project_collection_id=str(collection_id),
                    project_work_id=str(projectWorkId),
                    project_title=projectTitle,
                    project_url_slug=projectUrlSlug,
                    toc=toc,
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

            self.progressQueue.put(("max-topic", topicApiUrlListLen))
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
            for topicIndex in range(startIndex, topicApiUrlListLen):
                self.progressQueue.put(("progress-topic", topicIndex + 1))
                topicApiUrl = topicApiUrlList[topicIndex]
                topicUrl    = topicUrlsList[topicIndex] if topicIndex < len(topicUrlsList) else topicApiUrl
                topicNameRaw = topicApiNameList[topicIndex] if topicIndex < len(topicApiNameList) else f"topic-{topicIndex + 1}"
                topicName   = f"{topicIndex:03}-{self.fileUtils.filenameSlugify(topicNameRaw)}"

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
                    topicRawJson = self.resolveLazyLoadPlaceholders(
                        topicRawJson, author_id, collection_id, work_type
                    )
                    page_id = topicRow["page_id"] if topicRow else ""
                    topicRawJson = self.resolveDrawIOSlides(
                        topicRawJson, author_id, collection_id, page_id
                    )
                    topicComponents = self._extractTopicComponentsForPersistence(
                        topicRawJson=topicRawJson,
                        isProjectCourse=isProjectCourse,
                    )

                    # Normal topics must have persistable content.
                    if not isSpecialTopic and not topicComponents:
                        if topicRow:
                            self.db.mark_topic_error(
                                course_id   = course_id,
                                topic_index = topicRow["topic_index"],
                                error_msg   = "API returned JSON with no components/widgets",
                            )
                        raise Exception(f"Topic JSON missing persistable content: {topicApiUrl}")

                    if topicRow:
                        self.db.save_topic_content(
                            course_id     = course_id,
                            topic_index   = topicRow["topic_index"],
                            components    = topicComponents,
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
