from multiprocessing import Process
import multiprocessing
import os
import subprocess
import sys
import signal
import psutil


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
pyinstaller_build = ""


def get_chromdriver_pid():
    PROCNAME = "chromedriver"
    for proc in psutil.process_iter():
        if PROCNAME in proc.name():
            return proc.pid


def get_binary_path():
    current_os = sys.platform
    if current_os.startswith('darwin'):
        chromedriver = r'mac/chromedriver'
        pyinstaller_build = os.path.join(
            ROOT_DIR, "dist", "educative_scraper")
    elif current_os.startswith('linux'):
        chromedriver = r'linux/chromedriver'
        pyinstaller_build = os.path.join(
            ROOT_DIR, "dist", "educative_scraper")
    elif current_os.startswith('win32') or current_os.startswith('cygwin'):
        multiprocessing.freeze_support()
        chromedriver = r'win\chromedriver.exe'
        pyinstaller_build = os.path.join(
            ROOT_DIR, "dist", "educative_scraper.exe")
    return chromedriver, pyinstaller_build


def load_chromedriver():
    try:
        chromedriver, _ = get_binary_path()
        chromedriver_path = os.path.join(
            ROOT_DIR, "Chrome-driver", chromedriver)
        subprocess.run(f"{chromedriver_path} --port=9515",
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except KeyboardInterrupt:
        pass


def initiate_scraper_process():
    global pyinstaller_build
    try:
        '''For Pyinstaller
        _, scraper_path = get_binary_path()'''

        '''For Manual Python Execution'''
        scraper_path = "python " + \
            os.path.join(ROOT_DIR, "educative_scraper.py")
        subprocess.run(scraper_path, shell=True)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    get_binary_path()
    chromedriver_process = Process(target=load_chromedriver)
    scraper_process = Process(target=initiate_scraper_process)
    chromedriver_process.start()
    scraper_process.start()
    try:
        scraper_process.join()
        if scraper_process.exitcode == 0:
            os.kill(get_chromdriver_pid(), signal.SIGTERM)
            chromedriver_process.terminate()
    except KeyboardInterrupt:
        scraper_process.join()
        if scraper_process.exitcode == 0:
            os.kill(get_chromdriver_pid(), signal.SIGTERM)
            chromedriver_process.terminate()
