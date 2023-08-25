import asyncio
import json
import multiprocessing
import os
import time
import tkinter as tk

import psutil
import websockets
from selenium import webdriver

from src.Common.Constants import constants


class ChromeThread:
    def __init__(self):
        self.browser = None
        self.userDataDir = os.path.join(
            constants.OS_ROOT, "UserData0")
        self.devToolUrl = None


    def loadBrowser(self):
        # Rest of your WebDriver setup options...

        options = webdriver.ChromeOptions()
        # if self.configJson["headless"]:
        #     options.add_argument('headless')
        options.add_argument(f'user-data-dir={self.userDataDir}')
        options.add_argument('--profile-directory=Default')
        options.add_argument("--start-maximized")
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-web-security")
        options.add_argument('--allow-running-insecure-content')
        options.add_argument("--disable-site-isolation-trials")
        # options.add_argument('--remote-debugging-port=9222')
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument('--log-level=3')
        userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.56 Safari/537.36"
        options.add_argument(f'user-agent={userAgent}')
        options.binary_location = constants.chromeBinaryPath

        self.browser = webdriver.Remote(
            command_executor='http://127.0.0.1:9515', options=options)
        self.browser.set_window_size(1920, 1080)
        self.browser.command_executor._commands["send_command"] = (
            "POST", '/session/$sessionId/chromium/send_command')
        print("Driver Loaded")


    def run(self):
        print("HELLOOO")
        self.loadBrowser()
        self.browser.get("https://www.example.com")  # Load your desired URL
        i = 0
        while True:
            time.sleep(1)
            print("Running", i)
            i += 1


class GUI:
    def __init__(self, root):
        self.userDataDir = os.path.join(
            constants.OS_ROOT, "UserData0")
        self.chrome_thread = None
        self.root = root
        self.root.title("Chrome Controller")
        self.close_signal = multiprocessing.Queue()

        self.start_button = tk.Button(root, text="Start", command=self.start_thread)
        self.start_button.pack()

        self.stop_button = tk.Button(root, text="Stop", command=self.stop_thread)
        self.stop_button.pack()
        self.allProcesses = []


    def start_thread(self):
        self.chrome_thread = ChromeThread()
        # self.chrome_thread.loadBrowser()
        # print(self.chrome_thread.browser.quit())
        process = multiprocessing.Process(target=self.chrome_thread.run)
        process.start()
        self.allProcesses.append(process)

        print("Started")


    def getDevToolsUrl(self):
        with open(os.path.join(self.userDataDir, "DevToolsActivePort")) as f:
            devToolsFile = f.readlines()
            devToolsPort = devToolsFile[0].split("\n")[0]
            devToolsId = devToolsFile[1].split("\n")[0]
        self.devToolUrl = f"ws://127.0.0.1:{devToolsPort}{devToolsId}"


    async def shutdown_chrome(self):

        async with websockets.connect(self.devToolUrl) as websocket:
            message = {
                "id": 1,
                "method": "Browser.close"
            }
            await websocket.send(json.dumps(message))
            response = await websocket.recv()
            print("Response:", response)


    def stop_thread(self):
        print("Stopping Process")
        for process in self.allProcesses:
            try:
                self.getDevToolsUrl()
                process.terminate()
                process.join()
                asyncio.get_event_loop().run_until_complete(self.shutdown_chrome())
            except psutil.NoSuchProcess:
                pass
        self.allProcesses = []


    def get_all_children(self, proc: psutil.Process):
        try:
            if len(proc.children()) == 0:
                return []
            else:
                returned_list = []
                for item in proc.children():
                    returned_list.append(item)
                    returned_list.extend(self.get_all_children(item))
                return returned_list
        except psutil.NoSuchProcess:
            return []


if __name__ == '__main__':
    root = tk.Tk()
    app = GUI(root)
    root.mainloop()
