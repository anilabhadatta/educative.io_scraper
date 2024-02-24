import json
import os
import random
import shutil
import string
from psutil import Process
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
            # dstChromeDriverPAth = self.recreateChromedriver()
            if self.configJson["isProxy"]:
                options.add_argument("--proxy-server=http://" + f'{self.configJson["proxy"]}')
            self.browser = uc.Chrome(use_subprocess=True,driver_executable_path=constants.chromeDriverPath, options=options, user_data_dir=userDataDir)
            self.browser.set_window_size(1920, 1080)
            self.browser.set_script_timeout(60)
            remoteDebuggingAddress = self.browser.capabilities['goog:chromeOptions']['debuggerAddress']
            pid = str(self.browser.service.process.pid)
            self.saveWebSocketUrl(remoteDebuggingAddress, pid)
            self.browser.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
            self.logger.info(f"Browser Initiated")
            return self.browser
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            if "Failed to establish a new connection" in str(e) and 48 == lineNumber:
                raise Exception(f"BrowserUtility:loadBrowser: {lineNumber}: Chromedriver might not be running in background, Please click on Start Chromedriver.")
            raise Exception(f"BrowserUtility:loadBrowser: {lineNumber}: {e}")

    def recreateChromedriver(self):
        srcChromeDriverPath = constants.chromeDriverPath
        directory, filename = os.path.split(srcChromeDriverPath)
        fileName = ''.join(random.choice(string.ascii_lowercase) for _ in range(6)) + filename
        dstChromeDriverPAth = os.path.join(directory, fileName)
        shutil.copy2(srcChromeDriverPath, dstChromeDriverPAth)

        return dstChromeDriverPAth


    def terminateChrome(self):
        if self.browser is not None:
            self.browser.quit()
            try:
                pid = self.browser.service.process.pid
                Process(pid=pid).terminate()
                self.logger.info(f"Killed chromedriver {str(pid)}")
            except:
                self.logger.info(f"No chromedriver found")


    def saveWebSocketUrl(self, remoteDebuggingAddress, pid):
        self.logger.info("saveWebSocketUrl called")
        devToolJsonUrl = f"http://{remoteDebuggingAddress}/json/version"
        response = requests.get(devToolJsonUrl)
        devToolUrl = json.loads(response.content)['webSocketDebuggerUrl']
        content = devToolUrl + "\n" + pid
        self.fileUtils.createTextFile(self.devToolsFilePath, content)
        self.logger.info(f"saveWebSocketUrl completed with devToolUrl: {devToolUrl} pid : {pid}")


    async def shutdownChromeViaWebsocket(self):
        self.logger.debug("shutdownChromeViaWebsocket called")
        try:
            content = self.fileUtils.loadTextFile(self.devToolsFilePath)
            devToolUrl = content[0]
            pid = content[1]
            async with websockets.connect(devToolUrl) as websocket:
                message = {
                    "id": 1,
                    "method": "Browser.close"
                }
                await websocket.send(json.dumps(message))
                await websocket.recv()
                Process(pid=int(pid)).terminate()
                self.logger.info(f"Browser closed via websocket {devToolUrl} pid: {pid}")
        except Exception as e:
            self.logger.error("No Browser was open to close via websocket")


    def getCurrentHeight(self):
        return self.browser.execute_script("return document.body.scrollHeight")


    def scrollPage(self):
        self.logger.info("Scrolling Page")
        totalHeight = int(self.getCurrentHeight())
        for i in range(0, totalHeight, 500):
            self.osUtils.sleep(0.5)
            self.browser.execute_script(f"window.scrollTo({i}, {i+500});")
        self.browser.execute_script("window.scrollTo(0, 0);")
        self.osUtils.sleep(2)


    def setWindowSize(self):
        try:
            totalHeight = int(self.getCurrentHeight())
            self.browser.set_window_size(1920, totalHeight)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"BrowserUtility:setWindowSize: {lineNumber}: {e}")
