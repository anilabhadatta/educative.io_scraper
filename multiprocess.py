'''Create a virtual environment named env or else this script won't work
   Make sure you have xterm or uxterm or gnome-terminal installed in your Linux OS.
'''

from multiprocessing import Process
import multiprocessing
import os
import subprocess
import sys
import signal
import psutil
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_chromdriver_pid():
    PROCNAME = "chromedriver"
    for proc in psutil.process_iter():
        if PROCNAME in proc.name():
            return proc.pid


def get_binary_path():
    current_os = sys.platform
    if current_os.startswith('darwin'):
        chromedriver = r'mac/chromedriver'
        scraper_path = os.path.join(
            ROOT_DIR, "env/bin/python3")
    elif current_os.startswith('linux'):
        chromedriver = r'linux/chromedriver'
        scraper_path = os.path.join(
            ROOT_DIR, "env/bin/python3")
    elif current_os.startswith('win32') or current_os.startswith('cygwin'):
        chromedriver = r'win\chromedriver.exe'
        scraper_path = os.path.join(
            ROOT_DIR, r"env\Scripts\python.exe")

    return chromedriver, scraper_path


def load_chromedriver():
    try:
        current_os = sys.platform
        chromedriver, _ = get_binary_path()
        chromedriver_path = os.path.join(
            ROOT_DIR, "Chrome-driver", chromedriver)
        if current_os.startswith('win32') or current_os.startswith('cygwin'):
            subprocess.run(chromedriver_path,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        elif current_os.startswith('darwin'):
            subprocess.run(["open", "-a", "Terminal", chromedriver_path])
        elif current_os.startswith('linux'):
            subprocess.check_call(['chmod', 'u+x', chromedriver_path])
            try:
                try:
                    subprocess.run(['xterm', '-e', chromedriver_path])
                except Exception:
                    subprocess.run(['uxterm', '-e', chromedriver_path])
            except Exception:
                subprocess.run(['gnome-terminal', '--', chromedriver_path])
    except KeyboardInterrupt:
        pass


def initiate_scraper_process():
    try:
        _, scraper_path = get_binary_path()
        file_path = os.path.join(ROOT_DIR, "educative_scraper.py")

        if sys.platform.startswith('linux'):
            subprocess.check_call(['chmod', 'u+x', file_path])
            try:
                try:
                    subprocess.run(['xterm', '-e', scraper_path, file_path])
                except Exception:
                    subprocess.run(['uxterm', '-e', scraper_path, file_path])
            except Exception:
                subprocess.Popen(
                    ['gnome-terminal', '--', scraper_path, file_path])
        else:
            subprocess.run([scraper_path, file_path])
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    multiprocessing.freeze_support()
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
    except KeyboardInterrupt:
        sys.exit()
