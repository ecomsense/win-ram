from traceback import print_exc
from typing import Dict, Any
from constants import O_CNFG
from importlib import import_module
from typing import Dict, Any


def login():
    try:
        # Get broker name from config
        broker_name = O_CNFG.get("broker")
        if not broker_name:
            raise ValueError("Broker not specified in config file")

        # Dynamically import the broker module
        module_path = f"stock_brokers.{broker_name}.{broker_name}"
        broker_module = import_module(module_path)

        # Get the broker class (assuming class name matches the broker name)
        BrokerClass = getattr(broker_module, broker_name.capitalize())

        # Initialize API with config
        api = BrokerClass(**O_CNFG)

        if api.authenticate():
            message = "API connected"
            send_messages(message)
            return api
        else:
            send_messages("Failed to authenticate... exiting")
            __import__("sys").exit(1)
    except Exception as e:
        print_exc()
        send_messages(f"Error: {e}")
        return None


def send_messages(msg):
    print(msg)


class Helper:
    _api = None

    @classmethod
    @property
    def api(cls):
        if cls._api is None:
            cls._api = login()
        return cls._api

    @classmethod
    def ohlc(cls, exchange, token):
        try:
            resp = cls._api.scriptinfo(exchange, token)
            if resp is not None:
                return resp
            else:
                raise ValueError("resp is none")
        except Exception as e:
            message = f"{e} while ltp"
            send_messages(message)
            print_exc()

    @classmethod
    def place_order(cls, bargs):
        try:
            send_messages(str(bargs))
            return cls._api.order_place(**bargs)
        except Exception as e:
            message = f"helper error {e} while placing order"
            send_messages(message)
            print_exc()
            return None

    @classmethod
    def order_book(cls) -> Dict[str, Any]:
        try:
            temp = cls._api.orders
            ord = {order["order_id"]: order for order in temp}
            if ord is not None:
                return ord
            else:
                return {}
        except Exception as e:
            send_messages(f"helper error {e} while getting order")
            print_exc()
            return {}


if __name__ == "__main__":
    Helper.api
    resp = Helper._api.finvasia.get_order_book()
    print(resp)
