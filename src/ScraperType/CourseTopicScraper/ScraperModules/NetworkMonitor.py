import re
import time

from src.Logging.Logger import Logger


class NetworkMonitor:
    def __init__(self, configJson):
        self.browser = None
        self.logger = Logger(configJson, "NetworkMonitor").logger
        self.apiUrlPattern = re.compile(r"^https:\/\/(?:www\.)?educative\.io\/api\/[A-Za-z0-9_\/-]+(?:\?.*)?$")
        self.matchedUrls = []
        self.performanceResourceScript = """
            const entries = performance.getEntriesByType('resource') || [];
            return entries.map((entry) => ({
                name: entry && entry.name ? String(entry.name) : '',
                initiatorType: entry && entry.initiatorType ? String(entry.initiatorType) : ''
            }));
        """

    def _dedupeAndFilterApiUrls(self, urls):
        filtered = []
        for url in urls:
            if url and self.apiUrlPattern.match(url):
                filtered.append(url)
        # Keep order stable but avoid repeated URLs.
        return list(dict.fromkeys(filtered))


    def _getApiUrlsFromPerformanceEntries(self, timeout):
        if not hasattr(self.browser, "execute_script"):
            return []

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resources = self.browser.execute_script(self.performanceResourceScript) or []
            except Exception as e:
                self.logger.debug(f"Unable to read performance entries: {e}")
                return []

            resourceUrls = [
                item.get("name")
                for item in resources
                if isinstance(item, dict) and item.get("name")
            ]
            matchedUrls = self._dedupeAndFilterApiUrls(resourceUrls)
            if matchedUrls:
                return matchedUrls
            time.sleep(0.5)

        return []

    def getAPIUrls(self, timeout=30):
        try:
            self.logger.info("Getting APIUrl")
            try:
                self.matchedUrls = self._getApiUrlsFromPerformanceEntries(timeout)
                if self.matchedUrls:
                    self.logger.info("NetworkMonitor source: Browser Performance entries")
                    self.logger.debug(f"NetworkMonitor API URls: {self.matchedUrls}")
                    return self.matchedUrls

                self.logger.warning("No matching educative API URLs captured from browser Performance entries")
                self.logger.debug(f"NetworkMonitor API URls: {self.matchedUrls}")
                return self.matchedUrls
            except TimeoutError:
                self.logger.warning(f"Timeout after {timeout} seconds: API Url not found")
                return []
            # finally:
            #     self.browser.remove_listener("Network.requestWillBeSent", capture_request)
        except Exception as e:
            line_number = e.__traceback__.tb_lineno
            self.logger.error(f"Error in get_bearer_token at line {line_number}: {str(e)}")
            raise Exception(f"NetworkMonitor:getAPIUrl: {line_number}: {e}")