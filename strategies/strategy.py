from traceback import print_exc
from toolkit.kokoo import timer
from toolkit.logger import Logger
import pendulum as pdlm


class Strategy:

    def __init__(self, kwargs, helper_class):
        self._token = kwargs["symbol"]["instrument_token"]
        self._wait = kwargs["trade"]["wait_secs"]
        self._buy_plus = kwargs["trade"]["buy_plus"]
        self._order_args = kwargs["order"]
        self._orders = {}
        self._high = 0
        self.fn = self.enter_pending_order
        self.Helper = helper_class
        self.logging = Logger(10)

    def enter_pending_order(self):
        resp = self.Helper.ohlc(self._order_args["exchange"], self._token)
        if resp:
            self._high = float(resp["h"])
            args = self._order_args.copy()
            args["trigger_price"] = self._high + self._buy_plus
            args["price"] = self._high + self._buy_plus + 0.10
            resp = self.Helper.place_order(args)
            if resp:
                self._order_id = resp
                self.fn = self.is_order_complete
                self.logging.info(f"buy order {resp} is complete")
            else:
                self.logging.info(f"order failed with {resp=}")

    def is_order_complete(self):
        try:
            self._order_time = pdlm.now().add(seconds=self._wait)
            self._orders = self.Helper.order_book()
            if self._orders[self._order_id]["status"] == "complete":
                self.fn = self.exit
            else:
                self.logging.info(
                    f"buy order {self._order_id} status is {self._orders[self._order_id]['status']}"
                )
                timer(1)
        except Exception as e:
            print(f"{e} while is_order_complete")
            print_exc()

    def exit(self):
        try:
            args = self._order_args.copy()
            args["order_type"] = "MKT"
            args["trigger_price"] = 0
            args["price"] = 0
            while pdlm.now() < self._order_time:
                self.logging.info(
                    "waiting till {self._order_time.format('HH:mm:ss')} to place sell order"
                )
                timer(0.25)
            else:
                resp = self.Helper.place_order(args)
                if resp:
                    self.fn = self.enter_pending_order
                if not resp:
                    self.logging.error(f"exit failed {resp=}")
                    self.fn = None

        except Exception as e:
            print(f"{e} while exit")
            print_exc()

    def run(self):
        try:
            self.fn()
        except Exception as e:
            print(f"{e} while running strategy")
