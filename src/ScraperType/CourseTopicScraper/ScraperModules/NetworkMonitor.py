import re
import time

from src.Logging.Logger import Logger


class NetworkMonitor:
    _API_PATTERN = re.compile(r"^https://(?:www\.)?educative\.io/api/.+$")

    _PERFORMANCE_SCRIPT = """
        const entries = performance.getEntriesByType('resource') || [];
        return entries.map(e => ({ name: e.name ? String(e.name) : '' }));
    """

    def __init__(self, configJson):
        self.browser = None
        self.logger = Logger(configJson, "NetworkMonitor").logger

    def _collectApiUrls(self, timeout: int) -> list:
        deadline = time.time() + timeout
        while time.time() < deadline:
            resources = self.browser.execute_script(self._PERFORMANCE_SCRIPT) or []
            urls = [
                item["name"] for item in resources
                if isinstance(item, dict) and item.get("name")
                and self._API_PATTERN.match(item["name"])
            ]
            deduped = list(dict.fromkeys(urls))
            if deduped:
                return deduped
            time.sleep(0.5)
        return []

    def getAPIUrls(self, timeout: int = 30) -> list:
        self.logger.info("Getting API URLs from browser performance entries")
        urls = self._collectApiUrls(timeout)
        if urls:
            self.logger.info(f"NetworkMonitor: captured {len(urls)} API URL(s)")
            self.logger.debug(f"NetworkMonitor API URLs: {urls}")
        else:
            self.logger.warning("NetworkMonitor: no educative API URLs found in performance entries")
        return urls