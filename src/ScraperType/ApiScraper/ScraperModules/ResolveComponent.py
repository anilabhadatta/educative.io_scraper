from src.ScraperType.ApiScraper.APIScraperConstants import EDUCATIVE_BASE_URL


class ResolveComponent:
    def __init__(self, apiUtils, loginUtils, logger):
        self.apiUtils = apiUtils
        self.loginUtils = loginUtils
        self.logger = logger


    def resolveDrawIOSlides(self, topicJson: dict, author_id: str, collection_id: str, page_id: str) -> dict:
        try:
            components = topicJson.get("components", [])
            for component in components:
                if component.get("type") != "DrawIOWidget":
                    continue
                content = component.get("content", {})
                slides_id = content.get("slidesId")
                if not (content.get("slidesEnabled") and content.get("isSlides") and slides_id):
                    continue

                slides_api_url = f"{EDUCATIVE_BASE_URL}/api/slides/data?slides_id={slides_id}"
                self.logger.info(f"Fetching slides data for DrawIOWidget slidesId={slides_id}")
                self.loginUtils.checkIfLoggedIn()
                slides_data = self.apiUtils.executeJsToGetJson(slides_api_url)

                if not slides_data or isinstance(slides_data, str):
                    self.logger.warning(
                        f"No slides data for slidesId={slides_id} — response: {slides_data}"
                    )
                    continue

                component["content"]["slidesApiData"] = slides_data

                editor_image_path = content.get("editorImagePath", "")
                image_urls = self.extractSlidesImageUrls(slides_data, author_id, collection_id, page_id, editor_image_path)
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


    def extractSlidesImageUrls(self, slides_data: dict, author_id: str, collection_id: str, page_id: str, editor_image_path: str = "") -> list:
        base = ""
        if editor_image_path:
            import re
            match = re.search(r'(/api/collection/\d+/\d+/page/\d+/image)', editor_image_path)
            if match:
                base = match.group(1)

        if not base:
            base = f"/api/collection/{author_id}/{collection_id}/page/{page_id}/image"

        def _url_from_id(image_id) -> str:
            return f"{base}/{image_id}"

        if not isinstance(slides_data, dict):
            return []

        image_ids = slides_data.get("image_ids")
        if isinstance(image_ids, list):
            return [_url_from_id(img_id) for img_id in image_ids if img_id]

        return []


    def resolveLazyLoadPlaceholders(self, topicJson: dict, collectionId: str, courseId: str, workType: str) -> dict:
        try:
            components = topicJson.get("components", [])
            for component in components:
                if component.get("type") != "LazyLoadPlaceholder":
                    continue
                content = component.get("content", {})
                pageId = content.get("pageId")
                widgetIndex = content.get("widgetIndex")
                contentRevision = content.get("contentRevision")

                if pageId is None or widgetIndex is None or contentRevision is None:
                    self.logger.warning(f"Skipping LazyLoadPlaceholder — missing params: {content}")
                    continue

                lazyApiUrl = (
                    f"{EDUCATIVE_BASE_URL}/api/collection/{collectionId}/{courseId}"
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