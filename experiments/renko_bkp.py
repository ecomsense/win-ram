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


from stock_indicators import indicators
from decimal import Decimal
from stock_indicators import Quote


class ChartData:
    ltp = 22000
    symbol = "DUMB"
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
        self.df_ticks = pd.DataFrame([self._make_tick()])
        self.remove_data_counter = len(self.df_ticks)
        self.df_ohlc = None

    def _get_ohlc(self, df_work):
        df_work.set_index("timestamp", inplace=True)
        df_candle = df_work["ltp"].resample("2s").ohlc().dropna()
        df_candle = df_candle.reset_index()
        df_candle["vopen"] = df_candle["vclose"] = df_candle["volume"] = 0
        return df_candle

    def _calc_atr_renko(self):
        quotes = [
            Quote(
                date=row["timestamp"],
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
            )
            for _, row in self.df_ohlc.iterrows()
        ]

        results = indicators.get_renko_atr(quotes, 11)

        renko_df = pd.DataFrame(
            [[q.date, q.open, q.close] for q in results],
            columns=["date", "vopen", "vclose"],
        ).set_index("date")

        renko_df.index = pd.to_datetime(renko_df.index).floor("s")
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
        new_tick = self._make_tick()
        self.remove_data_counter += 1
        new_df = pd.DataFrame([new_tick])
        self.df_ticks = pd.concat([self.df_ticks, new_df], ignore_index=True)
        df_work = self.df_ticks.copy()
        self.df_ohlc = self._get_ohlc(df_work)
        if len(self.df_ohlc) > (100 + 11):
            renko_df = self._calc_atr_renko()
            candle = self.df_ohlc.copy()
            self.df_ohlc = self._merge_renko_and_ohlc(candle, renko_df)
        if self.df_ohlc is not None:
            self.df_ohlc["timestamp"] = (
                self.df_ohlc["timestamp"].dt.tz_localize(None).astype("datetime64[ns]")
            )
            self.df_ohlc["t"] = range(len(self.df_ohlc))
            self.df_ohlc.set_index("t", inplace=True)


class ChartManager:
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

    def update_loop(self):
        try:
            self.data.update_data()
            self.update_chart()
        except Exception as e:
            print(f"Error in update loop: {e}")


class TradingApp:
    def __init__(self):
        self.app = QApplication([])
        self.current_symbol = "DUMB"
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
