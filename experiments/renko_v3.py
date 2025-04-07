import finplot as fplt
import numpy as np
import pandas as pd
import time
from PyQt6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QGridLayout,
    QGraphicsView,
    QLabel,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QThread
from renkodf import RenkoWS


class ChartData:
    ticks = []

    def calculate_renko(self, df):
        volume_updates = []
        for _, candle in df.iterrows():
            atr = self.ATR.update(candle)
            print("atr", atr)
            bricks = self.Renko.update(candle["close"], atr)
            print("bricks", bricks)
            if bricks is None:
                volume_updates.append(0)  # No bricks, assign 0
            else:
                volume_updates.append(bricks[-1]["direction"])  # Use the last direction
                print(bricks[-1]["direction"])
        df["volume"] = volume_updates  # Replace volume with direction values
        return df

    def __init__(self, symbol="DUMB"):
        self.symbol = symbol
        """
        update_renkodf_period = 11
        self.ATR = si.ATR(atr_period)
        self.Renko = si.Renko()
        """
        self.df_ticks = pd.DataFrame(columns=["timestamp", "ltp"])
        self.df_ohlc = pd.DataFrame(columns=["open", "high", "low", "close"])
        tick = self.generate_data()
        new_df = pd.DataFrame([tick])
        self.df_ticks = pd.concat([self.df_ticks, new_df], ignore_index=True)
        initial_timestamp = self.df_ticks["timestamp"].iat[0]
        initial_price = self.df_ticks["ltp"].iat[0]
        self.rws = RenkoWS(initial_timestamp, initial_price, brick_size=0.04)

    def generate_data(self):
        """Generates a single tick with the current timestamp and a random LTP."""
        ticks = dict(
            timestamp=int(time.time()),
            # Current timestamp (UNIX time)
            ltp=round(100 + np.random.uniform(-1, 1), 2),  # Random price around 100
        )
        return ticks

    def update_data(self):
        new_tick = self.generate_data()
        self.rws.add_prices(new_tick["timestamp"], new_tick["ltp"])
        renko_df = self.rws.renko_animate("wicks", max_len=1000, keep=500)

        new_df = pd.DataFrame([new_tick])

        # 🛠 Ensure self.df_ticks retains previous data
        if self.df_ticks is None or self.df_ticks.empty:
            self.df_ticks = new_df
        else:
            self.df_ticks = pd.concat([self.df_ticks, new_df], ignore_index=True)

        # 🛠 Debugging: Check if timestamps are valid before processing
        print("Before filtering timestamps:\n", self.df_ticks.tail())

        # 🛠 Ensure timestamp conversion is correct
        self.df_ticks["timestamp"] = pd.to_datetime(
            self.df_ticks["timestamp"], unit="s", errors="coerce"
        )
        self.df_ticks.dropna(subset=["timestamp"], inplace=True)

        # 🛠 Debugging: Verify timestamps after conversion
        print("After timestamp conversion:\n", self.df_ticks.tail())

        # 🛠 Ensure timestamps are unique and sorted
        self.df_ticks = self.df_ticks.drop_duplicates(subset=["timestamp"])
        self.df_ticks = self.df_ticks.sort_values("timestamp")

        # 🛠 Set timestamp index for resampling
        self.df_ticks.set_index("timestamp", inplace=True)

        # 🛠 Ensure enough data exists before resampling
        if len(self.df_ticks) >= 5:
            self.df_ohlc = self.df_ticks.resample("1Min").agg({"ltp": "ohlc"})
        else:
            print("Not enough data for resampling, skipping.")

        # 🛠 Debugging: Check final OHLC data
        print("Updated OHLC:\n", self.df_ohlc.tail())


class ChartManager:
    def __init__(self, ax, ax2, data, price_label):
        self.ax = ax
        self.ax2 = ax2
        self.data = data
        self.price_label = price_label
        self.current_index = 1
        self.last_update_time = time.time()

    def update_chart(self):

        print(self.data.df_ohlc)
        if self.data.df_ohlc.empty or self.current_index >= len(self.data.df_ohlc):
            print("returning without data")
            return

        df_subset = self.data.df_ohlc.iloc[: self.current_index + 1]
        print(df_subset, "df_subset")
        self.ax.clear()
        self.ax2.clear()

        fplt.candlestick_ochl(df_subset, ax=self.ax)
        df_subset["volume"] = 0

        fplt.volume_ocv(df_subset[["open", "close", "volume"]], ax=self.ax2)

        latest_price = df_subset["close"].iloc[-1]
        self.price_label.setText(f"{latest_price:.2f}")

        fplt.refresh()
        self.current_index += 1

    def update_loop(self):
        now = time.time()
        self.data.update_data()  # Ensure data updates before refreshing chart
        self.update_chart()
        self.last_update_time = now

    def reset(self):
        self.current_index = 1
        self.ax.clear()
        self.update_chart()


class TradingApp:
    def __init__(self):
        self.app = QApplication([])
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
        self.price_label = QLabel("0")
        self.price_label.setFont(QFont("Arial", 16))  # Set font size to 16
        self.controls_layout.addWidget(self.price_label)

        self.layout.addLayout(self.controls_layout, 0, 1, 1, 1)

        # Create two separate panels for candlestick and volume
        self.ax, self.ax2 = fplt.create_plot(
            "Live Candlestick Chart", rows=2, init_zoom_periods=100, maximize=False
        )

        # Set the second panel (ax2) at the bottom for volume
        self.ax2.set_visible(True)
        self.ax.set_visible(True)

        self.chart_manager = ChartManager(
            self.ax, self.ax2, self.chart_data, self.price_label
        )

        self.layout.addWidget(self.ax.vb.win, 0, 0, 1, 1)
        self.layout.addWidget(self.ax2.vb.win, 1, 0, 1, 1)  # Volume chart at the bottom

    def run(self):
        fplt.show(qt_exec=False)
        self.wdw.show()
        fplt.timer_callback(self.chart_manager.update_loop, 1)
        self.app.exec()


if __name__ == "__main__":
    app = TradingApp()
    app.run()
    """
    c = ChartData()
    while True:
        c.update_data()
        __import__("time").sleep(30)
    """
