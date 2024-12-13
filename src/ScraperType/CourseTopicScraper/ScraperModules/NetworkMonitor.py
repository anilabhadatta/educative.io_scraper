import asyncio
import re

from src.Logging.Logger import Logger


class NetworkMonitor:
    def __init__(self, configJson):
        self.browser = None
        self.logger = Logger(configJson, "NetworkMonitor").logger
        self.apiUrlPattern = re.compile(r"https:\/\/(?:www\.)?educative\.io\/api\/(?:[a-zA-Z0-9\-]+\/)+[a-zA-Z0-9\-]+$")
        self.matchedUrls = []

    async def getAPIUrls(self, timeout=30):
        try:
            self.logger.info("Getting APIUrl")
            try:
                self.matchedUrls = []
                for request in self.browser.requests:
                    if request.response and self.apiUrlPattern.match(request.url):
                        self.matchedUrls.append(request.url)
                self.logger.info(f"API URls: {self.matchedUrls}")
                return self.matchedUrls
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout after {timeout} seconds: API Url not found")
                return None
            # finally:
            #     self.browser.remove_listener("Network.requestWillBeSent", capture_request)
        except Exception as e:
            line_number = e.__traceback__.tb_lineno
            self.logger.error(f"Error in get_bearer_token at line {line_number}: {str(e)}")
            raise Exception(f"NetworkMonitor:getAPIUrl: {line_number}: {e}")