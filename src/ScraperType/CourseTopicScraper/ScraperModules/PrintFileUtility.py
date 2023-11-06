import base64
import os
import io

from src.Logging.Logger import Logger
from src.ScraperType.CourseTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility

from pypdf import PdfWriter, PdfReader, PageObject, Transformation

class PrintFileUtility:
    def __init__(self, configJson):
        self.browser = None
        self.osUtils = OSUtility(configJson)
        self.fileUtils = FileUtility()
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)
        self.logger = Logger(configJson, "PrintFileUtility").logger


    def printPdfAsCdp(self, topicName):
        self.logger.info(f"printPdfAsCdp: Getting Full page PDF data for {topicName}")
        params = {
            "landscape": False,
            "displayHeaderFooter": True,
            "printBackground": True,
            "marginsType": 1,
            'paperWidth': 8.27,
            'paperHeight': 11.69,
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0
        }
        self.seleniumBasicUtils.browser = self.browser
        try:
            pageData = self.seleniumBasicUtils.sendCommand("Page.printToPDF", params)
            self.osUtils.sleep(2)
            pageData = base64.b64decode(pageData['data'])
            pdfBinaryData = io.BytesIO(pageData)
            return self.mergePdfPages(pdfBinaryData)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"PrintFileUtility:printPdfAsCdp: {lineNumber}: {e}")


    def mergePdfPages(self, pdfBinaryData):
        try:
            reader = PdfReader(pdfBinaryData)
            pagesLength = len(reader.pages)
            page1 = reader.pages[0]
            width = page1.mediabox.right
            height = page1.mediabox.top * pagesLength
            originalHeight = page1.mediabox.top
            newPage = PageObject.create_blank_page(None, width, height)
            for pageNum in range(pagesLength):
                page = reader.pages[pageNum]
                page.add_transformation(Transformation().translate(0, originalHeight * (pagesLength - pageNum - 1)))
                page.mediabox = newPage.mediabox
                newPage.merge_page(page)
            outputPdf = PdfWriter()
            outputPdf.add_page(newPage)
            return outputPdf
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"PrintFileUtility:mergePdfPages: {lineNumber}: {e}")