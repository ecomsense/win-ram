from ast import Dict
import curl_cffi.requests as requests
from curl_cffi.curl import CurlHttpVersion
import pyotp
from constants import O_CNFG
import sys
import os
import pendulum as pdlm
import pandas as pd
from stock_brokers.finvasia.finvasia import Finvasia

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from stocko import LiveFeedType, Instrument


from wserver import Wserver

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from stocko.stockoapi import AlphaTrade


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
            cls._ws = Wserver(cls._api)
            Token = cls._ws.broker.get_instrument_by_symbol("NSE", "Nifty 50")
            cls._ws.broker.subscribe(Token, LiveFeedType.COMPACT)
        return cls._api

    @classmethod
    def ticks(cls):
        return cls._ws.live_data

    @classmethod
    def history(cls):
        if cls._history is None:
            cls._history = history()
        return cls._history

    @classmethod
    def place_bo(cls, **kwargs):
        try:
            inst = Instrument(
                exchange=kwargs["exchange"],
                token=kwargs["token"],
                symbol=kwargs["symbol"],
                name="NIFTY",
                expiry=kwargs["expiry_date"],
                lot_size=75,
            )
            print(inst)
            resp = cls._api.buy_bo(
                instrument=inst,
                qty=75,
                price=kwargs["close_price"] + 20,
                trigger_price=None,
                stop_loss_value=8,
                square_off_value=5,
            )
            print(resp)
            return resp
        except Exception as e:
            print(e)

    @classmethod
    def _get_book(cls, bookname):
        payload = {"client_id": "MM781"}
        if bookname == "trade":
            resp = cls._api.fetch_trades(payload)
        elif bookname == "completed_orders":
            resp = cls._api.fetch_completed_orders(payload)
        elif bookname == "pending_orders":
            resp = cls._api.fetch_pending_orders(payload)
        else:
            resp = None

        if resp and any(resp):
            return resp
        else:
            return [{}]

    @classmethod
    def tradebook(cls):
        return cls._get_book("trade")

    @classmethod
    def completed_orderbook(cls):
        return cls._get_book("completed_orders")

    @classmethod
    def pending_orderbook(cls):
        return cls._get_book("pending_orders")

    @classmethod
    def orderbook(cls):
        return cls._get_book("order")


if __name__ == "__main__":
    try:
        Helper.api()
        instrument = Instrument(
            exchange="NFO",
            token="48200",
            symbol="NIFTY2541722850CE",
            name="NIFTY",
            expiry="17APR25",
            lot_size=75,
        )
        if not isinstance(instrument, Instrument):
            raise TypeError("Required parameter instrument not of type Instrument")
        else:
            print("instrument is successfuly validated")
        """
        print(Helper.pending_orderbook())
        print(Helper.completed_orderbook())
        # resp = Helper.history()
        while True:
            Helper.ticks()
        """
    except KeyboardInterrupt as k:
        print(k)
        __import__("sys").exit(0)
