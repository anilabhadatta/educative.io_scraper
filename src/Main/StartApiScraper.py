"""
StartApiScraper.py

Entry point for the new API-only scraping mode.
Drop-in replacement for StartScraper when you only want JSON stored in SQLite
(no HTML files, no screenshots).

Usage (from project root):
    python -m src.Main.StartApiScraper          # uses ~/EducativeScraper/config.ini
    python -m src.Main.StartApiScraper --manual  # attach to an existing Chrome session
"""

import argparse
import multiprocessing

from src.Logging.Logger import Logger
from src.Main.MailNotify import MailNotify
from src.ScraperType.ApiScraper.ApiScraperMain import ApiScraperMain
from src.Utility.ConfigUtility import ConfigUtility


class StartApiScraper:
    def __init__(self):
        self.logger = None
        self.mailNotify = MailNotify()

    # ------------------------------------------------------------------ #

    def start(self, configJson: dict, progressQueue: multiprocessing.Queue = None):
        self.logger = Logger(configJson, "StartApiScraper").logger
        self.logger.info("StartApiScraper – API-only mode initiated.")
        try:
            if progressQueue:
                progressQueue.put(("color", "green"))
            ApiScraperMain(configJson, progressQueue).start()
            self.mailNotify.send_email("API Scraping Complete")
        except KeyboardInterrupt:
            self.logger.warning("Keyboard interrupt – stopping.")
        except Exception as e:
            ln = e.__traceback__.tb_lineno
            self.logger.error(f"start: {ln}: {e}")
            self.mailNotify.send_email(f"API Scraper exception at line {ln}: {e}")
            if progressQueue:
                progressQueue.put(("color", "red"))
        finally:
            self.logger.debug("StartApiScraper exiting.")

    def startManual(self, configJson: dict):
        self.logger = Logger(configJson, "StartApiScraper").logger
        self.logger.info("StartApiScraper – manual (attach) mode initiated.")
        try:
            ApiScraperMain(configJson).startManual()
        except KeyboardInterrupt:
            self.logger.warning("Keyboard interrupt – stopping.")
        except Exception as e:
            ln = e.__traceback__.tb_lineno
            self.logger.error(f"startManual: {ln}: {e}")
        finally:
            self.logger.debug("StartApiScraper (manual) exiting.")


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Educative.io API-only scraper")
    parser.add_argument(
        "--manual", action="store_true",
        help="Attach to an existing Chrome DevTools session instead of launching a new browser."
    )
    args = parser.parse_args()

    config = ConfigUtility().loadConfig()
    configJson = dict(config["ScraperConfig"])
    # Normalise boolean strings
    for key in ("headless", "useExtension", "autonext"):
        if key in configJson:
            configJson[key] = configJson[key].lower() in ("true", "1", "yes")

    runner = StartApiScraper()
    if args.manual:
        runner.startManual(configJson)
    else:
        runner.start(configJson)
