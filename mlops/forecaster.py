"""Deployable trend forecaster, packaged as an MLflow pyfunc model.

Monthly log-price trend (average monthly log change over the whole history) with an 80% band that widens with sqrt(horizon).
Same method as the dashboard's production model, so the registered model and the website cannot drift apart.
"""
import numpy as np
import pandas as pd
import mlflow.pyfunc

Z80 = 1.2816  # 10th/90th percentile of a normal distribution


def trend_path(log_prices: np.ndarray, horizon: int) -> np.ndarray:
    drift = (log_prices[-1] - log_prices[0]) / (len(log_prices) - 1)
    return log_prices[-1] + drift * np.arange(1, horizon + 1)


def band_width(log_prices: np.ndarray, horizon: int, window: int = 60) -> np.ndarray:
    return np.sqrt(np.arange(1, horizon + 1)) * np.diff(log_prices)[-window:].std() * Z80


class TrendForecaster(mlflow.pyfunc.PythonModel):
    """Input: DataFrame with column `horizon_months` (int, 1-36). Output: month, forecast, p10, p90."""

    def __init__(self, months: list, log_prices: list, window: int = 60):
        self.months, self.log_prices, self.window = months, log_prices, window

    def predict(self, context, model_input, params=None):
        h = int(model_input["horizon_months"].iloc[0])
        if not 1 <= h <= 36:
            raise ValueError("horizon_months must be between 1 and 36")
        y = np.asarray(self.log_prices, float)
        mid, k = trend_path(y, h), band_width(y, h, self.window)
        start = pd.Period(self.months[-1], "M")
        return pd.DataFrame({"month": [str(start + i) for i in range(1, h + 1)], "forecast": np.exp(mid),
                             "p10": np.exp(mid - k), "p90": np.exp(mid + k)})
