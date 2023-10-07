import platform


class OSUtility:
    def __init__(self):
        self.currentOS = platform.system()
        self.architecture = platform.architecture()[0]
        self.machineType = platform.machine().lower()
        self.osSuffix = self.getOSSuffix()
        self.osFriendlyShortName = self.getOSFriendlyShortName()

    def getOSSuffix(self):
        os_suffixes = {
            "Linux": {
                "aarch64": "linux-arm64",
                "arm": "linux-arm64",
                "64bit": "linux64"
            },
            "Darwin": {
                "arm": "mac-arm64",
                "64bit": "mac-x64"
            },
            "Windows": {
                "64bit": "win64",
                "32bit": "win32"
            }
        }
        for key, value in os_suffixes.get(self.currentOS, {}).items():
            if key in (self.machineType, self.architecture):
                return value
        return None

    def getOSFriendlyShortName(self):
        friendly_names = {
            "Linux": "linux",
            "Darwin": "mac",
            "Windows": "win"
        }
        return friendly_names.get(self.currentOS, None)