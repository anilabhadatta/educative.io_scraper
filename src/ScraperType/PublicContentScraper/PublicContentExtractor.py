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
            return self._fetch_marketing_page(page_type, slug)

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

    def _fetch_marketing_page(self, page_type: str, slug: str) -> dict:
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
        
        if not isinstance(data, dict):
            raise ValueError(
                f"Marketing page API returned non-dict for {page_type} slug={slug!r} across types {type_ids}: {data!r}"
            )

        components = data.get("marketing_page_content")
        if not isinstance(components, list):
            raise ValueError(
                f"marketing_page_content is missing or not a list for {page_type} slug={slug!r} (tried {type_ids}). Result: {data.get('errorText', data)}"
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
