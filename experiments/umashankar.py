import finplot as fplt
import numpy as np
import pandas as pd
import time
from PyQt6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QPushButton,
    QGridLayout,
    QGraphicsView,
    QComboBox,
    QLabel,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QThread
import random


class OrderManager:
    def __init__(self):
        self.active_threads = []

    def place_buy_order(self):
        order_id = f"BUY-{random.randint(1000, 9999)}"
        print(f"Placing buy order: {order_id}")
        time.sleep(0.1)
        print(f"✅ Buy order {order_id} placed.")

    def start_buy_thread(self):
        broker_thread = BrokerThread(self.place_buy_order)
        self.active_threads.append(broker_thread)
        broker_thread.finished.connect(
            lambda: self.active_threads.remove(broker_thread)
        )
        broker_thread.start()


class BrokerThread(QThread):
    def __init__(self, order_function):
        super().__init__()
        self.order_function = order_function

    def run(self):
        self.order_function()


class ChartData:
    def __init__(self, symbol="DUMB"):
        self.symbol = symbol
        self.df = self.generate_data()

    def generate_data(self):
        random.seed(hash(self.symbol))
        v = np.random.normal(size=(1000, 4))
        df = pd.DataFrame(v, columns=["low", "open", "close", "high"])
        df = df.rolling(10).mean()
        ma = df["low"].rolling(20).mean().diff()
        for col in df.columns:
            df[col] *= ma * 100
        df.values.sort(axis=1)
        df = (df.T + np.sin(df.index / 87) * 3 + np.cos(df.index / 201) * 5).T + 20
        flip = df["open"].shift(-1) <= df["open"]
        df.loc[flip, ["open", "close"]] = df.loc[flip, ["close", "open"]].values
        df["volume"] = df["high"] - df["low"]
        df.index = np.linspace(1608332400 - 60 * 1000, 1608332400, 1000)  # epoch time
        return df.dropna(subset=["open", "close", "high", "low", "volume"])

    def update_data(self, symbol):
        self.symbol = symbol
        self.df = self.generate_data()


class ChartManager:
    def __init__(self, ax, data, price_label):
        self.ax = ax
        self.data = data
        self.price_label = price_label
        self.current_index = 1
        self.horizontal_line = None
        self.last_update_time = time.time()
        self.update_interval = 0.5

    def update_chart(self):
        if self.current_index >= len(self.data.df):
            return

        df_subset = self.data.df.iloc[: self.current_index + 1]
        self.ax.clear()
        fplt.candlestick_ochl(df_subset, ax=self.ax)

        latest_price = df_subset["close"].iloc[-1]
        self.price_label.setText(f"{latest_price:.2f}")

        fplt.refresh()
        self.current_index += 1

    def add_horizontal_line(self):
        if self.current_index < 2 or len(self.data.df) < 2:
            print("⚠️ Not enough data to add a line")
            return

        self.update_chart()

        try:
            if self.current_index - 2 >= len(self.data.df):
                print(
                    f"⚠️ Index out of range: current_index={self.current_index}, df length={len(self.data.df)}"
                )
                return

            y_value = self.data.df["high"].iloc[self.current_index - 2]
            x1, x2 = self.current_index - 2, len(self.data.df) - 1
            print(f"🔍 Debug: x1={x1}, x2={x2}, y_value={y_value}")

            self.horizontal_line = fplt.add_line(
                (x1, y_value),
                (x2, y_value),
                color="#0000FF",
                width=1,
                interactive=False,
            )
            fplt.refresh()
            print(f"✅ Horizontal line added at {y_value}")

        except IndexError:
            print(
                f"❌ IndexError: current_index={self.current_index}, df length={len(self.data.df)}"
            )

    def update_loop(self):
        now = time.time()
        if now - self.last_update_time >= self.update_interval:
            self.update_chart()
            self.last_update_time = now

    def reset(self):
        self.current_index = 1
        self.ax.clear()
        if self.horizontal_line is not None:
            self.ax.remove_line(self.horizontal_line)
            self.horizontal_line = None
        self.update_chart()


class TradingApp:
    def __init__(self):
        self.app = QApplication([])
        self.order_manager = OrderManager()
        self.current_symbol = "DUMB"
        self.chart_data = ChartData(self.current_symbol)

        self.init_ui()

    def init_ui(self):
        self.layout = QGridLayout()
        self.wdw = QGraphicsView()
        self.wdw.setWindowTitle("Trading Chart with Buy Button and Symbol Selection")
        self.wdw.setLayout(self.layout)
        self.wdw.resize(800, 600)

        self.controls_layout = QVBoxLayout()
        self.buy_button = QPushButton("Buy")
        self.controls_layout.addWidget(self.buy_button)

        self.symbol_dropdown = QComboBox()
        self.symbol_dropdown.addItems(["DUMB", "AAPL", "GOOG", "MSFT", "TSLA"])
        self.controls_layout.addWidget(self.symbol_dropdown)

        self.price_label = QLabel("0")
        self.price_label.setFont(QFont("Arial", 16))  # Set font size to 16
        self.controls_layout.addWidget(self.price_label)

        self.layout.addLayout(self.controls_layout, 0, 1, 1, 1)

        self.ax = fplt.create_plot(
            "Live Candlestick Chart", init_zoom_periods=100, maximize=False
        )
        self.chart_manager = ChartManager(self.ax, self.chart_data, self.price_label)

        self.layout.addWidget(self.ax.vb.win, 0, 0, 1, 1)

        self.buy_button.clicked.connect(self.on_buy_click)
        self.symbol_dropdown.currentTextChanged.connect(self.on_symbol_change)

    def on_buy_click(self):
        self.order_manager.start_buy_thread()
        self.chart_manager.add_horizontal_line()

    def on_symbol_change(self, symbol):
        self.chart_data.update_data(symbol)
        self.chart_manager.reset()
        self.ax.set_title(f"Live Candlestick Chart - {symbol}")
        fplt.refresh()

    def run(self):
        fplt.show(qt_exec=False)
        self.wdw.show()
        fplt.timer_callback(self.chart_manager.update_loop, 0.1)
        self.app.exec()


if __name__ == "__main__":
    app = TradingApp()
    app.run()
