import os
import re
from unicodedata import category

from slugify import slugify
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.ScraperType.CourseTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.ScraperType.CourseTopicScraper.ScraperModules.UrlUtility import UrlUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


class ApiUtility:
    def __init__(self, configJson):
        self.configJson = configJson
        self.browser = None
        self.timeout = 10
        self.osUtils = OSUtility(configJson)
        self.urlUtils = UrlUtility()
        self.fileUtils = FileUtility()
        self.logger = Logger(configJson, "ApiUtility").logger
        apiType = configJson["downloadType"]
        self.allowCollection = apiType in ("PAL+COLLECTION", "COLLECTION")
        self.allowPal = apiType in ("PAL", "PAL+COLLECTION")

    def _sanitize_topic_name(self, value) -> str:
        text = str(value or "")
        text = "".join(ch for ch in text if category(ch) not in ("Cf", "Cc", "Cs"))
        text = re.sub(r"\s+", " ", text).strip()
        return text or "untitled-topic"


    def getCourseApiUrlFromNetworkUrls(self, apiUrls, workType):
        try:
            if not apiUrls:
                self.logger.warning("No API URLs found in network capture")
                return None

            projectPattern = re.compile(r"^https:\/\/www\.educative\.io\/api\/project\/(\d+)\/(\d+)\/(\d+)(?:\/.*)?(?:\?.*)?$")
            palPattern = re.compile(r"^https:\/\/www\.educative\.io\/api\/pal\/(\d+)\/(\d+)(?:\/.*)?(?:\?.*)?$")
            collectionPattern = re.compile(r"^https:\/\/www\.educative\.io\/api\/collection\/(\d+)\/(\d+)(?:\/.*)?(?:\?.*)?$")
            courseAPIUrls = []
            # Priority 1: Project endpoint in network capture.
            for url in reversed(apiUrls):
                if not isinstance(url, str):
                    continue
                match = projectPattern.match(url.strip())
                if match:
                    authorId, collectionId, projectId = match.group(1), match.group(2), match.group(3)
                    courseAPIUrls.append(f"https://www.educative.io/api/project/{authorId}/{collectionId}/{projectId}?work_type={workType}")
                    return courseAPIUrls

            # Priority 1: PAL endpoint in network capture.
            if self.allowPal:
                for url in reversed(apiUrls):
                    if not isinstance(url, str):
                        continue
                    match = palPattern.match(url.strip())
                    if match:
                        authorId, collectionId = match.group(1), match.group(2)
                        courseAPIUrls.append(f"https://www.educative.io/api/pal/{authorId}/{collectionId}?work_type={workType}")

            # Priority 2: collection endpoint in network capture.
            if self.allowCollection:
                for url in reversed(apiUrls):
                    if not isinstance(url, str):
                        continue
                    match = collectionPattern.match(url.strip())
                    if match:
                        authorId, collectionId = match.group(1), match.group(2)
                        courseAPIUrls.append(f"https://www.educative.io/api/collection/{authorId}/{collectionId}?work_type={workType}")

            self.logger.debug(f"Captured Course API URLs from network capture: {courseAPIUrls}")
            return courseAPIUrls
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


    def getMainApiContentJson(self, apiUrl, courseType):
        try:
            self.logger.info(f"Getting Main API Content JSON from URL: {apiUrl}")
            retry = 1
            while retry < 3:
                try:
                    jsonData = self.executeJsToGetJson(apiUrl)
                    return jsonData if courseType == "Project" else jsonData["instance"]
                except Exception:
                    pass
                retry += 1
                if retry == 3:
                    raise Exception("Could not Main fetch data from API")
                self.osUtils.sleep(2)
                self.logger.info(f"Found Error fetching Json, retrying {retry} out of 2: {apiUrl}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getMainApiContentJson: {lineNumber}: {e}")


    def getProjectCollectionsJson(self, jsonData, workType):
        try:
            authorId = str(jsonData["author_id"])
            collectionId = str(jsonData["collection_id"])
            projectId = str(jsonData["project_id"])
            title = jsonData["title"]
        
            toc = []
            topicApiUrlList = []
            topicNameList = []
            topicSlugList = []
            topicUrlList = []
            topicTypeList = []

            def add_topic(authorId, collectionId, projectId, page, workType):
                topicTitle = self._sanitize_topic_name(page.get("title", ""))
                topicSlug = page.get("slug", slugify(topicTitle))
                pageType = page["type"]
                authorId = str(page.get("author_id", authorId))
                collectionId = str(page.get("collection_id", collectionId))
                pageId = str(page.get("page_id", page["id"]))

                topicApiUrl = f"https://www.educative.io/api/project/{authorId}/{collectionId}/{projectId}/{pageId}?work_type={workType}"
                topicUrl = "cannot infer_project_topic_url"  # Project topic URLs can vary widely in structure, so we won't attempt to infer them here.

                topicApiUrlList.append(topicApiUrl)
                topicNameList.append(topicTitle)
                topicSlugList.append(topicSlug)
                topicUrlList.append(topicUrl)
                topicTypeList.append(pageType)

                topicData = {
                    "title": topicTitle,
                    "slug": topicSlug,
                    "api_url": topicApiUrl,
                    "url": topicUrl,
                    "type": pageType
                }
                return topicData

            categories = jsonData["toc"]["categories"]
            for category in categories:
                if not category["pages"]:
                    topicData = add_topic(authorId, collectionId, projectId, category, workType)
                    toc.append(topicData)
                else:
                    categoryTopic = {"category": category["title"], "topics": []}
                    for page in category["pages"]:
                        topicData = add_topic(authorId, collectionId, projectId, page, workType)
                        categoryTopic["topics"].append(topicData)
                    toc.append(categoryTopic)
                    
            return {
                "authorId": authorId,
                "collectionId": collectionId,
                "projectId": projectId,
                "title": title,
                "topicApiUrlList": topicApiUrlList,
                "topicNameList": topicNameList,
                "topicSlugList": topicSlugList,
                "topicUrlList": topicUrlList,
                "topicTypeList": topicTypeList,
                "toc": toc,
            }
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getProjectCollectionsJson: {lineNumber}: {e}")


    def getCollectionsJson(self, courseApiUrls, courseType, workType, topicUrl):
        try:
            result = []
            if courseType == "Project":
                projectApiUrl = courseApiUrls[0]
                self.logger.info(f"Getting Course Collections JSON (Project) from URL: {projectApiUrl}")
                jsonData = self.getMainApiContentJson(projectApiUrl, courseType)
                result.append(self.getProjectCollectionsJson(jsonData, workType))
                return result
            
            for courseApiUrl in courseApiUrls:
                self.logger.info(f"Getting Course Collections JSON (Course/Path) from URL: {courseApiUrl}")
                jsonData = self.getMainApiContentJson(courseApiUrl, courseType)
                coursePathCollectionsJson = self.getCoursePathCollectionsJson(jsonData, courseType, workType, topicUrl)
                result.append(coursePathCollectionsJson)
            return result
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCollectionsJson: {lineNumber}: {e}")


    def getCoursePathCollectionsJson(self, jsonData, courseType, workType, topicUrl):
        try:
            jsonData = jsonData["details"]
            authorId = str(jsonData["author_id"])
            collectionId = str(jsonData["collection_id"])
            title = jsonData["title"]
            pathMeta = {
                "path_author_id": str(jsonData["path_author_id"]), 
                "path_collection_id": str(jsonData["path_id"]), 
                "path_url_slug": jsonData.get("path_url_slug", slugify(jsonData["path_title"])), 
                "path_title": jsonData["path_title"]
            } if courseType == "Path" else None
            
            toc = []
            topicApiUrlList = []
            topicNameList = []
            topicSlugList = []
            topicUrlList = []
            topicTypeList = []
            def add_topic(authorId, collectionId, page, workType, topicUrl):
                def _build_topic_url(topic_url, page):
                    base = str(topic_url).split("?", 1)[0].rstrip("/")
                    parent = base.rsplit("/", 1)[0]
                    slug = page.get("slug") or page.get("id")
                    return f"{parent}/{slug}?showContent=true"
                
                pageId = str(page["id"])
                topicTitle = self._sanitize_topic_name(page.get("title", ""))
                topicSlug = page.get("slug", slugify(topicTitle))
                pageType = page["type"]
                authorId = str(page.get("author_id", authorId))
                collectionId = str(page.get("collection_id", collectionId))
                pageId = str(page.get("page_id", page["id"]))

                topicApiUrl = f"https://www.educative.io/api/collection/{authorId}/{collectionId}/page/{pageId}?work_type={workType}"
                topicUrl = _build_topic_url(topicUrl, page)

                topicApiUrlList.append(topicApiUrl)
                topicNameList.append(topicTitle)
                topicSlugList.append(topicSlug)
                topicUrlList.append(topicUrl)
                topicTypeList.append(pageType)

                topicData = {
                    "title": topicTitle,
                    "slug": topicSlug,
                    "api_url": topicApiUrl,
                    "url": topicUrl,
                    "type": pageType,
                }
                return topicData

            categories = jsonData["toc"]["categories"]
            for category in categories:
                for tocEntry in category.get("toc", [category]):
                    pages = tocEntry.get("pages")
                    if not pages:
                        topicData = add_topic(authorId, collectionId, tocEntry, workType, topicUrl)
                        toc.append(topicData)
                    else:
                        categoryTitle = category["title"] if category.get("toc") else tocEntry["title"]
                        categoryTopic = {"category": categoryTitle, "topics": []}
                        for page in pages:
                            topicData = add_topic(authorId, collectionId, page, workType, topicUrl)
                            categoryTopic["topics"].append(topicData)
                        toc.append(categoryTopic)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCoursePathCollectionsJson:add_topic: {lineNumber}: {e}")
                
        return {
            "authorId": authorId,
            "collectionId": collectionId,
            "title": title,
            "topicApiUrlList": topicApiUrlList,
            "topicNameList": topicNameList,
            "topicSlugList": topicSlugList,
            "topicUrlList": topicUrlList,
            "topicTypeList": topicTypeList,
            "toc": toc,
            "pathMeta": pathMeta,
        }


    def getCourseUrl(self, textFileUrl):
        try:
            self.logger.info("Getting Course url")
            try:
                self.browser.get(textFileUrl)
                self.osUtils.sleep(3)
            except:
                self.logger.info("Page Loading Issue, pressing ESC to stop page load")
                self.browser.execute_script("window.stop();")
            try:
                courseTypeSelector = f"//div[contains(@id, 'view-collection-article-content-root')]//a[contains(@href, '/{textFileUrl.split('/')[3]}/')]"
                self.logger.info(f"Course Type Selector: {courseTypeSelector}")
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


    def getNextData(self, workType):
        try:
            self.logger.info(f"Could not find authorid, collectionid, trying to get Next Data")
            nextDataSelector = "script[id*='__NEXT_DATA__']"
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
            courseApiUrl = self.urlUtils.getCourseApiCollectionListUrl(nextData, workType)
            return courseApiUrl
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getNextData: {lineNumber}: {e}")


    def getAuthorAndCollectionId(self, workType):
        try:
            if not self.allowCollection:
                return []
            self.logger.info(f"Getting AuthorAndCollectionId")
            authorAndCollectionIdScript = fr"""
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
                courseApiUrl = self.urlUtils.getCourseApiCollectionListUrl(resMap, workType)
            else:
                self.logger.info("authorId/collectionId not found in __next_f, falling back to getNextData")
                courseApiUrl = self.getNextData(workType)
            return [courseApiUrl]
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getAuthorAndCollectionId: {lineNumber}: {e}")

