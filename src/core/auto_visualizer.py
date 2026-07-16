"""Auto Visualizer module.

Provides the AutoVisualizer class to inspect datasets and auto-generate plots
including histograms, boxplots, correlations, and timeseries charts.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from nicegui import ui

from src.utils.logging_config import get_logger
from src.utils.paths import ensure_dirs

logger = get_logger("auto_visualizer")


class AutoVisualizer:
    """Auto-generates charts and visualization reports from target DataFrames."""

    def __init__(self, storage_container: dict):
        """Initializes AutoVisualizer.

        Args:
            storage_container: Dictionary containing the dataset representation ('df_json', 'df_columns').
        """

        self.storage = storage_container

        self.output_dir = ensure_dirs()["charts"]

    def get_df(self):
        """Constructs pandas DataFrame from stored session storage.

        Returns:
            Pandas DataFrame if metadata exists and is parseable, otherwise None.
        """

        rows = self.storage.get(
            "df_json", []
        )

        cols = self.storage.get(
            "df_columns", []
        )

        if not rows or not cols:
            return None

        try:
            df = pd.DataFrame(rows)
            df = df[cols]
            return df

        except Exception as e:
            logger.warning(
                f"df build error: {e}"
            )
            return None

    def numeric_columns(self, df):
        """Finds all columns containing numeric datatypes.

        Args:
            df: Pandas DataFrame.

        Returns:
            List of column names containing numeric datatypes.
        """

        try:
            return list(
                df.select_dtypes(
                    include="number"
                ).columns
            )
        except Exception:
            return []

    def save_fig(self, name):
        """Saves current matplotlib figure state to temp charts directory.

        Args:
            name: Filename string for the saved png file.

        Returns:
            URL/relative path to file.
        """

        path = self.output_dir / name

        plt.tight_layout()
        plt.savefig(
            path,
            dpi=140,
            bbox_inches="tight"
        )
        plt.close()

        return f"/{path}"

    def histogram(self, df, col):
        """Creates histogram plot for a target column.

        Args:
            df: Pandas DataFrame.
            col: Target column name.

        Returns:
            Path of the saved image file.
        """

        plt.figure(figsize=(8, 4))
        df[col].dropna().hist(
            bins=30
        )
        plt.title(
            f"Distribution - {col}"
        )
        plt.xlabel(col)
        plt.ylabel("Count")

        return self.save_fig(
            f"hist_{col}.png"
        )

    def boxplot(self, df, col):
        """Creates boxplot for a target column.

        Args:
            df: Pandas DataFrame.
            col: Target column name.

        Returns:
            Path of the saved image file.
        """

        plt.figure(figsize=(8, 4))
        plt.boxplot(
            df[col].dropna()
        )
        plt.title(
            f"Boxplot - {col}"
        )

        return self.save_fig(
            f"box_{col}.png"
        )

    def correlation(self, df):
        """Creates correlation heatmap for numeric columns.

        Args:
            df: Pandas DataFrame.

        Returns:
            Path of the saved image file, or None if too few numeric columns.
        """

        nums = self.numeric_columns(df)

        if len(nums) < 2:
            return None

        corr = df[nums].corr()

        plt.figure(figsize=(8, 6))
        plt.imshow(
            corr,
            aspect="auto"
        )
        plt.colorbar()
        plt.xticks(
            range(len(nums)),
            nums,
            rotation=90
        )
        plt.yticks(
            range(len(nums)),
            nums
        )
        plt.title(
            "Correlation Heatmap"
        )

        return self.save_fig(
            "correlation.png"
        )

    def timeseries(self, df):
        """Generates line plot from first column and second numeric column.

        Args:
            df: Pandas DataFrame.

        Returns:
            Path of the saved image file, or None on failure.
        """

        if len(df.columns) < 2:
            return None

        try:
            x = df.iloc[:, 0]
            y = pd.to_numeric(
                df.iloc[:, 1],
                errors="coerce"
            )

            plt.figure(figsize=(10, 4))
            plt.plot(
                x,
                y
            )
            plt.title(
                "Auto Time Series"
            )
            plt.xticks(rotation=45)

            return self.save_fig(
                "timeseries.png"
            )

        except Exception:
            return None

    def render(self):
        """Spawns NiceGUI modal dialog displaying the auto-generated chart gallery."""

        df = self.get_df()

        if df is None:

            ui.notify(
                "No dataset loaded",
                type="negative"
            )
            return

        nums = self.numeric_columns(df)

        with ui.dialog() as dialog, ui.card().classes(
            "w-[1100px] max-w-full"
        ):

            ui.label(
                "Auto Visualization Engine"
            ).classes(
                "text-2xl font-bold"
            )

            with ui.column().classes(
                "w-full gap-6"
            ):

                # Correlation
                corr = self.correlation(df)

                if corr:
                    ui.label(
                        "Correlation Heatmap"
                    ).classes(
                        "text-lg font-bold"
                    )

                    ui.image(corr).classes(
                        "w-full rounded-xl"
                    )

                # Numeric charts
                for col in nums[:3]:

                    ui.separator()

                    ui.label(
                        f"Analytics for {col}"
                    ).classes(
                        "text-lg font-bold"
                    )

                    hist = self.histogram(
                        df, col
                    )

                    box = self.boxplot(
                        df, col
                    )

                    with ui.row().classes(
                        "w-full gap-4"
                    ):

                        ui.image(hist).classes(
                            "w-1/2 rounded-xl"
                        )

                        ui.image(box).classes(
                            "w-1/2 rounded-xl"
                        )

                # Timeseries
                ts = self.timeseries(df)

                if ts:
                    ui.separator()

                    ui.label(
                        "Auto Time Series"
                    ).classes(
                        "text-lg font-bold"
                    )

                    ui.image(ts).classes(
                        "w-full rounded-xl"
                    )

                ui.button(
                    "Close",
                    on_click=dialog.close
                )

        dialog.open()