import asyncio
import multiprocessing
import os
import shutil
import threading
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox
from tkinter import ttk
import queue 
import psutil
from PIL import Image, ImageTk

from src.Main.UpdateTxtFileFromLog import UpdateTxtFileFromLog
from src.Common.Constants import constants
from src.Logging.Logger import Logger
from src.Main.LoginAccount import LoginAccount
from src.Main.StartChromedriver import StartChromedriver
from src.Main.StartScraper import StartScraper
from src.Utility.BrowserUtility import BrowserUtility
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.DownloadUtility import DownloadUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.StaticAssetExtractor import run_from_config as run_static_asset_extractor
from src.Utility.StaticAssetDownloader import run_from_config as run_static_asset_downloader


class HomeScreen:
    def __init__(self):
        self.config = None
        self.logger = None
        self.process = None
        self.configJson = None
        self.processes = []
        self.checkboxes = []

        self.app = tk.Tk()
        style = ttk.Style(self.app)
        style.theme_use('clam')

        # Define styles with different colors
        style.configure("green.Horizontal.TProgressbar", troughcolor='white', background='#28a745')
        style.configure("red.Horizontal.TProgressbar", troughcolor='white', background='#dc3545')
        style.configure("TNotebook.Tab", padding=(12, 6))
        imagePath = os.path.join(constants.commonFolderPath, "icon.gif")
        pilImage = Image.open(imagePath)
        self.app.iconphoto(True, ImageTk.PhotoImage(pilImage))
        self.app.geometry("980x720")
        self.app.title("Educative Scraper")

        self.configFilePath = tk.StringVar()
        self.userDataDirVar = tk.StringVar()
        self.autoNextVar = tk.BooleanVar(value=False)
        self.headlessVar = tk.BooleanVar(value=False)
        self.ucdriverVar = tk.BooleanVar(value=False)
        self.autoResumeScraper = tk.BooleanVar(value=False)
        self.autoFixTextFile = tk.BooleanVar(value=False)
        self.overwriteVar = tk.BooleanVar(value=False)
        self.courseUrlsFilePathVar = tk.StringVar()
        self.saveDirectoryVar = tk.StringVar()
        self.isProxyVar = tk.BooleanVar(value=True)
        self.proxyVar = tk.StringVar()
        self.loggingLevelVar = tk.StringVar()
        self.loggingLevels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"]
        self.moduleTypeVar = tk.StringVar()
        self.moduleTypes = ["COURSE-PATH", "CLOUDLAB", "PROJECT"]
        self.logLevelDesc = {
            "DEBUG": "Detailed info for debugging.",
            "INFO": "Confirmation of expected functionality.",
            "WARNING": "Indication of unexpected events.",
            "ERROR": "Software can't perform a function.",
            "CRITICAL": "Program can't continue running.",
            "NOTSET": "Lowest level, turns off logging."
        }
        self.scrapingMethodVar = tk.StringVar()
        self.scrapingMethods = ["SingleFile-HTML", "Full-Page-Screenshot"]
        self.scraperTypeVar = tk.StringVar()
        self.scraperTypes = ["Course-Topic-Scraper", "All-Course-Urls-Text-File-Generator", "API-JSON-Scraper"]
        self.fileTypeVar = tk.StringVar()
        self.fileTypes = ["html2pdf", "html", "png2pdf", "png"]

        self.fileUtil = FileUtility()
        self.downloadUtil = DownloadUtility()
        self.topicProgressVar = tk.DoubleVar()
        self.courseProgressVar = tk.DoubleVar()
        self.configUtil = ConfigUtility()
        self.loadDefaultConfig()
        self.logLevelDescVar = tk.StringVar(value=self.configJson['logger'])
        self.logDescriptionLabel = None
        self.checkButtonStateVar = tk.StringVar()
        self.clickedByUser = False
        self.updateTextFromLog = UpdateTxtFileFromLog(self.configJson)


    def onConfigChange(self, *args):
        # if self.moduleTypeVar.get() != "COURSE-PATH":
        #     # AUTO RESUME AND AUTO FIX CURRENTLY DISABLED FOR CLOUDLAB AND PROJECTS
        #     self.autoFixTextFile.set(value=False)
        #     self.autoResumeScraper.set(value=False)
        self.createConfigJson()
        self.updateTextFromLog = UpdateTxtFileFromLog(self.configJson)
        self.logger = Logger(self.configJson, "HomeScreen").logger
        self.logLevelDescVar.set(self.configJson['logger'])
        self.logDescriptionLabel.config(text=self.logLevelDesc[self.logLevelDescVar.get()])


    def updateComboboxStates(self, *args):
        if not hasattr(self, "scrapingMethodCombobox"):
            return

        scraper_type = self.scraperTypeVar.get()
        is_api_scraper = scraper_type == "API-JSON-Scraper"
        hide_scraping_output_controls = scraper_type in (
            "All-Course-Urls-Text-File-Generator",
            "API-JSON-Scraper",
        )

        if hide_scraping_output_controls:
            self.scrapingMethodCombobox.config(state="disabled")
            self.fileTypeCombobox.config(state="disabled")
        elif scraper_type == "Course-Topic-Scraper":
            self.scrapingMethodCombobox.config(state="readonly")
            self.fileTypeCombobox.config(state="readonly")
            if self.scrapingMethodVar.get() == "SingleFile-HTML":
                if self.fileTypeVar.get() == "png" or self.fileTypeVar.get() == "png2pdf":
                    self.fileTypeVar.set("html")
                self.fileTypeCombobox['values'] = self.fileTypes[:2]
            else:
                self.fileTypeCombobox['values'] = self.fileTypes[1:]

        # API and URL-generator modes do not need scraping method/file type controls.
        if hide_scraping_output_controls:
            self.scrapingMethodLabel.grid_remove()
            self.scrapingMethodCombobox.grid_remove()
            self.fileTypeLabel.grid_remove()
            self.fileTypeCombobox.grid_remove()
        else:
            self.scrapingMethodLabel.grid(row=1, column=0, sticky="w", padx=2, pady=0)
            self.scrapingMethodCombobox.grid(row=1, column=1, sticky="w", padx=0, pady=5)
            self.fileTypeLabel.grid(row=2, column=0, sticky="w", padx=2, pady=0)
            self.fileTypeCombobox.grid(row=2, column=1, sticky="w", padx=0, pady=5)

        # Manual scraper remains visible but is disabled only in API mode.
        if is_api_scraper:
            self.startChromeDriverButton.config(state="disabled")
        elif not self.processes:
            self.startChromeDriverButton.config(state="normal")

        # Overwrite option should be visible only for API scraper.
        if hasattr(self, "overwriteCheckbox"):
            if is_api_scraper:
                self.overwriteCheckbox.grid(row=1, column=2, sticky="w", padx=(10, 0), pady=2)
            else:
                self.overwriteCheckbox.grid_remove()

        if hasattr(self, "extractAssetsButton") and hasattr(self, "downloadAssetsButton"):
            button_state = "normal" if is_api_scraper else "disabled"
            self.extractAssetsButton.config(state=button_state)
            self.downloadAssetsButton.config(state=button_state)

        # Keep window height tightly fit to visible controls when mode changes.
        self.app.after_idle(self.fixGeometry)
    

    def trackUserClick(self, event):
        self.clickedByUser = True


    def autoStartScraperOnConditions(self):
        if self.startScraperButton['state'] == 'normal' and \
            not self.updateTextFromLog.getBlockScraper() and \
            self.configJson['autoresume']:
            if self.updateTextFromLog.updateTextFileFromLogMain():
                self.startScraperButton.invoke()
                self.clickedByUser = False


    def createHomeScreen(self, version):
        self.logger = Logger(self.configJson, "HomeScreen").logger
        self.loggingLevelVar.trace("w", self.onConfigChange)
        self.moduleTypeVar.trace("w", self.onConfigChange)
        self.saveDirectoryVar.trace("w", self.onConfigChange)
        self.logLevelDescVar.trace("w", self.onConfigChange)
        self.scrapingMethodVar.trace("w", self.updateComboboxStates)
        self.scraperTypeVar.trace("w", self.updateComboboxStates)
        self.autoFixTextFile.trace("w", self.onConfigChange)
        self.autoResumeScraper.trace("w", self.onConfigChange)
        self.logger.info("Creating Home Screen...")

        mainNotebook = ttk.Notebook(self.app)
        scraperTab = ttk.Frame(mainNotebook)
        aboutTab = ttk.Frame(mainNotebook)
        mainNotebook.add(scraperTab, text="Scraper")
        mainNotebook.add(aboutTab, text="About")
        mainNotebook.pack(fill="both", expand=True, padx=10, pady=8)

        configFilePathFrame = tk.Frame(scraperTab)
        configFilePathLabel = tk.Label(configFilePathFrame, text="Config File Path:")
        configFileTextBox = tk.Entry(configFilePathFrame, textvariable=self.configFilePath, width=70)
        browseConfigFileButton = tk.Button(configFilePathFrame, text="...", command=self.browseConfigFile)
        configFilePathLabel.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        configFileTextBox.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        browseConfigFileButton.grid(row=0, column=2, padx=2)
        configFilePathFrame.pack(pady=3, padx=10, anchor="w")

        optionsContainerFrame = tk.Frame(scraperTab)
        optionsContainerFrame.grid_columnconfigure(0, weight=1)
        optionsContainerFrame.grid_columnconfigure(1, weight=1)
        scraperOptionFrame = tk.Frame(optionsContainerFrame)
        scraperTypeLabel = tk.Label(scraperOptionFrame, text="Scraper Type:")
        scraperTypeLabel.grid(row=0, column=0, sticky="w", padx=2, pady=0)
        self.scraperTypeCombobox = ttk.Combobox(scraperOptionFrame, textvariable=self.scraperTypeVar,
                                           values=self.scraperTypes, state="readonly", width=30)
        self.scraperTypeCombobox.grid(row=0, column=1, sticky="w", padx=0, pady=5)
        self.scrapingMethodLabel = tk.Label(scraperOptionFrame, text="Scraping Method:")
        self.scrapingMethodLabel.grid(row=1, column=0, sticky="w", padx=2, pady=0)
        self.scrapingMethodCombobox = ttk.Combobox(scraperOptionFrame, textvariable=self.scrapingMethodVar,
                                           values=self.scrapingMethods, state="readonly", width=30)
        self.scrapingMethodCombobox.grid(row=1, column=1, sticky="w", padx=0, pady=5)
        self.fileTypeLabel = tk.Label(scraperOptionFrame, text="File Type:")
        self.fileTypeLabel.grid(row=2, column=0, sticky="w", padx=2, pady=0)
        self.fileTypeCombobox = ttk.Combobox(scraperOptionFrame, textvariable=self.fileTypeVar,
                                           values=self.fileTypes, state="readonly", width=30)
        self.fileTypeCombobox.grid(row=2, column=1, sticky="w", padx=0, pady=5)
        loggerLevelLabel = tk.Label(scraperOptionFrame, text="Logger Level:")
        loggerLevelLabel.grid(row=3, column=0, sticky="w", padx=2, pady=0)
        loggingLevelCombobox = ttk.Combobox(scraperOptionFrame, textvariable=self.loggingLevelVar,
                                            values=self.loggingLevels, state="readonly", width=30)
        loggingLevelCombobox.grid(row=3, column=1, sticky="w", padx=0, pady=5)

        self.logDescriptionLabel = tk.Label(
            scraperOptionFrame,
            text=self.logLevelDesc[self.logLevelDescVar.get()],
            anchor="w",
        )
        self.logDescriptionLabel.grid(row=4, column=1, columnspan=2, sticky="w", padx=0, pady=(0, 2))

        moduleTypeLabel = tk.Label(scraperOptionFrame, text="Module Type:")
        moduleTypeLabel.grid(row=5, column=0, sticky="w", padx=2, pady=0)
        moduleTypeCombobox = ttk.Combobox(scraperOptionFrame, textvariable=self.moduleTypeVar,
                                            values=self.moduleTypes, state="readonly", width=30)
        moduleTypeCombobox.grid(row=5, column=1, sticky="w", padx=0, pady=5)

        self.proxyCheckboxOption = tk.Checkbutton(scraperOptionFrame, text="Proxy", variable=self.isProxyVar, anchor="w")
        self.proxyCheckboxOption.grid(row=6, column=0, sticky="w", padx=2, pady=2)
        self.proxyEntryOption = tk.Entry(scraperOptionFrame, textvariable=self.proxyVar, width=30)
        self.proxyEntryOption.grid(row=6, column=1, sticky="w", padx=0, pady=2)
        self.proxyFormatLabel = tk.Label(scraperOptionFrame, text="Host:Port")
        self.proxyFormatLabel.grid(row=6, column=2, sticky="w", padx=2, pady=2)

        checkboxesFrame = tk.LabelFrame(optionsContainerFrame, text="Runtime Options", padx=8, pady=6)
        for col in range(3):
            checkboxesFrame.grid_columnconfigure(col, weight=1)

        self.headlessCheckbox = tk.Checkbutton(checkboxesFrame, text="Headless", variable=self.headlessVar, anchor="w")
        self.headlessCheckbox.grid(row=0, column=0, sticky="w", padx=0, pady=2)
        self.checkboxes.append(self.headlessCheckbox)

        self.ucdriverCheckbox = tk.Checkbutton(checkboxesFrame, text="SeleniumBase(uc mode)", variable=self.ucdriverVar, anchor="w")
        self.ucdriverCheckbox.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
        self.checkboxes.append(self.ucdriverCheckbox)

        self.autoResumeScraperCheckbox = tk.Checkbutton(checkboxesFrame, text="Auto Resume Scraper", variable=self.autoResumeScraper, anchor="w")
        self.autoResumeScraperCheckbox.grid(row=0, column=2, sticky="w", padx=(10, 0), pady=2)
        self.checkboxes.append(self.autoResumeScraperCheckbox)

        self.autoFixTextFileCheckbox = tk.Checkbutton(checkboxesFrame, text="Auto Fix Url File", variable=self.autoFixTextFile, anchor="w")
        self.autoFixTextFileCheckbox.grid(row=1, column=0, sticky="w", padx=0, pady=2)
        self.checkboxes.append(self.autoFixTextFileCheckbox)

        self.autoNextCheckbox = tk.Checkbutton(checkboxesFrame, text="AutoNext", variable=self.autoNextVar, anchor="w")
        self.autoNextCheckbox.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=2)
        self.checkboxes.append(self.autoNextCheckbox)

        self.overwriteCheckbox = tk.Checkbutton(checkboxesFrame, text="Overwrite (API Scraper)", variable=self.overwriteVar, anchor="w")
        self.overwriteCheckbox.grid(row=1, column=2, sticky="w", padx=(10, 0), pady=2)
        self.overwriteCheckbox.grid_remove()

        scraperOptionFrame.grid(row=0, column=0, padx=0, pady=3, sticky="nw")
        checkboxesFrame.grid(row=0, column=1, padx=(12, 0), pady=3, sticky="new")
        optionsContainerFrame.pack(pady=3, padx=10, anchor="w")

        entriesFrame = tk.Frame(scraperTab)
        userDataDirLabel = tk.Label(entriesFrame, text="User Data Directory:")
        userDataDirEntry = tk.Entry(entriesFrame, textvariable=self.userDataDirVar, width=65)
        courseUrlsFilePathLabel = tk.Label(entriesFrame, text="Course URLs File Path:")
        courseUrlsFilePathEntry = tk.Entry(entriesFrame, textvariable=self.courseUrlsFilePathVar, width=65)
        courseUrlsFilePathButton = tk.Button(entriesFrame, text="...", command=self.browseCourseUrlsFile)
        saveDirectoryLabel = tk.Label(entriesFrame, text="Save Directory:")
        saveDirectoryEntry = tk.Entry(entriesFrame, textvariable=self.saveDirectoryVar, width=65)
        saveDirectoryButton = tk.Button(entriesFrame, text="...", command=self.browseSaveDirectory)
        logPathLabel = tk.Label(entriesFrame,
                                text="Logs are saved in Save Directory Path with name 'EducativeScraper.log")
        userDataDirLabel.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        userDataDirEntry.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        courseUrlsFilePathLabel.grid(row=1, column=0, sticky="w", padx=2, pady=2)
        courseUrlsFilePathEntry.grid(row=1, column=1, sticky="w", padx=2, pady=2)
        courseUrlsFilePathButton.grid(row=1, column=2, padx=2)
        saveDirectoryLabel.grid(row=2, column=0, sticky="w", padx=2, pady=2)
        saveDirectoryEntry.grid(row=2, column=1, sticky="w", padx=2, pady=2)
        saveDirectoryButton.grid(row=2, column=2, padx=2)
        logPathLabel.grid(row=3, column=1, sticky="w", padx=2, pady=2)
        entriesFrame.pack(pady=3, padx=10, anchor="w")

        buttonActionFrame = tk.Frame(scraperTab)
        for col in range(4):
            buttonActionFrame.grid_columnconfigure(col, weight=1)

        loadDefaultConfigButton = tk.Button(buttonActionFrame, text="Default Config", width=18,
                                            command=self.loadDefaultConfig)
        updateConfigButton = tk.Button(buttonActionFrame, text="Update Config", width=18, command=self.updateConfig)
        exportConfigButton = tk.Button(buttonActionFrame, text="Export Config", width=18, command=self.exportConfig)
        deleteUserDataButton = tk.Button(buttonActionFrame, text="Delete User Data", width=18, command=self.deleteUserData)

        self.downloadChromeDriverButton = tk.Button(buttonActionFrame, text="Download Chrome Driver", width=18,
                                                    command=self.downloadChromeDriver)
        self.downloadChromeBinaryButton = tk.Button(buttonActionFrame, text="Download Chrome Binary", width=18,
                                                    command=self.downloadChromeBinary)
        self.startChromeDriverButton = tk.Button(buttonActionFrame, text="Start Manual Scraper",
                                                 command=self.startManualScraper, width=18)
        self.loginAccountButton = tk.Button(buttonActionFrame, text="Login/Open Browser", command=self.loginAccount,
                                            width=18)
        self.startScraperButton = tk.Button(buttonActionFrame, text="Start Auto Scraper", command=self.startScraper,
                                            width=18)
        self.checkButtonStateVar.set(self.startScraperButton['state'])
        self.checkButtonStateVar.trace("w", lambda *args: self.autoStartScraperOnConditions())
        self.startScraperButton.bind("<Button-1>", self.trackUserClick)
        self.terminateProcessButton = tk.Button(buttonActionFrame, text="Stop Scraper/Close Browser",
                                                command=self.terminateProcess,
                                                width=18, state="disabled")
        self.extractAssetsButton = tk.Button(
            buttonActionFrame,
            text="Extract Assets",
            width=18,
            command=self.extractStaticAssets,
        )
        self.downloadAssetsButton = tk.Button(
            buttonActionFrame,
            text="Download Assets",
            width=18,
            command=self.downloadStaticAssets,
        )

        # Row 1: config buttons
        loadDefaultConfigButton.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        updateConfigButton.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        exportConfigButton.grid(row=0, column=2, sticky="ew", padx=2, pady=2)
        deleteUserDataButton.grid(row=0, column=3, sticky="ew", padx=2, pady=2)

        # Row 2: setup/browser actions
        self.downloadChromeDriverButton.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        self.downloadChromeBinaryButton.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        self.startChromeDriverButton.grid(row=1, column=2, sticky="ew", padx=2, pady=2)
        self.loginAccountButton.grid(row=1, column=3, sticky="ew", padx=2, pady=2)

        # Row 3: scraper + assets actions
        self.startScraperButton.grid(row=2, column=0, sticky="ew", padx=2, pady=2)
        self.terminateProcessButton.grid(row=2, column=1, sticky="ew", padx=2, pady=2)
        self.extractAssetsButton.grid(row=2, column=2, sticky="ew", padx=2, pady=2)
        self.downloadAssetsButton.grid(row=2, column=3, sticky="ew", padx=2, pady=2)

        buttonActionFrame.pack(fill="x", pady=4, padx=10, anchor="w")

        topicProgressBarFrame = tk.Frame(scraperTab)
        topicProgressBarFrame.grid_columnconfigure(1, weight=1)
        downloadProgressLabel = tk.Label(topicProgressBarFrame, text="Topic Progress:")
        self.topicProgressBar = ttk.Progressbar(topicProgressBarFrame, length=720, mode="determinate", variable=self.topicProgressVar, style="green.Horizontal.TProgressbar")
        downloadProgressLabel.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.topicProgressBar.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        topicProgressBarFrame.pack(fill="x", pady=3, padx=10)

        courseProgressBarFrame = tk.Frame(scraperTab)
        courseProgressBarFrame.grid_columnconfigure(1, weight=1)
        downloadProgressLabel = tk.Label(courseProgressBarFrame, text="Course Progress:")
        self.courseProgressBar = ttk.Progressbar(courseProgressBarFrame, length=720, mode="determinate", variable=self.courseProgressVar, style="green.Horizontal.TProgressbar")
        downloadProgressLabel.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.courseProgressBar.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        courseProgressBarFrame.pack(fill="x", pady=3, padx=10)

        aboutFrame = tk.Frame(aboutTab, padx=18, pady=18)
        aboutTitle = tk.Label(aboutFrame, text="Educative Scraper", font=("Segoe UI", 16, "bold"))
        aboutVersion = tk.Label(aboutFrame, text=version, font=("Segoe UI", 11, "bold"))
        aboutAuthor = tk.Label(aboutFrame, text="Developed by Anilabha Datta", font=("Segoe UI", 11))
        aboutDescription = tk.Label(
            aboutFrame,
            text=(
                "This tab keeps project info separate from scraping controls.\n"
                "Use the Scraper tab for scraping and static asset utilities."
            ),
            justify="left",
            anchor="w",
        )
        aboutTitle.pack(anchor="w", pady=(0, 4))
        aboutVersion.pack(anchor="w", pady=(0, 4))
        aboutAuthor.pack(anchor="w", pady=(0, 12))
        aboutDescription.pack(anchor="w")
        aboutFrame.pack(fill="both", expand=True)

        self.progressQueue = multiprocessing.Queue()
        self.updateProgress()

        self.updateComboboxStates()
        self.fixGeometry()
        self.app.update_idletasks()
        self.logger.debug("createHomeScreen completed")
        self.app.protocol("WM_DELETE_WINDOW", self.onClosingWindow)
        self.app.mainloop()


    def updateProgress(self):
        try:
            while True:
                msgType, value = self.progressQueue.get_nowait()
                if msgType == "max-topic":
                    self.topicProgressBar.config(maximum=value)
                elif msgType == "progress-topic":
                    self.topicProgressVar.set(value)
                elif msgType == "max-course":
                    self.courseProgressBar.config(maximum=value)
                elif msgType == "progress-course":
                    self.courseProgressVar.set(value)
                elif msgType == "color" and value == "red":
                    self.topicProgressBar.config(style="red.Horizontal.TProgressbar")
                    self.courseProgressBar.config(style="red.Horizontal.TProgressbar")
                elif msgType == "color" and value == "green":
                    self.topicProgressBar.config(style="green.Horizontal.TProgressbar")
                    self.courseProgressBar.config(style="green.Horizontal.TProgressbar")
        except queue.Empty:
            pass

        self.app.after(100, self.updateProgress)


    def onClosingWindow(self):
        self.terminateProcess()
        self.app.destroy()


    def fixGeometry(self):
        self.logger.debug("fixGeometry called")
        self.app.update_idletasks()
        req_width = self.app.winfo_reqwidth()
        req_height = self.app.winfo_reqheight()

        screen_width = self.app.winfo_screenwidth()
        screen_height = self.app.winfo_screenheight()
        max_width = max(screen_width - 40, 800)
        max_height = max(screen_height - 80, 600)
        width = min(req_width, max_width)
        height = min(req_height, max_height)
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.app.geometry(f"{width}x{height}+{x}+{y}")
        self.app.resizable(False, False)
        self.logger.debug("fixGeometry completed")


    def browseCourseUrlsFile(self):
        self.logger.debug("browseCourseUrlsFile called")
        courseUrlsFilePath = tk.filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt")])
        if courseUrlsFilePath:
            self.courseUrlsFilePathVar.set(courseUrlsFilePath)
        self.logger.debug(f"""browseCourseUrlsFile completed 
                              courseUrlsFilePath: {courseUrlsFilePath}
                            """)


    def browseSaveDirectory(self):
        self.logger.debug("browseSaveDirectory called")
        saveDirectoryPath = tk.filedialog.askdirectory()
        if saveDirectoryPath:
            self.saveDirectoryVar.set(saveDirectoryPath)
        self.logger.debug(f"""browseSaveDirectory completed
                              saveDirectoryPath: {saveDirectoryPath}
                            """)


    def browseConfigFile(self):
        self.logger.debug("browseConfigFile called")
        configFilePath = tk.filedialog.askopenfilename(
            filetypes=[("INI Files", "*.ini")])
        if configFilePath:
            self.configFilePath.set(configFilePath)
            self.config = self.configUtil.loadConfig(configFilePath)['ScraperConfig']
            self.mapConfigValues()
            self.createConfigJson()
            self.logger.debug(f"""browseConfigFile completed
                                  configFilePath: {configFilePath}
                                """)


    def mapConfigValues(self):
        self.userDataDirVar.set(self.config['userDataDir'])
        self.headlessVar.set(self.config['headless'])
        self.courseUrlsFilePathVar.set(self.config['courseUrlsFilePath'])
        self.saveDirectoryVar.set(self.config['saveDirectory'])
        self.loggingLevelVar.set(self.config['logger'])
        self.moduleTypeVar.set(self.config['moduleType'])
        self.isProxyVar.set(self.config['isProxy'])
        self.proxyVar.set(self.config['proxy'])
        self.fileTypeVar.set(self.config["fileType"])
        self.scraperTypeVar.set(self.config["scraperType"])
        self.scrapingMethodVar.set(self.config["scrapingMethod"])
        self.ucdriverVar.set(self.config["ucdriver"])
        self.autoResumeScraper.set(self.config["autoresume"])
        self.autoFixTextFile.set(self.config["autofixtextfile"])
        self.autoNextVar.set(self.config["autonext"])
        self.overwriteVar.set(self.config["overwrite"])


    def createConfigJson(self):
        self.configJson = {
            'userDataDir': self.userDataDirVar.get(),
            'headless': self.headlessVar.get(),
            'courseUrlsFilePath': self.courseUrlsFilePathVar.get(),
            'saveDirectory': self.saveDirectoryVar.get(),
            'logger': self.loggingLevelVar.get(),
            'moduleType': self.moduleTypeVar.get(),
            'isProxy': self.isProxyVar.get(),
            'proxy': self.proxyVar.get(),
            'scraperType': self.scraperTypeVar.get(),
            "scrapingMethod": self.scrapingMethodVar.get(),
            'fileType': self.fileTypeVar.get(),
            'ucdriver': self.ucdriverVar.get(),
            'binaryversion': self.config["binaryversion"],
            'autoresume': self.autoResumeScraper.get(),
            'autofixtextfile': self.autoFixTextFile.get(),
            'blockscraper': self.config["blockscraper"],
            'autonext': self.autoNextVar.get(),
            'overwrite': self.overwriteVar.get(),
            'useExtension': self.config["useExtension"]
        }


    def resetProgressBars(self):
        self.topicProgressVar.set(0)
        self.courseProgressVar.set(0)
        self.topicProgressBar.config(style="green.Horizontal.TProgressbar")
        self.courseProgressBar.config(style="green.Horizontal.TProgressbar")


    def extractStaticAssets(self):
        self.logger.debug("extractStaticAssets called")
        self.createConfigJson()
        if self.scraperTypeVar.get() != "API-JSON-Scraper":
            tk.messagebox.showinfo("Asset Tools", "Switch to API-JSON-Scraper to use asset tools.")
            return

        self.resetProgressBars()
        self.updateTextFromLog.setConfigExt(self.configJson)
        self.updateTextFromLog.setBlockScraper(True)
        self.process = multiprocessing.Process(
            name="AssetExtractor",
            target=run_static_asset_extractor,
            args=(self.configJson, None, self.progressQueue),
        )
        self.process.start()
        self.processes.append(self.process)
        self.updateButtonState()
        self.logger.debug("extractStaticAssets completed")


    def downloadStaticAssets(self):
        self.logger.debug("downloadStaticAssets called")
        self.createConfigJson()
        if self.scraperTypeVar.get() != "API-JSON-Scraper":
            tk.messagebox.showinfo("Asset Tools", "Switch to API-JSON-Scraper to use asset tools.")
            return

        self.resetProgressBars()
        self.updateTextFromLog.setConfigExt(self.configJson)
        self.updateTextFromLog.setBlockScraper(True)
        self.process = multiprocessing.Process(
            name="AssetDownloader",
            target=run_static_asset_downloader,
            args=(self.configJson, None, self.progressQueue),
        )
        self.process.start()
        self.processes.append(self.process)
        self.updateButtonState()
        self.logger.debug("downloadStaticAssets completed")


    def startScraper(self):
        self.logger.debug("startScraper called")
        self.createConfigJson()
        self.resetProgressBars()
        if self.clickedByUser:
            self.updateTextFromLog.setConfigExt(self.configJson)
            self.updateTextFromLog.setBlockScraper(False)
            self.updateTextFromLog.resetLastTopicUrlsList()
            if self.configJson['autofixtextfile'] and not self.updateTextFromLog.updateTextFileFromLogMain():
                self.logger.info("No URL found in log file. Starting Scraper from first url...")
        startScraper = StartScraper()
        self.process = multiprocessing.Process(name="Scraper", target=startScraper.start, args=(self.configJson, self.updateTextFromLog, self.progressQueue, ))
        self.process.start()
        self.processes.append(self.process)
        self.updateButtonState()
        self.logger.debug("startScraper completed")


    def startManualScraper(self):
        self.logger.debug("startManualScraper called")
        self.createConfigJson()
        if self.scraperTypeVar.get() == "API-JSON-Scraper":
            tk.messagebox.showinfo("Manual Scraper", "Manual scraper is disabled for API-JSON-Scraper.")
            return
        startScraper = StartScraper()
        self.process = multiprocessing.Process(name="ManualScraper", target=startScraper.startManual, args=(self.configJson, ))
        self.process.start()
        self.processes.append(self.process)
        self.updateManualScraperButtonState()
        self.logger.debug("startManualScraper completed")


    def loginAccount(self):
        self.logger.debug("loginAccount called")
        self.createConfigJson()
        self.updateTextFromLog.setConfigExt(self.configJson)
        self.updateTextFromLog.setBlockScraper(True)
        loginAccount = LoginAccount()
        self.process = multiprocessing.Process(name="LoginAccount", target=loginAccount.start, args=(self.configJson,))
        self.process.start()
        self.processes.append(self.process)
        self.updateButtonState()
        self.logger.debug("loginAccount completed")


    def terminateProcess(self):
        self.logger.debug("terminateProcess called")
        self.logger.info("Terminating Process...")
        self.updateTextFromLog.setConfigExt(self.configJson)
        self.updateTextFromLog.setBlockScraper(True)
        browserUtil = BrowserUtility(self.configJson)
        for process in self.processes:
            try:
                process.terminate()
                process.join()
            except psutil.NoSuchProcess:
                pass
        asyncio.get_event_loop().run_until_complete(browserUtil.shutdownChromeViaWebsocket())
        self.processes = []
        self.updateButtonState()
        self.logger.debug("terminateProcess completed")


    def updateButtonState(self, args=""):
        if self.process and self.process.name != "ManualScraper":
            if self.process.is_alive():
                self.EnableDisableButtons("disabled")
                self.terminateProcessButton.config(state="normal")
            else:
                self.EnableDisableButtons("normal")
                self.terminateProcessButton.config(state="disabled")
            self.checkButtonStateVar.set(self.startScraperButton['state'])
        if self.processes == []:
            self.EnableDisableButtons("normal")
            self.terminateProcessButton.config(state="disabled")
        self.app.after(1000, lambda: self.updateButtonState(args=args))


    def updateManualScraperButtonState(self):
        if self.scraperTypeVar.get() == "API-JSON-Scraper":
            self.startChromeDriverButton.config(state="disabled")
        elif self.process and self.process.name == "ManualScraper":
            if self.process.is_alive():
                self.startChromeDriverButton.config(state="disabled")
            else:
                self.startChromeDriverButton.config(state="normal")
        elif not self.processes:
            self.startChromeDriverButton.config(state="normal")
        self.app.after(1000, self.updateManualScraperButtonState)


    def EnableDisableButtons(self, state):
        self.downloadChromeDriverButton.config(state=state)
        self.downloadChromeBinaryButton.config(state=state)
        manual_state = "disabled" if self.scraperTypeVar.get() == "API-JSON-Scraper" else state
        self.startChromeDriverButton.config(state=manual_state)
        self.startScraperButton.config(state=state)
        self.loginAccountButton.config(state=state)
        if hasattr(self, "extractAssetsButton") and hasattr(self, "downloadAssetsButton"):
            if state == "disabled":
                self.extractAssetsButton.config(state="disabled")
                self.downloadAssetsButton.config(state="disabled")
            else:
                button_state = "normal" if self.scraperTypeVar.get() == "API-JSON-Scraper" else "disabled"
                self.extractAssetsButton.config(state=button_state)
                self.downloadAssetsButton.config(state=button_state)


    def startChromeDriver(self):
        self.logger.info(f"""  Starting Chrome Driver...
                                Path:  {constants.chromeDriverPath}
                          """)
        self.updateTextFromLog.setConfigExt(self.configJson)
        self.updateTextFromLog.setBlockScraper(True)
        StartChromedriver().loadChromeDriver()
        self.logger.debug("startChromeDriver completed")


    def loadDefaultConfig(self):
        self.configFilePath.set(constants.defaultConfigPath)
        self.config = self.configUtil.loadConfig()['ScraperConfig']
        self.mapConfigValues()
        self.createConfigJson()


    def deleteUserData(self):
        self.logger.debug("deleteUserData called")
        userDataDirPath = os.path.join(constants.OS_ROOT, self.userDataDirVar.get())
        if self.fileUtil.checkIfDirectoryExists(userDataDirPath):
            shutil.rmtree(userDataDirPath)
            self.logger.info(f"Deleted User Data Directory: {userDataDirPath}")


    def updateConfig(self):
        self.logger.debug("updateConfig called")
        self.createConfigJson()
        self.configUtil.updateConfig(self.configJson, 'ScraperConfig', self.configFilePath.get())
        self.logger.info(f"Updated Config with filePath: {self.configFilePath.get()}")


    def exportConfig(self):
        self.logger.debug("exportConfig called")
        self.createConfigJson()
        filePath = tk.filedialog.asksaveasfilename(defaultextension='.ini', filetypes=[('INI Files', '*.ini')],
                                                   title='Save Config File')
        if filePath:
            self.configUtil.updateConfig(self.configJson, 'ScraperConfig', filePath)
            self.logger.info(f"Exported Config with filePath: {filePath}")


    def downloadChromeDriver(self):
        self.updateTextFromLog.setConfigExt(self.configJson)
        self.updateTextFromLog.setBlockScraper(True)
        self.EnableDisableButtons("disabled")
        downloadThread = threading.Thread(target=lambda: self.downloadUtil.downloadChromeDriver(self.app,
                                                                                                self.topicProgressVar,
                                                                                                self.configJson))
        downloadThread.start()
        self.app.after(100, self.checkDownloadThread, downloadThread)


    def downloadChromeBinary(self):
        self.updateTextFromLog.setConfigExt(self.configJson)
        self.updateTextFromLog.setBlockScraper(True)
        self.EnableDisableButtons("disabled")
        downloadThread = threading.Thread(target=lambda: self.downloadUtil.downloadChromeBinary(self.app,
                                                                                                self.topicProgressVar,
                                                                                                self.configJson))
        downloadThread.start()
        self.app.after(100, self.checkDownloadThread, downloadThread)


    def checkDownloadThread(self, thread):
        if thread.is_alive():
            self.app.after(100, self.checkDownloadThread, thread)
        else:
            self.EnableDisableButtons("normal")
