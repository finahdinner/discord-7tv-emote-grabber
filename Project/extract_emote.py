from PIL import Image, ImageSequence
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from fake_useragent import UserAgent
import os

""" Logging configuration """
from for_logging import MyLogger
from pathlib import Path
file_name = Path(__file__).stem # get name of the current file (without the .py)
# Usage: my_logger.logger.[LEVEL]('[LOG MESSAGE]')
my_logger = MyLogger(file_name=file_name, log_file_path=f"logs/{file_name}.log") # create an instance of MyLogger


""" File paths """

DOWNLOADED_EMOTES_PATH = "downloaded_emotes/"
DISCORD_EMOTES_PATH = "discord_emotes/"


""" Selenium Settings"""

# Making the window 'headless' (not visible)
WINDOW_OPTIONS = Options()
WINDOW_OPTIONS.add_argument('--window-size=1920,1080') # so that element.click() works
WINDOW_OPTIONS.add_argument('--headless')
WINDOW_OPTIONS.add_argument('--disable-gpu')
# set user agent
ua = UserAgent()
user_agent = str(ua.chrome)
WINDOW_OPTIONS.add_argument(f'user-agent={user_agent}')


""" Functions """

def get_emote_details(page_url: str, name_given: str = "") -> tuple[str, str]:
    """ Extract 7TV emote ID from the page_url given """

    # emote id
    emote_id = page_url.split("/")[-1]
    my_logger.logger.debug(f'{emote_id=}')

    # if a name is given, we don't need to use Selenium to find the 7TV name
    if name_given:
        return (name_given, emote_id)

    # else if no name is given, use Selenium to extract the 7TV name
    if page_url.find('7tv.app') == -1: # if 7tv.app not in the name
        emote_name = ""
    else:
        s = Service(f"{os.environ.get('CHROMEDRIVER_PATH')}")
        driver = webdriver.Chrome(service=s, options=WINDOW_OPTIONS)
        try:
            driver.get(page_url)
            # check every 0.1 seconds (poll_frequency) if the title contains 'by'. Once this is true, the code continue.
            title_loaded = WebDriverWait(driver, 5, poll_frequency=0.1).until(expected_conditions.title_contains('by'))
            page_title = driver.title
            emote_name = page_title.split()[0]
            my_logger.logger.debug(f"SUCCESS: {emote_name=}")
        except:
            emote_name = ""
        finally:
            driver.quit()

    return (emote_name, emote_id)


def get_emote_url(emote_id: str, img_size_7tv: int = 4) -> str:
    """ Extract the exact emote path from the emote ID given """
    emote_url = f"https://cdn.7tv.app/emote/{emote_id}/{img_size_7tv}x.webp"
    my_logger.logger.debug(f'{emote_url=}')
    return emote_url


def download_emote(emote_id: str, emote_url: str, img_type: str = "webp") -> str:
    """ Download the (webp) emote with the emote url given, and return its path """

    response = requests.get(emote_url)
    if response.status_code != 200:
        return ""
    # img type is webp by default, but can also be gif or png
    if img_type == "webp": # if the download is webp, this is because we're downloading to check if animated
        img_path = f"{DOWNLOADED_EMOTES_PATH}{emote_id}.{img_type}"
    else: # ie if gif or png - this means we are downloading the type for discord
        img_path = f"{DISCORD_EMOTES_PATH}{emote_id}.{img_type}"

    with open(img_path, "wb") as img:
        img.write(response.content) # response.content is the image content
    my_logger.logger.debug(f'SUCCESS - Downloaded Image. Path = {img_path}.')

    return img_path


def is_animated(img_path: str) -> bool:
    """ Checks if webp image is animated or not. """
    media_file = Image.open(img_path)
    # counting the number of frames. if frames > 1, it is animated
    index = 0
    for _ in ImageSequence.Iterator(media_file):
        index += 1
    if index > 1:
        return True
    else:
        return False


def discord_img(emote_id:str, file_path: str, emote_url_webp: str) -> str:
    """ Convert the webp image into a gif, in order to be uploaded to Discord, and return its path. """

    try: # big try-except block, I know this is bad practice!
        img = Image.open(file_path)
        img.info.pop('background', None) # remove background

        if is_animated(file_path): # check if it's animated.
            img_type = 'gif'
        else:
            img_type = 'png'

        discord_emote_url = emote_url_webp.replace('x.webp', f'x.{img_type}') # generate the correct png or gif url
        discord_img_path = download_emote(emote_id=emote_id, emote_url=discord_emote_url, img_type=img_type)
        if not discord_img_path: # if it can't navigate to the page
            return ""
        my_logger.logger.debug(f'SUCCESS - Discord Image Downloaded. Path = {discord_img_path}.')

    except:
        return ""
    
    return discord_img_path


def main(page_url: str, name_given: str = "", img_size_7tv: int = 4) -> tuple[str, str, str]:
    """ Main function. Downloads the image from the given url and converts to either
    a gif (if animated) or a png format (if not animated).
    It returns a 2-value tuple including the file path (empty string if false)
    and error message (empty string if no errors). """

    if name_given: # if a name was provided
        emote_name, emote_id = get_emote_details(page_url, name_given=name_given) # get emote id from the given page url
    else: # if a name was not provided
        emote_name, emote_id = get_emote_details(page_url) # get emote id from the given page url
        if not emote_name: # if it was unable to find the name from the URL
            logger_message = f'Invalid URL Provided.'
            my_logger.logger.error(logger_message)
            return (emote_name, "", logger_message)

    emote_url_webp = get_emote_url(emote_id, img_size_7tv=img_size_7tv) # get webp img url
    downloaded_img_path = download_emote(emote_id=emote_id, emote_url=emote_url_webp, img_type="webp") # download webp image
    if not downloaded_img_path: # if it failed to find the url
        logger_message = f'Invalid URL Provided.'
        my_logger.logger.error(logger_message)
        return (emote_name, "", logger_message)

    discord_img_path = discord_img(emote_id=emote_id, file_path=downloaded_img_path, emote_url_webp=emote_url_webp)
    if not discord_img_path: # if it failed to load the downloaded file
        logger_message = f'Failed to download Discord image for --{page_url}--.'
        my_logger.logger.error(logger_message)
        return (emote_name, "", logger_message)

    return (emote_name, discord_img_path, "") # return file path if the process was successful


if __name__ == "__main__":
    page_url = "https://7tv.app/emotes/60abf171870d317bef23d399" # test url
    main(page_url)