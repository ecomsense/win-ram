import finplot as fplt
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QGridLayout,
    QGraphicsView,
    QLabel,
)
from PyQt6.QtGui import QFont
import pendulum as pdlm
from api import Helper

from stock_indicators import indicators
from decimal import Decimal
from stock_indicators import Quote


class ChartData:
    ltp = 22000
    symbol = "Nifty 50"
    timezone = "Asia/Kolkata"

    def _make_tick(self):
        """
        Generates a single tick with a timezone-aware pandas Timestamp and a random LTP.
        """
        timestamp = pdlm.now(self.timezone)
        price_base = self.ltp
        price_noise = np.random.uniform(-0.90, 0.90)
        self.ltp = round(price_base + price_noise, 2)
        ticks = dict(timestamp=timestamp, ltp=self.ltp)
        return ticks

    def __init__(self):
        self.df_ticks = None
        self.df_ohlc = None

    def _get_ohlc(self, df_work):
        df_work.set_index("timestamp", inplace=True)
        df_candle = df_work["ltp"].resample("5Min").ohlc().dropna()
        df_candle = df_candle.reset_index()
        df_candle["vopen"] = df_candle["vclose"] = df_candle["volume"] = 0
        return df_candle

    def _calc_atr_renko(self, ohlc):
        df_candle = Helper.history()
        df_candle["vopen"] = df_candle["vclose"] = df_candle["volume"] = 0
        ohlc = pd.concat([df_candle, ohlc], ignore_index=True)
        quotes = [
            Quote(
                date=row["timestamp"],
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
            )
            for _, row in ohlc.iterrows()
        ]

        results = indicators.get_renko_atr(quotes, 11)

        renko_df = pd.DataFrame(
            [[q.date, q.open, q.close] for q in results],
            columns=["date", "vopen", "vclose"],
        ).set_index("date")

        renko_df.index = pd.to_datetime(renko_df.index).floor("1min")
        renko_df = renko_df[~renko_df.index.duplicated(keep="first")]
        renko_df["volume"] = 0
        renko_df.loc[renko_df["vclose"] > renko_df["vopen"], "volume"] = 1
        renko_df.loc[renko_df["vclose"] < renko_df["vopen"], "volume"] = -1

        return renko_df

    def _merge_renko_and_ohlc(
        self, ohlc_df: pd.DataFrame, renko_df: pd.DataFrame
    ) -> pd.DataFrame:
        for renko_time, renko_volume in renko_df["volume"].items():
            # Ensure renko_time is a pandas Timestamp with the correct timezone
            renko_time = pd.Timestamp(renko_time, tz=self.timezone)
            ohlc_indices_to_update: pd.Index = ohlc_df[
                ohlc_df["timestamp"] >= renko_time
            ].index
            if not ohlc_indices_to_update.empty:
                ohlc_df.loc[ohlc_indices_to_update[0], "volume"] = renko_volume
        return ohlc_df

    def update_data(self):
        timestamp = pdlm.now(self.timezone)
        full_tick = Helper.ticks()["NSE|Nifty 50"]
        new_tick = dict(timestamp=timestamp, ltp=full_tick["ltp"])
        # new_tick = self._make_tick()
        new_df = pd.DataFrame([new_tick])
        self.df_ticks = pd.concat([self.df_ticks, new_df], ignore_index=True)
        df_work = self.df_ticks.copy()
        ohlc = self._get_ohlc(df_work)
        # todo
        candle = ohlc.copy()
        renko_df = self._calc_atr_renko(ohlc)
        self.df_ohlc = self._merge_renko_and_ohlc(candle, renko_df)
        if self.df_ohlc is not None:
            self.df_ohlc["timestamp"] = (
                self.df_ohlc["timestamp"].dt.tz_localize(None).astype("datetime64[ns]")
            )
            self.df_ohlc["t"] = range(len(self.df_ohlc))
            self.df_ohlc.set_index("t", inplace=True)

    def manage_trades(self):
        pass


class ChartManager:
    signal = 0

    def __init__(self, ax, ax2, price_label):
        self.ax = ax
        self.ax2 = ax2
        self.data = ChartData()
        self.price_label = price_label

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

            plot_df["vclose"] = plot_df["volume"]

            # Plot candlestick chart
            fplt.candlestick_ochl(plot_df[["open", "close", "high", "low"]], ax=self.ax)

            # Plot volume chart
            fplt.volume_ocv(plot_df[["vopen", "vclose", "volume"]], ax=self.ax2)

            # Update price label
            latest_price = plot_df["close"].iloc[-1] if not plot_df.empty else 0
            self.price_label.setText(f"{latest_price:.2f}")

            # Refresh the plot
            fplt.refresh()

        except Exception as e:
            print(f"Error updating chart: {e}")
            return False

    def try_and_trade(self):
        if self.data.df_ohlc is None or self.data.df_ohlc.empty:
            return

        counted = len(self.data.df_ohlc)
        if counted <= 1:
            return

        if counted != self.counted:
            self.counted = counted
            last = self.data.df_ohlc.iloc[-1]
            prev = self.data.df_ohlc.iloc[-2]
            print(last, prev)

            if prev["volume"] == 1:
                self.signal = 1
            elif prev["volume"] == -1:
                self.signal = -1

    def check_exit_status(self):
        pass

    def update_loop(self):
        try:
            self.data.update_data()
            self.update_chart()
            if self.signal == 0:
                self.try_and_trade()
            else:
                self.check_exit_status()
        except Exception as e:
            print(f"Error in update loop: {e}")


class TradingApp:
    def __init__(self):
        Helper.api()
        self.app = QApplication([])
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

        self.chart_manager = ChartManager(self.ax, self.ax2, self.price_label)

        self.layout.addWidget(self.ax.vb.win, 0, 0, 1, 1)
        self.layout.addWidget(self.ax2.vb.win, 1, 0, 1, 1)

    def run(self):
        fplt.show(qt_exec=False)
        self.wdw.show()
        fplt.timer_callback(self.chart_manager.update_loop, 0.1)
        self.app.exec()


if __name__ == "__main__":
    app = TradingApp()
    app.run()
