"""Smart Recommendations module.

Analyzes datasets to output targeted advice lists across data quality, statistical analysis,
visualization types, ML viability, and industrial process monitoring options.
"""

import pandas as pd
import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger("smart_recommendations")


def storage_to_df(storage: dict) -> pd.DataFrame:
    """Converts the session storage representation into a pandas DataFrame.

    Args:
        storage: Web app session state dictionary.

    Returns:
        Pandas DataFrame reconstructed from JSON storage representation.
    """

    rows = storage.get("df_json", [])
    cols = storage.get("df_columns", [])

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    if cols:
        safe_cols = [c for c in cols if c in df.columns]
        if safe_cols:
            df = df[safe_cols]

    return df


def numeric_columns(df: pd.DataFrame):
    """Extracts column headers containing numeric-convertible data.

    Args:
        df: Pandas DataFrame.

    Returns:
        List of numeric column header name strings.
    """

    if df.empty:
        return []

    return list(
        df.select_dtypes(
            include=np.number
        ).columns
    )


def text_columns(df: pd.DataFrame):
    """Extracts column headers that do not contain numeric data.

    Args:
        df: Pandas DataFrame.

    Returns:
        List of non-numeric column header name strings.
    """

    if df.empty:
        return []

    nums = numeric_columns(df)

    return [
        c for c in df.columns
        if c not in nums
    ]


def recommend_quality(df: pd.DataFrame):
    """Evaluates data quality metrics and provides quality-related recommendations.

    Args:
        df: Target DataFrame.

    Returns:
        List of quality recommendation strings.
    """

    lines = []

    if df.empty:
        return [
            "No dataset loaded."
        ]

    # missing values
    miss = df.isna().sum()
    miss = miss[miss > 0]

    if len(miss) > 0:

        for col, val in miss.items():

            pct = round(
                (val / len(df)) * 100,
                2
            )

            lines.append(
                f"Column '{col}' has "
                f"{int(val)} missing values "
                f"({pct}%). "
                f"Consider imputation."
            )

    # duplicates
    dup = int(df.duplicated().sum())

    if dup > 0:
        lines.append(
            f"{dup} duplicate rows detected. "
            f"Consider removing duplicates."
        )

    # constant columns
    for col in df.columns:

        try:
            uniq = df[col].nunique(dropna=True)

            if uniq <= 1:
                lines.append(
                    f"Column '{col}' has no variability. "
                    f"Consider removing it."
                )

        except Exception:
            pass

    if not lines:
        lines.append(
            "Dataset quality looks healthy."
        )

    return lines


def recommend_analytics(df: pd.DataFrame):
    """Assesses correlation matrix density and offers analytical guidance.

    Args:
        df: Target DataFrame.

    Returns:
        List of analytical recommendation strings.
    """

    lines = []

    nums = numeric_columns(df)

    if len(nums) >= 2:

        try:
            corr = (
                df[nums]
                .corr()
                .abs()
                .unstack()
                .sort_values(
                    ascending=False
                )
            )

            used = set()

            for (a, b), val in corr.items():

                if a == b:
                    continue

                key = tuple(
                    sorted([a, b])
                )

                if key in used:
                    continue

                used.add(key)

                if val >= 0.75:

                    lines.append(
                        f"Strong relationship "
                        f"between '{a}' and '{b}' "
                        f"(corr={round(val,3)}). "
                        f"Use regression or monitoring."
                    )

                if len(lines) >= 3:
                    break

        except Exception:
            pass

    if len(nums) >= 1:

        lines.append(
            "Numeric columns detected. "
            "Forecasting models can be applied."
        )

    if not lines:
        lines.append(
            "Limited analytics opportunities detected."
        )

    return lines


def recommend_visuals(df: pd.DataFrame):
    """Suggests appropriate chart types based on present columns and datatype profiles.

    Args:
        df: Target DataFrame.

    Returns:
        List of visualization recommendation strings.
    """

    lines = []

    nums = numeric_columns(df)

    if len(nums) >= 2:
        lines.append(
            "Use correlation heatmap "
            "for numeric variables."
        )

    if len(nums) >= 1:
        lines.append(
            "Use histograms and boxplots "
            "for outlier detection."
        )

    if "time" in " ".join(
        [c.lower() for c in df.columns]
    ):
        lines.append(
            "Time column detected. "
            "Use trend line charts."
        )

    if not lines:
        lines.append(
            "Use table preview "
            "for manual inspection."
        )

    return lines


def recommend_ml(df: pd.DataFrame):
    """Proposes machine learning strategies based on sample size and column profiles.

    Args:
        df: Target DataFrame.

    Returns:
        List of ML recommendations.
    """

    lines = []

    rows = len(df)
    cols = len(df.columns)

    if rows >= 100:
        lines.append(
            "Enough rows for "
            "machine learning experiments."
        )

    if rows >= 1000:
        lines.append(
            "Dataset size suitable for "
            "deep learning pipelines."
        )

    if cols >= 5:
        lines.append(
            "Feature engineering may improve results."
        )

    nums = numeric_columns(df)

    if len(nums) >= 2:
        lines.append(
            "Regression and anomaly detection "
            "models are recommended."
        )

    if not lines:
        lines.append(
            "Small dataset: use simpler models."
        )

    return lines


def recommend_process(df: pd.DataFrame):
    """Scans column names for industrial keyword matches (temperature, pH, oxygen) to recommend bioprocess checks.

    Args:
        df: Target DataFrame.

    Returns:
        List of industrial process advice strings.
    """

    lines = []

    cols_lower = [
        c.lower()
        for c in df.columns
    ]

    if any(
        "temp" in c
        for c in cols_lower
    ):
        lines.append(
            "Temperature variables detected. "
            "Monitor thermal stability."
        )

    if any(
        "ph" in c
        for c in cols_lower
    ):
        lines.append(
            "pH variables detected. "
            "Use control limits."
        )

    if any(
        "oxygen" in c or "o2" in c
        for c in cols_lower
    ):
        lines.append(
            "Oxygen variables detected. "
            "Check aeration efficiency."
        )

    if any(
        "co2" in c
        for c in cols_lower
    ):
        lines.append(
            "CO2 variables detected. "
            "Use respiration trend monitoring."
        )

    if not lines:
        lines.append(
            "No specific process signals found."
        )

    return lines


def generate_recommendations(
    df: pd.DataFrame
):
    """Combines recommendations across multiple sections.

    Args:
        df: Target DataFrame.

    Returns:
        List of formatted recommendation strings, separated by section headers.
    """

    if df.empty:
        return [
            "No dataset loaded."
        ]

    logger.info(
        "Generating smart recommendations..."
    )

    output = []

    output.append(
        "SMART RECOMMENDATIONS"
    )
    output.append("")

    # sections
    sections = [
        (
            "DATA QUALITY",
            recommend_quality(df)
        ),
        (
            "ANALYTICS",
            recommend_analytics(df)
        ),
        (
            "VISUALIZATION",
            recommend_visuals(df)
        ),
        (
            "MACHINE LEARNING",
            recommend_ml(df)
        ),
        (
            "PROCESS INSIGHTS",
            recommend_process(df)
        ),
    ]

    for title, lines in sections:

        output.append(title)

        for i, line in enumerate(
            lines, start=1
        ):
            output.append(
                f"{i}. {line}"
            )

        output.append("")

    logger.info(
        "Recommendations ready."
    )

    return output


def recommend_from_storage(
    storage: dict
):
    """Entry point to convert shared storage mapping into a recommendation list.

    Args:
        storage: Web app session state dictionary.

    Returns:
        List of recommendation strings.
    """

    df = storage_to_df(storage)

    return generate_recommendations(df)