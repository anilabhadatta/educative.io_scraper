import platform

class OSUtility:
    def __init__(self):
        self.currentOS = platform.system()
        self.architecture = platform.architecture()[0]
        self.machineType = platform.machine().lower()
        self.osSuffix, self.osFriendlyShortName = self.getCurrentOSInfo()

    def getCurrentOSInfo(self):
        os_info = {
            ("Linux", "64bit"): ("linux64", "Linux"),
            ("Linux", "arm64"): ("linux-arm64", "Linux"),
            ("Darwin", "64bit"): ("mac-x64", "macOS"),
            ("Darwin", "arm64"): ("mac-arm64", "macOS"),
            ("Windows", "64bit"): ("win64", "Windows"),
            ("Windows", "32bit"): ("win32", "Windows")
        }
        return os_info.get((self.currentOS, self.architecture), (None, None))