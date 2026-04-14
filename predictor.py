"""
predictor.py — ML-based subscriber growth prediction
Supports both Prophet and a scikit-learn fallback (Linear Regression + Polynomial).
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ─────────────────────────────────────────────
# Prophet Predictor
# ─────────────────────────────────────────────

def prophet_forecast(history_df: pd.DataFrame, days_ahead: int = 90) -> dict:
    """
    Fit a Prophet model on subscriber history, forecast `days_ahead` days.
    Returns dict with keys: forecast_df, model_name, rmse_estimate.
    """
    try:
        from prophet import Prophet

        df = history_df[["date", "est_subs"]].dropna().copy()
        df.columns = ["ds", "y"]
        df["ds"] = pd.to_datetime(df["ds"])

        # Clip negative values
        df["y"] = df["y"].clip(lower=0)

        model = Prophet(
            changepoint_prior_scale=0.3,
            seasonality_prior_scale=10,
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.80,
        )
        model.fit(df)

        future = model.make_future_dataframe(periods=days_ahead, freq="D")
        forecast = model.predict(future)

        # Keep only future portion for the "prediction" section
        last_date = df["ds"].max()
        future_fc = forecast[forecast["ds"] > last_date][["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        future_fc.columns = ["date", "predicted", "lower", "upper"]
        future_fc["predicted"] = future_fc["predicted"].clip(lower=0).astype(int)
        future_fc["lower"]     = future_fc["lower"].clip(lower=0).astype(int)
        future_fc["upper"]     = future_fc["upper"].clip(lower=0).astype(int)

        # Full timeline (history + future) for chart
        full_fc = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        full_fc.columns = ["date", "predicted", "lower", "upper"]
        full_fc["predicted"] = full_fc["predicted"].clip(lower=0).astype(int)
        full_fc["lower"]     = full_fc["lower"].clip(lower=0).astype(int)
        full_fc["upper"]     = full_fc["upper"].clip(lower=0).astype(int)

        return {
            "future_df": future_fc,
            "full_df":   full_fc,
            "model_name": "Facebook Prophet",
            "history_df": df,
        }

    except ImportError:
        return sklearn_forecast(history_df, days_ahead)
    except Exception as e:
        print(f"Prophet failed ({e}), falling back to sklearn")
        return sklearn_forecast(history_df, days_ahead)


# ─────────────────────────────────────────────
# Scikit-learn fallback
# ─────────────────────────────────────────────

def sklearn_forecast(history_df: pd.DataFrame, days_ahead: int = 90) -> dict:
    """Polynomial regression fallback when Prophet is unavailable."""
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.pipeline import make_pipeline

    df = history_df[["date", "est_subs"]].dropna().copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    origin = df["date"].min()
    df["t"] = (df["date"] - origin).dt.days

    X = df[["t"]].values
    y = df["est_subs"].values

    deg = 3
    model = make_pipeline(PolynomialFeatures(deg), LinearRegression())
    model.fit(X, y)

    # Residual std for a rough confidence interval
    y_pred_train = model.predict(X)
    residuals = y - y_pred_train
    sigma = np.std(residuals) * 1.5

    last_t = int(df["t"].max())
    future_t = np.arange(last_t + 1, last_t + days_ahead + 1)
    future_dates = [origin + timedelta(days=int(t)) for t in future_t]

    pred = model.predict(future_t.reshape(-1, 1))
    pred = np.clip(pred, 0, None).astype(int)

    future_fc = pd.DataFrame({
        "date":      future_dates,
        "predicted": pred,
        "lower":     np.clip(pred - int(sigma), 0, None).astype(int),
        "upper":     (pred + int(sigma)).astype(int),
    })

    # Full timeline
    all_t     = np.concatenate([X.flatten(), future_t])
    all_dates = list(df["date"]) + future_dates
    all_pred  = np.clip(model.predict(all_t.reshape(-1, 1)), 0, None).astype(int)

    full_fc = pd.DataFrame({
        "date":      all_dates,
        "predicted": all_pred,
        "lower":     np.clip(all_pred - int(sigma), 0, None).astype(int),
        "upper":     (all_pred + int(sigma)).astype(int),
    })

    return {
        "future_df": future_fc,
        "full_df":   full_fc,
        "model_name": "Polynomial Regression (sklearn)",
        "history_df": df.rename(columns={"date": "ds", "est_subs": "y"}),
    }


# ─────────────────────────────────────────────
# Milestone date estimator
# ─────────────────────────────────────────────

def estimate_goal_date(forecast_result: dict, goal_subs: int) -> dict | None:
    """
    Given a forecast result dict, find the predicted date when subscribers
    cross `goal_subs`. Returns None if never reached in forecast window.
    """
    future_df = forecast_result["future_df"]
    match = future_df[future_df["predicted"] >= goal_subs]
    if match.empty:
        # Goal is outside window — extrapolate linearly from the last few points
        last = future_df.tail(30)
        if len(last) < 2:
            return None
        rate = (last["predicted"].iloc[-1] - last["predicted"].iloc[0]) / len(last)
        if rate <= 0:
            return None
        gap = goal_subs - future_df["predicted"].iloc[-1]
        extra_days = int(gap / rate)
        est_date = future_df["date"].iloc[-1] + timedelta(days=extra_days)
        return {
            "date": est_date,
            "days_away": extra_days + len(future_df),
            "in_window": False,
        }

    est_date = pd.to_datetime(match["date"].iloc[0])
    today    = datetime.now()
    days_away = (est_date - today).days
    return {
        "date": est_date,
        "days_away": days_away,
        "in_window": True,
    }


# ─────────────────────────────────────────────
# Quick milestone snapshots (30 / 60 / 90 days)
# ─────────────────────────────────────────────

def get_milestone_predictions(forecast_result: dict) -> dict:
    future_df = forecast_result["future_df"]
    milestones = {}
    for days in [30, 60, 90]:
        target_date = datetime.now() + timedelta(days=days)
        row = future_df[pd.to_datetime(future_df["date"]) <= target_date]
        if not row.empty:
            r = row.iloc[-1]
            milestones[days] = {
                "predicted": int(r["predicted"]),
                "lower": int(r["lower"]),
                "upper": int(r["upper"]),
                "date": r["date"],
            }
        else:
            milestones[days] = None
    return milestones
