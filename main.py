import json
import os
from typing import Optional, TypedDict

import pandas as pd
from dpath.util import get as dpath_get
from pandas import DataFrame
from selenium import webdriver
from selenium.common.exceptions import (
    WebDriverException,
)
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
    full_name: str
    spec_place: str
    spec_name: str
    initials: str
    gender: str
    assistant: str
    proc_name: str


def load_data_table(dir_path) -> DataFrame:
    table_headers = ["Nazwisko pacjenta", "Imię pacjenta", "Usługa", "Data"]

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
        df.insert(2, "Plec", "0")
        df.insert(5, "Inicjały", "0")
        df.insert(6, "Asysta", "")  # TODO: support for asysta

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


class SMKAutomation:
    """Web automation using Selenium for filling procedure tables in SMK.

    Rows data is taken from excel files. Some data is taken from config file.
    """

    LOGIN_URL = "https://smk.ezdrowie.gov.pl/login.jsp?locale=pl"
    DATA_DIR = "./arkusze"

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
        table = load_data_table(self.DATA_DIR)
        print(f'\nLoaded procedures: \n{table.head(10)}')

        self._login(
            username=self.config["username"], password=self.config["password"]
        )
        self._go_to_procedure_tables()
        input(
            (
                "Make sure the proper procedure table is open!\n"
                "Press [Enter] to start filling the table:"
            )
        )
        try:
            self._fill_table(
                table,
                year=self.config["rok_szkolenia"],
                code=self.config["kod_zabiegu_wartosc_na_liscie"],
                doctor_name=self.config["imie_nazwisko_lekarza"],
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

    def _get_element(
        self,
        xpath_key: str,
        wait_long: bool = False,
        xpath_value_kwargs: Optional[dict] = None,
    ):
        """Returns element by xpath json key"""
        method = self.wait if not wait_long else self.wait_long
        xpath_value = dpath_get(self.xpaths, xpath_key)
        if xpath_value_kwargs:
            xpath_value = xpath_value.format(**xpath_value_kwargs)
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
        year: str,
        code: str,
        doctor_name: str,
        spec_place: str,
        spec_name: str,
    ):
        """Fills the procedure table with data from the excel files"""
        print(f"Adding new empty table rows:")
        for i in range(table.shape[0]):
            self._get_element("procedures/add_new_btn").click()

        print(f"Filling table rows:")
        for i in tqdm(range(table.shape[0])):
            row_data = RowData(
                row_index=i + 1,
                date=table.iat[i, 4],
                year=year,
                code=str(int(code) - 1),
                full_name=doctor_name,
                spec_place=spec_place,
                spec_name=spec_name,
                initials=table.iat[i, 5],
                gender=table.iat[i, 2],
                assistant=table.iat[i, 6],
                proc_name=table.iat[i, 3],
            )
            try:
                self._fill_row(row_data)
            except Exception as e:
                print(f"Error occured for row: {row_data}")
                raise e

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
        get("procedures/nazwisko").send_keys(row_data["full_name"])
        Select(get("procedures/miejsce")).select_by_index(
            row_data["spec_place"]
        )
        Select(get("procedures/nazwa_stazu")).select_by_index(
            row_data["spec_name"]
        )
        get("procedures/inicjaly").send_keys(row_data["initials"])
        Select(get("procedures/plec")).select_by_value(row_data["gender"])
        get("procedures/asysta").send_keys(row_data["assistant"])
        get("procedures/nazwa_procedury").send_keys(row_data["proc_name"])


if __name__ == "__main__":
    SMKAutomation().run()
