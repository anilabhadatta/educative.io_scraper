import os
import re

from slugify import slugify
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.ScraperType.CourseTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.Utility.UrlUtility import UrlUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


class ApiUtility:
    def __init__(self, configJson):
        self.browser = None
        self.timeout = 10
        self.osUtils = OSUtility(configJson)
        self.urlUtils = UrlUtility()
        self.fileUtils = FileUtility()
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["ApiUtility"]
        self.logger = Logger(configJson, "ApiUtility").logger


    def getCourseApiUrlFromNetworkUrls(self, apiUrls, courseUrl):
        try:
            if not apiUrls:
                self.logger.warning("No API URLs found in network capture")
                return None

            workType = "module" if "/module/" in courseUrl or "/pal/" in courseUrl else "collection"
            projectPattern = re.compile(r"^https:\/\/www\.educative\.io\/api\/project\/(\d+)\/(\d+)\/(\d+)(?:\/.*)?(?:\?.*)?$")
            palPattern = re.compile(r"^https:\/\/www\.educative\.io\/api\/pal\/(\d+)\/(\d+)(?:\/.*)?(?:\?.*)?$")
            collectionPattern = re.compile(r"^https:\/\/www\.educative\.io\/api\/collection\/(\d+)\/(\d+)(?:\/.*)?(?:\?.*)?$")

            # Priority 1: Project endpoint in network capture.
            for url in reversed(apiUrls):
                if not isinstance(url, str):
                    continue
                match = projectPattern.match(url.strip())
                if match:
                    authorId, collectionId, projectId = match.group(1), match.group(2), match.group(3)
                    return f"https://www.educative.io/api/project/{authorId}/{collectionId}/{projectId}"

            # Priority 1: PAL endpoint in network capture.
            for url in reversed(apiUrls):
                if not isinstance(url, str):
                    continue
                match = palPattern.match(url.strip())
                if match:
                    authorId, collectionId = match.group(1), match.group(2)
                    return f"https://www.educative.io/api/pal/{authorId}/{collectionId}?work_type={workType}"

            # Priority 2: collection endpoint in network capture.
            for url in reversed(apiUrls):
                if not isinstance(url, str):
                    continue
                match = collectionPattern.match(url.strip())
                if match:
                    authorId, collectionId = match.group(1), match.group(2)
                    return f"https://www.educative.io/api/collection/{authorId}/{collectionId}?work_type={workType}"

            self.logger.warning(
                f"No matching /api/project/<author>/<collection>/<project>, /api/pal/<author>/<collection> "
                f"or /api/collection/<author>/<collection> ID URL found (count={len(apiUrls)})"
            )
            self.logger.debug(f"Captured API URLs: {apiUrls}")

            return None
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseApiUrlFromNetworkUrls: {lineNumber}: {e}")


    def executeJsToGetJson(self, url):
        self.logger.info(f"Executing JS to get JSON from URL: {url}")
        apiJsonScript = f"""
            return new Promise((resolve, reject) => {{
                fetch("{url}", {{
                    method: 'GET',
                    mode: 'cors',
                    cache: 'no-store',
                    headers: {{
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
                    }}
                }})
                    .then(response => {{
                        if (response.status === 401 || response.status === 403) {{
                            reject('HTTP_' + response.status);
                            return;
                        }}
                        if (response.status !== 200) {{
                            resolve('HTTP_' + response.status);
                            return;
                        }}
                        return response.json();
                    }})
                    .then(data => {{
                        if (data !== undefined) resolve(data);
                    }})
                    .catch(error => {{
                        reject(error);
                    }});
            }});
        """
        result = self.browser.execute_script(apiJsonScript)
        if isinstance(result, str) and result in ("HTTP_401", "HTTP_403"):
            code = result.split("_")[1]
            raise Exception(f"HTTP {code} fetching API URL — topic inaccessible or session expired: {url}")
        return result


    def getTopicApiContentJson(self, topicApiUrl):
        try:
            self.logger.info(f"Getting Topic API Content JSON from URL: {topicApiUrl}")
            retry = 1
            while retry < 3:
                try:
                    jsonData = self.executeJsToGetJson(topicApiUrl)
                    if "components" in jsonData:
                        self.logger.info("Successfully fetched JSON API data")
                        return jsonData["components"]
                except Exception:
                    pass
                retry += 1
                self.osUtils.sleep(2)
                self.logger.info(f"Found Error fetching Json, retrying {retry} out of 2: {topicApiUrl}")
            return None
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseApiContentJson: {lineNumber}: {e}")


    def getCourseApiContentJson(self, courseApiUrl):
        try:
            self.logger.info(f"Getting Course API Content JSON from Course API URL: {courseApiUrl}")
            retry = 1
            while retry < 3:
                try:
                    jsonData = self.executeJsToGetJson(courseApiUrl)
                    if "instance" in jsonData:
                        self.logger.info("Successfully fetched JSON API data")
                        return jsonData["instance"]
                    if isinstance(jsonData, dict) and "details" in jsonData and isinstance(jsonData["details"], dict):
                        self.logger.info("Successfully fetched JSON API details payload")
                        return {"details": jsonData["details"]}
                    if isinstance(jsonData, dict) and "toc" in jsonData:
                        self.logger.info("Successfully fetched direct JSON payload")
                        return {"details": jsonData}
                except Exception:
                    pass
                retry += 1
                if retry == 3:
                    raise Exception("Could not Course fetch data from API")
                self.osUtils.sleep(2)
                self.logger.info(f"Found Error fetching Json, retrying {retry} out of 2: {courseApiUrl}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseApiContentJson: {lineNumber}: {e}")


    def _normalizeProjectApiPayload(self, projectPayload):
        if not isinstance(projectPayload, dict):
            return {}
        if "instance" in projectPayload and isinstance(projectPayload.get("instance"), dict):
            instance = projectPayload.get("instance", {})
            if isinstance(instance.get("details"), dict):
                return instance["details"]
            return instance
        if isinstance(projectPayload.get("details"), dict):
            return projectPayload["details"]
        return projectPayload


    def _inferProjectTopicApiTemplate(self, apiUrls, authorId, collectionId, projectId, topicIds):
        baseProjectApiUrl = f"https://www.educative.io/api/project/{authorId}/{collectionId}/{projectId}"
        topicIdSet = {str(topicId) for topicId in topicIds if topicId is not None}
        if apiUrls:
            for url in reversed(apiUrls):
                if not isinstance(url, str):
                    continue
                cleanUrl = url.strip().split("?")[0]
                if not cleanUrl.startswith(baseProjectApiUrl + "/"):
                    continue
                suffix = cleanUrl[len(baseProjectApiUrl) + 1:]
                suffixParts = [part for part in suffix.split("/") if part]
                if not suffixParts:
                    continue
                suffixId = suffixParts[-1]
                if suffixId not in topicIdSet:
                    continue
                if len(suffixParts) == 1:
                    return baseProjectApiUrl + "/{topic_id}"
                prefix = "/".join(suffixParts[:-1])
                return f"{baseProjectApiUrl}/{prefix}/{{topic_id}}"

        # Fallback for project task APIs when no per-topic call was captured yet.
        return baseProjectApiUrl + "/{topic_id}"


    def getCourseCollectionsJsonProject(self, projectApiUrl, jsonData, apiUrls=None):
        try:
            self.logger.info(f"Getting Course Collections JSON (Project) from URL: {projectApiUrl}")
            authorId = str(jsonData.get("author_id", "") or "")
            collectionId = str(jsonData.get("collection_id", "") or "")
            projectId = str(jsonData.get("project_id", "") or "")
            courseTitle = jsonData.get("title", "")
            courseType = str(jsonData.get("work_type", "collection") or "collection")

            # Some project payloads omit IDs in details; recover from the API URL.
            if not (authorId and collectionId and projectId):
                projectMatch = re.search(r"/api/project/([^/]+)/([^/]+)/([^/?]+)", str(projectApiUrl))
                if projectMatch:
                    if not authorId:
                        authorId = projectMatch.group(1)
                    if not collectionId:
                        collectionId = projectMatch.group(2)
                    if not projectId:
                        projectId = projectMatch.group(3)

            projectMeta = {
                "project_author_id": authorId,
                "project_collection_id": collectionId,
                "project_id": projectId,
                "project_title": courseTitle,
                "project_url_slug": str(jsonData.get("url_slug", "") or ""),
            }
            pathMeta = {
                "path_author_id": str(jsonData.get("path_author_id", "") or ""),
                "path_collection_id": str(jsonData.get("path_id", "") or ""),
                "path_url_slug": str(jsonData.get("path_url_slug", "") or ""),
                "path_title": str(jsonData.get("path_title", "") or ""),
            }

            categories = jsonData.get("toc", {}).get("categories", [])
            topicApiUrlList = []
            topicNameList = []
            topicSlugList = []
            topicIdx = 0
            toc = []

            allTopicIds = []
            for category in categories:
                if not isinstance(category, dict):
                    continue
                pages = category.get("pages")
                if not isinstance(pages, list):
                    continue
                for page in pages:
                    if not isinstance(page, dict):
                        continue
                    topicId = page.get("id", page.get("page_id"))
                    if topicId is not None:
                        allTopicIds.append(topicId)

            topicApiTemplate = self._inferProjectTopicApiTemplate(apiUrls or [], authorId, collectionId, projectId, allTopicIds)

            def appendTopic(topicId, topicTitle, topicSlugValue, topicBucket):
                nonlocal topicIdx
                if topicId is None or not topicTitle:
                    return
                topicSlug = topicSlugValue if isinstance(topicSlugValue, str) and topicSlugValue else slugify(topicTitle)
                topicApiUrl = topicApiTemplate.replace("{topic_id}", str(topicId))

                topicApiUrlList.append(topicApiUrl)
                topicNameList.append(topicTitle)
                topicSlugList.append(topicSlug)

                topicData = {
                    "index": topicIdx,
                    "title": topicTitle,
                    "slug": topicSlug,
                    "api_url": topicApiUrl,
                }
                topicBucket.append(topicData)
                topicIdx += 1

            for category in categories:
                if not isinstance(category, dict):
                    continue
                moduleTitle = category.get("title", "")
                pages = category.get("pages")
                if not isinstance(pages, list) or not pages:
                    continue

                moduleTopics = []
                for page in pages:
                    if not isinstance(page, dict):
                        continue
                    topicId = page.get("id", page.get("page_id"))
                    topicTitle = page.get("title", moduleTitle)
                    topicSlugValue = page.get("slug", "")
                    appendTopic(topicId, topicTitle, topicSlugValue, moduleTopics)

                if moduleTopics:
                    toc.append({"category": moduleTitle, "topics": moduleTopics})

            return {
                "courseTitle": courseTitle,
                "topicApiUrlList": topicApiUrlList,
                "topicNameList": topicNameList,
                "topicSlugList": topicSlugList,
                "toc": toc,
                "pathMeta": pathMeta,
                "projectMeta": projectMeta,
                "courseType": "Project",
                "workType": courseType,
            }
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseCollectionsJsonProject: {lineNumber}: {e}")


    def getCourseCollectionsJsonPal(self, courseApiUrl, categoryType, courseType, jsonData):
        try:
            self.logger.info(f"Getting Course Collections JSON (PAL) from URL: {courseApiUrl}")
            categories = jsonData["toc"]["categories"]
            courseTitle = jsonData["title"]
            pathMeta = {
                "path_author_id": str(jsonData.get("path_author_id", "") or ""),
                "path_collection_id": str(jsonData.get("path_id", "") or ""),
                "path_url_slug": str(jsonData.get("path_url_slug", "") or ""),
                "path_title": str(jsonData.get("path_title", "") or ""),
            }

            topicApiUrlList = []
            topicNameList = []
            topicSlugList = []
            topicIdx = 0
            toc = []

            def appendTopic(topicId, topicTitle, authorId, collectionId, topicBucket=None):
                nonlocal topicIdx
                if topicId is None or not topicTitle:
                    return
                baseApiUrl = f"https://www.educative.io/api/collection/{authorId}/{collectionId}/page/"
                topicApiUrl = baseApiUrl + str(topicId) + f"?work_type={courseType}"
                topicSlug = slugify(topicTitle)

                topicApiUrlList.append(topicApiUrl)
                topicNameList.append(topicTitle)
                topicSlugList.append(topicSlug)

                topicData = {
                    "index": topicIdx,
                    "title": topicTitle,
                    "slug": topicSlug,
                    "api_url": topicApiUrl,
                }
                if topicBucket is None:
                    toc.append(topicData)
                else:
                    topicBucket.append(topicData)
                topicIdx += 1

            for category in categories:
                if not (
                    any(cType in category.get("type", "") for cType in categoryType)
                    and (
                        isinstance(category.get("id"), int)
                        or len(str(category.get("id", ""))) <= 10
                        or category.get("type") in ("LINKED_MOCK_INTERVIEW",)
                    )
                ):
                    continue

                moduleTitle = category.get("title", "")
                moduleTopics = []

                nestedToc = category.get("toc")
                if isinstance(nestedToc, list) and nestedToc:
                    # PAL module payload keeps lessons under category.toc[*].pages.
                    for tocEntry in nestedToc:
                        pages = tocEntry.get("pages")
                        if isinstance(pages, list) and pages:
                            for page in pages:
                                topicId = page.get("page_id", page.get("id"))
                                topicTitle = page.get("title", tocEntry.get("title", moduleTitle))
                                authorId = page.get("author_id") or jsonData["author_id"]
                                collectionId = page.get("collection_id") or jsonData["collection_id"]
                                appendTopic(topicId, topicTitle, authorId, collectionId, moduleTopics)
                        else:
                            topicId = tocEntry.get("page_id", tocEntry.get("id"))
                            topicTitle = tocEntry.get("title", moduleTitle)
                            authorId = tocEntry.get("author_id") or jsonData["author_id"]
                            collectionId = tocEntry.get("collection_id") or jsonData["collection_id"]
                            appendTopic(topicId, topicTitle, authorId, collectionId, moduleTopics)
                else:
                    pages = category.get("pages")
                    if isinstance(pages, list) and pages:
                        for page in pages:
                            topicId = page.get("page_id", page.get("id"))
                            topicTitle = page.get("title", moduleTitle)
                            authorId = page.get("author_id") or jsonData["author_id"]
                            collectionId = page.get("collection_id") or jsonData["collection_id"]
                            appendTopic(topicId, topicTitle, authorId, collectionId, moduleTopics)
                    else:
                        topicId = category.get("page_id", category.get("id"))
                        topicTitle = category.get("title", "")
                        authorId = category.get("author_id") or jsonData["author_id"]
                        collectionId = category.get("collection_id") or jsonData["collection_id"]
                        appendTopic(topicId, topicTitle, authorId, collectionId, moduleTopics)

                if moduleTopics:
                    toc.append({"category": moduleTitle, "topics": moduleTopics})

            return {
                "courseTitle": courseTitle,
                "topicApiUrlList": topicApiUrlList,
                "topicNameList": topicNameList,
                "topicSlugList": topicSlugList,
                "toc": toc,
                "pathMeta": pathMeta,
            }
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseCollectionsJsonPal: {lineNumber}: {e}")


    def getCourseCollectionsJson(self, courseApiUrlV2, courseApiUrl=None, courseUrl=None, apiUrls=None):
        try:
            # Backward compatibility: legacy call shape was (courseApiUrl, courseUrl).
            if courseUrl is None:
                courseUrl = courseApiUrl
                courseApiUrl = courseApiUrlV2
            if courseApiUrl is None:
                courseApiUrl = courseApiUrlV2

            self.logger.info(f"Getting Course Collections JSON from Course API URL: {courseApiUrlV2}")
            self.logger.info(f"Getting Course Collections JSON from Course API Fallback URL: {courseApiUrl}")

            projectApiUrl = None
            for candidate in (courseApiUrlV2, courseApiUrl):
                if isinstance(candidate, str) and "/api/project/" in candidate:
                    projectApiUrl = candidate
                    break
            if not projectApiUrl and apiUrls:
                inferredApiUrl = self.getCourseApiUrlFromNetworkUrls(apiUrls, courseUrl or "")
                if isinstance(inferredApiUrl, str) and "/api/project/" in inferredApiUrl:
                    projectApiUrl = inferredApiUrl

            if projectApiUrl:
                try:
                    projectPayload = self.executeJsToGetJson(projectApiUrl)
                except Exception:
                    if courseApiUrl and courseApiUrl != projectApiUrl:
                        self.logger.warning(
                            f"Error fetching from Project API URL, falling back to original Course API URL: {courseApiUrl}"
                        )
                        projectPayload = self.executeJsToGetJson(courseApiUrl)
                    else:
                        raise
                projectJson = self._normalizeProjectApiPayload(projectPayload)
                return self.getCourseCollectionsJsonProject(projectApiUrl, projectJson, apiUrls)

            primaryApiUrl = None
            if isinstance(courseApiUrlV2, str) and courseApiUrlV2:
                primaryApiUrl = courseApiUrlV2
            elif isinstance(courseApiUrl, str) and courseApiUrl:
                primaryApiUrl = courseApiUrl

            fallbackApiUrl = None
            if primaryApiUrl == courseApiUrlV2 and isinstance(courseApiUrl, str) and courseApiUrl and courseApiUrl != primaryApiUrl:
                fallbackApiUrl = courseApiUrl
            elif primaryApiUrl == courseApiUrl and isinstance(courseApiUrlV2, str) and courseApiUrlV2 and courseApiUrlV2 != primaryApiUrl:
                fallbackApiUrl = courseApiUrlV2

            if not primaryApiUrl:
                raise Exception("No collection API URL resolved from network capture or fallback extraction")

            courseUrl = str(courseUrl or "")
            courseUrlParts = courseUrl.split('/')
            courseType = courseUrlParts[3] if len(courseUrlParts) > 3 else ""
            isPalUrl = "/pal/" in primaryApiUrl
            if "module" in courseType or isPalUrl:
                courseType = "module"
            else:
                courseType = "collection"
            try:
                jsonData = self.getCourseApiContentJson(primaryApiUrl)
            except Exception:
                if fallbackApiUrl:
                    self.logger.warning(
                        f"Error fetching from primary Course API URL, falling back to alternate URL: {fallbackApiUrl}"
                    )
                    jsonData = self.getCourseApiContentJson(fallbackApiUrl)
                else:
                    raise
            jsonData = jsonData.get("details", jsonData)
            authorId = str(jsonData["author_id"])
            collectionId = str(jsonData["collection_id"])
            pathMeta = {
                "path_author_id": str(jsonData.get("path_author_id", "") or ""),
                "path_collection_id": str(jsonData.get("path_id", "") or ""),
                "path_url_slug": str(jsonData.get("path_url_slug", "") or ""),
                "path_title": str(jsonData.get("path_title", "") or ""),
            }
            categories = jsonData["toc"]["categories"]
            courseTitle = jsonData["title"]
            topicApiUrlList = []
            topicNameList = []
            topicSlugList = []
            categoryType = ["COLLECTION_PROJECT", "COLLECTION_CATEGORY", "COLLECTION_ASSESSMENT", "PATH_EXTERNAL_PROJECT", "PATH_EXTERNAL_ASSESSMENT", "CLOUD_LAB", "LINKED_MOCK_INTERVIEW", "PATH_INTERNAL_MODULE"]
            if isPalUrl:
                return self.getCourseCollectionsJsonPal(primaryApiUrl, categoryType, courseType, jsonData)
            baseApiUrl = f"https://www.educative.io/api/collection/{authorId}/{collectionId}/page/"
            topicIdx = 0
            toc = []
            for category in categories:
                if any(cType in category["type"] for cType in categoryType) and (
                        isinstance(category["id"], int) or len(category["id"]) <= 10 or category["type"] in ("LINKED_MOCK_INTERVIEW")):
                    if not category["pages"]:
                        topicApiUrl = baseApiUrl + str(category["id"]) + f"?work_type={courseType}"
                        topicApiUrlList.append(topicApiUrl)
                        topicNameList.append(category["title"])
                        topicSlugList.append(slugify(category["title"]))
                        category_topic = {"index": topicIdx, "title": category["title"], "slug": slugify(category["title"]), "api_url": topicApiUrl}
                        toc.append(category_topic)
                        topicIdx += 1
                    else:
                        category_topic = {"category": category["title"], "topics": []}
                        toc.append(category_topic)

                        for page in category["pages"]:
                            topicApiUrl = baseApiUrl + str(page["id"]) + f"?work_type={courseType}"
                            topicApiUrlList.append(topicApiUrl)
                            topicNameList.append(page["title"])
                            topicSlugList.append(slugify(page["title"]))
                            category_topic["topics"].append({"index": topicIdx, "title": page["title"], "slug": slugify(page["title"]), "api_url": topicApiUrl})
                            topicIdx += 1

            return {
                "courseTitle": courseTitle,
                "topicApiUrlList": topicApiUrlList,
                "topicNameList": topicNameList,
                "topicSlugList": topicSlugList,
                "toc": toc,
                "pathMeta": pathMeta,
            }
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseCollectionsJson: {lineNumber}: {e}")


    def getCourseTopicUrlsList(self, topicUrl, courseUrl):
        try:
            self.logger.info(f"Getting Course Topic URLs List from Course URL: {courseUrl}")
            self.browser.get(courseUrl)
            self.logger.info(f"Topic URL: {topicUrl}")
            topicUrlSelector = self.urlUtils.getTopicUrlSelector(topicUrl)
            self.logger.info(f"Topic URL Selector: {topicUrlSelector}")
            self.osUtils.sleep(2)
            WebDriverWait(self.browser, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, topicUrlSelector)))
            if "/module/" not in topicUrl:
                self.seleniumBasicUtils.browser = self.browser
                self.seleniumBasicUtils.expandAllSections()
            pathFolderName = None
            if "/module/" in topicUrl:
                pathFolderName = self.getPathFolderName()
            self.logger.info(f"Topic URL Selector: {topicUrlSelector}")
            topicUrlJsScript = f"""
            var topicUrls = document.evaluate("{topicUrlSelector}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
            var hrefData  = [];
            for (var i = 0; i < topicUrls.snapshotLength; i++) {{
                var element = topicUrls.snapshotItem(i);
                var href = 'https://www.educative.io' + element.getAttribute('href') + "?showContent=true";
                isButtonInsideHref = element.querySelector('button');
                if(isButtonInsideHref === null && href.indexOf("/certificate?") === -1) {{
                    hrefData.push(href);
                }}
            }}
            return hrefData;
            """
            topicUrls = self.browser.execute_script(topicUrlJsScript)
            return topicUrls, pathFolderName
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseTopicUrlsList: {lineNumber}: {e}")


    def getCourseUrl(self, topicUrl):
        try:
            self.logger.info("Getting Course url")
            try:
                self.browser.get(topicUrl)
            except:
                self.logger.info("Page Loading Issue, pressing ESC to stop page load")
                self.browser.execute_script("window.stop();")
            # courseTypeSelector = f"//nav//a[contains(@href, '/{topicUrl.split('/')[3]}/')]/span/.."
            courseTypeSelector = f"//div[contains(@id, 'view-collection-article-content-root')]//a[contains(@href, '/{topicUrl.split('/')[3]}/')]"
            self.logger.info(f"Course Type Selector: {courseTypeSelector}")
            try:
                WebDriverWait(self.browser, self.timeout).until(
                    EC.presence_of_element_located((By.XPATH, courseTypeSelector)))
            except:
                try:
                    courseTypeSelector = "//nav//a[contains(@href, '/collection/')]/span/.."
                    self.logger.info(f"New Course Type Selector: {courseTypeSelector}")
                    WebDriverWait(self.browser, self.timeout).until(
                        EC.presence_of_element_located((By.XPATH, courseTypeSelector)))
                except:
                    courseTypeSelector = "(//*[starts-with(@id,'problemPage_breadcrumbsContainer')]//a)[last()]"
                    self.logger.info(f"New Course Type Selector: {courseTypeSelector}")
                    WebDriverWait(self.browser, self.timeout).until(
                        EC.presence_of_element_located((By.XPATH, courseTypeSelector)))

            courseUrlJsScript = f"""
            var anchorElement = document.evaluate(
                                "{courseTypeSelector}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                            ).singleNodeValue;
            var hrefValue = "";
            if (anchorElement) {{
                hrefValue = anchorElement.getAttribute('href');
            }}
            return "https://www.educative.io" + hrefValue + "?showContent=true";
            """
            courseUrl = self.browser.execute_script(courseUrlJsScript)
            self.logger.info(f"Found Course URL: {courseUrl}")
            return courseUrl
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseUrl: {lineNumber}: {e}")

    def getNextData(self):
        try:
            self.logger.info(f"Could not find authorid, collectionid, trying to get Next Data")
            nextDataSelector = self.selectors["nextData"]
            nextDataScript = f"""
            const el = document.querySelectorAll("{nextDataSelector}")[0];
            if (!el) return null;
            return JSON.parse(el.textContent);
                            """
            nextData = self.browser.execute_script(nextDataScript)
            if not nextData:
                raise Exception("__NEXT_DATA__ script element not found on page")
            nextData = nextData["query"]
            self.logger.info(f"Found Next Data authorid {nextData.get('authorId')}, collectionid {nextData.get('collectionId')}")
            courseApiUrl = self.urlUtils.getCourseApiCollectionListUrl(nextData)
            return courseApiUrl
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getNextData: {lineNumber}: {e}")

    def getAuthorAndCollectionId(self):
        try:
            self.logger.info(f"Getting AuthorAndCollectionId")
            authorAndCollectionIdScript = f"""
                                    const resultMap = {{}};
                                    if (!window.__next_f || !Array.isArray(window.__next_f)) return resultMap;
                                    window.__next_f.forEach(entry => {{
                                        if (!Array.isArray(entry) || typeof entry[1] !== 'string') return;

                                        const text = entry[1];

                                        const authorMatch = text.match(/["']?author_?[iI]d["']?\s*:\s*["']?(\d+)["']?/i);
                                        const collectionMatch = text.match(/["']?collection_?[iI]d["']?\s*:\s*["']?(\d+)["']?/i);

                                        if (authorMatch && collectionMatch) {{
                                            resultMap['authorId'] = String(authorMatch[1]);
                                            resultMap['collectionId'] = String(collectionMatch[1]);
                                        }}
                                    }});
                                    return resultMap;
            """
            # window.__next_f is populated progressively — retry to handle timing
            retry = 1
            resMap = {}
            while retry <= 3:
                resMap = self.browser.execute_script(authorAndCollectionIdScript)
                self.logger.info(f"Attempt {retry}: Found AuthorAndCollectionId {resMap}")
                if resMap.get('authorId') and resMap.get('collectionId'):
                    break
                retry += 1
                self.osUtils.sleep(2)

            if resMap.get('authorId') and resMap.get('collectionId'):
                courseApiUrl = self.urlUtils.getCourseApiCollectionListUrl(resMap)
            else:
                self.logger.info("authorId/collectionId not found in __next_f, falling back to getNextData")
                courseApiUrl = self.getNextData()
            return courseApiUrl
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getAuthorAndCollectionId: {lineNumber}: {e}")


    def getPathFolderName(self):
        try:
            self.logger.info("Module, getting path folder name")
            pathNameSelector = self.selectors["pathSelector"]
            pathScript = f"""
            var anchorElement = document.evaluate(
                    "{pathNameSelector}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            return anchorElement.text;
            """
            return self.browser.execute_script(pathScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getPathFolderName: {lineNumber}: {e}")
