import re
from typing import Literal


dct_sym = {
    "NIFTY": {
        "diff": 50,
        "index": "Nifty 50",
        "exchange": "NSE",
        "token": "26000",
        "depth": 16,
    },
    "BANKNIFTY": {
        "diff": 100,
        "index": "Nifty Bank",
        "exchange": "NSE",
        "token": "26009",
        "depth": 25,
    },
    "MIDCPNIFTY": {
        "diff": 100,
        "index": "NIFTY MID SELECT",
        "exchange": "NSE",
        "token": "26074",
        "depth": 21,
    },
    "FINNIFTY": {
        "diff": 50,
        "index": "Nifty Fin Services",
        "exchange": "NSE",
        "token": "26037",
        "depth": 16,
    },
}


class Symbols:
    """
    Class to get symbols from finvasia

    Parameters
    ----------
    symbol : str
        Symbol
    expiry : str
        Expiry

    Returns
    -------
    None
    """

    def __init__(self, option_exchange: str, base: str, expiry: str):
        self._option_exchange = option_exchange
        self._base = base
        self.expiry = expiry

    def get_atm(self, ltp) -> int:
        current_strike = ltp - (ltp % dct_sym[self._base]["diff"])
        next_higher_strike = current_strike + dct_sym[self._base]["diff"]
        if ltp - current_strike < next_higher_strike - ltp:
            return int(current_strike)
        return int(next_higher_strike)

    def find_option_type(self, tradingsymbol):
        option_pattern = re.compile(rf"{self._base}{self.expiry}([CP])\d+")
        match = option_pattern.match(tradingsymbol)
        if match:
            return match.group(1)  # Returns 'C' for call, 'P' for put
        else:
            return False

    def get_atm_strike(
        self, oc, expiry_date, option_type: Literal["call_option", "put_option"]
    ):
        data = oc["result"][0]
        expiry_date = data["expiry_date"]
        for strike in data["strikes"]:
            if data["expiry_date"] == expiry_date:
                selected_option = strike[option_type]
                short_form = "CE" if option_type == "call_option" else "PE"
                return {
                    "expiry_date": expiry_date,
                    "strike_price": strike["strike_price"],
                    "option_type": short_form,
                    "token": selected_option["token"],
                    "exchange": selected_option["exchange"],
                    "symbol": selected_option["symbol"],
                    "trading_symbol": selected_option["trading_symbol"],
                    "close_price": float(selected_option["close_price"]),
                }
            else:
                print(data)


if __name__ == "__main__":
    symbols = Symbols("NFO", "BANKNIFTY", "26JUN24")
