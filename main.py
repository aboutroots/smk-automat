import json
import math
import os
from datetime import date
from typing import Optional, TypedDict

import pandas as pd
from dpath.util import get as dpath_get
from pandas import DataFrame
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager


class RowData(TypedDict):
    row_index: int
    date: str
    year: str
    code: str
    spec_place: str
    spec_name: str
    initials: str
    gender: str
    doctor_name: str
    assistant_name: str
    proc_name: str


def load_data_table(dir_path: str, with_assist: bool) -> DataFrame:
    table_headers = ["Nazwisko pacjenta", "Imię pacjenta", "Usługa", "Data"]
    if with_assist:
        table_headers.append("Lekarz opisujący")

    data_files = os.listdir(dir_path)
    df = pd.DataFrame()
    for file_index in range(len(data_files)):
        try:
            xls_file = pd.ExcelFile(
                os.path.join(dir_path, data_files[file_index])
            )
        except ValueError as e:
            if (
                "Excel file format cannot be determined, you must specify an engine manually"
                in str(e)
            ):
                raise ValueError(
                    "Please close all excel files before running the automation"
                )
            raise e
        new_df = xls_file.parse(0)
        df = df.append(new_df, ignore_index=True)
        df = df.astype(str)
        df = df[table_headers]
        if with_assist:
            column_to_move = df.pop("Lekarz opisujący")
            df.insert(2, "Plec", "0")
            df.insert(5, "Inicjały", "0")
            df.insert(6, "Lekarz", column_to_move)
        else:
            df.insert(2, "Plec", "0")
            df.insert(5, "Inicjały", "0")
            df.insert(6, "Lekarz", "")

    for i in range(df.shape[0]):
        # convert date
        df.iat[i, 4] = df.iat[i, 4][0:10]
        # trim fullname
        head, sep, tail = df.iat[i, 1].partition(" ")
        df.iat[i, 1] = head
        # create initials
        df.iat[i, 5] = df.iat[i, 1][0] + df.iat[i, 0][0]
        # identify gender (names with "a" at the end are females)
        name = df.iat[i, 1]
        gender = "K" if name.lower().endswith("a") else "M"
        df.iat[i, 2] = gender
        # cleanup "assistant"
        if df.iat[i, 6] == "nan":
            df.iat[i, 6] = ""
    return df


def parse_starting_year(input_str: str) -> date:
    day, month, year = [int(x) for x in input_str.split(".")]
    return date(year, month, day)


def parse_procedure_date(input_str: str) -> date:
    year, month, day = [int(x) for x in input_str.split("-")]
    return date(year, month, day)


class SMKAutomation:
    """Web automation using Selenium for filling procedure tables in SMK.

    Rows data is taken from excel files. Some data is taken from config file.
    """

    LOGIN_URL = "https://smk.ezdrowie.gov.pl/login.jsp?locale=pl"
    DATA_DIR = "./arkusze"
    MAX_VISIBLE_ROWS_IN_TABLE = 100

    def __init__(self):
        with open("./xpaths.json") as xpaths_data:
            self.xpaths = json.load(xpaths_data)
        with open("./config.json") as config_data:
            self.config = json.load(config_data)
        self.driver = self._setup_webdriver()
        self.wait = WebDriverWait(self.driver, 50, poll_frequency=1)
        self.wait_long = WebDriverWait(self.driver, 1000, poll_frequency=1)

    def run(self):
        self.driver.get(self.LOGIN_URL)
        with_assist = (
            str(input("With assist? Write 1 or 0 and press [Enter]:")) == "1"
        )
        table = load_data_table(self.DATA_DIR, with_assist=with_assist)
        print(
            f"\nLoaded procedures (total: {table.shape[0]}): \n{table.head(10)}\n..."
        )

        self._login(
            username=self.config["username"], password=self.config["password"]
        )
        self._go_to_procedure_tables()
        try:
            self._fill_table(
                table,
                your_name=self.config["imie_nazwisko_lekarza"],
                starting_year=parse_starting_year(
                    self.config["data_zaczecia_rezydentury"]
                ),
                spec_place=self.config["miejsce_szkolenia_pozycja_na_liscie"],
                spec_name=self.config["nazwa_szkolenia_pozycja_na_liscie"],
            )
            print("Everything ok! Remember to save!")
        except WebDriverException as e:
            print(f"A selenium error occured: {str(e)[:1500]}")
        input("[Enter] to exit application")

    @staticmethod
    def _setup_webdriver() -> WebDriver:
        options = Options()
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        return webdriver.Chrome(
            ChromeDriverManager().install(), options=options
        )

    def _get_xpath(
        self, xpath_key: str, xpath_value_kwargs: Optional[dict] = None
    ) -> str:
        xpath_value = dpath_get(self.xpaths, xpath_key)
        if xpath_value_kwargs:
            xpath_value = xpath_value.format(**xpath_value_kwargs)
        return xpath_value

    def _get_element(
        self,
        xpath_key: str,
        wait_long: bool = False,
        xpath_value_kwargs: Optional[dict] = None,
        direct_xpath: bool = False,
    ):
        """Returns element by xpath json key"""
        method = self.wait if not wait_long else self.wait_long
        if direct_xpath:
            xpath_value = xpath_key
        else:
            xpath_value = self._get_xpath(xpath_key, xpath_value_kwargs)
        return method.until(EC.element_to_be_clickable((By.XPATH, xpath_value)))

    def _login(self, username, password):
        """Performs user login"""
        self._get_element("login/btn_smk").click()
        self._get_element("login/username").send_keys(username)
        self._get_element("login/password").send_keys(password)
        self._get_element("login/cookies_btn").click()
        self._get_element("login/login_btn").click()

    def _go_to_procedure_tables(self):
        """Redirect to view with procedure tables"""
        self._get_element("go_to_primary_table/btn_card_1").click()
        self._get_element(
            "go_to_primary_table/btn_table_expand", wait_long=True
        ).click()
        self._get_element("go_to_primary_table/btn_table_edit").click()
        self._get_element("go_to_primary_table/btn_index_card").click()
        self._get_element("go_to_primary_table/btn_module_expand").click()

    def _fill_table(
        self,
        table: DataFrame,
        starting_year: date,
        your_name: str,
        spec_place: str,
        spec_name: str,
    ):
        """Fills the procedure table with data from the excel files"""
        button_xpath = input(
            (
                "Make sure the proper procedure table is open!\n"
                'Paste "Dodaj" button XPATH and click [Enter]:'
            )
        )
        rows_count = table.shape[0]
        print(f"Adding new empty table rows:")
        for _ in tqdm(range(rows_count)):
            self._get_element(button_xpath, direct_xpath=True).click()

        print(f"Filling table rows:")
        # Process table rows in groups to allow clicking on "next page" in between
        # groups
        batch_n = math.ceil(rows_count / self.MAX_VISIBLE_ROWS_IN_TABLE)
        for batch_idx in range(batch_n):
            print(f"Starting filling rows on page {batch_idx + 1}/{batch_n}.")
            if batch_idx != 0:
                input(
                    "Press [Enter] to continue. You may need to switch to next page in the"
                    " table first"
                )
            start_idx = batch_idx * self.MAX_VISIBLE_ROWS_IN_TABLE
            end_idx = (
                batch_idx * self.MAX_VISIBLE_ROWS_IN_TABLE
                + self.MAX_VISIBLE_ROWS_IN_TABLE
            )
            if end_idx > rows_count:
                end_idx = rows_count
            for i in tqdm(range(start_idx, end_idx)):
                row_index = i + 1 - batch_idx * self.MAX_VISIBLE_ROWS_IN_TABLE
                row_data = self._get_row_data(
                    table=table,
                    current_index=i,
                    row_index=row_index,
                    your_name=your_name,
                    starting_year=starting_year,
                    spec_name=spec_name,
                    spec_place=spec_place,
                )
                try:
                    self._fill_row(row_data)
                except Exception as e:
                    print(f"Error occured for row {i}: {row_data}")
                    raise e

    @staticmethod
    def _get_row_data(
        table: DataFrame,
        current_index: int,
        row_index: int,
        your_name: str,
        starting_year: date,
        spec_place: str,
        spec_name: str,
    ) -> RowData:
        """Parse row information into a final format for filling"""
        doctor = table.iat[current_index, 6]
        doctor_name = doctor if doctor else your_name
        assistant_name = your_name if doctor else ""
        code = 1 if assistant_name else 0  # assistant or operator

        procedure_date = table.iat[current_index, 4]
        procedure_date_obj = parse_procedure_date(procedure_date)
        year_delta = procedure_date_obj - starting_year
        year = year_delta.days // 365 + 1
        return RowData(
            row_index=row_index,
            date=procedure_date,
            year=str(year),
            code=str(code),
            spec_place=spec_place,
            spec_name=spec_name,
            initials=table.iat[current_index, 5],
            gender=table.iat[current_index, 2],
            proc_name=table.iat[current_index, 3],
            doctor_name=doctor_name,
            assistant_name=assistant_name,
        )

    def _fill_row(self, row_data: RowData):
        """Fills the single procedure table row with provided data"""

        get = lambda key: self._get_element(
            key, xpath_value_kwargs={"idx": row_data["row_index"]}
        )
        get("procedures/data").send_keys(row_data["date"])
        Select(get("procedures/rok_szkolenia")).select_by_value(
            row_data["year"]
        )
        Select(get("procedures/kod_zabiegu")).select_by_index(row_data["code"])
        get("procedures/nazwisko").send_keys(row_data["doctor_name"])
        Select(get("procedures/miejsce")).select_by_index(
            row_data["spec_place"]
        )
        Select(get("procedures/nazwa_stazu")).select_by_index(
            row_data["spec_name"]
        )
        get("procedures/inicjaly").send_keys(row_data["initials"])
        Select(get("procedures/plec")).select_by_value(row_data["gender"])

        get("procedures/asysta").send_keys(row_data["assistant_name"])

        get("procedures/nazwa_procedury").send_keys(row_data["proc_name"])


if __name__ == "__main__":
    SMKAutomation().run()
