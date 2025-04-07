import polars as pl
import random
import time
from datetime import datetime, timedelta

# Store last known price to simulate realistic movement
last_price = 100.0  # Start with a base price
candles = []  # Store OHLC data


def generate_fake_ohlc():
    """Simulates OHLC data with random price movement."""
    global last_price

    now = datetime.now()
    time_bin = now.replace(second=0, microsecond=0)  # Round to nearest minute

    open_price = last_price
    high_price = open_price + random.uniform(0.1, 1.5)
    low_price = open_price - random.uniform(0.1, 1.5)
    close_price = random.choice(
        [high_price, low_price, open_price + random.uniform(-0.5, 0.5)]
    )

    # Ensure consistency
    high_price = max(open_price, high_price, close_price)
    low_price = min(open_price, low_price, close_price)

    volume = random.randint(100, 500)  # Fake volume

    # Update last price
    last_price = close_price

    # Append new candle
    candles.append(
        {
            "from": time_bin,
            "to": time_bin + timedelta(seconds=5),  # 5-second candles
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
        }
    )

    # Keep last 50 candles
    if len(candles) > 50:
        candles.pop(0)

    return candles  # Return list of dictionaries


# Fake OHLC function for testing
def get_ohlc(token=None):
    """Returns simulated OHLC data as a Polars DataFrame."""
    ohlc_data = generate_fake_ohlc()
    return pl.DataFrame(ohlc_data)


# Test the function
if __name__ == "__main__":
    for _ in range(10):  # Generate 10 fake candles
        print(get_ohlc().select(["from", "open", "close", "high", "low"]))
        time.sleep(1)  # Simulate real-time data flow
