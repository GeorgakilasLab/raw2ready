"""AI Forecast Engine module.

Implements basic statistical linear regression models to forecast future numeric
time series steps and save results to session state maps.
"""

import math
import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


def log(msg):
    """Outputs a formatted console log message.

    Args:
        msg: Message string.
    """
    print(f"[FORECAST_ENGINE] {msg}")


def storage_to_df(storage: dict) -> pd.DataFrame:
    """Converts the session storage representation into a pandas DataFrame.

    Converts any numeric-looking columns to float/integer.

    Args:
        storage: Web app session state dictionary.

    Returns:
        Pandas DataFrame reconstructed from JSON storage representation.
    """

    rows = storage.get("df_json", [])

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # try converting numeric-looking columns
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except Exception:
            pass

    return df


def detect_time_column(df):
    """Searches for common datetime index column names.

    Args:
        df: Pandas DataFrame.

    Returns:
        The matched column header name string, or None if not found.
    """

    candidates = [
        "time",
        "timestamp",
        "date",
        "datetime",
        "Time",
        "Date",
    ]

    for col in df.columns:

        if col in candidates:
            return col

        low = str(col).lower()

        if "time" in low:
            return col

        if "date" in low:
            return col

    return None


def numeric_columns(df):
    """Extracts column headers containing numeric-convertible data.

    Args:
        df: Pandas DataFrame.

    Returns:
        List of numeric column header name strings.
    """

    cols = []

    for col in df.columns:
        try:
            numeric = pd.to_numeric(
                df[col],
                errors="coerce"
            )

            if numeric.notna().sum() > 0:
                cols.append(col)

        except Exception:
            pass

    return cols


def prepare_series(df, target_col):
    """Extracts a target column, parses to numeric, drops nulls, and resets index.

    Args:
        df: Pandas DataFrame.
        target_col: Target column name.

    Returns:
        Cleaned pandas Series.
    """

    series = df[target_col].copy()

    series = pd.to_numeric(
        series,
        errors="coerce"
    )

    series = series.dropna()

    return series.reset_index(drop=True)


def linear_forecast(
    series: pd.Series,
    future_steps=10
):
    """Runs a standard linear regression forecast on a series.

    Args:
        series: Pandas Series representing the historical values.
        future_steps: Number of future points to predict. Defaults to 10.

    Returns:
        Dictionary mapping model metrics and list of forecasted future values,
        or None if data is insufficient.
    """

    if len(series) < 5:
        return None

    X = np.arange(
        len(series)
    ).reshape(-1, 1)

    y = series.values

    model = LinearRegression()
    model.fit(X, y)

    preds_train = model.predict(X)

    mae = mean_absolute_error(
        y,
        preds_train
    )

    rmse = math.sqrt(
        mean_squared_error(
            y,
            preds_train
        )
    )

    future_x = np.arange(
        len(series),
        len(series) + future_steps
    ).reshape(-1, 1)

    future_preds = model.predict(
        future_x
    )

    return {
        "model": model,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "future": [
            round(float(x), 6)
            for x in future_preds.tolist()
        ],
    }


def save_forecast_to_memory(
    storage,
    target_column,
    model_used,
    steps,
    future_values,
):
    """Stores forecast metrics in the runtime state container dictionary.

    Args:
        storage: Web app session state dictionary.
        target_column: Target forecasted column name.
        model_used: Name of model algorithm.
        steps: Forecast step count.
        future_values: List of forecasted values.
    """
    if "forecasts" not in storage:
        storage["forecasts"] = {}

    storage["forecasts"][target_column] = {
        "model": model_used,
        "steps": steps,
        "future": future_values,
    }

    log(f"Forecast stored in Runtime Memory ({target_column})")


def run_forecast(
    storage: dict,
    future_steps=10
):
    """Iterates over numeric columns and saves their forecasted values in storage.

    Args:
        storage: Web app session state dictionary.
        future_steps: Forecast step count. Defaults to 10.

    Returns:
        Dictionary containing title and message lines reporting forecast results.
    """

    log("Starting forecast engine")

    df = storage_to_df(storage)

    if df.empty:
        return {
            "title": "Forecast Engine",
            "lines": [
                "No dataset loaded."
            ]
        }

    nums = numeric_columns(df)

    if len(nums) == 0:
        return {
            "title": "Forecast Engine",
            "lines": [
                "No numeric columns available."
            ]
        }

    lines = []

    lines.append(
        f"Rows analyzed: {len(df)}"
    )

    lines.append(
        f"Numeric columns found: {len(nums)}"
    )

    dataset_id = storage.get(
        "dataset_id",
        None
    )

    lines.append(
        f"Dataset ID: {dataset_id}"
    )

    lines.append("")

    saved_counter = 0

    for col in nums[:5]:

        log(f"Forecasting column: {col}")

        series = prepare_series(
            df,
            col
        )

        result = linear_forecast(
            series,
            future_steps
        )

        if result is None:
            lines.append(
                f"{col}: not enough data."
            )
            continue

        next_val = round(
            result["future"][0], 4
        )

        last_val = round(
            float(series.iloc[-1]),
            4
        )

        trend = (
            "UP"
            if next_val > last_val
            else "DOWN"
        )

        lines.append(f"{col}")
        lines.append(
            f"Last Value: {last_val}"
        )
        lines.append(
            f"Next Forecast: {next_val}"
        )
        lines.append(
            f"Trend: {trend}"
        )
        lines.append(
            f"MAE: {result['mae']}"
        )
        lines.append(
            f"RMSE: {result['rmse']}"
        )
        lines.append("")

        # --------------------------------------
        # SAVE TO POSTGRESQL
        # --------------------------------------
        save_forecast_to_memory(
            storage=storage,
            target_column=col,
            model_used="LinearRegression",
            steps=future_steps,
            future_values=result["future"],
        )

        saved_counter += 1

    lines.append(
        f"Forecasts saved to Runtime Memory: {saved_counter}"
    )

    log("Forecast complete")

    return {
        "title": "AI Forecast Results",
        "lines": lines
    }


def ask_forecast(
    prompt: str,
    storage: dict
):
    """Processes natural language requests for forecasts and configures prediction intervals.

    Args:
        prompt: User query text.
        storage: Web app session state dictionary.

    Returns:
        AI Forecast Results dictionary.
    """

    prompt = prompt.lower()

    future_steps = 10

    if "30" in prompt:
        future_steps = 30

    elif "7" in prompt:
        future_steps = 7

    elif "5" in prompt:
        future_steps = 5

    return run_forecast(
        storage,
        future_steps
    )