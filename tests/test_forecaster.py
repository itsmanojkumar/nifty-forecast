import numpy as np, pandas as pd, pytest
from mlops.forecaster import TrendForecaster, trend_path, band_width
from mlops.backtest import backtest, gate


def series(n=120, drift=0.01, vol=0.03, seed=0):
    r = np.random.default_rng(seed).normal(drift, vol, n)
    return pd.Series(np.cumsum(r) + 7, index=pd.date_range("2015-01-31", periods=n, freq="M"))


def test_trend_path_extends_average_drift():
    y = np.array([0.0, 1.0, 2.0, 3.0]); assert np.allclose(trend_path(y, 3), [4.0, 5.0, 6.0])


def test_band_widens_with_horizon():
    k = band_width(series().values, 12); assert (np.diff(k) > 0).all()


def test_predict_shape_and_ordering():
    y = series(); m = TrendForecaster([i.strftime("%Y-%m") for i in y.index], list(y.values))
    out = m.predict(None, pd.DataFrame({"horizon_months": [14]}))
    assert len(out) == 14 and out.month.iloc[0] == "2025-01"
    assert (out.p10 < out.forecast).all() and (out.forecast < out.p90).all()


@pytest.mark.parametrize("h", [0, 37])
def test_predict_rejects_bad_horizon(h):
    y = series(); m = TrendForecaster([i.strftime("%Y-%m") for i in y.index], list(y.values))
    with pytest.raises(ValueError):
        m.predict(None, pd.DataFrame({"horizon_months": [h]}))


def test_backtest_metrics_and_gate():
    m, rows = backtest(series(200))
    assert {"mape_12m_trend", "coverage80_12m_pct", "improvement_12m_pct"} <= set(m)
    assert rows.horizon.nunique() == 4
    assert gate({"improvement_12m_pct": 5.0, "coverage80_12m_pct": 90.0})[0]
    assert not gate({"improvement_12m_pct": -1.0, "coverage80_12m_pct": 90.0})[0]
    assert not gate({"improvement_12m_pct": 5.0, "coverage80_12m_pct": 60.0})[0]
