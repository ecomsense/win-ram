import os
from datetime import datetime
import sys
from time import sleep
import warnings
import pandas as pd

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from constants import S_DATA
from stocko import (
    LiveFeedType,
    TransactionType,
    OrderType,
    ProductType,
)

warnings.filterwarnings("ignore")


class Wserver:
    socket_opened = False
    SYMBOLDICT = {}
    live_data = {}
    ord_updt = []

    def __init__(self, broker) -> None:
        self.broker = broker
        self.broker.start_websocket(
            subscribe_callback=self.event_handler_quote_update,
            socket_open_callback=self.open_callback,
            run_in_background=True,
        )
        while not self.socket_opened:
            print("waiting for socket to open")
            pass
        print("Connected to WebSocket...")
        # broker.subscribe(broker.get_instrument_by_symbol('NSE', 'TATASTEEL-EQ'), LiveFeedType.MARKET_DATA)
        # sleep(3)

    def event_handler_quote_update(self, inmessage):
        fields = [
            "token",
            "ltp",
            "pc",
            "close",
            "open",
            "high",
            "low",
            "volume",
            "ltq",
            "ltp",
            "best_bid_price",
            "best_ask_price",
            "atp",
            "current_oi",
            "initial_oi",
            "yearly_high",
            "yearly_low",
            "low_dpr",
            "high_dpr",
        ]
        message = {
            field: inmessage[field] for field in set(fields) & set(inmessage.keys())
        }

        key = inmessage["exchange"] + "|" + inmessage["instrument"][2]
        if key in self.SYMBOLDICT:
            symbol_info = self.SYMBOLDICT[key]
            symbol_info.update(message)
            self.SYMBOLDICT[key] = symbol_info
            self.live_data[key] = symbol_info
        else:
            self.SYMBOLDICT[key] = message
            self.live_data[key] = message
        # print(f"WS quote updated:- \n",live_data)

    def order_update_callback(self, msg):
        self.ord_updt = msg
        print("\n WS order update:- \n ", self.ord_updt)

    def open_callback(self):
        self.socket_opened = True
        print("\n Websocket opened!")
        subs_lst = []

    def exchange_messages(self, exch_msg):
        print("\n Exchange msg : ", exch_msg)

    def market_status(self, mkt_Stat):
        print("\n Market Status : ", mkt_Stat)


def place_order(
    exchange: str, symbol: str, qty: int, price: float, BS: str, order_type: str
):
    ordid = 0
    try:
        if BS == "SELL":
            t_type = TransactionType.Sell
        else:
            t_type = TransactionType.Buy

        if order_type == "MARKET":
            order_type = (OrderType.Market,)
            price = 0.0
        else:
            order_type = (OrderType.Limit,)
            price = price

        ordid = broker.place_order(
            transaction_type=t_type,
            instrument=broker.get_instrument_by_symbol(exchange, symbol),
            quantity=qty,
            order_type=OrderType.Market,
            product_type=ProductType.Delivery,
            price=price,
            trigger_price=0.0,
            stop_loss=None,
            square_off=None,
            trailing_sl=None,
            is_amo=False,
        )
    except Exception as Er:
        print(f"Error: {Er}")
    return ordid


if __name__ == "__main__":
    from api import Helper

    try:
        print("Running Stocko app..")
        # Start websocket
        broker = Helper.api()
        print(
            broker.get_candles(
                "NSE",
                "Nifty 50",
                datetime(2025, 1, 14),
                datetime.now(),
                interval=30,
                time="minute",
            )
        )
        ## Inititate variables for OPTIONCHAIN and create OC table
        Token = broker.get_instrument_by_symbol("NSE", "Nifty 50")
        strikes = 3
        mid_strike = 23000
        oc = broker.get_optionchain(Token, strikes, mid_strike)
        data = oc["result"][0]
        rows = []
        expiry_date = data["expiry_date"]
        for strike in data["strikes"]:
            strike_price = strike["strike_price"]
            call = strike["call_option"]
            put = strike["put_option"]
            rows.append(
                {
                    "expiry_date": expiry_date,
                    "strike_price": strike_price,
                    "option_type": "CE",
                    "token": call["token"],
                    "exchange": call["exchange"],
                    "symbol": call["symbol"],
                    "trading_symbol": call["trading_symbol"],
                    "close_price": float(call["close_price"]),
                }
            )
            rows.append(
                {
                    "expiry_date": expiry_date,
                    "strike_price": strike_price,
                    "option_type": "PE",
                    "token": put["token"],
                    "exchange": put["exchange"],
                    "symbol": put["symbol"],
                    "trading_symbol": put["trading_symbol"],
                    "close_price": float(put["close_price"]),
                }
            )
        df = pd.DataFrame(rows)
        print(df)
        # save to CSV
        df.to_csv(S_DATA + "options_table.csv", index=False)

        print("\n GET INSTRUMENT BY SYMBOL :-")
        print("#" * 50, "\n")
        idx = broker.get_instrument_by_symbol("NSE", "NIFTY50 EQL Wgt")
        print(idx, "\n")

        print("Scrip info :-")
        print("#" * 50, "\n")
        scrip_info = broker.get_scrip_info(idx)
        print(scrip_info, "\n")
        """
        print("Profile :-")
        print("#" * 50, "\n")
        profile = broker.get_profile()
        print(profile, "\n")

        print("Balance :-")
        print("#" * 50, "\n")
        bal = broker.get_balance()
        print(bal, "\n")

        print("Demat holdings :-")
        print("#" * 50, "\n")
        holdings = broker.get_dematholdings()
        print(holdings, "\n")

        print("Subscribed exchanges :-")
        print("#" * 50, "\n")
        enabled_exchanges = broker.get_exchanges()
        print(enabled_exchanges, "\n")
        print("Ws live feed subscription, MARKET_DATA :-")
        print("#" * 50, "\n")
        print(type(Token))
        broker.subscribe(idx, LiveFeedType.MARKET_DATA)
        """
        sleep(2)
        print("\n Ws live feed subscription, COMPACT :-")
        print("#" * 50, "\n")
        broker.subscribe(Token, LiveFeedType.COMPACT)
        """
        sleep(2)
        print("\n Ws live feed subscription, SNAPQUOTE :-")
        print("#" * 50, "\n")
        broker.subscribe(Token, LiveFeedType.SNAPQUOTE)
        sleep(2)
        print("\n Ws live feed subscription, FULL SNAPQUOTE :-")
        print("#" * 50, "\n")
        broker.subscribe(Token, LiveFeedType.FULL_SNAPQUOTE)
        sleep(2)

        print("\n Ws live feed subscription for IDEA-EQ Order testing :-")
        print("#" * 50, "\n")
        Token = broker.get_instrument_by_symbol("NSE", "IDEA-EQ")
        broker.subscribe(Token, LiveFeedType.MARKET_DATA)
        sleep(1)
        ############ ORDERS

        # Cautiously Place market order -
        ord1 = place_order("NSE", "IDEA-EQ", 1, 5.00, "BUY", "LIMIT")
        print("\nOrder placed :- ", ord1)
        print("\n Order Number - ", ord1["data"]["oms_order_id"])
        print("#" * 50, "\n")
        sleep(2)

        print("WS Order update in Dataframe :- ")
        print(pd.DataFrame([ord_updt]))
        print("#" * 50, "\n")
        ##############################################
        print("Order status :-")
        ord_hist = broker.get_order_history(order_id=ord1["data"]["oms_order_id"])
        print(ord_hist)
        print("#" * 50, "\n")

        print("Tradeboook :-")
        tradebook = broker.get_tradebook()
        print(tradebook)
        print("#" * 50, "\n")

        print("Orderbook completed :-")
        ordbook = broker.get_orderbook(pending=False)
        print(ordbook)
        print("#" * 50, "\n")

        print("Orderbook pendings :-")
        ordbook = broker.get_orderbook(pending=True)
        print(ordbook)
        print("#" * 50, "\n")

        print("Orderbook default (pending) :-")
        ordbook = broker.get_orderbook()
        print(ordbook)
        print("#" * 50, "\n")

        print("Live netpositions :-")
        day_pos = broker.fetch_live_positions()
        print(day_pos)
        print("#" * 50, "\n")

        print("Historical netpositions :-")
        net_pos = broker.fetch_netwise_positions()
        print(net_pos)
        print("#" * 50, "\n")

        best_ask_pricent("cancel order :-")
        cancel = broker.cancel_order(ord1["data"]["oms_order_id"])
        print(cancel)
        print("#" * 50, "\n")
        """

    except (KeyboardInterrupt, SystemExit):
        print("Keyboard Interrupt. EXITING ....")
        sys.exit()
