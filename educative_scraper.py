from time import sleep
from selenium.webdriver.common.by import By
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from slugify import slugify
import glob
import zipfile
import json
import sys
import base64
import re


OS_ROOT = os.path.expanduser('~')
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    config_path = os.path.join(OS_ROOT, ".educative")
    if ".educative" not in os.listdir(OS_ROOT) or f"config_{selected_config}.json" not in os.listdir(config_path):
        raise Exception("No config found, Please create one")
    with open(os.path.join(config_path, f"config_{selected_config}.json"), "r") as config_file:
        config = json.load(config_file)
    if "url_file_path" not in config or "save_path" not in config or "headless" not in config:
        raise Exception("Config is corrupted, Please recreate the config")
    url_text_file = config["url_file_path"]
    save_path = config["save_path"]
    headless = config["headless"]
    return url_text_file, save_path, headless


def load_chrome_driver(headless):
    chrome_path = get_binary_path()
    user_data_dir = os.path.join(
        OS_ROOT, ".educative", f"User Data_{selected_config}")
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('headless')
    options.add_argument(f'user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')
    options.add_argument("--start-maximized")
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('--log-level=3')
    userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.56 Safari/537.36"
    options.add_argument(f'user-agent={userAgent}')
    options.binary_location = os.path.join(ROOT_DIR, "Chrome-bin", chrome_path)
    driver = webdriver.Remote(
        command_executor='http://127.0.0.1:9515', options=options)
    driver.set_window_size(1920, 1080)
    driver.command_executor._commands["send_command"] = (
        "POST", '/session/$sessionId/chromium/send_command')
    print("Driver Loaded")
    return driver


def create_course_folder(driver, url):
    print("Create Course Folder Function")
    course_name = get_file_name(driver, True)
    create_folder(course_name)
    print("Inside Course Folder", course_name)


def next_page(driver):
    print("Next Page Function")
    next_page_selector = "button[class*='outlined-primary m-0']"

    if not driver.find_elements(By.CSS_SELECTOR, next_page_selector):
        return False
    base_js_cmd = f'''document.querySelectorAll("{next_page_selector}")[0]'''
    check_next_module = driver.execute_script(
        "return " + base_js_cmd + ".innerHTML.slice(0,11);")
    if "Next Module" in check_next_module:
        return False
    driver.execute_script(base_js_cmd + ".click()")
    print("Going Next Page")
    return True


def open_slides(driver):
    print("Finding Slides Function")
    svg_label = "svg[aria-label*='view all slides']"

    slides = driver.find_elements(
        By.CSS_SELECTOR, svg_label)
    if slides:
        print("Slides Found")
        driver.execute_script('''
        ele = document.querySelectorAll("svg[aria-label*='view all slides']");
        for(i=0;i<ele.length;i++){
            ele[i].parentNode.click();
        }
        ''')
        sleep(10)
    else:
        print("No Slides Found")


def get_file_name_standard(driver, course_folder=False):
    print("Get File name standard")
    meta_script_selector = "script[type='application/ld+json']"
    title_selector = "meta[property='og:title']"

    metadata_elements = driver.find_elements(
        By.CSS_SELECTOR, meta_script_selector)
    for meta_element in metadata_elements:
        meta_content = json.loads(meta_element.get_attribute('innerHTML'))
        if "name" in meta_content:
            break
    course_name = meta_content['name']

    title = driver.find_element(
        By.CSS_SELECTOR, title_selector).get_attribute('content')
    if course_name in title:
        page_name = title[:len(title)-len(course_name)]
    else:
        page_name = title

    return course_name if course_folder else page_name


def get_file_name_from_module(driver, course_folder=False):
    print("Get File name module")
    title_selector = "meta[property='og:title']"
    article_selector = "div[id='handleArticleScroll']"

    title_els = driver.find_elements(By.CSS_SELECTOR, title_selector)
    article_ele = driver.find_elements(By.CSS_SELECTOR, article_selector)

    assert len(
        title_els) == 2 and len(article_ele) > 0, "Expected to find two og:title elements."

    titles = [title_el.get_attribute('content').strip()
              for title_el in title_els]
    title = max(titles, key=len)
    h1_title = article_ele[0].find_element(By.TAG_NAME, 'h1').text.strip()
    if title == h1_title:
        title = title_els[1].get_attribute('content').strip()
    course_name, page_name = title[len(h1_title):], h1_title
    return course_name if course_folder else page_name


def replace_filename(str):
    numDict = {':': ' ', '?': ' ', '|': ' ', '>': ' ', '<': ' ', '/': ' '}
    return numDict[str.group()]


def get_file_name(driver, course_folder=False):
    print("Getting File Name")

    # is that a standard page or module page?
    # TODO: is there a proper/better way to differentiate?
    canonical_selector = "link[rel='canonical']"

    els = driver.find_elements(By.CSS_SELECTOR, canonical_selector)
    if len(els) > 0:
        print("> This is a module page")
        file_name = get_file_name_from_module(driver, course_folder)
    else:
        print("> This is a standard page")
        try:
            file_name = get_file_name_standard(driver, course_folder)
        except:
            file_name = get_file_name_from_module(driver, course_folder)
    file_name = slugify(file_name, replacements=[
                        ['+', 'plus']]).replace("-", " ")
    return re.sub(r'[:?|></]', replace_filename, file_name)


def delete_node(driver, node, xpath=False):
    print("Node deleted", node)

    driver.execute_script(f"""
                                var element = document.querySelectorAll("{node}");
                                if (element.length > 0)
                                    for(i=0; i<element.length; i++){{
                                        element[i].remove();
                                    }}
                                """)
    sleep(1)


def remove_tags(driver):
    print("Removing Unnecessary Tags from page")
    nav_node = f"div[class*='ed-grid'] > nav"
    privacy_div = "div[aria-label*='Your Privacy']"
    ask_a_question_and_dark_mode_toolbar = "div[id*='view-collection-article-content-root']> :not(#handleArticleScroll) > *"
    streak_div = "div[aria-labelledby*='simple-modal-title']"

    delete_node(driver, nav_node)
    delete_node(driver, privacy_div)
    delete_node(driver, ask_a_question_and_dark_mode_toolbar)
    delete_node(driver, streak_div)
    sleep(2)


def add_style_tag_with_filter(driver):
    print("Adding Style Tag with Filter")
    driver.execute_script("""
                            var head = document.getElementsByTagName('head')[0];

                                var style = document.createElement('style');
                                style.type = 'text/css';

                                var css = '*{filter: none !important;}';
                                if (style.styleSheet){
                                style.styleSheet.cssText = css;
                                } else {
                                style.appendChild(document.createTextNode(css));
                                }
                                head.appendChild(style);
                            """)


def get_current_height(driver):
    return driver.execute_script('return document.body.parentNode.scrollHeight')


def create_html_with_image(file_name, base_64_png, quiz_html):
    with open(file_name + ".html", "w+", encoding="utf-8") as fh:
        fh.write(f'''
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <title>{file_name}</title>
                </head>
                <body style="zoom: 80%">
                    <div style="text-align: center">
                        <img style="display: block;margin-left: auto; margin-right: auto;" src="data:image/png;base64,{base_64_png}" alt="">
                        {quiz_html}
                    </div>
                </body>
                </html>
            ''')
    sleep(1)


def create_html_with_singleFile(file_name, page_content, quiz_html):
    print("Creating HTML File")
    with open(file_name + ".html", "w+", encoding="utf-8") as fh:
        fh.write(f'''
                    {page_content}
                    {quiz_html}
            ''')
    sleep(1)
    print("HTML File Created")


def send_command(driver, cmd, params={}):
    resource = "/session/%s/chromium/send_command_and_get_result" % driver.session_id
    url = driver.command_executor._url + resource
    body = json.dumps({'cmd': cmd, 'params': params})
    response = driver.command_executor._request('POST', url, body)
    return response.get('value')


def screenshot_as_cdp(driver, ele_to_screenshot, scale=0.8):

    sleep(1)
    size, location = ele_to_screenshot.size, ele_to_screenshot.location
    width, height = size['width'], size['height']
    x, y = location['x'], location['y']

    params = {
        "format": "png",
        "captureBeyondViewport": True,
        "clip": {
            "width": width,
            "height": height,
            "x": x,
            "y": y,
            "scale": scale
        }
    }
    screenshot = send_command(driver, "Page.captureScreenshot", params)
    return screenshot['data']


def take_full_html_screenshot(driver, file_name, quiz_html):
    print("Take Screenshot Function")
    article_page_selector = "(//div[@id='handleArticleScroll']//div[count(div)>=2])[1]"
    general_page_selector = "(//div[@id='view-collection-article-content-root']//div[count(div)>=2])[1]"

    ele_to_screenshot = driver.find_elements(
        By.XPATH, article_page_selector) or driver.find_elements(
        By.CSS_SELECTOR, general_page_selector)

    base_64_png = screenshot_as_cdp(driver, ele_to_screenshot[0], 1)
    sleep(2)
    create_html_with_image(file_name, base_64_png, quiz_html)
    print("Screenshot taken and HTML File generated")


def fix_all_svg_tags_inside_object_tags(driver):
    print("Fixing SVG Tags inside Object Tags")
    object_tag_selector = "object[role='img']"
    driver.execute_script(f'''
                            iframes = document.querySelectorAll("{object_tag_selector}")
                            for (var i = 0; i < iframes.length; i++) {{
                                try{{
                                    svg_element = iframes[i].contentDocument.documentElement;
                                    cls_name = iframes[i].className;
                                    parent_tag = iframes[i].parentNode;
                                    children_tags = iframes[i].parentNode.children;
                                    for(j=0;j<children_tags.length;j++){{
                                        children_tags[j].remove();
                                        }}
                                    parent_tag.append(svg_element);
                                    svg_element.classList.add(cls_name);
                                }}
                                catch(error){{
                                    console.log(error);
                                }}
                            }}''')


def make_code_selectable(driver):
    print("make_code_selectable function")
    driver.execute_script('''
        let code_containers = document.getElementsByClassName('monaco-editor');
        for(let i=0;i<code_containers.length;i++){
            if ( code_containers[i].classList.contains('no-user-select') )
        code_containers[i].classList.remove('no-user-select');
        }
    ''')
    print("make_code_selectable function executed")


def single_file_js_executer(driver):
    return driver.execute_script('''
                                    const { content, title, filename } = await singlefile.getPageData({
                                        removeImports: true,
                                        removeScripts: true,
                                        removeAudioSrc: true,
                                        removeVideoSrc: true,
                                        removeHiddenElements: true,
                                        removeUnusedStyles: true,
                                        removeUnusedFonts: true,
                                        compressHTML: true,
                                        blockVideos: true,
                                        blockScripts: true,
                                        networkTimeout: 60000
                                    });
                                    return content;
    ''')


def get_pagecontent_using_singleFile(driver, file_name, quiz_html):
    print("Get HTML Page Content Using Single File Function")

    # Inject SingleFile JS script
    driver.execute_script('''
        inject = document.createElement('script');
        inject.src = "https://anilabhadatta.github.io/SingleFile/lib/single-file.js";
        document.getElementsByTagName('head')[0].appendChild(inject);
    ''')
    sleep(2)

    make_code_selectable(driver)
    try:
        try:
            page_content = single_file_js_executer(driver)
        except Exception:
            page_content = single_file_js_executer(driver)
        create_html_with_singleFile(file_name, page_content, quiz_html)
    except Exception:
        take_full_html_screenshot(driver, file_name, quiz_html)

    print("HTML Page content taken.")


def show_hints_answer(driver):
    print("Show Hints Function")
    hints_g_id_selector = "g[id*='noun_lightbulb']"

    hints_list = driver.find_elements(
        By.CSS_SELECTOR, hints_g_id_selector)
    if hints_list:
        driver.execute_script('''
            ele = document.querySelectorAll("g[id*='noun_lightbulb']");
            for(i=0;i<ele.length;i++){
            ele[i].closest('svg').parentNode.click();
            }
        ''')
        print("Show Hints Complete")
    else:
        print("No hints found")


def click_using_driver_js(driver, selector):
    driver.execute_script(f'''
            document.querySelector("{selector}").click();
        ''')


def show_solutions(driver):
    print("Show Solution Function")
    solution_button = "//button[contains(text(),'olution')]"
    confirm_button = "button[aria-label*='confirm']"

    answer_list = driver.find_elements(By.XPATH, solution_button)
    if answer_list:
        driver.execute_script(f'''
                        var nodesSnapshot = document.evaluate("{solution_button}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                        for(i=0;i<nodesSnapshot.snapshotLength;i++){{
                            nodesSnapshot.snapshotItem(i).click();
                            document.querySelector("{confirm_button}").click();
                        }}''')
        print("Show Solution Complete")
    else:
        print("No Solution found")


def create_temp_textarea(driver):
    driver.execute_script('''
        var div = document.querySelector('div[class*="ed-grid-main"]');
                var input = document.createElement("textarea");
                input.name = "temptextarea";
                input.className = "temptextarea";
                input.maxLength = "10000";
                input.cols = "50";
                input.rows = "10";
                div.prepend(input);
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


def click_on_sidebar(driver, code):
    file_div_selector = "div[class*='ml-2']"
    action = ActionChains(driver)

    try:
        elements = code.find_element(
            By.CSS_SELECTOR, file_div_selector).find_elements(By.CSS_SELECTOR, "svg")
        for element in elements:
            try:
                action.move_to_element(element).click().perform()
            except Exception:
                pass
    except Exception:
        pass


def check_file_in_dir(original_file_name):
    file_name_splitted = original_file_name.split(".")
    if len(file_name_splitted) == 1 and original_file_name in os.listdir():
        return original_file_name
    elif len(file_name_splitted) > 1 and file_name_splitted[0] == "":
        for file in os.listdir():
            if file_name_splitted[1] in file:
                return file
    else:
        return original_file_name


def download_file(driver, element):
    print("Download File Function")
    action = ActionChains(driver)
    file_name_selector = "div[class*='tooltip-inner']"

    original_file_name = element.find_element(
        By.XPATH, "../..").find_element(By.CSS_SELECTOR, "span").get_attribute('innerHTML')
    try:
        hover_file_name = driver.find_element(
            By.CSS_SELECTOR, file_name_selector).get_attribute('innerHTML')
    except Exception:
        hover_file_name = original_file_name

    action.move_to_element(element).click().perform()
    sleep(1)
    parent_div = element.find_element(By.XPATH, "../../..")
    svg_button = parent_div.find_elements(By.CSS_SELECTOR, "svg")
    if len(svg_button) == 1:
        action.move_to_element(element).click().perform()
        sleep(1)
        parent_div = element.find_element(By.XPATH, "../../..")
        svg_button = parent_div.find_elements(By.CSS_SELECTOR, "svg")
    if len(svg_button) == 2:
        action.move_to_element(svg_button[-1]).click().perform()
        sleep(1)
        parent_div = element.find_element(By.XPATH, "../../..")
        svg_button = parent_div.find_elements(By.CSS_SELECTOR, "svg")
        if len(svg_button) == 3:
            action.move_to_element(svg_button[-1]).click().perform()
            sleep(2)
            original_file_name = check_file_in_dir(original_file_name)
            os.rename(original_file_name, slugify(hover_file_name,
                      replacements=[['+', 'plus']]).replace("-", "."))


def download_code_manually(driver, code):
    print("Download Code Manually Function")
    file_div_selector = "div[class*='ml-2']"
    svg_path_1 = "path[d*='M6 12l4']"
    svg_path_2 = "path[d*='M4 6l4']"
    action = ActionChains(driver)

    elements = code.find_element(
        By.CSS_SELECTOR, file_div_selector).find_elements(By.CSS_SELECTOR, "svg")
    for element in elements:
        try:
            element.location_once_scrolled_into_view
            if element.find_elements(By.CSS_SELECTOR, svg_path_1):
                action.move_to_element(element).click().perform()
            elif element.find_elements(By.CSS_SELECTOR, svg_path_2):
                continue
            else:
                action.move_to_element(element).perform()
                sleep(2)
                download_file(driver, element)
            sleep(1)
        except Exception as e:
            print(e)
            pass


def code_container_download_type(driver):
    print("Code Container Download Type Function")
    code_container_selector = "div[class*='code-tabs-code-wrapper']"
    div_class_selector = "div[aria-label*='webpackbin-tabs']"
    download_svg_selector = "svg:not([title])"
    action = ActionChains(driver)

    code_containers = driver.find_elements(
        By.CSS_SELECTOR, code_container_selector)
    if code_containers:
        code_directory_path = os.getcwd()
        for folder_index, code in enumerate(code_containers):
            buttons = code.find_elements(
                By.CSS_SELECTOR, div_class_selector)
            if not buttons:
                click_on_sidebar(driver, code)
                buttons = code.find_elements(
                    By.CSS_SELECTOR, div_class_selector)
            if buttons:
                download_button = code.find_elements(
                    By.CSS_SELECTOR, download_svg_selector)
                if download_button:
                    create_folder("code_downloaded" + str(folder_index))
                    download_parameters_for_chrome_headless(driver)
                    sleep(1)
                    action.move_to_element(
                        download_button[-1]).click().perform()
                    sleep(2)
                    if os.listdir() == []:
                        try:
                            # download_code_manually(driver, code)
                            pass
                        except Exception:
                            pass
                    else:
                        print("Downloaded Zip File")
                else:
                    print("Zip File not Downloaded")
            os.chdir(code_directory_path)
    else:
        print("No Code Container Downloadable Type found")


def copy_code(container, driver, use_svg=True):
    print("Copy Code Function")
    clipboard_title_svg = "svg[title='Copy To Clipboard']"
    clipboard_title_button = "button[title='Copy To Clipboard']"
    action = ActionChains(driver)
    sleep(1)

    if use_svg:
        svg_button = container.find_elements(
            By.CSS_SELECTOR, clipboard_title_svg)[0]
    else:
        svg_button = container.find_elements(
            By.CSS_SELECTOR, clipboard_title_button)[0]
    print("Clicked on Clipboard")
    action.move_to_element(svg_button).click().perform()
    sleep(1)
    textbox = click_on_textbox(driver)
    if current_os == "darwin":
        textbox.send_keys(Keys.COMMAND, "a")
        textbox.send_keys(Keys.COMMAND, "v")
    else:
        textbox.send_keys(Keys.CONTROL, "a")
        textbox.send_keys(Keys.CONTROL, "v")
    print("Paste complete")
    sleep(1)
    return textbox.get_attribute('value')


def write_code(file_name, content):
    print("Write Code Function")
    file_name = slugify(file_name, replacements=[['+', 'plus']])
    with open(file_name + ".txt", 'w', encoding='utf-8') as f:
        f.write(content)


def iterate_top_nav_bar(code, top_nav_bar_buttons, side_nav_bar_butttons, driver, folder_index):
    print('Inside iterate_top_nav_bar function')
    nav_bar_tab_title = "span[id*='tab-title']"
    side_nav_bar_butttons_selector = "div[class*='Widget_multi-files'] > div > div > div > :not(div[class*='monaco-editor'])"

    for idx in range(len(top_nav_bar_buttons)):
        nav_bar_tab = find_nav_bar_buttons(driver, folder_index)
        nav_bar_file_name = nav_bar_tab[idx].find_element(
            By.CSS_SELECTOR, nav_bar_tab_title).text

        driver.execute_script("arguments[0].click();", nav_bar_tab[idx])
        sleep(1)
        print("Clicked on Tab")

        side_nav_bar_butttons = code.find_elements(
            By.CSS_SELECTOR, side_nav_bar_butttons_selector)
        if side_nav_bar_butttons:
            iterate_side_nav_bar(code, side_nav_bar_butttons,
                                 driver, nav_bar_file_name)
        else:
            try:
                returned_code = copy_code(code, driver)
                write_code(nav_bar_file_name, returned_code)
            except Exception as e:
                print(e)
                print("Failed to write")
            find_and_write_code_solutions(
                driver, code, nav_bar_file_name + str(file_index))


def iterate_side_nav_bar(code, side_nav_bar_butttons, driver, nav_bar_file_name=""):
    print("Inside iterate_side_nav_bar function")
    side_nav_bar_butttons_selector = "div[class*='Widget_multi-files'] > div > div > div > :not(div[class*='monaco-editor'])"
    action = ActionChains(driver)

    for idx in range(len(side_nav_bar_butttons)):
        side_button = code.find_elements(
            By.CSS_SELECTOR, side_nav_bar_butttons_selector)[idx]
        side_button_text = side_button.text
        action.move_to_element(side_button).click().perform()
        sleep(1)
        try:
            returned_code = copy_code(code, driver)
            file_name = nav_bar_file_name + side_button_text
            write_code(file_name, returned_code)
        except Exception as e:
            print(e)
            print("Failed to write")
    if nav_bar_file_name == "":
        find_and_write_code_solutions(
            driver, code, "")


def find_and_write_code_solutions(driver, code, file_index):
    print("Solution copying Function")
    solution_code_selector = "div[class*='runnable-enter-done']"

    code = code.find_element(By.XPATH, "../..").find_elements(
        By.CSS_SELECTOR, solution_code_selector)
    if code:
        try:
            returned_code = copy_code(code[0], driver, False)
            write_code(f"{file_index}_Solution", returned_code)
        except Exception as e:
            print(e)
            print("Failed to write")
    else:
        print("No solution found")


def iterate_general_code(code, driver, file_index):
    print("Iterate General Code Function")

    try:
        returned_code = copy_code(code, driver, file_index)
        write_code(f"Code_{file_index}", returned_code)
    except Exception as e:
        print(e)
        print("Failed to write")
    find_and_write_code_solutions(driver, code, file_index)


def find_nav_bar_buttons(driver, folder_index):
    print("Execute Nav Bar Code Function")
    nav_bar_tab_title = "span[id*='tab-title']"
    code_container_selector = "div[class*='code-container']"

    return driver.find_elements(By.CSS_SELECTOR, code_container_selector)[
        folder_index].find_element(By.XPATH, "../..").find_element(By.CSS_SELECTOR, nav_bar_tab_title).find_element(By.XPATH, "../../../../..").find_elements(By.CSS_SELECTOR, "button")


def code_container_clipboard_type(driver):
    print("Code Container Clipboard Type Function")
    code_container_selector = "div[class*='code-container']"
    side_nav_bar_butttons_selector = "div[class*='Widget_multi-files'] > div > div > div > :not(div[class*='monaco-editor'])"
    textbox_selector = "textarea[class*='temptextarea']"

    code_containers = driver.find_elements(
        By.CSS_SELECTOR, code_container_selector)
    if code_containers:
        create_temp_textarea(driver)
        code_directory_path = os.getcwd()
        for folder_index, code in enumerate(code_containers):
            create_folder("code_clipboard" + str(folder_index))
            try:
                top_nav_bar_buttons = find_nav_bar_buttons(
                    driver, folder_index)
            except Exception as e:
                top_nav_bar_buttons = []
            side_nav_bar_butttons = code.find_elements(
                By.CSS_SELECTOR, side_nav_bar_butttons_selector)

            if top_nav_bar_buttons:
                print("Nav Bar Found in code container")
                iterate_top_nav_bar(
                    code, top_nav_bar_buttons, side_nav_bar_butttons, driver, folder_index)
            elif not top_nav_bar_buttons and side_nav_bar_butttons:
                print("Side Nav Bar Found in code container")
                iterate_side_nav_bar(code, side_nav_bar_butttons, driver)
            elif not top_nav_bar_buttons and not side_nav_bar_butttons:
                print("General Code Container Found")
                iterate_general_code(code, driver, str(folder_index))

            os.chdir(code_directory_path)
        delete_node(driver, textbox_selector)
    else:
        print("No code containers found")


def widget_tab_container_function(container, driver):
    print("Widget Tab Container Function")
    widget_inner_container = "div[class*='Widget__WidgetTabs']"
    widget_code_selector = "div[class*='styles__CodeEditorStyled']"
    li_selector = "ul > li[class*='Widget__WidgetTab']"
    output_selector = "div[class*='HtmlResponsiveViewer']"
    action = ActionChains(driver)

    widget_tabs = container.find_elements(
        By.CSS_SELECTOR, widget_inner_container)
    if widget_tabs:
        widget_tabs = widget_tabs[0].find_elements(
            By.CSS_SELECTOR, li_selector)
        for idx in range(len(widget_tabs)):
            tab = container.find_element(By.CSS_SELECTOR, widget_inner_container).find_elements(
                By.CSS_SELECTOR, li_selector)[idx]
            try:
                file_name = tab.get_attribute('innerHTML')
                action.move_to_element(tab).click().perform()
            except Exception as e:
                pass
            sleep(2)
            code_container_inside_tab = container.find_element(By.CSS_SELECTOR, widget_inner_container).find_elements(
                By.CSS_SELECTOR, widget_code_selector)
            output_containers_inside_tab = container.find_element(By.CSS_SELECTOR, widget_inner_container).find_elements(
                By.CSS_SELECTOR, output_selector)
            try:
                if code_container_inside_tab:
                    copy_code_from_widget_container(
                        code_container_inside_tab[0], driver, file_name)
                elif output_containers_inside_tab:
                    take_screenshot_widget_tab(
                        driver, output_containers_inside_tab[0], file_name, idx)
            except Exception as e:
                pass


def runjs_container_function(container, driver):
    print("RunJS Container Function")
    output_selector = "div[class*='HtmlResponsiveViewer']"
    runjs_code_selector = "div[class*='styles__CodeEditor']"
    runjs_selector = "div[class*='runjs-container']"

    runjs_containers = container.find_elements(
        By.CSS_SELECTOR, runjs_selector)
    if runjs_containers:
        code_editors_inside_runjs = runjs_containers[0].find_elements(
            By.CSS_SELECTOR, runjs_code_selector)
        for idx, code_editor in enumerate(code_editors_inside_runjs):
            try:
                copy_code_from_widget_container(
                    code_editor, driver, f"code_{idx}")
            except Exception as e:
                pass
        output_containers = runjs_containers[0].find_elements(
            By.CSS_SELECTOR, output_selector)
        for idx, output_container in enumerate(output_containers):
            try:
                take_screenshot_widget_tab(
                    driver, output_container, "Output", idx)
            except Exception as e:
                pass


def code_widget_type(driver):
    print("Inside Widget Container Function")
    container_selector = "div[class*='Widget__WidgetStyled']"
    textbox_selector = "textarea[class*='temptextarea']"

    widget_type_containers = driver.find_elements(
        By.CSS_SELECTOR, container_selector)
    if widget_type_containers:
        code_directory_path = os.getcwd()
        create_temp_textarea(driver)
        for folder_index, container in enumerate(widget_type_containers):
            create_folder("code_widget_type" + str(folder_index))
            widget_tab_container_function(container, driver)
            runjs_container_function(container, driver)
            os.chdir(code_directory_path)
        delete_node(driver, textbox_selector)
    else:
        print("No widget container found")


def copy_code_from_widget_container(code_container_inside_tab, driver, file_name):
    print("Copying Code From Widget Container Function")
    line_div_selector = "div[class*='lines-content']"
    view_line_div_selector = "div[class*='view-line']"
    action = ActionChains(driver)

    line_div = code_container_inside_tab.find_element(
        By.CSS_SELECTOR, line_div_selector).find_element(By.CSS_SELECTOR, view_line_div_selector)
    action.move_to_element(line_div).click().perform()
    copy_from_container(driver)
    textbox = click_on_textbox(driver)
    copy_from_container(driver, textbox)
    write_code(file_name, textbox.get_attribute('value'))


def take_screenshot_widget_tab(driver, output_container, file_name, idx=0):
    print("Taking Screenshot From Widget Container Function")
    # output_image = screenshot_as_cdp(driver, output_container)
    output_image = output_container.screenshot_as_base64
    file_name = slugify(file_name, replacements=[['+', 'plus'], ['span', '']])
    with open(f"{file_name}_{idx}.png", "wb") as f:
        f.write(base64.urlsafe_b64decode(output_image))


def click_on_textbox(driver):
    print("Click On Textbox Function")
    action = ActionChains(driver)
    textbox_selector = "textarea[class*='temptextarea']"

    textbox = driver.find_element(
        By.CSS_SELECTOR, textbox_selector)
    action.move_to_element(textbox).click().perform()
    sleep(1)
    return textbox


def copy_from_container(driver, element=""):
    print("Copy Code From Container Function")
    action = ActionChains(driver)
    sleep(1)

    if current_os == "darwin":
        if element:
            element.send_keys(Keys.COMMAND, "a")
            element.send_keys(Keys.COMMAND, "v")
        else:
            action.key_down(Keys.COMMAND).send_keys(
                'a').key_up(Keys.COMMAND).perform()
            action.key_down(Keys.COMMAND).send_keys(
                'c').key_up(Keys.COMMAND).perform()
    else:
        if element:
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.CONTROL, "v")
        else:
            action.key_down(Keys.CONTROL).send_keys(
                'a').key_up(Keys.CONTROL).perform()
            action.key_down(Keys.CONTROL).send_keys(
                'c').key_up(Keys.CONTROL).perform()
    sleep(1)


def extract_zip_files():
    print("Zip File Extraction")

    for path in glob.iglob("./**/*educative-code-widget.zip", recursive=True):
        zf = os.path.basename(path)
        zipfile.ZipFile(path, 'r').extractall(path[:-len(zf)])
        os.remove(path)


def demark_as_completed(driver):
    print("Remove Mark completed")
    div_selector = "div[class*='styles__Checkbox']"

    try:
        driver.execute_script(f'''
            ele = document.querySelectorAll("{div_selector}");
            ele[ele.length-1].click();
        ''')
    except Exception:
        pass


def click_option_quiz(driver, quiz_container):
    print("Click on Option Quiz")
    option_selector = "div[class*='question-option-view']"
    action = ActionChains(driver)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, option_selector)))
        option = quiz_container.find_element(
            By.CSS_SELECTOR, option_selector)
        option.location_once_scrolled_into_view
        action.move_to_element(option).click().perform()
        sleep(1)
    except Exception:
        pass


def quiz_container_html(driver, quiz_container, markdown=False):
    print("Take Quiz Screenshot Function")
    if not markdown:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div[class*='question-option-view']")))
    quiz_container.location_once_scrolled_into_view
    container_screenshot = screenshot_as_cdp(driver, quiz_container)
    sleep(1)
    return f'''<img style="display: block;margin-left: auto; margin-right: auto;" src="data:image/png;base64,{container_screenshot}" alt="">'''


def click_right_button_quiz(driver, quiz_container):
    print("Clicking on Right button in Quiz")
    action = ActionChains(driver)
    right_button_selector = "button[class*='Button_quiz-widget-controls']:last-child"

    quiz_html = ""
    right_button = quiz_container.find_elements(
        By.CSS_SELECTOR, right_button_selector)

    if not right_button:
        click_option_quiz(driver, quiz_container)
        click_submit_quiz(driver, quiz_container)
        click_submit_quiz(driver, quiz_container)

    while right_button:
        click_option_quiz(driver, quiz_container)
        click_submit_quiz(driver, quiz_container)
        quiz_html += quiz_container_html(driver, quiz_container)
        if check_last_right_button(right_button):
            break
        action.move_to_element(right_button[0]).click().perform()
        print("Clicking on Right button")
        click_on_submit_dialog_if_visible(driver)
        right_button = quiz_container.find_elements(
            By.CSS_SELECTOR, right_button_selector)

    return quiz_html


def check_last_right_button(right_button):
    print("Check Last Right Button in Quiz")
    if right_button[0].find_elements(By.CSS_SELECTOR, "path"):
        return True
    return False


def click_on_submit_dialog_if_visible(driver):
    print("Clicking on Submit dialog in Quiz")
    div_selector = "div[class*='ConfirmationModal']"
    button_selector = "button[id*='confirm-button']"
    action = ActionChains(driver)

    try:
        dialog_box = driver.find_elements(
            By.CSS_SELECTOR, div_selector)
        if dialog_box:
            button = dialog_box[0].find_elements(
                By.CSS_SELECTOR, button_selector)
            action.move_to_element(button[0]).click().perform()
        else:
            print("No submit dialog found")
    except Exception:
        pass


def click_submit_quiz(driver, quiz_container):
    print("Inside Submit button Quiz Function")
    action = ActionChains(driver)

    try:
        buttons = quiz_container.find_elements(By.CSS_SELECTOR, "button")
        action.move_to_element(buttons[-1]).click().perform()
        sleep(1)
    except Exception:
        pass


def take_quiz_screenshot(driver):
    print("Inside take_quiz_screenshot function")
    quiz_container_selector = "div[class*='quiz-view-mode']"
    quiz_html = ""

    quiz_containers = driver.find_elements(
        By.CSS_SELECTOR, quiz_container_selector)
    if quiz_containers:
        for quiz_container in quiz_containers:
            quiz_html += click_right_button_quiz(
                driver, quiz_container)
    else:
        print("Quiz not found")
    return quiz_html


def find_mark_down_quiz_containers(driver):
    print("Inside find_mark_down_quiz_containers function")
    div_selector = "//span[contains(@class, 'markdown')]/ancestor::div[contains(@id, 'widget-parent')]"
    right_button_selector = "button[class*='Button_circle-button']:last-child"
    quiz_html = ""
    action = ActionChains(driver)

    quiz_containers = driver.find_elements(
        By.XPATH, div_selector)
    if quiz_containers:
        for quiz_container in quiz_containers:
            right_button = quiz_container.find_elements(
                By.CSS_SELECTOR, right_button_selector)
            if right_button:
                while True:
                    click_on_mark_down_quiz(driver, quiz_container)
                    quiz_html += quiz_container_html(driver,
                                                     quiz_container, True)
                    if right_button[0].get_attribute("disabled"):
                        break
                    right_button = quiz_container.find_elements(
                        By.CSS_SELECTOR, right_button_selector)
                    action.move_to_element(right_button[0]).click().perform()
                    sleep(1)
            else:
                print("No right button found in Mark Down Quiz")
                click_on_mark_down_quiz(driver, quiz_container)
    else:
        print("No mark down quiz_container found")
    return quiz_html


def click_on_mark_down_quiz(driver, quiz_container):
    print("Clicking on Mark Down Quiz function")
    show_answer_button = "//div[@role='button']/span[text()='Show Answer']"

    show_answer_buttons = quiz_container.find_elements(
        By.XPATH, show_answer_button)
    if show_answer_buttons:
        driver.execute_script(f'''
                        var nodesSnapshot = document.evaluate("{show_answer_button}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                        for(i=0;i<nodesSnapshot.snapshotLength;i++){{
                            nodesSnapshot.snapshotItem(i).click();
                        }}''')
    else:
        print("No mark down quiz_container found")


def wait_webdriver(driver):
    article_page_selector = "(//div[@id='handleArticleScroll']//div[count(div)>=2])[1]"
    next_button_selector = "div[class*='outlined-primary m-0']"
    header_1 = "//h1[text()]"
    header_2 = "//h2[text()]"

    try:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, article_page_selector)))
        except Exception:
            pass
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, next_button_selector)))
        except Exception:
            pass
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, header_1)))
        except Exception:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, header_2)))
    except Exception:
        pass


def scroll_page(driver):
    print("Scrolling Page")

    total_height = int(driver.execute_script(
        "return document.body.scrollHeight"))
    for i in range(1, total_height, 10):
        driver.execute_script("window.scrollTo(0, {});".format(i))
    sleep(2)


def add_name_tag_in_next_back_button(driver):
    print("Adding Name Tag in Next Back Button")
    next_button_selector = "button[class*='outlined-primary m-0']"
    back_button_selector = "button[class*='outlined-default m-0']"
    try:
        next_button = driver.find_element(
            By.CSS_SELECTOR, next_button_selector)
        driver.execute_script(
            "arguments[0].setAttribute('name', arguments[1]);", next_button, "next")
    except Exception:
        pass
    try:
        back_button = driver.find_element(
            By.CSS_SELECTOR, back_button_selector)
        driver.execute_script(
            "arguments[0].setAttribute('name', arguments[1]);", back_button, "back")
    except Exception:
        pass


def scrape_page(driver, file_index):
    quiz_html = ""
    scroll_page(driver)
    wait_webdriver(driver)
    title = get_file_name(driver)
    check_page(title)
    file_name = str(file_index) + "-" + title
    driver.set_window_size(1920, get_current_height(driver))
    remove_tags(driver)
    add_style_tag_with_filter(driver)
    show_hints_answer(driver)
    quiz_html += find_mark_down_quiz_containers(driver)
    show_solutions(driver)
    open_slides(driver)
    create_folder(file_name)
    quiz_html += take_quiz_screenshot(driver)
    # take_full_html_screenshot(driver, file_name, quiz_html)
    add_name_tag_in_next_back_button(driver)
    fix_all_svg_tags_inside_object_tags(driver)
    get_pagecontent_using_singleFile(driver, file_name, quiz_html)
    code_widget_type(driver)
    code_container_download_type(driver)
    code_container_clipboard_type(driver)
    demark_as_completed(driver)

    if not next_page(driver):
        sleep(5)
        return False
    return True


def check_for_captcha(driver):
    print('Checking for captcha Function...')
    captcha_selector = "h4[class*='mt-2 mb-4']"

    captcha = driver.find_elements(By.CSS_SELECTOR, captcha_selector)
    if captcha and "Captcha" in captcha[0].get_attribute('innerHTML'):
        return False
    return True


def check_login(driver):
    print("Checking Login Function")

    return bool(driver.execute_script(
        '''return document.cookie.includes('logged_in')'''))


def check_page(title):
    print("Checking page")

    if "something went wrong" == title:
        raise Exception("Something went wrong")


def load_webpage(driver, url):
    print("Load Webpage Function")

    global file_index
    _, save_path, _ = load_config()
    driver.get(url)
    sleep(10)
    log_url = url
    if not check_login(driver):
        create_log(file_index, log_url, save_path, "Not logged in")
        return False
    if not check_for_captcha(driver):
        create_log(file_index, log_url, save_path, "Captcha detected")
        return False
    os.chdir(save_path)

    create_course_folder(driver, url)
    course_path = os.getcwd()
    while True:
        if not check_login(driver):
            create_log(file_index-1, log_url, save_path, "Not logged in")
            return False
        if not check_for_captcha(driver):
            create_log(file_index-1, log_url, save_path, "Captcha detected")
            return False
        log_url = driver.current_url
        if not scrape_page(driver, file_index):
            break
        print("---------------", file_index, "Complete-------------------")
        file_index += 1
        sleep(10)
        os.chdir(course_path)
    os.chdir(course_path)
    extract_zip_files()
    os.chdir(save_path)
    return True


def create_log(file_index, url, save_path, e):
    with open(os.path.join(save_path, 'log.txt'), 'a') as file:
        file.write(f"{file_index} {url} \n{e}\n")


def scrape_courses():
    clear()
    global file_index
    print('''
                Scraper Started, Log file can be found in Save directory
    ''')

    try:
        url_text_file, save_path, headless = load_config()
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
                driver = load_chrome_driver(headless)
                print(f'''
                            [Selected config: {selected_config}] Starting Scraping: {file_index}, {url}
                ''')
                if not load_webpage(driver, url):
                    driver.quit()
                    break
                else:
                    driver.quit()
                print("Next Course")
            except KeyboardInterrupt:
                create_log(file_index, driver.current_url, save_path, "")
                raise Exception("Exited Manually")
            except Exception as e:
                try:
                    create_log(file_index, driver.current_url, save_path, e)
                    driver.quit()
                except Exception:
                    pass
                print("Found Issue, Going Next Course", e)

        print("Script Execution Complete")
    except Exception as e:
        print("Exception, Driver exited", e)
        driver.quit()
        raise Exception(e)


def generate_config():
    clear()
    print('''
        Leave Blank and Press Enter if you don't want to overwrite Previous Values
    ''')
    try:
        url_text_file, save_path, headless = load_config()
    except Exception:
        print('''
                    Config doesnt exist, Create a new one.
                    Enter the paths for your config
            ''')
    url_text_file = input("Enter the URL text file path: ") or url_text_file
    save_path = input("Enter Save Path: ") or save_path
    headless = bool(input("Headless T/F? ") == 'T')

    base_config_path = create_base_config_dir()

    with open(os.path.join(base_config_path, f"config_{selected_config}.json"), "w+") as config_file:
        json.dump({
            "url_file_path": url_text_file,
            "save_path": save_path,
            "headless": headless or headless
        }, config_file)


def create_base_config_dir():
    base_config_path = os.path.join(OS_ROOT, ".educative")
    if ".educative" not in os.listdir(OS_ROOT):
        os.mkdir(base_config_path)
    return base_config_path


def select_config():
    global selected_config
    base_config_path = create_base_config_dir()
    print("\nIf you are creating a new config, please select 1 in main menu to generate the new config and also you must login your educative account.\n")

    if len(os.listdir(base_config_path)) > 0:
        for configs in os.listdir(base_config_path):
            if ".json" in configs:
                print(configs)
        selected_config = input(
            "\nSelect a config or enter a number to create a new config: ") or "0"


def login_educative():
    clear()
    driver = load_chrome_driver(False)
    try:
        driver.get("https://educative.io")
        input("Press Enter to return to Main Menu after Login is successfull")
        driver.quit()
        print("Login Success!")
    except Exception as e:
        print("Exception occured, Try again", e)
        driver.quit()


def get_binary_path():
    global current_os
    if current_os.startswith('darwin'):
        chrome_path = r"mac/Chromium.app/Contents/MacOS/Google Chrome"
    elif current_os.startswith('linux'):
        chrome_path = r"linux/chrome/chrome"
    elif current_os.startswith('win32') or current_os.startswith('cygwin'):
        chrome_path = r'win\chrome.exe'
    return chrome_path


def clear():
    global current_os
    if current_os.startswith('darwin'):
        os.system('clear')
    elif current_os.startswith('linux'):
        os.system('clear')
    elif current_os.startswith('win32') or current_os.startswith('cygwin'):
        os.system('cls')


if __name__ == '__main__':
    current_os = sys.platform
    selected_config = "0"
    clear()
    while True:
        file_index = 0
        try:
            print(f'''
                        Educative Scraper (version 7.9), developed by Anilabha Datta
                        Project Link: https://github.com/anilabhadatta/educative.io_scraper
                        Please go through the ReadMe for more information about this project.

                        Press 1 and Enter to generate config
                        Press 2 and Enter to select a config [Currently selected config {selected_config}]
                        Press 3 and Enter to login Educative
                        Press 4 and Enter to start scraping
                        Press Enter to exit
            ''')
            choice = input("Enter your choice: ")
            if choice == "1":
                generate_config()
            elif choice == "2":
                select_config()
            elif choice == "3":
                login_educative()
            elif choice == "4":
                scrape_courses()
            else:
                break
        except KeyboardInterrupt:
            input("Press Enter to continue")
        except Exception as e:
            print("Main Exception", e)
            input("Press Enter to continue")
