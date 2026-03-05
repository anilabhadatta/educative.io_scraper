"""
StaticAssetDownloader.py

Reads every URL stored in the static_assets table, downloads the file via an
authenticated requests.Session (cookies extracted from the browser after login),
and saves it under save_dir/ mirroring the URL path exactly.

No CORS issues — downloads happen server-side via Python requests, not via
browser-side fetch(). The browser is only used to authenticate and hand over
its cookies.

Extension rules
---------------
  URL already ends with a filename extension (.png, .zip …)
      → saved at exact path, extension unchanged

  URL ends with a bare image ID (no extension)
      → saved at exact path with no extension added (e.g. …/image/5779054965817344)

Deduplication
-------------
  A Python set tracks every URL already downloaded within this run.
  On restart, existence of the file on disk is checked first, so
  previously downloaded files are never re-fetched.

Usage
-----
  python -m src.Database.StaticAssetDownloader <path/to/educative_scraper.db>
  python -m src.Database.StaticAssetDownloader          # auto-discover db
"""

import asyncio
import configparser
import json
import sqlite3
import sys
from pathlib import Path
import requests

from src.Common.Constants import constants
from src.Main.LoginAccount import LoginAccount
from src.Utility.BrowserUtility import BrowserUtility
from src.Utility.OSUtility import OSUtility
from src.Logging.Logger import Logger


# ── Helpers ───────────────────────────────────────────────────────────────── #

def _load_config_json() -> dict:
    """Build a configJson dict from the user's config.ini (same keys as GUI)."""
    cfg = configparser.ConfigParser()
    cfg.read(constants.defaultConfigPath)
    s = cfg["ScraperConfig"]

    def _bool(key):
        return s.get(key, "false").strip().lower() == "true"

    return {
        "userDataDir":        s.get("userdatadir", "UserData0"),
        "headless":           _bool("headless"),
        "courseUrlsFilePath": s.get("courseurlsfilepath", ""),
        "saveDirectory":      s.get("savedirectory", "."),
        "logger":             s.get("logger", "INFO"),
        "moduleType":         s.get("moduletype", "COURSE-PATH"),
        "isProxy":            _bool("isproxy"),
        "proxy":              s.get("proxy", ""),
        "scraperType":        s.get("scrapertype", "API-JSON-Scraper"),
        "scrapingMethod":     s.get("scrapingmethod", "SingleFile-HTML"),
        "fileType":           s.get("filetype", "html"),
        "ucdriver":           _bool("ucdriver"),
        "binaryversion":      s.get("binaryversion", "116"),
        "autoresume":         _bool("autoresume"),
        "autofixtextfile":    _bool("autofixtextfile"),
        "blockscraper":       _bool("blockscraper"),
        "autonext":           _bool("autonext"),
        "overwrite":          _bool("overwrite"),
        "useExtension":       _bool("useExtension"),
    }


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _url_path(url: str) -> str:
    """Extract the path portion of a URL without using urlparse.

    urlparse treats ';' as a path-parameter separator and silently removes it
    from .path, which corrupts filenames like '5900909211549696;'.
    Manual splitting avoids that.
    """
    try:
        after_scheme = url.split("://", 1)[1]          # strip scheme
        raw_path = after_scheme.split("/", 1)[1]        # strip host
        return raw_path.split("?")[0].split("#")[0]     # strip query + fragment
    except IndexError:
        return url


def _file_path_for_url(url: str, save_dir: Path) -> Path:
    """
    Map a full URL to a local path under save_dir, mirroring the URL path exactly.

    URL with     extension:  .../image/123/file.zip  → save_dir/api/.../image/123/file.zip
    URL without  extension:  .../image/123456789     → save_dir/api/.../image/123456789
    URL with trailing ';':   .../image/123456789;    → save_dir/api/.../image/123456789;
    """
    return save_dir / _url_path(url)


def _build_session(browser) -> requests.Session:
    """
    Extract all cookies from the authenticated browser and load them into a
    requests.Session. Also sets a realistic User-Agent and Referer so the
    API doesn't reject the request.
    """
    session = requests.Session()
    for cookie in browser.get_cookies():
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain", ".educative.io"),
        )
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/116.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.educative.io/",
        "Accept": "*/*",
    })
    return session


# ── Core download logic ───────────────────────────────────────────────────── #

def download_all(db_path: str, config_json: dict):
    logger   = Logger(config_json, "StaticAssetDownloader").logger
    save_dir = Path(config_json["saveDirectory"])

    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT course_id, topic_index, assets_json FROM static_assets ORDER BY course_id, topic_index"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        print("No rows found in static_assets. Run StaticAssetExtractor first.")
        return

    # Collect all unique URLs across all topics (preserving encounter order)
    all_urls: list = []
    seen_urls: set = set()
    for row in rows:
        try:
            assets = json.loads(row["assets_json"])
        except json.JSONDecodeError:
            continue
        for comp_idx, url_list in assets.items():
            for url in url_list:
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_urls.append(url)

    logger.info(f"Total unique asset URLs to process: {len(all_urls)}")
    print(f"Total unique asset URLs to process: {len(all_urls)}")

    # ── Start browser, log in, extract cookies, then close browser ── #
    browserUtils = BrowserUtility(config_json)
    loginUtils   = LoginAccount(config_json)
    osUtils      = OSUtility(config_json)

    browser = browserUtils.loadBrowser()
    browserUtils.browser = browser
    loginUtils.browser   = browser
    browser.set_window_size(1920, 1080)

    try:
        browser.get("https://www.educative.io")
        osUtils.sleep(3)
        loginUtils.checkIfLoggedIn()
        session = _build_session(browser)
        logger.info(f"Extracted {len(browser.get_cookies())} cookies from browser session")
    except Exception as e:
        logger.error(f"Login / cookie extraction failed: {e}")
        raise
    finally:
        try:
            asyncio.get_event_loop().run_until_complete(
                browserUtils.shutdownChromeViaWebsocket()
            )
        except Exception:
            pass

    # ── Download loop — pure Python requests, no browser, no CORS ── #
    downloaded_set: set = set()
    downloaded = 0
    skipped    = 0
    failed     = 0

    try:
        for idx, url in enumerate(all_urls, 1):
            if url in downloaded_set:
                skipped += 1
                continue

            # Check if already on disk (glob handles bare-ID files with any extension)
            stem_path = save_dir / _url_path(url)
            existing  = (
                list(stem_path.parent.glob(f"{stem_path.name}*"))
                if stem_path.parent.exists() else []
            )
            if existing:
                logger.info(f"[{idx}/{len(all_urls)}] Already on disk, skipping: {url}")
                downloaded_set.add(url)
                skipped += 1
                continue

            logger.info(f"[{idx}/{len(all_urls)}] Downloading: {url}")
            try:
                resp = session.get(url, timeout=30, stream=True)
            except requests.RequestException as e:
                logger.warning(f"Request error for {url}: {e}")
                failed += 1
                continue

            if not resp.ok:
                logger.warning(f"Failed (HTTP {resp.status_code}): {url}")
                failed += 1
                continue

            file_bytes = resp.content
            if not file_bytes:
                logger.warning(f"Empty response body for: {url}")
                failed += 1
                continue

            dest = _file_path_for_url(url, save_dir)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(file_bytes)

            downloaded_set.add(url)
            downloaded += 1
            content_type = resp.headers.get("content-type", "")
            logger.info(f"Saved ({len(file_bytes)} bytes, {content_type}): {dest}")

            osUtils.sleep(0.3)

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")

    summary = (
        f"\nDone. Downloaded: {downloaded} | "
        f"Skipped (already on disk / dup): {skipped} | "
        f"Failed: {failed}"
    )
    logger.info(summary)
    print(summary)


# ── Entry point ───────────────────────────────────────────────────────────── #

def _resolve_db_path() -> str:
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if not p.exists():
            raise SystemExit(f"Error: database not found at '{p}'")
        return str(p)

    default = Path(constants.defaultConfigPath).parent.parent / "downloaded_files" / "educative_scraper.db"
    if default.exists():
        return str(default)

    fallback = Path(__file__).resolve().parent.parent.parent / "downloaded_files" / "educative_scraper.db"
    if fallback.exists():
        return str(fallback)

    raise SystemExit(
        "Usage: python -m src.Database.StaticAssetDownloader <path/to/educative_scraper.db>\n"
        f"Auto-discover path '{default}' also not found."
    )


if __name__ == "__main__":
    db  = _resolve_db_path()
    cfg = _load_config_json()
    print(f"Database : {db}")
    print(f"Save dir : {cfg['saveDirectory']}")
    download_all(db, cfg)



# ── Helpers ───────────────────────────────────────────────────────────────── #

def _load_config_json() -> dict:
    """Build a configJson dict from the user's config.ini (same keys as GUI)."""
    cfg = configparser.ConfigParser()
    cfg.read(constants.defaultConfigPath)
    s = cfg["ScraperConfig"]

    def _bool(key):
        return s.get(key, "false").strip().lower() == "true"

    return {
        "userDataDir":      s.get("userdatadir", "UserData0"),
        "headless":         _bool("headless"),
        "courseUrlsFilePath": s.get("courseurlsfilepath", ""),
        "saveDirectory":    s.get("savedirectory", "."),
        "logger":           s.get("logger", "INFO"),
        "moduleType":       s.get("moduletype", "COURSE-PATH"),
        "isProxy":          _bool("isproxy"),
        "proxy":            s.get("proxy", ""),
        "scraperType":      s.get("scrapertype", "API-JSON-Scraper"),
        "scrapingMethod":   s.get("scrapingmethod", "SingleFile-HTML"),
        "fileType":         s.get("filetype", "html"),
        "ucdriver":         _bool("ucdriver"),
        "binaryversion":    s.get("binaryversion", "116"),
        "autoresume":       _bool("autoresume"),
        "autofixtextfile":  _bool("autofixtextfile"),
        "blockscraper":     _bool("blockscraper"),
        "autonext":         _bool("autonext"),
        "overwrite":        _bool("overwrite"),
        "useExtension":     _bool("useExtension"),
    }



