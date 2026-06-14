from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.Logging.Logger import Logger
from src.ScraperType.ApiScraper.APIScraperConstants import (
    COLLECTION_API_URL_PATTERN,
    COURSE_TYPE_BREADCRUMB_SELECTOR,
    COURSE_TYPE_COLLECTION_NAV_SELECTOR,
    COURSE_TYPE_SELECTOR_TEMPLATE,
    EDUCATIVE_BASE_URL,
    HTTP_AUTH_ERRORS,
    MINIMAP_BUTTON_XPATH,
    NEXT_DATA_SELECTOR,
    PAL_API_URL_PATTERN,
    PROJECT_API_URL_PATTERN,
    RETRY_MAIN_API_MAX_ATTEMPTS,
    RETRY_NEXT_F_MAX_ATTEMPTS,
    SHOW_CONTENT_QUERY,
)
from src.ScraperType.ApiScraper.ScraperModules.CoursePathModule import CoursePathModule
from src.ScraperType.ApiScraper.ScraperModules.ProjectModule import ProjectModule
from src.Utility.UrlUtility import UrlUtility
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
        self.projectModule = ProjectModule(configJson)
        self.coursePathModule = CoursePathModule(configJson)


    def getCourseApiUrlFromNetworkUrls(self, apiUrls, workType):
        try:
            if not apiUrls:
                self.logger.warning("No API URLs found in network capture")
                return None

            courseAPIUrls = []
            # Priority 1: Project endpoint in network capture.
            for url in reversed(apiUrls):
                if not isinstance(url, str):
                    continue
                match = PROJECT_API_URL_PATTERN.match(url.strip())
                if match:
                    authorId, collectionId, projectId = match.group(1), match.group(2), match.group(3)
                    courseAPIUrls.append(self.urlUtils.getCourseApiProjectUrl(authorId, collectionId, projectId, workType))
                    return courseAPIUrls

            # Priority 1: PAL endpoint in network capture.
            if self.allowPal:
                for url in reversed(apiUrls):
                    if not isinstance(url, str):
                        continue
                    match = PAL_API_URL_PATTERN.match(url.strip())
                    if match:
                        authorId, collectionId = match.group(1), match.group(2)
                        courseAPIUrls.append(self.urlUtils.getCourseApiPalUrl(authorId, collectionId, workType))
                        # break

            # Priority 2: collection endpoint in network capture.
            if self.allowCollection:
                for url in reversed(apiUrls):
                    if not isinstance(url, str):
                        continue
                    match = COLLECTION_API_URL_PATTERN.match(url.strip())
                    if match:
                        authorId, collectionId = match.group(1), match.group(2)
                        courseAPIUrls.append(self.urlUtils.getCourseApiCollectionListUrl(
                            {"authorId": authorId, "collectionId": collectionId}, workType
                        ))
                        break

            self.logger.debug(f"Captured Course API URLs from network capture: {courseAPIUrls}")
            return courseAPIUrls
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCourseApiUrlFromNetworkUrls: {lineNumber}: {e}")


    def executeJsToGetJson(self, url):
        self.logger.info(f"Executing JS to get JSON from URL: {url}")
        apiJsonScript = f"""
            return new Promise((resolve, reject) => {{
                const timeoutId = setTimeout(() => reject(new Error('HTTP_TIMEOUT')), 15000);
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
                            clearTimeout(timeoutId);
                            reject(new Error('HTTP_' + response.status));
                            return;
                        }}
                        if (response.status !== 200) {{
                            clearTimeout(timeoutId);
                            resolve('HTTP_' + response.status);
                            return;
                        }}
                        return response.json();
                    }})
                    .then(data => {{
                        clearTimeout(timeoutId);
                        if (data !== undefined) resolve(data);
                        else resolve({{}});
                    }})
                    .catch(error => {{
                        clearTimeout(timeoutId);
                        reject(error);
                    }});
            }});
        """
        try:
            result = self.browser.execute_script(apiJsonScript)
            return result
        except Exception as e:
            error_msg = str(e)
            if "HTTP_401" in error_msg or "HTTP_403" in error_msg:
                code = "401" if "HTTP_401" in error_msg else "403"
                raise Exception(f"HTTP {code} fetching API URL — topic inaccessible or session expired: {url}")
            elif "HTTP_TIMEOUT" in error_msg:
                raise Exception(f"HTTP_TIMEOUT: API fetch request timed out after 15 seconds for URL: {url}")
            else:
                raise Exception(f"JS execution failed for URL {url}: {e}")


    def getMainApiContentJson(self, apiUrl, courseType):
        try:
            self.logger.info(f"Getting Main API Content JSON from URL: {apiUrl}")
            retry = 1
            while retry <= RETRY_MAIN_API_MAX_ATTEMPTS:
                try:
                    jsonData = self.executeJsToGetJson(apiUrl)
                    return jsonData if courseType == "Project" else jsonData["instance"]
                except Exception:
                    pass
                retry += 1
                if retry > RETRY_MAIN_API_MAX_ATTEMPTS:
                    raise Exception("Could not Main fetch data from API")
                self.osUtils.sleep(2)
                self.logger.info(f"Found Error fetching Json, retrying {retry} out of {RETRY_MAIN_API_MAX_ATTEMPTS}: {apiUrl}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getMainApiContentJson: {lineNumber}: {e}")


    def getCollectionsJson(self, courseApiUrls, courseType, workType, topicUrl):
        try:
            result = []
            if courseType == "Project":
                projectApiUrl = courseApiUrls[0]
                self.logger.info(f"Getting Course Collections JSON (Project) from URL: {projectApiUrl}")
                jsonData = self.getMainApiContentJson(projectApiUrl, courseType)
                result.append(self.projectModule.getProjectCollectionsJson(jsonData, workType))
                return result
            
            for courseApiUrl in courseApiUrls:
                self.logger.info(f"Getting Course Collections JSON (Course/Path) from URL: {courseApiUrl}")
                jsonData = self.getMainApiContentJson(courseApiUrl, courseType)
                coursePathCollectionsJson = self.coursePathModule.getCoursePathCollectionsJson(
                    jsonData, courseType, workType, topicUrl
                )
                result.append(coursePathCollectionsJson)
            return result
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ApiUtility:getCollectionsJson: {lineNumber}: {e}")


    def getCourseUrl(self, textFileUrl):
        try:
            self.logger.info("Getting Course url")
            if self.urlUtils.isCourseUrl(textFileUrl):
                self.logger.info(f"Provided URL is already a course URL: {textFileUrl}")
                try:
                    self.browser.get(textFileUrl)
                    self.osUtils.sleep(10)
                except:
                    self.logger.info("Page Loading Issue, pressing ESC to stop page load")
                    self.browser.execute_script("window.stop();")
                
                res_url = self.urlUtils.appendShowContentQuery(textFileUrl)
                self.logger.info(f"Found Course URL: {res_url}")
                return res_url

            try:
                self.browser.get(textFileUrl)
                self.osUtils.sleep(10)
            except:
                self.logger.info("Page Loading Issue, pressing ESC to stop page load")
                self.browser.execute_script("window.stop();")
            try:
                courseTypeSelector = COURSE_TYPE_SELECTOR_TEMPLATE.format(segment=textFileUrl.split('/')[3])
                self.logger.info(f"Course Type Selector: {courseTypeSelector}")
                WebDriverWait(self.browser, self.timeout).until(
                    EC.presence_of_element_located((By.XPATH, courseTypeSelector)))
            except:
                try:
                    courseTypeSelector = COURSE_TYPE_COLLECTION_NAV_SELECTOR
                    self.logger.info(f"New Course Type Selector: {courseTypeSelector}")
                    WebDriverWait(self.browser, self.timeout).until(
                        EC.presence_of_element_located((By.XPATH, courseTypeSelector)))
                except:
                    courseTypeSelector = COURSE_TYPE_BREADCRUMB_SELECTOR
                    self.logger.info(f"New Course Type Selector: {courseTypeSelector}")
                    WebDriverWait(self.browser, self.timeout).until(
                        EC.presence_of_element_located((By.XPATH, courseTypeSelector)))

            # Find and click MiniMap button using JavaScript
            try:
                miniMapClickScript = f"""
                var button = document.evaluate("{MINIMAP_BUTTON_XPATH}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (button) {{
                    button.click();
                    return true;
                }}
                return false;
                """
                isClicked = self.browser.execute_script(miniMapClickScript)
                if isClicked:
                    self.osUtils.sleep(2)  # Wait a moment for the UI to update after clicking
                    self.logger.info("Clicked on MiniMap button")
                else:
                    self.logger.debug("MiniMap button not found")
            except Exception as e:
                self.logger.debug(f"Error clicking MiniMap button: {e}")

            courseUrlJsScript = f"""
            var anchorElement = document.evaluate(
                                "{courseTypeSelector}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                            ).singleNodeValue;
            var hrefValue = "";
            if (anchorElement) {{
                hrefValue = anchorElement.getAttribute('href');
            }}
            return "{EDUCATIVE_BASE_URL}" + hrefValue + "{SHOW_CONTENT_QUERY}";
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
            nextDataScript = f"""
            const el = document.querySelectorAll("{NEXT_DATA_SELECTOR}")[0];
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

                // 1. Check og:image meta tag (highly reliable for current course)
                // const metaTag = document.querySelector('meta[property="og:image"]');
                // if (metaTag && metaTag.content) {{
                //     const match = metaTag.content.match(/\/api\/(?:collection|page|project)\/(\d+)\/(\d+)/i);
                //     if (match) {{
                //         resultMap['authorId'] = match[1];
                //         resultMap['collectionId'] = match[2];
                //         return resultMap;
                //     }}
                // }}

                // 2. Fallback to __next_f looking for exact "details" object
                if (window.__next_f && Array.isArray(window.__next_f)) {{
                    for (const entry of window.__next_f) {{
                        if (Array.isArray(entry) && typeof entry[1] === 'string') {{
                            const text = entry[1];
                            const detailsMatch = text.match(/"details"\s*:\s*\{{[^}}]*"author_id"\s*:\s*(\d+)[^}}]*"collection_id"\s*:\s*(\d+)/i);
                            if (detailsMatch) {{
                                resultMap['authorId'] = String(detailsMatch[1]);
                                resultMap['collectionId'] = String(detailsMatch[2]);
                                return resultMap;
                            }}
                        }}
                    }}
                    
                    // 3. Last resort: Generic regex, stopping at FIRST match to avoid grabbing linked courses at the bottom
                    for (const entry of window.__next_f) {{
                        if (Array.isArray(entry) && typeof entry[1] === 'string') {{
                            const text = entry[1];
                            const authorMatch = text.match(/["']?author_?[iI]d["']?\s*:\s*["']?(\d+)["']?/i);
                            const collectionMatch = text.match(/["']?collection_?[iI]d["']?\s*:\s*["']?(\d+)["']?/i);

                            if (authorMatch && collectionMatch) {{
                                resultMap['authorId'] = String(authorMatch[1]);
                                resultMap['collectionId'] = String(collectionMatch[1]);
                                return resultMap;
                            }}
                        }}
                    }}
                }}
                
                return resultMap;
            """
            # window.__next_f is populated progressively — retry to handle timing
            retry = 1
            resMap = {}
            while retry <= RETRY_NEXT_F_MAX_ATTEMPTS:
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

