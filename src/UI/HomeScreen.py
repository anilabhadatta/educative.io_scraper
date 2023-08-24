import os
import shutil
import sys
import tkinter as tk
import tkinter.filedialog
from tkinter import ttk

from src.Common.Constants import constants
from src.Main.StartChromedriver import StartChromedriver
from src.Utility.ConfigUtility import ConfigUtility
from src.Utility.DownloadUtility import DownloadUtility
from src.Utility.FileUtility import FileUtility


class HomeScreen:
    def __init__(self):
        self.configJson = None
        self.currentOS = sys.platform
        self.app = tk.Tk()
        self.app.geometry("400x400")
        self.app.title("Educative Scraper")
        self.configFilePath = tk.StringVar()
        self.configFilePath.set(constants.defaultConfigPath)

        self.userDataDirVar = tk.StringVar()
        self.headlessVar = tk.BooleanVar(value=False)
        self.courseUrlsFilePathVar = tk.StringVar()
        self.saveDirectoryVar = tk.StringVar()
        self.singleFileHTMLVar = tk.BooleanVar(value=True)
        self.fullPageScreenshotHTMLVar = tk.BooleanVar(value=True)
        self.openSlidesVar = tk.BooleanVar(value=True)
        self.openMarkdownQuizVar = tk.BooleanVar(value=True)
        self.openHintsVar = tk.BooleanVar(value=True)
        self.openSolutionsVar = tk.BooleanVar(value=True)
        self.unMarkAsCompletedVar = tk.BooleanVar(value=True)
        self.scrapeQuizVar = tk.BooleanVar(value=True)
        self.scrapeCodesVar = tk.BooleanVar(value=True)
        self.loggerVar = tk.BooleanVar(value=True)
        self.progressVar = tk.DoubleVar()

        self.configUtil = ConfigUtility()
        self.config = self.configUtil.loadConfig()['ScraperConfig']
        self.mapConfigValues()
        self.fileUtil = FileUtility()
        self.downloadUtil = DownloadUtility()
        self.pythonExecutable = sys.executable


    def createHomeScreen(self):
        configFilePathFrame = tk.Frame(self.app)
        configFilePathLabel = tk.Label(configFilePathFrame, text="Config File Path:")
        configFileTextBox = tk.Entry(configFilePathFrame, textvariable=self.configFilePath, width=60)
        browseConfigFileButton = tk.Button(configFilePathFrame, text="...", command=self.browseConfigFile)

        configFilePathLabel.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        configFileTextBox.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        browseConfigFileButton.grid(row=0, column=2, padx=2)
        configFilePathFrame.pack(pady=10, padx=10, anchor="w")

        checkboxesFrame = tk.Frame(self.app)
        optionCheckboxes = [
            ("Headless", self.headlessVar),
            ("Single File HTML", self.singleFileHTMLVar),
            ("Full Page Screenshot HTML", self.fullPageScreenshotHTMLVar),
            ("Open Slides", self.openSlidesVar),
            ("Open Markdown Quiz", self.openMarkdownQuizVar),
            ("Open Hints", self.openHintsVar),
            ("Open Solutions", self.openSolutionsVar),
            ("Unmark As Completed", self.unMarkAsCompletedVar),
            ("Scrape Quiz", self.scrapeQuizVar),
            ("Scrape Codes", self.scrapeCodesVar),
            ("Logger", self.loggerVar)
        ]

        for optionText, optionVar in optionCheckboxes:
            checkbox = tk.Checkbutton(checkboxesFrame, text=optionText, variable=optionVar, wraplength=400, anchor="w")
            checkbox.pack(anchor="w", padx=10)

        checkboxesFrame.pack(pady=10, padx=10, anchor="w")

        entriesFrame = tk.Frame(self.app)
        userDataDirLabel = tk.Label(entriesFrame, text="User Data Directory:")
        userDataDirEntry = tk.Entry(entriesFrame, textvariable=self.userDataDirVar, width=55)
        courseUrlsFilePathLabel = tk.Label(entriesFrame, text="Course URLs File Path:")
        courseUrlsFilePathEntry = tk.Entry(entriesFrame, textvariable=self.courseUrlsFilePathVar, width=55)
        courseUrlsFilePathButton = tk.Button(entriesFrame, text="...", command=self.browseCourseUrlsFile)
        saveDirectoryLabel = tk.Label(entriesFrame, text="Save Directory:")
        saveDirectoryEntry = tk.Entry(entriesFrame, textvariable=self.saveDirectoryVar, width=55)
        saveDirectoryButton = tk.Button(entriesFrame, text="...", command=self.browseSaveDirectory)

        userDataDirLabel.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        userDataDirEntry.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        courseUrlsFilePathLabel.grid(row=1, column=0, sticky="w", padx=2, pady=2)
        courseUrlsFilePathEntry.grid(row=1, column=1, sticky="w", padx=2, pady=2)
        courseUrlsFilePathButton.grid(row=1, column=2, padx=2)
        saveDirectoryLabel.grid(row=2, column=0, sticky="w", padx=2, pady=2)
        saveDirectoryEntry.grid(row=2, column=1, sticky="w", padx=2, pady=2)
        saveDirectoryButton.grid(row=2, column=2, padx=2)
        entriesFrame.pack(pady=10, padx=10, anchor="w")

        buttonConfigFrame = tk.Frame(self.app)
        updateConfigButton = tk.Button(buttonConfigFrame, text="Update Config", command=self.updateConfig)
        exportConfigButton = tk.Button(buttonConfigFrame, text="Export Config", command=self.exportConfig)
        deleteUserDataButton = tk.Button(buttonConfigFrame, text="Delete User Data", command=self.deleteUserData)

        updateConfigButton.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        exportConfigButton.grid(row=0, column=2, sticky="w", padx=2, pady=2)
        deleteUserDataButton.grid(row=0, column=3, sticky="w", padx=2, pady=2)
        buttonConfigFrame.pack(pady=20, padx=100, anchor="w")

        buttonScraperFrame = tk.Frame(self.app)
        downloadChromeDriverButton = tk.Button(buttonScraperFrame, text="Download Chrome Driver",
                                               command=lambda: self.downloadUtil.downloadChromeDriver(self.app,
                                                                                                      self.progressVar))
        downloadChromeBinaryButton = tk.Button(buttonScraperFrame, text="Download Chrome Binary",
                                               command=lambda: self.downloadUtil.downloadChromeBinary(self.app,
                                                                                                      self.progressVar))
        startChromeDriverButton = tk.Button(buttonScraperFrame, text="Start Chrome Driver",
                                            command=self.startChromeDriver, width=19)
        startScraperButton = tk.Button(buttonScraperFrame, text="Start Scraper", command=self.startScraper, width=20)

        downloadChromeDriverButton.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        downloadChromeBinaryButton.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        startChromeDriverButton.grid(row=1, column=0, sticky="w", padx=2, pady=2)
        startScraperButton.grid(row=1, column=1, sticky="w", padx=2, pady=2)
        buttonScraperFrame.pack(pady=20, padx=100, anchor="w")

        progressBarFrame = tk.Frame(self.app)
        downloadProgressLabel = tk.Label(progressBarFrame, text="Download Progress:")
        progressBar = ttk.Progressbar(progressBarFrame, length=380, mode="determinate", variable=self.progressVar)
        downloadProgressLabel.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        progressBar.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        progressBarFrame.pack(pady=2)

        self.fixGeometry()
        self.app.mainloop()


    def fixGeometry(self):
        self.app.update_idletasks()
        width = self.app.winfo_reqwidth()
        height = self.app.winfo_reqheight()

        screen_width = self.app.winfo_screenwidth()
        screen_height = self.app.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.app.geometry(f"{width}x{height}+{x}+{y}")


    def browseCourseUrlsFile(self):
        courseUrlsFilePath = tk.filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt")])
        if courseUrlsFilePath:
            self.courseUrlsFilePathVar.set(courseUrlsFilePath)


    def browseSaveDirectory(self):
        saveDirectoryPath = tk.filedialog.askdirectory()
        if saveDirectoryPath:
            self.saveDirectoryVar.set(saveDirectoryPath)


    def browseConfigFile(self):
        configFilePath = tk.filedialog.askopenfilename(
            filetypes=[("INI Files", "*.ini")])
        if configFilePath:
            self.configFilePath.set(configFilePath)
            self.config = self.configUtil.loadConfig(configFilePath)['ScraperConfig']
            self.mapConfigValues()


    def mapConfigValues(self):
        self.userDataDirVar.set(self.config['userDataDir'])
        self.headlessVar.set(self.config['headless'])
        self.courseUrlsFilePathVar.set(self.config['courseUrlsFilePath'])
        self.saveDirectoryVar.set(self.config['saveDirectory'])
        self.singleFileHTMLVar.set(self.config['singleFileHTML'])
        self.fullPageScreenshotHTMLVar.set(self.config['fullPageScreenshotHTML'])
        self.openSlidesVar.set(self.config['openSlides'])
        self.openMarkdownQuizVar.set(self.config['openMarkdownQuiz'])
        self.openHintsVar.set(self.config['openHints'])
        self.openSolutionsVar.set(self.config['openSolutions'])
        self.unMarkAsCompletedVar.set(self.config['unMarkAsCompleted'])
        self.scrapeQuizVar.set(self.config['scrapeQuiz'])
        self.scrapeCodesVar.set(self.config['scrapeCodes'])
        self.loggerVar.set(self.config['logger'])


    def createConfigJson(self):
        self.configJson = {
            'userDataDir': self.userDataDirVar.get(),
            'headless': self.headlessVar.get(),
            'courseUrlsFilePath': self.courseUrlsFilePathVar.get(),
            'saveDirectory': self.saveDirectoryVar.get(),
            'singleFileHTML': self.singleFileHTMLVar.get(),
            'fullPageScreenshotHTML': self.fullPageScreenshotHTMLVar.get(),
            'openSlides': self.openSlidesVar.get(),
            'openMarkdownQuiz': self.openMarkdownQuizVar.get(),
            'openHints': self.openHintsVar.get(),
            'openSolutions': self.openSolutionsVar.get(),
            'unMarkAsCompleted': self.unMarkAsCompletedVar.get(),
            'scrapeQuiz': self.scrapeQuizVar.get(),
            'scrapeCodes': self.scrapeCodesVar.get(),
            'logger': self.loggerVar.get()
        }


    def startScraper(self):
        self.createConfigJson()
        print(self.createConfigJson())


    @staticmethod
    def startChromeDriver():
        print("Starting Chrome Driver", constants.chromeDriverPath)
        StartChromedriver().loadChromeDriver()


    def deleteUserData(self):
        userDataDirPath = os.path.join(constants.OS_ROOT, self.userDataDirVar.get())
        if self.fileUtil.checkIfDirectoryExists(userDataDirPath):
            shutil.rmtree(userDataDirPath)


    def updateConfig(self):
        self.createConfigJson()
        self.configUtil.updateConfig(self.configJson, self.configFilePath.get())


    def exportConfig(self):
        self.createConfigJson()
        filePath = tk.filedialog.asksaveasfilename(defaultextension='.ini', filetypes=[('INI Files', '*.ini')],
                                                   title='Save Config File')
        self.configUtil.updateConfig(self.configJson, filePath)
