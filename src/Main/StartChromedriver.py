import platform
import subprocess

from src.Common.Constants import constants


class StartChromedriver:
    def __init__(self):
        self.currentOS = platform.system()


    @staticmethod
    def getDefaultLinuxTerminal():
        terminals = ['gnome-terminal', 'xfce4-terminal', 'konsole', 'xterm', 'lxterminal', 'mate-terminal', 'urxvt',
                     'alacritty', 'termite']

        for terminal in terminals:
            try:
                subprocess.run(['which', terminal], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
                return terminal
            except subprocess.CalledProcessError:
                pass
        return None


    def loadChromeDriver(self):
        if self.currentOS == "Windows":
            subprocess.Popen(["start", "cmd", "/k", constants.chromeDriverPath], shell=True)
        else:
            if self.currentOS == "Darwin":
                subprocess.Popen(["open", "-a", "Terminal", constants.chromeDriverPath])
            elif self.currentOS == "Linux":
                subprocess.Popen([self.getDefaultLinuxTerminal(), "-e", constants.chromeDriverPath])
