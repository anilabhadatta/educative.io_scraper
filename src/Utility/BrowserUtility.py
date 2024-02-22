import json
import os
import requests
import websockets

from selenium import webdriver

from src.Common.Constants import constants
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility
from src.Logging.Logger import Logger
import undetected_chromedriver as uc

class BrowserUtility:
    def __init__(self, configJson=None):
        self.devToolJsonUrl = None
        self.browser = None
        self.configJson = configJson
        self.devToolUrl = None
        if configJson:
            self.logger = Logger(configJson, "BrowserUtility").logger
        self.osUtils = OSUtility(configJson)
        self.fileUtils = FileUtility()
        self.devToolsFilePath = os.path.join(constants.OS_ROOT, self.configJson["userDataDir"], "Default",
                                             "DevToolsActivePort")


    def loadBrowser(self):
        try:
            self.logger.info("Loading Browser...")
            userDataDir = os.path.join(constants.OS_ROOT, self.configJson["userDataDir"], "Default")
            options = uc.ChromeOptions()
            if self.configJson["headless"]:
                options.add_argument('--headless=new')
            options.add_argument("--start-maximized")
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--ignore-certificate-errors-spki-list')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument("--disable-web-security")
            options.add_argument('--allow-running-insecure-content')
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument('--log-level=3')
            options.binary_location = constants.chromeBinaryPath
            if self.configJson["isProxy"]:
                options.add_argument("--proxy-server=http://" + f'{self.configJson["proxy"]}')
            self.browser = uc.Chrome(driver_executable_path=constants.chromeDriverPath, options=options, user_data_dir=userDataDir)
            self.browser.set_window_size(1920, 1080)
            self.browser.set_script_timeout(60)
            remoteDebuggingAddress = self.browser.capabilities['goog:chromeOptions']['debuggerAddress']
            self.saveWebSocketUrl(remoteDebuggingAddress)
            self.browser.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
            self.logger.info(f"Browser Initiated")
            return self.browser
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            if "Failed to establish a new connection" in str(e) and 48 == lineNumber:
                raise Exception(f"BrowserUtility:loadBrowser: {lineNumber}: Chromedriver might not be running in background, Please click on Start Chromedriver.")
            raise Exception(f"BrowserUtility:loadBrowser: {lineNumber}: {e}")


    def saveWebSocketUrl(self, remoteDebuggingAddress):
        self.logger.debug("getDevToolsUrl called")
        devToolJsonUrl = f"http://{remoteDebuggingAddress}/json/version"
        response = requests.get(devToolJsonUrl)
        devToolUrl = json.loads(response.content)['webSocketDebuggerUrl']
        with open(self.devToolsFilePath, 'w') as f:
            f.write(devToolUrl)
        self.logger.info("getDevToolsUrl completed with devToolUrl: " + devToolUrl)


    async def shutdownChromeViaWebsocket(self):
        self.logger.debug("shutdownChromeViaWebsocket called")
        try:
            devToolUrl = self.fileUtils.loadTextFile(self.devToolsFilePath)[0]
            async with websockets.connect(devToolUrl) as websocket:
                message = {
                    "id": 1,
                    "method": "Browser.close"
                }
                await websocket.send(json.dumps(message))
                await websocket.recv()
                self.logger.info("Browser closed via websocket")
        except Exception as e:
            self.logger.error("No Browser was open to close via websocket")


    def getCurrentHeight(self):
        return self.browser.execute_script("return document.body.scrollHeight")


    def scrollPage(self):
        self.logger.info("Scrolling Page")
        totalHeight = int(self.getCurrentHeight())
        for i in range(0, totalHeight, 50):
            self.browser.execute_script(f"window.scrollTo({i}, {i+50});")
        self.browser.execute_script("window.scrollTo(0, 0);")
        self.osUtils.sleep(2)


    def setWindowSize(self):
        try:
            totalHeight = int(self.getCurrentHeight())
            self.browser.set_window_size(1920, totalHeight)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"BrowserUtility:setWindowSize: {lineNumber}: {e}")
