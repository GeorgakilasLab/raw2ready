"""Merge GUI module.

Provides a user interface to combine multiple datasets using either row-wise
(concatenation) or column-wise (merge/join) operations.
"""

from nicegui import ui, app
import pandas as pd
import traceback

import src.utils.theme as theme
from src.utils.logging_config import get_logger
from src.utils.paths import ensure_dirs

logger = get_logger("merge_gui")


class mergegui:
    """Manages the merge page interface and operations.

    Attributes:
        storage: Data storage container dict.
        config_: Configuration dictionary.
        page_url_path: URL path for the page.
        frame_name: Display name of the page frame.
        df: The currently merged pandas DataFrame.
        file_select: Dropdown selector for datasets.
        reference_file: Dropdown selector for reference files.
        merge_type: Selector for Row-wise or Column-wise merges.
        merge_on: Selector for columns to merge on.
        group_columns: Selector for columns to group by.
        output_name: Input for custom output dataset name.
        preview_container: Container displaying the merged data.
        info_label: Label displaying merge status.
    """

    # =====================================================
    # INIT
    # =====================================================
    def __init__(
        self,
        config,
        page_url_path="/merge",
        frame_name="Merge",
        add_page=False,
        storage_container=None,
        storage_container_=None,
    ):
        """Initializes the mergegui.

        Args:
            config: Configuration dictionary.
            page_url_path: URL path for the page. Defaults to "/merge".
            frame_name: Display name of the page frame. Defaults to "Merge".
            add_page: Whether to register the page route. Defaults to False.
            storage_container: Primary data storage dictionary. Defaults to None.
            storage_container_: Alternate storage container dictionary. Defaults to None.
        """

        logger.info("initialising mergegui")

        if storage_container is None and storage_container_ is not None:
            storage_container = storage_container_

        if storage_container is None:
            storage_container = {}

        self.storage = storage_container
        self.config_ = config

        self.page_url_path = page_url_path
        self.frame_name = frame_name

        self.df = None

        # UI
        self.file_select = None
        self.reference_file = None
        self.merge_type = None
        self.merge_on = None
        self.group_columns = None
        self.output_name = None

        self.preview_container = None
        self.info_label = None

        if add_page:
            self.add_page()

    # =====================================================
    # PAGE
    # =====================================================
    def add_page(self):
        """Adds this page as a distinct route in the application."""

        @ui.page(self.page_url_path)
        def page():

            if "shared_data" in app.storage.general:
                self.storage = app.storage.general["shared_data"]

            with theme.frame(self.frame_name):
                self.content_()

    # =====================================================
    # UI
    # =====================================================
    def content_(self):

        with ui.row().classes("w-full no-wrap"):

            # =========================
            # LEFT PANEL
            # =========================
            with ui.column().classes("w-[430px] p-4 gap-4 bg-slate-100"):

                ui.label("Merge Datasets").classes("text-h5")

                ui.label("Select Files")

                self.file_select = ui.select(
                    [],
                    label="Datasets",
                    multiple=True
                ).classes("w-full")

                self.file_select.on_value_change(lambda e: self.update_columns())
                self.reference_file = ui.select(
                    [],
                    label="Reference File"
                ).classes("w-full")

                ui.button(
                    "REFRESH FILES",
                    on_click=self.refresh_loaded_files
                ).classes("w-full")

                ui.separator()

                ui.label("Merge Settings")

                self.merge_type = ui.select(
                    ["Column-wise", "Row-wise"],
                    value="Column-wise",
                    label="Merge Type"
                ).classes("w-full")

                self.merge_on = ui.select(
                    [],
                    multiple=True,
                    label="Merge Columns"
                ).classes("w-full")

                self.group_columns = ui.select(
                    [],
                    multiple=True,
                    label="Group Columns (optional)"
                ).classes("w-full")

                self.output_name = ui.input(
                    label="Output Dataset Name"
                ).classes("w-full")

                with ui.row().classes("w-full gap-2"):
                    ui.button("MERGE", on_click=self.run_merge).classes("flex-1")

                ui.button("EXPORT CSV", on_click=self.export_csv).classes("w-full")

                self.info_label = ui.label("No merge yet")

            # =========================
            # RIGHT PANEL
            # =========================
            with ui.column().classes("flex-1 p-4 gap-3"):

                ui.label("Merged Dataset Preview").classes("text-h6")

                self.preview_container = ui.column().classes("w-full")

        self.refresh_loaded_files()
        self.reference_file.on_value_change(lambda e: self.update_columns())

    # =====================================================
    # LOAD DATAFRAME
    # =====================================================
    def load_df(self, name):
        """Loads a pandas DataFrame from storage cache by name.

        Args:
            name: Filename or key of the cached dataset.

        Returns:
            The loaded pandas DataFrame, or None if not found.
        """

        cache = self.storage.get("parsed_cache", {})

        if name in cache:
            return pd.DataFrame(cache[name])

        return None

    # =====================================================
    # REFRESH FILES
    # =====================================================
    def refresh_loaded_files(self):
        """Refreshes the file selection dropdown options from storage cache."""

        files = list(self.storage.get("parsed_cache", {}).keys())

        self.file_select.options = files
        self.reference_file.options = files

        self.file_select.update()
        self.reference_file.update()

    # =====================================================
    # SUGGEST TIME COLUMN
    # =====================================================
    def suggest_time_column(self, df):
        """Suggests a column name likely representing datetime.

        Args:
            df: The pandas DataFrame.

        Returns:
            The suggested column name string, or None.
        """

        for col in df.columns:
            if col.lower() in ["datetime", "time", "timestamp"]:
                return col
        return None

    # =====================================================
    # UPDATE COLUMNS
    # =====================================================
    def update_columns(self):
        """Updates selectable columns in dropdowns based on loaded datasets."""

        files = self.file_select.value
        ref = self.reference_file.value
    
        if not files or not ref:
            return
    
        dfs = {}
    
        # load all dfs
        for f in files:
            df = self.load_df(f)
            if df is not None:
                dfs[f] = df
    
        if not dfs:
            return
    
        # -------------------------
        # FIND COMMON COLUMNS
        # -------------------------
        common_cols = set(list(dfs.values())[0].columns)
    
        for df in dfs.values():
            common_cols = common_cols.intersection(set(df.columns))
    
        common_cols = list(common_cols)
    
        # -------------------------
        # FAIL SAFE (IMPORTANT)
        # -------------------------
        if not common_cols:
            if self.merge_type.value == "Column-wise":
                ui.notify("No common columns found between datasets", type="warning")
    
            # fallback: show reference columns instead
            ref_df = dfs.get(ref)
            if ref_df is not None:
                self.merge_on.options = list(ref_df.columns)
            else:
                self.merge_on.options = []
    
        else:
            self.merge_on.options = common_cols
    
        # group columns = reference columns
        ref_df = dfs.get(ref)
        if ref_df is not None:
            self.group_columns.options = list(ref_df.columns)
    
        # -------------------------
        # AUTO SELECT DATETIME
        # -------------------------
        for col in self.merge_on.options:
            if col.lower() in ["datetime", "time", "timestamp"]:
                self.merge_on.value = [col]
                break
    
        self.merge_on.update()
        self.group_columns.update()

    # =====================================================
    # DATETIME NORMALIZATION
    # =====================================================
    def normalize_datetime(self, df, col):
        """Normalizes and sorts a DataFrame's column to datetime.

        Args:
            df: The pandas DataFrame to normalize.
            col: The column name to convert.

        Returns:
            The normalized pandas DataFrame sorted by the datetime column.
        """

        df[col] = pd.to_datetime(df[col], errors="coerce")
        df = df.dropna(subset=[col])
        return df.sort_values(col)

    # =====================================================
    # VALIDATION
    # =====================================================
    def validate_merge(self, dfs, merge_cols):
        """Validates that all DataFrames contain the required merge columns.

        Args:
            dfs: Dictionary mapping names to pandas DataFrames.
            merge_cols: List of column names to check.

        Returns:
            True if valid, False otherwise.
        """

        missing = []

        for name, df in dfs.items():
            for col in merge_cols:
                if col not in df.columns:
                    missing.append((name, col))

        if missing:
            msg = "\n".join([f"{f} missing {c}" for f, c in missing])
            ui.notify(f"Missing columns:\n{msg}", type="negative")
            return False

        return True

    # =====================================================
    # COLUMN-WISE MERGE
    # =====================================================
    def merge_columnwise(self, dfs, ref_name, merge_cols):
        """Merges multiple DataFrames column-wise using a left join on reference.

        Args:
            dfs: Dictionary mapping names to pandas DataFrames.
            ref_name: Name of the reference DataFrame.
            merge_cols: List of column names to join on.

        Returns:
            The merged pandas DataFrame.
        """

        ref_df = dfs[ref_name].copy()
        result = ref_df
    
        for name, df in dfs.items():
    
            if name == ref_name:
                continue
    
            df_copy = df.copy()
    
            # -----------------------------
            # HANDLE DUPLICATE COLUMNS
            # -----------------------------
            overlap = set(result.columns).intersection(df_copy.columns) - set(merge_cols)
    
            if overlap:
                rename_map = {}
    
                for col in overlap:
                    short = name.split(".")[0]
                    new_name = f"{col}__{name}"
                    rename_map[col] = new_name
    
                df_copy = df_copy.rename(columns=rename_map)
    
                ui.notify(
                    f"Renamed duplicate columns in {name}: {list(rename_map.keys())}",
                    type="warning"
                )
    
            # -----------------------------
            # MERGE
            # -----------------------------
            result = pd.merge(
                result,
                df_copy,
                on=merge_cols,
                how="left"
            )
    
        return result

    # =====================================================
    # ROW-WISE MERGE
    # =====================================================
    def merge_rowwise(self, dfs, merge_cols):
        """Merges multiple DataFrames row-wise (concatenation).

        Args:
            dfs: Dictionary mapping names to pandas DataFrames.
            merge_cols: List of column names to sort by if present.

        Returns:
            The concatenated pandas DataFrame.
        """
    
        if not dfs:
            return None
    
        # --------------------------------------------------
        # 1. UNION OF ALL COLUMNS
        # --------------------------------------------------
        all_columns = set()
        for df in dfs.values():
            all_columns.update(df.columns)
    
        # --------------------------------------------------
        # 2. SMART COLUMN ORDER (IMPORTANT)
        # --------------------------------------------------
        priority = ["datetime", "experiment_name"]
        existing_priority = [c for c in priority if c in all_columns]
        other_cols = sorted([c for c in all_columns if c not in existing_priority])
    
        all_columns = existing_priority + other_cols
    
        # --------------------------------------------------
        # 3. ALIGN EACH DATAFRAME
        # --------------------------------------------------
        aligned_dfs = []
    
        for name, df in dfs.items():
            df_copy = df.copy()
    
            # add missing columns
            for col in all_columns:
                if col not in df_copy.columns:
                    df_copy[col] = pd.NA
    
            # enforce same column order
            df_copy = df_copy[all_columns]
    
            aligned_dfs.append(df_copy)
    
        # --------------------------------------------------
        # 4. CONCAT (STACK)
        # --------------------------------------------------
        result = pd.concat(aligned_dfs, ignore_index=True)
    
        # --------------------------------------------------
        # 5. OPTIONAL SORT (if merge_cols exist)
        # --------------------------------------------------
        if merge_cols:
            valid_sort_cols = [c for c in merge_cols if c in result.columns]
            if valid_sort_cols:
                result = result.sort_values(valid_sort_cols)
    
        result.reset_index(drop=True, inplace=True)
    
        return result

    # =====================================================
    # MAIN MERGE
    # =====================================================
    def run_merge(self):
        """Executes the merge workflow and saves results to storage."""
        self._run_merge(save=True)

    def _run_merge(self, save=True):
        """Helper to execute the merge workflow.

        Args:
            save: Whether to persist the merge result to storage cache. Defaults to True.
        """

        try:

            files = self.file_select.value
            ref = self.reference_file.value
            merge_cols = self.merge_on.value

            if not files or len(files) < 2:
                ui.notify("Select at least 2 files", type="negative")
                return

            if ref not in files:
                ui.notify("Reference must be in selected files", type="negative")
                return

            if not merge_cols:
                ui.notify("Select merge columns", type="negative")
                return

            dfs = {f: self.load_df(f) for f in files}
            
            if self.merge_type.value == "Column-wise":
                if not self.validate_merge(dfs, merge_cols):
                    return

            # normalize datetime
            for name in dfs:
                for col in merge_cols:
                    dfs[name] = self.normalize_datetime(dfs[name], col)

            # MERGE
            if self.merge_type.value == "Column-wise":
                result = self.merge_columnwise(dfs, ref, merge_cols)
            else:
                result = self.merge_rowwise(dfs, merge_cols)

            if result is None:
                return

            self.df = result
            self.refresh_preview()

            if not save:
                return

            # SAVE
            name = self.output_name.value or "merged_dataset"

            if "parsed_cache" not in self.storage:
                self.storage["parsed_cache"] = {}

            if name in self.storage["parsed_cache"]:
                ui.notify("Dataset name already exists", type="warning")
                return

            self.storage["parsed_cache"][name] = result.astype(str).to_dict("records")
            self.storage["parsed_df_json"] = result.astype(str).to_dict("records")
            self.storage["parsed_df_columns"] = list(result.columns)
            self.storage["last_loaded_file"] = name

            # history
            if "merge_history" not in self.storage:
                self.storage["merge_history"] = []

            self.storage["merge_history"].append({
                "name": name,
                "files": files,
                "type": self.merge_type.value,
            })

            self.info_label.text = f"{name} | {len(result)} rows"

            ui.notify("Merge completed", type="info")

        except Exception as e:
            logger.error(traceback.format_exc())
            ui.notify(f"Merge failed: {str(e)}", type="negative")

    # =====================================================
    # EXPORT
    # =====================================================
    def export_csv(self):
        """Exports the merged dataset as a downloadable CSV file."""

        if self.df is None:
            return

        path = str(ensure_dirs()["exports"] / "merged_dataset.csv")
        self.df.to_csv(path, index=False)

        ui.download(path)

    # =====================================================
    # PREVIEW TABLE
    # =====================================================
    def refresh_preview(self):
        """Refreshes the merged dataset preview table."""

        if not self.preview_container:
            return

        self.preview_container.clear()

        with self.preview_container:

            if self.df is None:
                ui.label("No merged dataset")
                return

            ui.label(f"{len(self.df)} rows | {len(self.df.columns)} columns")

            ui.table(
                columns=[
                    {"name": c, "label": c, "field": c}
                    for c in self.df.columns
                ],
                rows=self.df.head(200).astype(str).to_dict("records"),
                pagination=10,
            ).classes("w-full")