import subprocess
import sys

from src.Common.Constants import constants


class StartChromedriver:
    def __init__(self):
        self.currentOS = sys.platform


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
        if self.currentOS.startswith('win32') or self.currentOS.startswith('cygwin'):
            subprocess.Popen(
                ["start", "cmd", "/k", constants.chromeDriverPath], shell=True)
        else:
            subprocess.check_call(['chmod', 'u+x', constants.chromeDriverPath])
            subprocess.check_call(['chmod', 'u+x', constants.chromeBinaryPath])
            if self.currentOS.startswith('darwin'):
                subprocess.Popen(["open", "-a", "Terminal", constants.chromeDriverPath])
            elif self.currentOS.startswith('linux'):
                subprocess.Popen([self.getDefaultLinuxTerminal(), "-e", constants.chromeDriverPath])
