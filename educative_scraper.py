from time import sleep
from selenium.webdriver.common.by import By
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
'''
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
'''
from selenium.webdriver.common.keys import Keys
from slugify import slugify
import glob
import zipfile
import json

OS_ROOT = os.path.expanduser('~')
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    if ".educative_scraper_config" not in os.listdir(OS_ROOT):
        raise Exception("No config found, Please create one")
    with open(os.path.join(OS_ROOT, ".educative_scraper_config", "config.json"), "r") as config_file:
        config = json.load(config_file)
    if "user_data_dir" not in config or "chrome_exe" not in config or "url_file_path" not in config or "save_path" not in config:
        raise Exception("Config is corrupted, Please recreate the config")
    user_data_dir = os.path.join(OS_ROOT, f"User Data")
    chrome_exe = ROOT_DIR
    # user_data_dir = config["user_data_dir"]
    # chrome_exe = config["chrome_exe"]
    url_text_file = config["url_file_path"]
    save_path = config["save_path"]
    return user_data_dir, chrome_exe, url_text_file, save_path


def load_chrome_driver(headless=True):
    global chromedriver, chrome_os
    user_data_dir, chrome_exe, _, _ = load_config()
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('headless')
    options.add_argument(f'user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')
    options.add_argument("--start-maximized")
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--log-level=3')
    userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.56 Safari/537.36"
    options.add_argument(f'user-agent={userAgent}')
    options.binary_location = os.path.join(chrome_exe, chrome_os)
    driver = webdriver.Chrome(service=ChromeService(
        os.path.join(f"{ROOT_DIR}", f"{chromedriver}")), options=options)
    driver.set_window_size(1920, 1080)
    driver.command_executor._commands["send_command"] = (
        "POST", '/session/$sessionId/chromium/send_command')
    print("Driver Loaded")
    return driver


r"""
# Firefox has issues with screenshots being too large
def load_firefox_driver(headless):
    profile_path = r'C:\Users\anila\AppData\Roaming\Mozilla\Firefox\Profiles\Educative'
    options = FirefoxOptions()
    options.add_argument("-profile")
    options.add_argument(profile_path)
    if headless:
        options.add_argument("-headless")
    driver = webdriver.Firefox(
        options=options, service=FirefoxService(GeckoDriverManager().install()))
    return driver
"""


def create_course_folder(driver):
    print("Create Course Folder Function")
    course_name_class = "mb-4 px-6"

    course_name = slugify(driver.find_element(
        By.CSS_SELECTOR, f"h4[class='{course_name_class}']").get_attribute('innerHTML'))
    if course_name not in os.listdir():
        print("Created a folder")
        os.mkdir(course_name)
    os.chdir(course_name)
    print("Inside Course Folder")


def next_page(driver):
    print("Next Page Function")
    next_page_class = "outlined-primary m-0"

    if not driver.find_elements(By.CSS_SELECTOR, f"button[class='{next_page_class}']"):
        return False
    base_js_cmd = f'''document.getElementsByClassName("{next_page_class}")[0]'''
    check_next_module = driver.execute_script(
        '''return ''' + base_js_cmd + '''.innerHTML.slice(0,11);''')
    if check_next_module == "Next Module":
        return False
    driver.execute_script(base_js_cmd + '''.click()''')
    print("Next Page")
    return True


def open_slides(driver):
    print("Finding Slides Function")
    slidebox_class = "text-center block"
    menubar_class = "styles__ButtonsWrap-sc-8tvqhb-5"
    button_class = "Button-sc-1i9ny0d-0"

    total_slides = driver.find_elements(
        By.CSS_SELECTOR, f"div[class*='{slidebox_class}']")
    if total_slides:
        for slide in total_slides:
            slide = slide.find_elements(
                By.CSS_SELECTOR, f"div[class*='{menubar_class}']")
            if slide:
                slide[0].find_elements(
                    By.CSS_SELECTOR, f"button[class*='{button_class}']")[-2].click()
                print("Slides opened")
        sleep(10)
    else:
        print("No Slides Found")


def get_file_name(driver):
    print("Getting File Name")
    '''
    # Depreciated this part as it is not working
    primary_heading_class = "mt-10"
    secondary_heading_class = "text-3xl"

    primary_heading_list = driver.find_elements(
        By.CSS_SELECTOR, f"h1[class*='{primary_heading_class}']")
    file_name = ""
    if primary_heading_list:
        if primary_heading_list[0] != "":
            file_name = primary_heading_list[0].get_attribute('innerHTML')
    else:
        file_name = driver.find_element(
            By.CSS_SELECTOR, f"h1[class*='{secondary_heading_class}']").get_attribute('innerHTML')
    '''
    heading_class = "flex flex-col"

    heading_element = driver.find_element(
        By.XPATH, f"//div[contains(@class,'{heading_class}')]//descendant::node()[1]")
    file_name = heading_element.get_attribute('innerHTML')
    print("File Name Found")
    return slugify(file_name)


def delete_node(driver, node):
    driver.execute_script(f"""
                            var element = document.querySelector("{node}");
                            if (element)
                                element.parentNode.removeChild(element);
                            """)
    sleep(1)


def get_current_height(driver):
    return driver.execute_script('return document.body.parentNode.scrollHeight')


def increase_window_size(driver):
    driver.execute_script(f"window.scrollTo(0,{get_current_height(driver)})")
    sleep(2)
    driver.set_window_size(1920, get_current_height(driver))
    sleep(2)
    driver.set_window_size(1920, get_current_height(driver))
    sleep(2)


def create_html(file_name, base_64_png):
    with open(file_name + ".html", "w+") as fh:
        fh.write(f'''
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <title>{file_name}</title>
                </head>
                <body style="zoom: 80%">
                    <div style="text-align: center">
                        <img src="data:image/png;base64,{base_64_png}" alt="">
                    </div>
                </body>
                </html>
            ''')
    sleep(1)


def take_screenshot(driver, file_name):
    print("Take Screenshot Function")
    page_class = "PageContent-sc-8tufop-0"
    main_class = "ed-grid"
    nav_node = f"div[class*='{main_class}'] > nav"

    delete_node(driver, nav_node)
    increase_window_size(driver)
    base_64_png = driver.find_element(
        By.CSS_SELECTOR, f"div[class*='{page_class}']").screenshot_as_base64
    sleep(2)
    create_html(file_name, base_64_png)
    driver.set_window_size(1920, 1080)
    print("Screenshot taken and HTML File generated")


def show_hints_answer(driver):
    print("Show Hints Function")
    hints_button_class = "whitespace-normal outlined-default m-0"
    hints_list = driver.find_elements(
        By.CSS_SELECTOR, f"button[class*='{hints_button_class}']")
    if hints_list:
        for hints in hints_list:
            hints.click()
            sleep(1)
        print("Show Hints Complete")
    else:
        print("No hints found")


def show_code_box_answer(driver):
    print("Show Codebox Answers Function")
    sol1 = "solution"
    sol2 = "show solution"
    show_solution_class = "text-default py-2 m-2"
    answer_list = driver.find_elements(By.CSS_SELECTOR,
                                       f'button[aria-label="{sol1}"]') + driver.find_elements(By.CSS_SELECTOR, f'button[aria-label="{sol2}"]')
    if answer_list:
        for answer in answer_list:
            answer.click()
            sleep(1)
            driver.find_element(
                By.CSS_SELECTOR, f"button[class*='{show_solution_class}']").click()
            sleep(1)
        print("Show Codebox Answers Complete")
    else:
        print("No Codebox answers found")


def create_temp_textarea(driver):
    driver.execute_script('''
        var div = document.getElementsByClassName("ed-grid-main")[0];
                var input = document.createElement("textarea");
                input.name = "temptextarea";
                input.className = "temptextarea";
                input.maxLength = "10000";
                input.cols = "50";
                input.rows = "10";
                div.appendChild(input);
    ''')
    sleep(1)


def create_folder(folder_name):
    if folder_name not in os.listdir():
        os.mkdir(folder_name)
    os.chdir(folder_name)


def download_parameters_for_chrome_headless(driver):
    params = {'cmd': 'Page.setDownloadBehavior', 'params': {
        'behavior': 'allow', 'downloadPath': os.getcwd()}}
    driver.execute("send_command", params)


def code_container_download_type(driver):
    print("Code Container Download Type Function")
    code_container_class = "styles__Spa_Container-sc-1vx22vv"
    svg_class = "w-7 h-7"

    code_containers = driver.find_elements(
        By.CSS_SELECTOR, f"div[class*='{code_container_class}']")
    if code_containers:
        code_directory_path = os.getcwd()
        for folder_index, code in enumerate(code_containers):
            create_folder("code_downloaded" + str(folder_index))
            download_parameters_for_chrome_headless(driver)
            svg_buttons = code.find_elements(
                By.CSS_SELECTOR, f"svg[class*='{svg_class}']")
            if svg_buttons:
                for svg in svg_buttons:
                    svg.click()
                sleep(2)
                print("Downloaded Zip File")
            else:
                print("Zip File not Downloaded")
            os.chdir(code_directory_path)
    else:
        print("No Code Container Downloadable Type found")


def copy_code(container, driver, use_svg=True):
    svg_class = "w-7 h-7"

    if use_svg:
        container.find_elements(
            By.CSS_SELECTOR, f"svg[class*='{svg_class}'")[0].click()
    else:
        container.find_elements(
            By.CSS_SELECTOR, f"button[title='Copy To Clipboard']")[0].click()
    print("Clicked on Clipboard")
    textbox = driver.find_element(
        By.CSS_SELECTOR, "textarea[class*='temptextarea']")
    textbox.click()
    sleep(1)
    textbox.send_keys(Keys.CONTROL, "a")
    textbox.send_keys(Keys.CONTROL, "v")
    sleep(1)
    print("Paste complete")
    return textbox.get_attribute('value')


def write_code(file_name, content):
    with open(file_name + ".txt", 'w', encoding='utf-8') as f:
        f.write(content)


def iterate_nav_bar(code, code_nav_bar, code_nav_tab, driver):
    print('Inside iterate_nav_bar function')
    nav_bar_tabs_class = "styles__TabTitle"

    nav_bar_tabs = code_nav_bar.find_elements(
        By.CSS_SELECTOR, f"span[class*='{nav_bar_tabs_class}']")
    for idx, _ in enumerate(nav_bar_tabs):
        driver.execute_script(f'''
            return document.querySelectorAll("span[class*='{nav_bar_tabs_class}']")[{idx}].click();
        ''')
        sleep(1)
        print("Clicked on Tab")
        nav_bar_file_name = driver.execute_script(f'''
            return document.querySelectorAll("span[class*='{nav_bar_tabs_class}']")[{idx}].textContent;
        ''')
        if code_nav_tab:
            iterate_nav_tab(code, code_nav_tab, driver, nav_bar_file_name)
        else:
            try:
                returned_code = copy_code(code, driver)
                write_code(nav_bar_file_name, returned_code)
            except Exception as e:
                print("Failed to write")


def iterate_nav_tab(code, code_nav_tab, driver, nav_bar_file_name=""):
    print("Inside iterate_nav_tab function")
    for tab in code_nav_tab:
        tab.click()
        sleep(1)
        try:
            returned_code = copy_code(code, driver)
            file_name = nav_bar_file_name + tab.get_attribute('innerHTML')
            write_code(file_name, returned_code)
        except Exception as e:
            print("Failed to write")


def iterate_general_code(code, driver, file_index):
    solution_code_class = "styles__Buttons_Wrapper"
    try:
        returned_code = copy_code(code, driver)
        write_code(f"Code_{file_index}", returned_code)
    except Exception as e:
        print("Failed to write")

    if code.find_elements(By.CSS_SELECTOR, f"div[class*='{solution_code_class}']"):
        try:
            returned_code = copy_code(code, driver, False)
            write_code(f"Code_Solution_{file_index}", returned_code)
        except Exception as e:
            print("Failed to write")


def code_container_clipboard_type(driver):
    print("Code Container Clipboard Type Function")
    code_container_class = "code-container"
    code_nav_bar_class = "styles__TabNav"
    code_nav_tab_class = "Widget__NavigaitonTab"

    code_containers = driver.find_elements(
        By.CSS_SELECTOR, f"div[class*='{code_container_class}']")
    if code_containers:
        create_temp_textarea(driver)
        code_directory_path = os.getcwd()
        for folder_index, code in enumerate(code_containers):
            create_folder("code_clipboard" + str(folder_index))
            code_nav_bar = code.find_element(
                By.XPATH, "../..").find_elements(By.CSS_SELECTOR, f"ul[class*='{code_nav_bar_class}']")
            code_nav_tab = code.find_elements(
                By.CSS_SELECTOR, f"div[class*='{code_nav_tab_class}']")
            if code_nav_bar:
                print("Nav Bar Found in code container")
                iterate_nav_bar(code, code_nav_bar[0], code_nav_tab, driver)
            elif not code_nav_bar and code_nav_tab:
                iterate_nav_tab(code, code_nav_tab, driver)
            elif not code_nav_bar and not code_nav_tab:
                iterate_general_code(code, driver, str(folder_index))

            os.chdir(code_directory_path)
        delete_node(driver, "textarea[class*='temptextarea']")
    else:
        print("No code containers found")


def extract_zip_files():
    print("Zip File Extraction")
    for path in glob.iglob("./**/*zip", recursive=True):
        zf = os.path.basename(path)
        zipfile.ZipFile(path, 'r').extractall(path[:-len(zf)])
        os.remove(path)


def scrape_page(driver, file_index):
    title = get_file_name(driver)
    file_name = str(file_index) + "-" + title
    driver.set_window_size(1920, get_current_height(driver))
    show_hints_answer(driver)
    show_code_box_answer(driver)
    open_slides(driver)
    create_folder(file_name)
    take_screenshot(driver, file_name)
    code_container_download_type(driver)
    code_container_clipboard_type(driver)

    if not next_page(driver):
        sleep(5)
        return False
    return True


def check_login(driver):
    is_logged_in = driver.find_elements(
        By.CSS_SELECTOR, "a[href*='/unlimited']")
    if not is_logged_in:
        return True
    print("Please log in")
    return False


def load_webpage(driver, url, file_index):
    _, _, _, save_path = load_config()
    driver.get(url)
    sleep(10)
    if not check_login(driver):
        return False
    os.chdir(save_path)
    create_course_folder(driver)
    course_path = os.getcwd()
    while check_login(driver) and scrape_page(driver, file_index):
        print("---------------", file_index, "Complete-------------------")
        sleep(10)
        file_index += 1
        os.chdir(course_path)
    os.chdir(course_path)
    extract_zip_files()
    os.chdir(save_path)
    return True


def scrape_courses():
    clear()
    print('''
                Scraper Started, Log file can be found in config directory
    ''')

    driver = load_chrome_driver(headless=True)
    try:
        _, _, url_text_file, save_path = load_config()
        if not os.path.isfile(url_text_file):
            raise Exception(
                "Url Text file path not found, Please check your config")
        with open(url_text_file, 'r') as file:
            url_list = file.readlines()
        for url_data in url_list:
            url_data = url_data.split()
            if len(url_data) == 2:
                file_index, url = int(url_data[0]), url_data[1]
            else:
                file_index, url = 0, url_data[0]
            try:
                print(f'''
                            Starting Scraping: {file_index}, {url}
                ''')
                if not load_webpage(driver, url, file_index):
                    break
                print("Next Course")
            except Exception as e:
                with open(os.path.join(save_path, 'log.txt'), 'a') as file:
                    file.write(f"{url}\n")
                print("Found Issue, Going Next Course", e)

        print("Script Execution Complete")
        driver.quit()
    except Exception as e:
        driver.quit()
        print("Exception, Driver exited")
        raise Exception(e)


def generate_config():
    clear()
    print('''
        Leave Blank in you don't want to overwrite Previous Values
    ''')
    try:
        user_data_dir, chrome_exe, url_text_file, save_path = load_config()
    except Exception as e:
        print(e)
    # user_data_dir = input(
    #     "Enter the Chrome User Data directory path: ") or user_data_dir
    # chrome_exe = input("Enter Chrome Executable path: ") or chrome_exe
    user_data_dir = os.path.join(OS_ROOT, f"User Data")
    chrome_exe = ROOT_DIR
    url_text_file = input("Enter the URL text file path: ") or url_text_file
    save_path = input("Enter Save Path: ") or save_path

    folder_name = ".educative_scraper_config"
    if folder_name not in os.listdir(OS_ROOT):
        os.mkdir(os.path.join(OS_ROOT, folder_name))

    with open(os.path.join(OS_ROOT, folder_name, "config.json"), "w+") as config_file:
        json.dump({
            "user_data_dir": user_data_dir,
            "chrome_exe": chrome_exe,
            "url_file_path": url_text_file,
            "save_path": save_path
        }, config_file)


def login_educative():
    clear()
    driver = load_chrome_driver(headless=False)
    try:
        driver.get("https://educative.io")
        input("Press enter to return to Main Menu after Login is successfull")
        # driver.save_screenshot('test.png')
        driver.quit()
        print("Login Success!")
    except Exception as e:
        print("Exception occured, Try again", e)
        driver.quit()


def clear():
    global chromedriver, chrome_os
    if os.name == "nt":
        os.system('cls')
        chromedriver = r'Chrome-bin\win\chromedriver.exe'
        chrome_os = r'Chrome-bin\win\chrome.exe'
    else:
        os.system('clear')
        chromedriver = r'Chrome-bin/mac/chromedriver'
        chrome_os = r"Chrome-bin/mac/Chromium.app/Contents/MacOS/Chromium"


if __name__ == '__main__':
    chromedriver = ""
    chrome_os = ""
    while True:
        clear()
        try:
            print('''
                        Educative Scraper, made by Anilabha Datta
                        Project Link: github.com/anilabhadatta/educative.io_scraper
                        Read the documentation for more information about this project.

                        Press 1 to generate config
                        Press 2 to login Educative
                        Press 3 to start scraping
                        Press any key to exit
            ''')
            choice = input("Enter your choice: ")
            if choice == "1":
                generate_config()
            elif choice == "2":
                login_educative()
            elif choice == "3":
                scrape_courses()
            else:
                break
        except KeyboardInterrupt:
            input("Press Enter to continue")
        except Exception as e:
            print("Main Exception", e)
            input("Press Enter to continue")
