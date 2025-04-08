import curl_cffi.requests as requests
from curl_cffi.curl import CurlHttpVersion
import pyotp
from constants import O_CNFG
import sys
import os
import pendulum as pdlm
import pandas as pd

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from stocko.stockoapi import AlphaTrade
from stock_brokers.finvasia.finvasia import Finvasia


def history():
    cred = O_CNFG["finvasia"]
    api = Finvasia(**cred)
    if api.authenticate():
        fm = pdlm.now().subtract(days=6)
        fm = fm.replace(hour=9, minute=0, second=0, microsecond=0).timestamp()
        to = pdlm.now().replace(hour=15, minute=30, second=0, microsecond=0).timestamp()
        resp = api.historical("NSE", "26000", fm, to, 5)
        df = (
            pd.DataFrame(resp)[["into", "inth", "intl", "intc", "time"]]
            .rename(
                columns={
                    "into": "open",
                    "inth": "high",
                    "intl": "low",
                    "intc": "close",
                    "time": "timestamp",
                },
            )
            .head(115)
            .sort_index(ascending=False)
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d-%m-%Y %H:%M:%S")
        return df
    else:
        print("failed to authenticate finvasia")


def get_access_token(user_id, password, totp_key):

    base_url = "https://web.stocko.in/assets/broker/app-config.json"
    login_url = "https://web.stocko.in/api/v3/user/login"
    otp_url = "https://web.stocko.in/api/v3/user/validatetotp"

    headers = {"x-device-type": "web"}

    with requests.Session(
        impersonate="safari_ios", headers=headers, http_version=CurlHttpVersion(2)
    ) as s:
        _ = s.get(base_url)
        login_response = s.post(
            login_url, data={"login_id": user_id, "password": password}
        )
        if login_response.status_code == 200:
            twofa_token = (
                login_response.json()
                .get("data", {})
                .get("twofa", {})
                .get("twofa_token")
            )

            if twofa_token:
                otp_response = s.post(
                    otp_url,
                    data={
                        "login_id": user_id,
                        "twofa_token": twofa_token,
                        "totp": pyotp.TOTP(totp_key).now(),
                    },
                )
                if otp_response.status_code == 200:
                    auth_token = otp_response.json().get("data", {}).get("auth_token")
                    print(" AUTH TOKEN ".center(150, "="))
                    print(auth_token)
                    print("*" * 150)
                else:
                    print(f"Error in otp validation :: {otp_response.text}")
        else:
            print(f"Error in login response :: {login_response.text}")

    return auth_token


def login():
    cred = O_CNFG["stocko"]
    user_id = cred["user_id"]
    password = cred["password"]
    totp_key = cred["totp_key"]
    access_token = get_access_token(
        user_id=user_id, password=password, totp_key=totp_key
    )
    obj = AlphaTrade(
        login_id=user_id,
        password=password,
        totp=totp_key,
        client_secret=cred["client_secret"],
        access_token=access_token,
        master_contracts_to_download=["NSE", "NFO"],
    )
    return obj


class Helper:

    _api = None
    _history = None

    @classmethod
    def api(cls):
        if cls._api is None:
            cls._api = login()
        return cls._api

    @classmethod
    def history(cls):
        if cls._history is None:
            cls._history = history()
        return cls._history


if __name__ == "__main__":
    Helper.api()
    resp = Helper.history()
