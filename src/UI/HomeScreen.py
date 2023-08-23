import tkinter as tk
import tkinter.filedialog

from src.Common.Constants import constants
from src.Utility.ConfigUtility import ConfigUtility


class HomeScreen:
    def __init__(self):
        self.app = tk.Tk()
        self.app.geometry("500x600")
        self.app.title("Educative Scraper")
        self.configFilePath = tk.StringVar()
        self.configFilePath.set(constants.defaultConfigPath)

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

        self.configUtil = ConfigUtility()
        self.config = self.configUtil.loadConfig()
        self.mapConfigValues()


    def createHomeScreen(self):

        # Config File Path
        configFilePathFrame = tk.Frame(self.app)
        configFilePathLabel = tk.Label(configFilePathFrame, text="Config File Path:")
        configFileTextBox = tk.Entry(configFilePathFrame, textvariable=self.configFilePath, width=50)
        browseConfigFileButton = tk.Button(configFilePathFrame, text="...", command=self.browseConfigFile)

        configFilePathLabel.pack(side="left")
        configFileTextBox.pack(side="left", fill="x", expand=True)
        browseConfigFileButton.pack(side="left")
        configFilePathFrame.pack(pady=(20, 0), padx=10, anchor="w")

        # Checkboxes
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

        # Course URLs File Path and Save Directory
        entriesFrame = tk.Frame(self.app)
        courseUrlsFilePathLabel = tk.Label(entriesFrame, text="Course URLs File Path:")
        courseUrlsFilePathEntry = tk.Entry(entriesFrame, textvariable=self.courseUrlsFilePathVar, width=50)
        courseUrlsFilePathButton = tk.Button(entriesFrame, text="...", command=self.browseCourseUrlsFile)
        saveDirectoryLabel = tk.Label(entriesFrame, text="Save Directory:")
        saveDirectoryEntry = tk.Entry(entriesFrame, textvariable=self.saveDirectoryVar, width=50)
        saveDirectoryButton = tk.Button(entriesFrame, text="...", command=self.browseSaveDirectory)

        courseUrlsFilePathLabel.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        courseUrlsFilePathEntry.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        courseUrlsFilePathButton.grid(row=0, column=2, padx=5)
        saveDirectoryLabel.grid(row=1, column=0, sticky="w", padx=10, pady=5)
        saveDirectoryEntry.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        saveDirectoryButton.grid(row=1, column=2, padx=5)

        entriesFrame.pack(pady=10, padx=10, anchor="w")

        # Start Scraper Button
        startScraperButton = tk.Button(self.app, text="Start Scraper", command=self.startScraper)
        startScraperButton.pack(pady=(20, 0))

        # Start the Tkinter main loop
        self.app.mainloop()


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
            self.config = self.configUtil.loadConfig(configFilePath)
            self.mapConfigValues()


    def mapConfigValues(self):
        self.headlessVar.set(self.config['Headless'])
        self.courseUrlsFilePathVar.set(self.config['CourseUrlsFilePath'])
        self.saveDirectoryVar.set(self.config['SaveDirectory'])
        self.singleFileHTMLVar.set(self.config['SingleFileHTML'])
        self.fullPageScreenshotHTMLVar.set(self.config['FullPageScreenshotHTML'])
        self.openSlidesVar.set(self.config['OpenSlides'])
        self.openMarkdownQuizVar.set(self.config['OpenMarkdownQuiz'])
        self.openHintsVar.set(self.config['OpenHints'])
        self.openSolutionsVar.set(self.config['OpenSolutions'])
        self.unMarkAsCompletedVar.set(self.config['UnMarkAsCompleted'])
        self.scrapeQuizVar.set(self.config['ScrapeQuiz'])
        self.scrapeCodesVar.set(self.config['ScrapeCodes'])
        self.loggerVar.set(self.config['Logger'])


    def startScraper(self):
        headless = self.headlessVar.get()
        courseUrlsFilePath = self.courseUrlsFilePathVar.get()
        saveDirectory = self.saveDirectoryVar.get()
        singleFileHTML = self.singleFileHTMLVar.get()
        fullPageScreenshotHTML = self.fullPageScreenshotHTMLVar.get()
        openSlides = self.openSlidesVar.get()
        openMarkdownQuiz = self.openMarkdownQuizVar.get()
        openHints = self.openHintsVar.get()
        openSolutions = self.openSolutionsVar.get()
        unMarkAsCompleted = self.unMarkAsCompletedVar.get()
        scrapeQuiz = self.scrapeQuizVar.get()
        scrapeCodes = self.scrapeCodesVar.get()
        logger = self.loggerVar.get()

        # Replace this with your actual scraper code
        print(f"Headless: {headless}")
        print(f"Course URLs File Path: {courseUrlsFilePath}")
        print(f"Save Directory: {saveDirectory}")
        print(f"Single File HTML: {singleFileHTML}")
        print(f"Full Page Screenshot HTML: {fullPageScreenshotHTML}")
        print(f"Open Slides: {openSlides}")
        print(f"Open Markdown Quiz: {openMarkdownQuiz}")
        print(f"Open Hints: {openHints}")
        print(f"Open Solutions: {openSolutions}")
        print(f"Unmark as Completed: {unMarkAsCompleted}")
        print(f"Scrape Quiz: {scrapeQuiz}")
        print(f"Scrape Codes: {scrapeCodes}")
        print(f"Logger: {logger}")
