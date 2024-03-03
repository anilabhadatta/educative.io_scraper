import json
import os

import psutil
import requests
import websockets
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

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
        self.userDataDir = os.path.join(constants.OS_ROOT, self.configJson["userDataDir"], f"ucDriver-{self.configJson['ucdriver']}")
        self.devToolsFilePath = os.path.join(self.userDataDir, "DevToolsActivePort")


    def loadBrowser(self):
        try:
            self.logger.info("Loading Browser...")
            options = self.setChromeOptions()
            if self.configJson["ucdriver"]:
                self.browser = uc.Chrome(driver_executable_path=constants.ucDriverPath, options=options, user_data_dir=self.userDataDir)
            else:
                options.add_argument(f'user-data-dir={self.userDataDir}')
                chromeService = Service(executable_path=constants.chromeDriverPath)
                self.browser = webdriver.Chrome(service=chromeService, options=options)
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
            raise Exception(f"BrowserUtility:loadBrowser: {lineNumber}: {e}")


    def setChromeOptions(self):
        options = uc.ChromeOptions()
        if self.configJson["headless"]:
            options.add_argument('--headless=new')
        if self.configJson["isProxy"]:
            options.add_argument("--proxy-server=http://" + f'{self.configJson["proxy"]}')
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
        return options


    def killProcessByPid(self, pid, pname="chromedriver"):
        self.logger.info(f"Trying to terminate {pname} (PID {pid}).")
        try:
            psutil.Process(pid=pid).terminate()
            self.logger.info(f"Process {pname} (PID {pid}) terminated successfully.")
        except:
            self.logger.info(f"No {pname} process found")


    def killProcessByName(self, processNameArr):
        for process in psutil.process_iter():
            try:
                pname = process.name()
                pid = process.pid
                if pname in processNameArr:
                    self.killProcessByPid(pid, pname)
            except:
                self.logger.info(f"No {process} process found")


    def deleteLockFiles(self):
        try:
            files = os.listdir(self.userDataDir)
            for file in files:
                if file.startswith("Singleton"):
                    filePath = os.path.join(self.userDataDir, file)
                    if not os.path.isdir(filePath):
                        os.remove(filePath)
                        self.logger.info(f"Deleted: {filePath}")
            self.logger.info(f"Deletion of files with prefix Singleton completed.")
        except Exception as e:
            self.logger.info(f"An error occurred while deleting lock files: {e}")


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
                self.logger.info(f"Browser closed via websocket {devToolUrl}")
        except Exception as e:
            self.logger.error("No Browser was open to close via websocket")
        finally:
            # self.killProcessByPid(int(pid))
            self.deleteLockFiles()
            self.killProcessByName(["chrome", "chrome.exe", "chromedriver", "chromedriver.exe"])


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
