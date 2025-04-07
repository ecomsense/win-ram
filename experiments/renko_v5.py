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
import pendulum as pdlm
import streaming_indicators as si
import logging


class ChartData:
    ltp = 500

    def _make_tick(self):
        """
        Generates a single tick with a sequential timestamp and a random LTP.
        Using sequential timestamps avoids gaps in the data.
        """
        timestamp = pdlm.now("Asia/Kolkata").timestamp()
        # Generate simulated price with some trend and volatility
        price_base = self.ltp  # Small upward trend
        price_noise = np.random.uniform(-0.90, 0.90)  # Random component
        self.ltp = round(price_base + price_noise, 2)

        ticks = dict(
            timestamp=timestamp,
            ltp=self.ltp,
        )
        return ticks

    def __init__(self, symbol="DUMB"):
        self.symbol = symbol
        # Initialize dataframes with proper columns
        self.df_ticks = pd.DataFrame(columns=["timestamp", "ltp"])

        tick = self._make_tick()
        new_df = pd.DataFrame([tick])
        self.df_ticks = pd.concat([self.df_ticks, new_df], ignore_index=True)

        self.atr = si.ATR(11)
        self.renko = si.Renko()

        # Data counter for sequential timestamps
        self.remove_data_counter = 1

        # Process initial data to create OHLC DataFrame
        self.df_ohlc = None
        self.process_data()

    def process_data(self, renko=False):
        """Process tick data into OHLC format with proper index for finplot"""
        if self.df_ticks.empty:
            return None

        # Create a working copy
        df_work = self.df_ticks.copy()

        # candlesonvert timestamps properly
        df_work["timestamp"] = df_work["timestamp"].apply(
            lambda ts: pdlm.from_timestamp(ts, tz="Asia/Kolkata")
        )

        # Drop any rows with invalid timestamps
        df_work.dropna(subset=["timestamp"], inplace=True)

        if df_work.empty:
            print("No valid timestamps found")
            return None

        # Ensure timestamps are unique and sorted
        df_work = df_work.drop_duplicates(subset=["timestamp"])
        df_work = df_work.sort_values("timestamp")

        # Set timestamp as index for resampling
        df_work.set_index("timestamp", inplace=True)

        # Resample to OHLC format (1-minute candles)
        self.df_ohlc = df_work["ltp"].resample("1Min").ohlc().dropna()

        # Reset index to get timestamp as a column
        self.df_ohlc = self.df_ohlc.reset_index()

        # Create numeric index for finplot compatibility
        self.df_ohlc["t"] = range(len(self.df_ohlc))
        self.df_ohlc.set_index("t", inplace=True)

        logging.debug(f"Processed OHLC data: {len(self.df_ohlc)} rows")

        self.df_ohlc["vopen"] = 0

        if renko:
            for idx, candle in self.df_ohlc.iterrows():
                atr = self.atr.update(candle)
                bricks = self.renko.update(candle["close"], atr)
                if bricks and any(bricks):
                    self.df_ohlc.loc[idx, "vclose"] = bricks[-1][
                        "direction"
                    ]  # direct assignment
                    print(bricks)
                    self.df_ohlc.loc[idx, "volume"] = bricks[-1][
                        "direction"
                    ]  # direct assignment
                else:
                    self.df_ohlc.loc[idx, "vclose"] = 0
                    self.df_ohlc.loc[idx, "volume"] = 0
        return self.df_ohlc

    def update_data(self):
        # Generate a new tick with sequential timestamp
        new_tick = self._make_tick()
        self.remove_data_counter += 1

        # Add the new tick to our dataframe
        new_df = pd.DataFrame([new_tick])
        self.df_ticks = pd.concat([self.df_ticks, new_df], ignore_index=True)

        # Reprocess all data to update OHLC
        self.process_data(renko=True)

        return self.df_ohlc


class ChartManager:
    def __init__(self, ax, ax2, data, price_label):
        self.ax = ax
        self.ax2 = ax2
        self.data = data
        self.price_label = price_label
        self.last_update_time = time.time()

        # Don't initialize with empty data - wait for the first update
        self.initialized = False

    def update_chart(self):
        if self.data.df_ohlc is None or self.data.df_ohlc.empty:
            print("No OHLC data available for chart")
            return False

        try:
            # Get plot data
            plot_df = self.data.df_ohlc.copy()

            # Clear previous data
            self.ax.reset()
            self.ax2.reset()

            print(plot_df)

            # Plot candlestick chart
            fplt.candlestick_ochl(plot_df[["open", "close", "high", "low"]], ax=self.ax)

            # Plot volume chart
            fplt.volume_ocv(plot_df[["vopen", "vclose", "volume"]], ax=self.ax2)

            # Update price label
            latest_price = plot_df["close"].iloc[-1] if not plot_df.empty else 0
            self.price_label.setText(f"{latest_price:.2f}")

            # Refresh the plot
            fplt.refresh()

            # Mark as initialized after first successful update
            self.initialized = True
            return True

        except Exception as e:
            print(f"Error updating chart: {e}")
            return False

    def update_loop(self):
        try:
            self.data.update_data()
            self.update_chart()
        except Exception as e:
            print(f"Error in update loop: {e}")

    def reset(self):
        self.ax.reset()
        self.ax2.reset()
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
        self.wdw.setWindowTitle("Renko Chart Demo")
        self.wdw.setLayout(self.layout)
        self.wdw.resize(800, 600)

        self.controls_layout = QVBoxLayout()
        self.price_label = QLabel("0")
        self.price_label.setFont(QFont("Arial", 16))
        self.controls_layout.addWidget(self.price_label)

        self.layout.addLayout(self.controls_layout, 0, 1, 1, 1)

        # Create two separate panels for candlestick and volume
        self.ax, self.ax2 = fplt.create_plot(
            "Live Candlestick Chart", rows=2, init_zoom_periods=100, maximize=False
        )

        # Set the panels visible
        self.ax2.set_visible(True)
        self.ax.set_visible(True)

        self.chart_manager = ChartManager(
            self.ax, self.ax2, self.chart_data, self.price_label
        )

        self.layout.addWidget(self.ax.vb.win, 0, 0, 1, 1)
        self.layout.addWidget(self.ax2.vb.win, 1, 0, 1, 1)

        # Initial update before showing
        self.chart_manager.update_chart()

    def run(self):
        fplt.show(qt_exec=False)
        self.wdw.show()
        fplt.timer_callback(self.chart_manager.update_loop, 0.1)
        self.app.exec()


if __name__ == "__main__":
    app = TradingApp()
    app.run()
