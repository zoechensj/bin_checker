from datetime import datetime
import logging
from dateutil import parser
import re
from typing import List, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from contextlib import closing
from os import getenv


# setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Regular expression to match the date format in the collection information
DATE_PATTERN = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})"
)


def setup_chrome_driver() -> webdriver.Chrome:
    """
    Sets up the Chrome WebDriver with necessary options.
    Returns a Chrome WebDriver instance.
    """
    # Set up Chrome options
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  # optional, but useful in some cases
    options.add_argument("--disable-software-rasterizer")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)  # Wait for elements to load
    return driver


def get_north_herts_bins() -> List[Tuple[datetime, str]]:
    """
    Given a specified house number and postcode, scrapes NHDC Waste and
    Recycling portal for upcoming bin collections and returns a List of
    Tuples (collection_date, collection_description)
    """
    """ Returns the web address for my address bin collection page """
    # load environment variables
    HOME_URL = getenv("HOME_URL")
    POST_CODE = getenv("POST_CODE")
    ADDRESS = getenv("ADDRESS")

    if not HOME_URL or not POST_CODE or not ADDRESS:
        raise ValueError("HOME_URL environment variable is not set.")
    else:
        logger.info(
            "HOME_URL, POST_CODE and ADDRESS environment variables are set. Starting scraping..."
        )

        with closing(setup_chrome_driver()) as driver:
            logger.info("Setting up Chrome driver for bins scraping...")

            # Set up the Chrome driver
            wait = WebDriverWait(driver, 10)
            driver.get(HOME_URL)
            logger.info(f"started with {HOME_URL}")

            # Input postcode
            input_box = wait.until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "relation_path_type_ahead_search")
                )
            )
            logger.info("find the input box for postcode and house number.")
            # input the postcode in the input box, clear the input box first
            input_box.clear()
            input_box.send_keys(POST_CODE)
            logger.info(f"input postcode: {POST_CODE}")

            # select the correct address from the dropdown
            address_xpath = f'//li[contains(@aria-label, "{ADDRESS}")]'
            try:
                address_option = wait.until(
                    EC.presence_of_element_located((By.XPATH, address_xpath))
                )
                address_option.click()
                logger.info(f"input address options: {ADDRESS}")

            except Exception as e:
                logger.error(f"Address '{ADDRESS}' not found in the list.")
                raise ValueError(
                    f"Address {ADDRESS} isn't found in the dropdown. Please check the address."
                ) from e

            # click the button to submit the address
            button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//input[@value='Select address and continue']")
                )
            )
            button.click()
            logger.info("Clicked the button to submit the address.")

            """ Load to a new page with the collection information """
            # find the collection information on the new page
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "value-as-text")))
            elements = driver.find_elements(By.CLASS_NAME, "value-as-text")

            collection_info = [element.text for element in elements]
            logger.info("Found collection information on the new page.")

            matched_bins = []
            for i, item in enumerate(collection_info):
                match = DATE_PATTERN.search(item)
                if match:
                    try:
                        collection_date = parser.parse(match.group(0))
                        bin_name = collection_info[
                            i - 1
                        ]  # The bin name is usually the previous item
                        matched_bins.append((collection_date, bin_name))
                        logger.info(
                            f"collection has found {collection_date} for {bin_name}"
                        )
                    except ValueError as e:
                        logger.warning(f"Error parsing date from item '{item}': {e}")
            logger.info(f"Find {len(matched_bins)} matched bins with collection dates.")
            return matched_bins


if __name__ == "__main__":
    result = get_north_herts_bins()
    print(result)
