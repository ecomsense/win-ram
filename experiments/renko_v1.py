import finplot as fplt
import pandas as pd
import time
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QVBoxLayout,
    QLabel,
    QGraphicsView,
)
from PyQt6.QtGui import QFont


class ChartData:
    def __init__(self, symbol):
        self.symbol = symbol
        self.df = self.load_data()

    def load_data(self):
        # Simulated OHLCV data for testing
        data = {
            "timestamp": pd.date_range("2024-03-01", periods=10, freq="5T"),
            "open": [100, 102, 105, 103, 108, 110, 107, 111, 115, 117],
            "high": [102, 106, 107, 108, 112, 113, 110, 114, 118, 120],
            "low": [99, 101, 103, 102, 107, 109, 106, 110, 113, 115],
            "close": [101, 105, 104, 107, 110, 111, 109, 113, 116, 119],
            "volume": [500, 600, 550, 700, 750, 720, 710, 730, 800, 850],
        }
        df = pd.DataFrame(data)

        # Ensure correct datetime index format for Finplot
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)

        return df


class ChartManager:
    def __init__(self, ax, ax2, data, price_label):
        self.ax = ax
        self.ax2 = ax2
        self.data = data
        self.price_label = price_label
        self.current_index = 1
        self.last_update_time = time.time()
        self.update_interval = 0.5

    def update_chart(self):
        if self.current_index >= len(self.data.df):
            return

        df_subset = self.data.df.iloc[: self.current_index + 1].copy()

        # Ensure timestamps are in datetime64[ns] format
        df_subset.index = pd.to_datetime(df_subset.index)

        # Clear previous plots
        self.ax.clear()
        self.ax2.clear()

        # Plot candlestick and volume
        fplt.candlestick_ochl(df_subset, ax=self.ax)
        fplt.volume_ocv(df_subset[["open", "close", "volume"]], ax=self.ax2)

        # Update price label
        latest_price = df_subset["close"].iloc[-1]
        self.price_label.setText(f"{latest_price:.2f}")

        # Refresh plot
        fplt.refresh()
        self.current_index += 1

    def update_loop(self):
        now = time.time()
        if now - self.last_update_time >= self.update_interval:
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
        fplt.timer_callback(self.chart_manager.update_loop, 0.1)
        self.app.exec()


if __name__ == "__main__":
    app = TradingApp()
    app.run()
