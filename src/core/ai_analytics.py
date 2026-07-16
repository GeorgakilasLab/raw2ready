"""AI Analytics module.

Provides lightweight analytical utilities to load datasets from session storage,
generate summaries, identify outliers, and perform automated cleaning.
"""

import pandas as pd
import numpy as np


def storage_to_df(storage):
    """Loads a pandas DataFrame from session storage data.

    Args:
        storage: Dictionary storage representing the session state.

    Returns:
        Pandas DataFrame reconstructed from JSON storage representation.
    """

    data = storage.get("df_json", [])
    cols = storage.get("df_columns", [])

    if not data:
        return pd.DataFrame(columns=cols)

    return pd.DataFrame(data)


def summarize_df(df: pd.DataFrame) -> list:
    """Generates a list-based text summary and basic insights from a DataFrame.

    Args:
        df: Pandas DataFrame to summarize.

    Returns:
        List of summary statistics and column-level insights.
    """

    if df.empty:
        return ["No dataset loaded."]

    rows = len(df)
    cols = len(df.columns)

    numeric_cols = df.select_dtypes(
        include=[np.number]
    ).columns.tolist()

    text_cols = df.select_dtypes(
        exclude=[np.number]
    ).columns.tolist()

    missing = int(df.isna().sum().sum())

    duplicates = int(df.duplicated().sum())

    lines = [
        f"Rows: {rows}",
        f"Columns: {cols}",
        f"Numeric Columns: {len(numeric_cols)}",
        f"Text Columns: {len(text_cols)}",
        f"Missing Values: {missing}",
        f"Duplicate Rows: {duplicates}",
        "",
        "Insights:"
    ]

    # Add numeric insights
    for col in numeric_cols[:5]:

        try:
            mn = round(df[col].min(), 3)
            mx = round(df[col].max(), 3)
            avg = round(df[col].mean(), 3)

            lines.append(
                f"{col}: min={mn}, max={mx}, mean={avg}"
            )

        except Exception:
            pass

    if len(numeric_cols) == 0:
        lines.append("No numeric columns detected")

    return lines


def detect_anomalies(df: pd.DataFrame) -> list:
    """Detects numeric column outliers using the Interquartile Range (IQR) method.

    Args:
        df: Pandas DataFrame to analyze.

    Returns:
        List of anomaly summary text reports per column.
    """

    if df.empty:
        return ["No dataset loaded."]

    numeric_cols = df.select_dtypes(
        include=[np.number]
    ).columns.tolist()

    findings = []

    for col in numeric_cols[:8]:

        try:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1

            low = q1 - 1.5 * iqr
            high = q3 + 1.5 * iqr

            outliers = df[
                (df[col] < low) |
                (df[col] > high)
            ]

            count = len(outliers)

            if count > 0:
                findings.append(
                    f"{col}: {count} anomalies detected"
                )

        except Exception:
            pass

    if not findings:
        findings.append(
            "No major anomalies detected"
        )

    return findings


def clean_df(df: pd.DataFrame):
    """Performs automated standard cleaning on a DataFrame.

    Cleans duplicate rows, fills missing numerical values with column medians,
    fills text/object columns with modes, and normalizes column headers.

    Args:
        df: Target pandas DataFrame.

    Returns:
        A tuple containing:
            - DataFrame: The cleaned DataFrame.
            - List: List of strings reporting modifications.
    """

    if df.empty:
        return df, ["No dataset loaded."]

    before_rows = len(df)

    # Remove duplicates
    dup_removed = int(df.duplicated().sum())
    df = df.drop_duplicates()

    # Fill NaN values
    for col in df.columns:

        if df[col].dtype.kind in "biufc":

            median = df[col].median()
            df[col] = df[col].fillna(median)

        else:

            mode = (
                df[col].mode()[0]
                if not df[col].mode().empty
                else "Unknown"
            )

            df[col] = df[col].fillna(mode)

    # Normalize column names
    df.columns = [
        str(c).strip().lower().replace(" ", "_")
        for c in df.columns
    ]

    after_rows = len(df)

    report = [
        f"Rows before: {before_rows}",
        f"Rows after: {after_rows}",
        f"Duplicates removed: {dup_removed}",
        "Missing values filled",
        "Column names normalized",
    ]

    return df, report


def save_df_to_storage(df, storage):
    """Safely converts DataFrame datatypes and saves back to state storage dict.

    Args:
        df: Pandas DataFrame to serialize.
        storage: Destination session state storage dictionary.
    """

    if df is None:
        storage["df_json"] = []
        storage["df_columns"] = []
        return

    df = df.copy()

    # ----------------------------------------
    # Convert datetime columns
    # ----------------------------------------
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)

    # ----------------------------------------
    # Convert all problematic objects
    # ----------------------------------------
    def safe(v):
        if pd.isna(v):
            return ""
        if isinstance(v, pd.Timestamp):
            return str(v)
        if isinstance(v, (np.integer, np.int64)):
            return int(v)
        if isinstance(v, (np.floating, np.float64)):
            return float(v)
        return v

    df = df.map(safe)

    storage["df_json"] = df.to_dict(orient="records")
    storage["df_columns"] = list(df.columns)