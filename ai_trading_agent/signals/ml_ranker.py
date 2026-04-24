from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import RandomForestRegressor


FEATURES = ["ret_1", "rsi_14", "volatility_20", "dollar_volume"]


@dataclass
class MLPatternRanker:
    model: RandomForestRegressor | None = None

    def train(self, frame: pd.DataFrame) -> None:
        df = frame.dropna(subset=FEATURES + ["target"]).copy()
        if len(df) < 100:
            self.model = None
            return
        m = RandomForestRegressor(n_estimators=120, max_depth=6, random_state=42)
        m.fit(df[FEATURES], df["target"])
        self.model = m

    def predict_score(self, frame: pd.DataFrame) -> float:
        if self.model is None or frame.empty:
            return 0.5
        row = frame[FEATURES].tail(1).fillna(0)
        pred = float(self.model.predict(row)[0])
        return max(0.0, min(1.0, pred))
