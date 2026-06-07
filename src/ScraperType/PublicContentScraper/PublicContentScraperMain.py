"""
PublicContentScraperMain.py

Scrapes Educative public content pages (Answers, Blog, Newsletter) using
clean JSON APIs and stores them in the existing DB schema:

  courses    → 1 row per content type  (Answers / Blog / Newsletter)
  topics     → 1 row per scraped page
  components → same table as course topics (course_id + topic_index)
  static_assets → same pipeline as courses

Full ResolveComponent pipeline is applied (DrawIO slides, LazyLoad) so any
component type that appears on public pages is handled correctly and the
existing viewer renders them without any changes.

API endpoints used:
  Blog       → GET /api/page/url/5002/{slug}
  Newsletter → GET /api/page/url/5005/{slug}
  Answers    → GET /api/edpresso/shot/url/{slug}
"""

import asyncio

from slugify import slugify

from src.Logging.Logger import Logger
from src.Main.LoginAccount import LoginAccount
from src.ScraperType.ApiScraper.Database.DatabaseManager import DatabaseManager
from src.ScraperType.ApiScraper.ScraperModules.ApiUtility import ApiUtility
from src.ScraperType.ApiScraper.ScraperModules.CommonUtility import CommonUtility
from src.ScraperType.ApiScraper.ScraperModules.ResolveComponent import ResolveComponent
from src.ScraperType.PublicContentScraper.PublicContentExtractor import PublicContentExtractor
from src.Utility.BrowserUtility import BrowserUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


_PUBLIC_TYPE_MAP = {
    "answers":    "Answers",
    "blog":       "Blog",
    "newsletter": "Newsletter",
}


def _detect_page_type(url: str) -> str:
    """Return 'Answers', 'Blog', or 'Newsletter' based on URL path segment."""
    segment = url.rstrip("/").split("/")[3] if url.count("/") >= 3 else ""
    page_type = _PUBLIC_TYPE_MAP.get(segment.lower())
    if not page_type:
        raise ValueError(
            f"Cannot detect public page type from URL: {url!r}. "
            f"Expected one of: {list(_PUBLIC_TYPE_MAP.keys())}"
        )
    return page_type


class PublicContentScraperMain:
    def __init__(self, configJson, progressQueue=None):
        self.configJson    = configJson
        self.progressQueue = progressQueue or _NullQueue()

        self.logger        = Logger(configJson, "PublicContentScraper").logger
        self.fileUtils     = FileUtility()
        self.osUtils       = OSUtility(configJson)
        self.loginUtils    = LoginAccount(configJson)
        self.browserUtils  = BrowserUtility(configJson)
        self.db            = DatabaseManager(configJson)

        self.browser       = None
        self.apiUtils      = None        # wired after browser init
        self.resolveComp   = None        # wired after browser init

    # ------------------------------------------------------------------ #
    #  Entry point
    # ------------------------------------------------------------------ #

    def start(self):
        self.logger.info("PublicContentScraperMain started.")
        urls = self.fileUtils.loadTextFile(self.configJson["courseUrlsFilePath"])

        self.progressQueue.put(("max-course", len(urls)))
        self.progressQueue.put(("progress-course", 0))

        for idx, page_url in enumerate(urls):

            self.logger.info(
                f"------------------------------------------------------------\n"
                f"[{idx+1}/{len(urls)}] Scraping public page: {page_url}"
            )
            try:
                self._ensure_browser()

                try:
                    page_type = _detect_page_type(page_url)
                except ValueError as e:
                    self.logger.warning(str(e))
                    self.progressQueue.put(("progress-course", idx + 1))
                    continue

                if page_type:
                    course_id = self.db.upsert_public_course(page_type)
                    topic_row = self.db.get_topic_by_api_url(course_id, page_url)
                    overwrite = self.configJson["ScraperConfig"].get("overwrite", "false").lower() == "true"
                    
                    if topic_row and topic_row["status"] == "done":
                        if not overwrite:
                            self.logger.info(f"Topic already downloaded, skipping: {page_url}")
                            self.progressQueue.put(("progress-course", idx + 1))
                            continue
                        else:
                            self.logger.info(f"Topic downloaded, but overwrite is enabled. Re-scraping: {page_url}")
                            # Mark as pending to prevent partial state on crash
                            self.db.mark_topic_error(course_id, topic_row["topic_index"], "Pending overwrite")

                self._scrape_page(page_url)
                self.progressQueue.put(("progress-course", idx + 1))
            except KeyboardInterrupt:
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                raise
            except Exception as exc:
                asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
                raise Exception(f"PublicContentScraperMain:start: {exc}")

        asyncio.get_event_loop().run_until_complete(self.browserUtils.shutdownChromeViaWebsocket())
        self.logger.info("PublicContentScraperMain completed.")

    # ------------------------------------------------------------------ #
    #  Per-page scrape
    # ------------------------------------------------------------------ #

    def _scrape_page(self, page_url: str):
        page_type = _detect_page_type(page_url)

        # Ensure the aggregator course row exists (created once, reused forever)
        course_id = self.db.upsert_public_course(page_type)

        # ── Fetch page data from the JSON API ────────────────────────────
        extractor = PublicContentExtractor(self.apiUtils, self.logger)
        page_data = extractor.extract(page_type, page_url)

        title     = CommonUtility.sanitize_topic_name(page_data["title"])
        slug      = page_data["slug"] or slugify(title)
        source_id = page_data["source_id"]   # shotId / marketing_page_id
        author_id = page_data["author_id"]

        # Register topic (appends if new, skips if already scraped)
        topic_index, is_new = self.db.upsert_topic_in_public_course(
            course_id  = course_id,
            topic_url  = page_url,
            title      = title,
            slug       = slug,
            page_id    = source_id,
        )
        self.logger.info(
            f"Topic '{title}' → course_id={course_id} "
            f"topic_index={topic_index} ({'new' if is_new else 'existing'})"
        )

        components = page_data["components"]
        if not components:
            self.logger.warning(f"No components found for: {page_url}")
            self.db.topics.mark_topic_error(
                course_id, topic_index, "API returned no components"
            )
            return

        # ── Full component resolution pipeline ───────────────────────────
        # collection_id for DrawIO/LazyLoad path building — use source_id as best proxy
        collection_id = source_id

        topic_json = {"components": components}

        # DrawIO slides: fetches /api/slides/data?slides_id=...
        topic_json = self.resolveComp.resolveDrawIOSlides(
            topic_json, author_id, collection_id, source_id
        )
        # LazyLoad: rare on public pages but handled if present
        topic_json = self.resolveComp.resolveLazyLoadPlaceholders(
            topic_json, collection_id, source_id, workType="collection"
        )
        components = topic_json["components"]

        # Pre-set image paths before save so save_topic_content doesn't overwrite
        components = extractor.enrich_image_paths(components, page_type, source_id)

        # ── Persist ──────────────────────────────────────────────────────
        self.db.save_topic_content(
            course_id     = course_id,
            topic_index   = topic_index,
            components    = components,
            author_id     = author_id,
            collection_id = collection_id,
            topic_api_url = page_url,
        )

        # Rebuild aggregator course TOC after each successful page
        self.db.update_public_course_toc(course_id)
        self.logger.info(f"Saved public page: {title!r} ({page_type})")

    # ------------------------------------------------------------------ #
    #  Browser lifecycle
    # ------------------------------------------------------------------ #

    def _ensure_browser(self):
        """Start browser if not already running; wire deps that need it."""
        if self.browser is not None:
            return
        self.browser = self.browserUtils.loadBrowser()
        self.browser.set_window_size(1920, 1080)
        self.loginUtils.browser = self.browser
        self.loginUtils.checkIfLoggedIn()   # ensure session cookie is present
        self._wire_api_deps()

    def _wire_api_deps(self):
        """Wire browser into ApiUtility and ResolveComponent."""
        if self.apiUtils is None:
            self.apiUtils = ApiUtility(self.configJson)
        self.apiUtils.browser = self.browser
        self.resolveComp = ResolveComponent(self.apiUtils, self.loginUtils, self.logger)


class _NullQueue:
    """Placeholder when no progress queue is provided."""
    def put(self, _):
        pass
