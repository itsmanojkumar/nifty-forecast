"""Load the registered champion model and forecast.   python -m mlops.predict "Nifty Metal" 14"""
import sys
import mlflow, pandas as pd
from .data import INDICES
from .train import TRACKING_URI

if __name__ == "__main__":
    name, h = sys.argv[1], int(sys.argv[2])
    mlflow.set_tracking_uri(TRACKING_URI)
    model = mlflow.pyfunc.load_model(f"models:/{INDICES[name]}@champion")
    print(model.predict(pd.DataFrame({"horizon_months": [h]})).round(0).to_string(index=False))
