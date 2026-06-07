"""
PublicContentExtractor.py

Fetches Educative public content pages via clean JSON APIs (no RSC/DOM parsing).

API endpoints by type:
  Blog       → GET /api/page/url/5003/{slug}
  Newsletter → GET /api/page/url/5005/{slug}   (last URL segment only)
  Answers    → GET /api/edpresso/shot/url/{slug}

All three return a component list in the same format as course topic components,
so the existing save_topic_content / ResolveComponent pipeline works unchanged.
"""

from src.ScraperType.ApiScraper.APIScraperConstants import EDUCATIVE_BASE_URL


# Map page type name → List of possible API URL type IDs
_TYPE_IDS = {
    "Blog":       ["5002", "5003"],
    "Newsletter": ["5005"],
}


class PublicContentExtractor:
    def __init__(self, api_utils, logger):
        """
        Args:
            api_utils: ApiUtility instance (browser already wired in).
            logger:    standard logger.
        """
        self.api_utils = api_utils
        self.logger    = logger

    # ------------------------------------------------------------------ #
    #  Public entry point
    # ------------------------------------------------------------------ #

    def extract(self, page_type: str, page_url: str) -> dict:
        """
        Fetch page data from the appropriate API and return a normalised dict:
        {
            title, slug, source_id, author_id, author_name,
            published_date, tags, summary, components
        }
        """
        slug = self._slug_from_url(page_url, page_type)
        self.logger.info(f"Fetching {page_type} via API, slug={slug!r}")

        if page_type == "Answers":
            return self._fetch_answers(slug)
        else:
            return self._fetch_marketing_page(page_url, page_type, slug)

    def enrich_image_paths(self, components: list, page_type: str, source_id: str) -> list:
        """
        Pre-populate content['path'] on Image/File components that carry a
        serving_url or image_id, before save_topic_content is called.
        The path guard in save_topic_content skips the course-API URL builder,
        so the correct public-page CDN/API path is stored.
        """
        from src.ScraperType.ApiScraper.Database.DatabaseQueryUtilities import (
            urls_for_public_image,
        )
        for component in components:
            comp_type = component.get("type")
            if comp_type not in ("Image", "File"):
                continue
            content = component.get("content")
            if not isinstance(content, dict):
                continue
            if content.get("path"):
                continue  # already set by a previous pass
            path = urls_for_public_image(content, page_type, source_id)
            if path:
                content["path"] = path
        return components

    # ------------------------------------------------------------------ #
    #  Blog / Newsletter  →  /api/page/url/{type_id}/{slug}
    # ------------------------------------------------------------------ #

    def _fetch_marketing_page(self, page_url: str, page_type: str, slug: str) -> dict:
        type_ids = _TYPE_IDS[page_type]
        data = None
        
        for type_id in type_ids:
            api_url = f"{EDUCATIVE_BASE_URL}/api/page/url/{type_id}/{slug}"
            self.logger.info(f"Trying Marketing page API: {api_url}")

            try:
                data = self.api_utils.executeJsToGetJson(api_url)
            except Exception as e:
                self.logger.debug(f"API {api_url} failed with exception: {e}")
                continue

            if isinstance(data, dict) and "marketing_page_content" in data:
                break  # Successfully found the payload
        
        if not isinstance(data, dict) or "marketing_page_content" not in data:
            self.logger.info(f"API endpoints returned 404. Initiating JS-native RSC memory extraction for {slug}...")
            data = self._extract_rsc_via_browser(page_url)
            
        if not data or not isinstance(data, dict):
            raise ValueError(
                f"Marketing page API and JS RSC extractor failed for {page_type} slug={slug!r}."
            )

        components = data.get("marketing_page_content")
        if not isinstance(components, list):
            raise ValueError(
                f"marketing_page_content is missing or not a list for {page_type} slug={slug!r}."
            )

        tags = self._collect_tags(data)
        title = data.get("marketing_page_title") or data.get("title") or ""
        page_slug = data.get("marketing_page_url") or data.get("slug") or slug

        self.logger.info(
            f"Fetched {page_type}: title={title!r}, "
            f"components={len(components)}, tags={len(tags)}"
        )

        return {
            "title":          title,
            "slug":           page_slug,
            "source_id":      str(data.get("marketing_page_id") or ""),
            "author_id":      str(data.get("author_id") or ""),
            "author_name":    str(data.get("author_name") or ""),
            "published_date": str(data.get("published_date") or ""),
            "tags":           tags,
            "summary":        str(data.get("marketing_page_summary") or ""),
            "components":     components,
        }

    def _extract_rsc_via_browser(self, page_url: str) -> dict:
        """
        Executes a native JavaScript parser directly inside the browser memory.
        This handles Next.js hexadecimal template strings perfectly.
        """
        self.api_utils.logger.info(f"Navigating browser to extract RSC for: {page_url}")
        
        try:
            self.api_utils.browser.get(page_url)
            self.api_utils.osUtils.sleep(2)
        except Exception as e:
            self.api_utils.logger.info("Page Loading Issue, pressing ESC to stop page load")
            self.api_utils.browser.execute_script("window.stop();")

        js_script = """
            function getRscPayload() {
                if (!window.__next_f) return null;
                
                let rscData = "";
                window.__next_f.forEach(chunk => {
                    if (Array.isArray(chunk) && typeof chunk[1] === 'string') {
                        rscData += chunk[1];
                    }
                });
                
                const ssrIndex = rscData.indexOf('"ssrContent":{');
                if (ssrIndex === -1) return null;
                
                const startIdx = ssrIndex + 13;
                let braceCount = 0;
                let endIdx = -1;
                let inString = false;
                let escape = false;
                
                for (let i = startIdx; i < rscData.length; i++) {
                    const char = rscData[i];
                    if (inString) {
                        if (escape) escape = false;
                        else if (char === '\\\\') escape = true;
                        else if (char === '"') inString = false;
                    } else {
                        if (char === '"') inString = true;
                        else if (char === '{') braceCount++;
                        else if (char === '}') {
                            braceCount--;
                            if (braceCount === 0) {
                                endIdx = i + 1;
                                break;
                            }
                        }
                    }
                }
                
                if (endIdx === -1) return null;
                
                const ssrJsonStr = rscData.substring(startIdx, endIdx);
                let ssrJson;
                try {
                    ssrJson = JSON.parse(ssrJsonStr);
                } catch (e) {
                    return { error: "Failed to parse JSON: " + e.toString() };
                }
                
                const encoder = new TextEncoder();
                const decoder = new TextDecoder("utf-8");
                
                function resolveReferences(obj) {
                    if (Array.isArray(obj)) {
                        for (let i = 0; i < obj.length; i++) {
                            obj[i] = resolveReferences(obj[i]);
                        }
                    } else if (obj !== null && typeof obj === 'object') {
                        for (let key in obj) {
                            if (typeof obj[key] === 'string' && obj[key].startsWith("$") && obj[key].length > 1) {
                                const refId = obj[key].substring(1);
                                if (/^[a-zA-Z0-9_]+$/.test(refId)) {
                                    const regexT = new RegExp("(?:^|[^a-zA-Z0-9_])" + refId + ":T([0-9a-fA-F]+),");
                                    const matchT = rscData.match(regexT);
                                    if (matchT) {
                                        const len = parseInt(matchT[1], 16);
                                        const sIdx = matchT.index + matchT[0].length;
                                        
                                        const remainderStr = rscData.substring(sIdx);
                                        const remainderBytes = encoder.encode(remainderStr);
                                        const extractedBytes = remainderBytes.slice(0, len);
                                        obj[key] = decoder.decode(extractedBytes);
                                    } else {
                                        const regexS = new RegExp("(?:^|[^a-zA-Z0-9_])" + refId + ':"((?:\\\\\\\\"|[^"])*)"');
                                        const matchS = rscData.match(regexS);
                                        if (matchS) {
                                            try {
                                                obj[key] = JSON.parse('"' + matchS[1] + '"');
                                            } catch(e) {}
                                        }
                                    }
                                }
                            } else if (typeof obj[key] === 'object') {
                                obj[key] = resolveReferences(obj[key]);
                            }
                        }
                    }
                    return obj;
                }
                
                if (ssrJson.marketing_page_content) {
                    ssrJson.marketing_page_content = resolveReferences(ssrJson.marketing_page_content);
                }
                
                return ssrJson;
            }
            return getRscPayload();
        """
        
        try:
            result = self.api_utils.browser.execute_script(js_script)
            if result and "error" not in result:
                return result
        except Exception as e:
            self.logger.error(f"JS RSC Extractor failed: {e}")
            
        return None

    # ------------------------------------------------------------------ #
    #  Answers  →  /api/edpresso/shot/url/{slug}
    # ------------------------------------------------------------------ #

    def _fetch_answers(self, slug: str) -> dict:
        api_url = f"{EDUCATIVE_BASE_URL}/api/edpresso/shot/url/{slug}"
        self.logger.info(f"Answers API: {api_url}")

        data = self.api_utils.executeJsToGetJson(api_url)
        if not isinstance(data, dict):
            raise ValueError(
                f"Answers API returned non-dict for slug={slug!r}: {data!r}"
            )

        # Answers wraps content under "content" key at top level or under shot data
        shot = data.get("shot") or data
        components = shot.get("content") or []
        if not isinstance(components, list):
            raise ValueError(
                f"Answers content is not a list for slug={slug!r}"
            )

        tags = self._collect_tags(shot, data)
        title = shot.get("title") or data.get("title") or ""
        page_slug = shot.get("url") or slug
        source_id = str(shot.get("shotId") or data.get("shotId") or "")

        self.logger.info(
            f"Fetched Answers: title={title!r}, "
            f"components={len(components)}, source_id={source_id}"
        )

        return {
            "title":          title,
            "slug":           page_slug,
            "source_id":      source_id,
            "author_id":      str(shot.get("creatorId") or data.get("creatorId") or ""),
            "author_name":    str(shot.get("creatorName") or data.get("creatorName") or ""),
            "published_date": str(shot.get("publishDate") or data.get("publishDate") or ""),
            "tags":           tags,
            "summary":        str(shot.get("teaser") or data.get("teaser") or ""),
            "components":     components,
        }

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _slug_from_url(page_url: str, page_type: str) -> str:
        """
        Extract the slug from the public page URL.
          Blog:       /blog/{slug}        → last segment
          Newsletter: /newsletter/{cat}/{slug} → last segment
          Answers:    /answers/{slug}     → last segment
        """
        segments = [s for s in page_url.rstrip("/").split("/") if s]
        # segments[-1] is always the slug for all three types
        return segments[-1] if segments else ""

    @staticmethod
    def _collect_tags(*sources) -> list:
        """Collect unique tag name strings from multiple source dicts."""
        tags, seen = [], set()
        for src in sources:
            if not isinstance(src, dict):
                continue
            for key in ("tags", "programming_tags", "topic_tags", "categories"):
                for item in (src.get(key) or []):
                    name = item.get("name") if isinstance(item, dict) else str(item)
                    if name and name not in seen:
                        seen.add(name)
                        tags.append(name)
        return tags
