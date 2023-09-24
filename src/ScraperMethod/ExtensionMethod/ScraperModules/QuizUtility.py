import os

from src.Logging.Logger import Logger
from src.Utility.FileUtility import FileUtility


class QuizUtility:
    def __init__(self, configJson):
        self.generatedText = None
        self.component = None
        self.quizFolderPath = None
        self.fileUtils = FileUtility()
        self.configJson = configJson
        self.logger = Logger(configJson, "QuizUtility").logger


    def downloadQuizFiles(self, courseTopicPath, component, componentIndex):
        try:
            self.component = component
            if "StructuredQuiz" in component["type"]:
                self.quizFolderPath = os.path.join(courseTopicPath, f"MarkDownQuiz")
                self.downloadMarkdownQuizFiles()
            elif "Quiz" in component["type"]:
                self.quizFolderPath = os.path.join(courseTopicPath, f"Quiz")
                self.downloadQuiz()

            self.fileUtils.createFolderIfNotExists(self.quizFolderPath)
            textFilePath = os.path.join(self.quizFolderPath, f"Quiz-{componentIndex + 1}.txt")
            self.fileUtils.createTextFile(textFilePath, self.generatedText)
            self.logger.info(f"Quiz Downloaded at: {textFilePath}")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"QuizUtility:downloadQuizFiles: {lineNumber}: {e}")


    def downloadMarkdownQuizFiles(self):
        try:
            self.logger.info("Downloading MarkDown Quiz...")
            content = self.component["content"]
            questions = content["questions"]
            self.generatedText = ""
            for questionIndex, question in enumerate(questions):
                questionText = question["questionText"]
                answerText = question["answerText"]
                self.generatedText += f"""
## Question {questionIndex + 1}
{questionText}
### Answer
{answerText}
---------------------------------------
"""
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"QuizUtility:downloadMarkdownQuizFiles: {lineNumber}: {e}")


    def downloadQuiz(self):
        try:
            self.logger.info("Downloading Quiz...")
            content = self.component["content"]
            questions = content["questions"]
            self.generatedText = ""
            for questionIndex, question in enumerate(questions):
                questionText = question["questionText"]
                questionOptions = question["questionOptions"]
                questionOptionsText = ""
                for optionIndex, option in enumerate(questionOptions):
                    optionText = option["text"]
                    explanation = option["explanation"]["mdText"]
                    correct = "Correct" if option["correct"] else "Incorrect"
                    questionOptionsText += f"""
{optionIndex + 1}. {optionText}
{correct}
{explanation}
----------------------------
"""
                self.generatedText += f"""
## Question {questionIndex + 1}
{questionText}
### Options
{questionOptionsText}
---------------------------------------------
"""
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"QuizUtility:downloadQuiz: {lineNumber}: {e}")
