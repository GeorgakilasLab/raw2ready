"""Calculate GUI module.

Provides a user interface for performing mathematical and logical column operations
on loaded experimental datasets.
"""

from nicegui import ui
import pandas as pd
import numpy as np

import src.utils.theme as theme
from src.utils.logging_config import get_logger
from src.utils.paths import ensure_dirs

logger = get_logger("calculate_gui")


class calculategui:
    """Manages the calculation page interface and operations.

    Attributes:
        config_: Configuration dictionary.
        frame_name: Name of the page frame.
        page_url_path: URL path for the page.
        storage: Data storage container dict.
        df: The currently loaded pandas DataFrame.
        alias_inputs: Mapping of column names to user-defined aliases.
    """

    def __init__(
        self,
        config,
        page_url_path="/calculate",
        frame_name="Calculate",
        add_page=False,
        storage_container=None,
        storage_container_=None,
    ) -> None:
        """Initializes the calculategui.

        Args:
            config: Configuration dictionary.
            page_url_path: URL path for the page. Defaults to "/calculate".
            frame_name: Display name of the page frame. Defaults to "Calculate".
            add_page: Whether to register the page route. Defaults to False.
            storage_container: Primary data storage dictionary. Defaults to None.
            storage_container_: Alternate storage container dictionary. Defaults to None.
        """

        logger.info("initialising calculategui")

        # backward compatibility
        if storage_container_ is not None:
            storage_container = storage_container_

        if storage_container is None:
            storage_container = {}

        self.config_ = config
        self.frame_name = frame_name
        self.page_url_path = page_url_path
        self.storage = storage_container

        self.df = None
        self.alias_inputs = {}

        self.load_from_storage()

        if add_page:
            self.add_page(
                page_url=self.page_url_path,
                frame_name=self.frame_name,
            )

    # ---------------------------------------------------
    def load_from_storage(self):
        """Loads dataframes from storage container dictionary."""

        self.df = None
        self.current_df = None
    
        try:
            # ---------------------------------
            # Preferred JSON-safe persistence
            # ---------------------------------
            if (
                "df_json" in self.storage and
                "df_columns" in self.storage
            ):
    
                self.df = pd.DataFrame(
                    self.storage["df_json"]
                )
    
                self.df = self.df[
                    self.storage["df_columns"]
                ]
    
                self.current_df = self.df
                return
    
            # ---------------------------------
            # Fallback from uploaded files
            # ---------------------------------
            files = self.storage.get("files", {})
    
            if isinstance(files, dict) and files:
    
                last_file = self.storage.get(
                    "last_loaded_file"
                )
    
                if last_file in files:
                    fname = last_file
                else:
                    fname = list(files.keys())[0]
    
                first_sheet = files[fname][
                    "sheet names"
                ][0]
    
                sheet_obj = files[fname][
                    "file data"
                ][first_sheet]
    
                if (
                    "sheet json" in sheet_obj and
                    "sheet columns" in sheet_obj
                ):
                    self.df = pd.DataFrame(
                        sheet_obj["sheet json"]
                    )
                
                    self.df = self.df[
                        sheet_obj["sheet columns"]
                    ]
                
                elif "sheet data" in sheet_obj:

                    # old storage migration
                    self.df = sheet_obj["sheet data"].copy()
                
                    sheet_obj["sheet json"] = self.df.to_dict(
                        orient="records"
                    )
                
                    sheet_obj["sheet columns"] = list(
                        self.df.columns
                    )
                
                    del sheet_obj["sheet data"]
    
                self.current_df = self.df
                return
    
        except Exception:
            self.df = None
            self.current_df = None
            
    # ---------------------------------------------------
    def get_available_files(self):
        """Gets list of available file names from parsed cache.

        Returns:
            List of filenames as strings.
        """
        return list(
            self.storage.get("parsed_cache", {}).keys()
        )
    # ---------------------------------------------------
    def add_page(
        self,
        page_url="/calculate",
        frame_name="Calculate"
    ) -> None:
        """Adds this page as a distinct route in the application.

        Args:
            page_url: The URL path. Defaults to "/calculate".
            frame_name: The display name of the frame. Defaults to "Calculate".
        """

        @ui.page(page_url)
        def page_():
        
            if "shared_data" not in app.storage.general:
                app.storage.general["shared_data"] = {}

            with theme.frame(frame_name):
                self.content_()

    # ---------------------------------------------------
    def export_csv(self):
        """Exports the current calculated DataFrame as a CSV download."""

        if self.df is None:
            ui.notify("No dataframe loaded")
            return
    
        try:
            filename = str(
                ensure_dirs()["exports"] / "calculated_dataset.csv"
            )
    
            self.df.to_csv(filename, index=False)
    
            ui.download(filename)
    
            ui.notify("CSV exported successfully")
    
        except Exception as e:
            ui.notify(str(e))
    # ---------------------------------------------------
    def content_(self):
        """Renders the HTML/CSS contents of the calculation page."""

        self.load_from_storage()

        with ui.row().classes("w-full no-wrap"):

            # ==================================================
            # LEFT PANEL
            # ==================================================
            with ui.column().classes(
                "w-[390px] p-4 gap-3 bg-slate-100"
            ):

                ui.label("Calculate").classes("text-h5")

                ui.label("Select Data File").classes("text-subtitle1")

                with ui.row().classes("w-full items-center gap-2"):

                    self.file_selector = ui.select(
                        [],
                        label="Loaded Files",
                        with_input=True,
                        on_change=self.load_selected_file,
                    ).classes("flex-1")

                    ui.button(
                        "REFRESH",
                        on_click=self.refresh_files
                    )

                self.info_label = ui.label("")

                # ----------------------------------------------
                # FILTERS
                # ----------------------------------------------
                self.exp_col = ui.select(
                    [],
                    label="Experiment Column",
                    with_input=True,
                    on_change=lambda e: self.update_experiment_values(),
                ).classes("w-full")

                self.exp_val = ui.select(
                    [],
                    label="Experiment Values",
                    multiple=True,
                    with_input=True,
                    on_change=lambda e: self.show_filtered_table(),
                ).props("use-chips").classes("w-full")

                self.well_selector = ui.select(
                    [],
                    label="Wells",
                    multiple=True,
                    with_input=True,
                    on_change=lambda e: self.show_filtered_table(),
                ).props("use-chips").classes("w-full")

                # ----------------------------------------------
                # VARIABLES
                # ----------------------------------------------
                self.var_selector = ui.select(
                    [],
                    label="Variables X & Y",
                    multiple=True,
                    with_input=True,
                    on_change=lambda e: self.update_ui(),
                ).props("use-chips").classes("w-full")

                ui.label("Aliases").classes("text-sm")

                self.alias_box = ui.column().classes(
                    "w-full gap-2 bg-white p-2 rounded shadow"
                )

                self.new_col = ui.input(
                    label="New Column Name",
                    placeholder="example: growth_rate"
                ).classes("w-full")

                self.formula = ui.input(
                    label="Formula",
                    placeholder="example: A / B"
                ).classes("w-full")

                ui.label("Examples:")
                ui.label("A / B")
                ui.label("log(A)")
                ui.label("sqrt(B)")
                ui.label("A.diff()")
                ui.label("A.rolling(5).mean()")

                ui.button(
                    "CALCULATE",
                    on_click=self.calculate_expression
                ).classes("w-full")

                ui.button(
                    "CLEAR",
                    on_click=lambda: self.plot_area.clear()
                ).classes("w-full")
                
                ui.button(
                    "EXPORT",
                    on_click=self.export_csv
                ).classes("w-full")
                
                

            # ==================================================
            # RIGHT PANEL
            # ==================================================
            with ui.column().classes("flex-1 p-4"):

                ui.label("Filtered DataFrame").classes("text-h5")
            
                self.preview_box = ui.column().classes(
                    "w-full h-[720px] overflow-auto bg-white p-2 rounded shadow"
                )

                self.plot_area = self.preview_box

        self.update_ui()
        self.refresh_files()

    # ---------------------------------------------------
    def refresh_files(self):
        """Refreshes the file selector options from the parsed cache."""

        # ======================================
        # GET FILES FROM PARSED CACHE
        # ======================================
        files = self.get_available_files()
    
        # ======================================
        # UPDATE SELECT OPTIONS
        # ======================================
        self.file_selector.options = files
        self.file_selector.update()
    
        # ======================================
        # HANDLE EMPTY STATE
        # ======================================
        if not files:
            self.file_selector.value = None
            self.preview_box.clear()
            with self.preview_box:
                ui.label("No parsed datasets available.")
            return
    
        # ======================================
        # RESTORE LAST SELECTED FILE
        # ======================================
        last = self.storage.get("last_loaded_file")
    
        if last in files:
            selected = last
        else:
            selected = files[0]
    
        # ======================================
        # SET VALUE ONLY IF CHANGED
        # (prevents unnecessary reloads)
        # ======================================
        if self.file_selector.value != selected:
            self.file_selector.value = selected
            self.file_selector.update()
    
        # ======================================
        # LOAD DATA FROM CACHE (NO PARSE)
        # ======================================
        self.load_selected_file()
    
    # ---------------------------------------------------
    def update_selectors(self):
        """Updates options for the dropdown selectors based on active dataframe columns."""

        if self.df is None:
            return
    
        cols = list(self.df.columns)
    
        # file stats
        if hasattr(self, "stats_label"):
            self.stats_label.text = (
                f"Rows: {len(self.df)} | Columns: {len(cols)}"
            )
    
        # Experiment column selector
        if hasattr(self, "exp_col"):
            self.exp_col.options = cols
            self.exp_col.update()
    
        # Variables selector
        if hasattr(self, "var_selector"):
            self.var_selector.options = cols
            self.var_selector.update()
    
        # Wells selector
        for c in cols:
            if "well" in c.lower():
    
                wells = sorted(
                    self.df[c]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                    .tolist()
                )
    
                if hasattr(self, "well_selector"):
                    self.well_selector.options = wells
                    self.well_selector.update()
    
                break

    # ---------------------------------------------------
    def load_selected_file(self):
        """Loads the currently selected file data from the cache into memory."""

        try:
            filename = self.file_selector.value
    
            if not filename:
                ui.notify("No file selected")
                return
    
            # ================================
            # LOAD FROM CACHE (NO PARSE)
            # ================================
            cached = self.storage.get("parsed_cache", {}).get(filename)
    
            if not cached:
                ui.notify("File not found in cache", type="negative")
                return
    
            # reconstruct dataframe
            df = pd.DataFrame(cached)
    
            self.df = df.copy()
            self.current_df = df.copy()
    
            # keep global copy (optional but useful)
            self.storage["df_json"] = cached
            self.storage["df_columns"] = list(df.columns)
    
            # ================================
            # CLEAN COLUMNS
            # ================================
            self.df.columns = self.df.columns.astype(str).str.strip()
    
            for c in self.df.columns:
                try:
                    self.df[c] = pd.to_numeric(self.df[c])
                except:
                    pass
    
            # ================================
            # UPDATE UI
            # ================================
            self.update_selectors()
    
            self.preview_box.clear()
    
            with self.preview_box:
    
                ui.label(f"Rows Loaded: {len(self.df)}")
    
                ui.table(
                    columns=[
                        {"name": c, "label": c, "field": c}
                        for c in self.df.columns
                    ],
                    rows=self.df.head(10).to_dict("records"),
                    pagination=10,
                ).classes("text-xs")
    
            ui.notify(f"{filename} loaded from cache")
    
        except Exception as e:
            ui.notify(f"Load error: {str(e)}")

    # ---------------------------------------------------
    def update_experiment_values(self):
        """Updates available values for the experiment column filter based on selection."""

        if self.df is None:
            return

        col = self.exp_col.value

        if not col or col not in self.df.columns:
            return

        vals = sorted(
            self.df[col]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        self.exp_val.options = vals
        self.exp_val.update()

        self.show_filtered_table()

    # ---------------------------------------------------
    def update_ui(self):
        """Updates the general UI parameters and options based on current DataFrame state."""

        if self.df is None:
            self.info_label.text = "No dataframe loaded"
            return

        self.info_label.text = (
            f"Rows: {len(self.df)} | "
            f"Columns: {len(self.df.columns)}"
        )

        cols = list(self.df.columns)

        self.var_selector.options = cols
        self.exp_col.options = cols

        self.var_selector.update()
        self.exp_col.update()

        if not self.var_selector.value:

            numeric = self.df.select_dtypes(
                include=np.number
            ).columns.tolist()
        
            # remove helper columns
            numeric = [
                c for c in numeric
                if "time" not in c.lower()
                and "date" not in c.lower()
            ]
        
            if len(numeric) >= 2:
                self.var_selector.value = numeric[:2]
        
            elif len(numeric) == 1:
                self.var_selector.value = numeric
        
            else:
                # fallback first 2 columns
                self.var_selector.value = cols[:2]
        
            self.var_selector.update()
            
        well_col = self.get_well_column()

        if well_col:

            wells = sorted(
                self.df[well_col]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

            self.well_selector.options = wells
            self.well_selector.update()

        self.generate_alias_inputs()
        self.show_filtered_table()

    # ---------------------------------------------------
    def get_well_column(self):
        """Finds the name of the column containing well identifiers.

        Returns:
            The column name string or None if not found.
        """

        for c in self.df.columns:
            if "well" in c.lower():
                return c

        return None

    # ---------------------------------------------------
    def get_filtered_df(self):
        """Applies experiment and well filters to the current DataFrame.

        Returns:
            A filtered copy of the pandas DataFrame.
        """

        df = self.df.copy()

        if (
            self.exp_col.value
            and self.exp_val.value
            and self.exp_col.value in df.columns
        ):
            df = df[
                df[self.exp_col.value]
                .astype(str)
                .isin(self.exp_val.value)
            ]

        well_col = self.get_well_column()

        if well_col and self.well_selector.value:
            df = df[
                df[well_col]
                .astype(str)
                .isin(self.well_selector.value)
            ]

        return df

    # ---------------------------------------------------
    def generate_alias_inputs(self):
        """Generates input text fields dynamically for aliasing selected columns."""

        self.alias_box.clear()
        self.alias_inputs = {}

        if not self.var_selector.value:
            return

        with self.alias_box:

            for i, col in enumerate(self.var_selector.value):

                alias = chr(65 + i)

                self.alias_inputs[col] = ui.input(
                    label=f"{col} --> Alias",
                    value=alias
                ).classes("w-full")

    # ---------------------------------------------------
    def show_filtered_table(self):
        """Displays the filtered DataFrame inside the NiceGUI preview table."""

        if self.df is None:
            return
    
        self.plot_area.clear()
    
        df = self.get_filtered_df()
    
        # ==========================================
        # SAFE SELECTED COLUMNS
        # ==========================================
        selected = self.var_selector.value or []
    
        # keep only columns that actually exist
        selected = [
            c for c in selected
            if c in df.columns
        ]
    
        # ==========================================
        # AUTO ADD IMPORTANT COLUMNS
        # ==========================================
        visible_cols = []
    
        important_patterns = [
            "time",
            "datetime",
            "well",
            "protocol"
        ]
    
        for c in df.columns:
    
            cl = str(c).lower()
    
            if any(p in cl for p in important_patterns):
                visible_cols.append(c)
    
        # add selected columns
        for c in selected:
            if c not in visible_cols:
                visible_cols.append(c)
    
        # ==========================================
        # FINAL SAFETY
        # ==========================================
        valid_cols = [
            c for c in visible_cols
            if c in df.columns
        ]
    
        # fallback
        if not visible_cols:
            visible_cols = list(df.columns)
    
        table_df = df[valid_cols].copy()
    
        # ==========================================
        # TABLE UI
        # ==========================================
        with self.plot_area:
    
            ui.label("Filtered DataFrame").classes(
                "text-h6"
            )
    
            ui.table(
                columns=[
                    {
                        "name": c,
                        "label": c,
                        "field": c
                    }
                    for c in table_df.columns
                ],
                rows=table_df.to_dict("records"),
                pagination=25,
            ).classes("w-full text-xs")

    # ---------------------------------------------------
    def calculate_expression(self):
        """Evaluates the custom formula on selected columns and writes results to the DataFrame."""
    
        if self.df is None:
            ui.notify("No data loaded")
            return
    
        expr = self.formula.value.strip()
    
        if not expr:
            ui.notify("Enter formula")
            return
    
        new_col = self.new_col.value.strip()
    
        if not new_col:
            ui.notify("Enter new column name")
            return
    
        try:
            filtered_df = self.get_filtered_df()
    
            if filtered_df.empty:
                ui.notify("No rows match current filters")
                return
    
            # ---------------------------------
            # SAFE FUNCTIONS
            # ---------------------------------
            safe = {
                "np": np,
                "pd": pd,
                "log": np.log,
                "sqrt": np.sqrt,
                "exp": np.exp,
                "abs": np.abs,
                "sin": np.sin,
                "cos": np.cos,
                "tan": np.tan,
                "mean": np.mean,
                "median": np.median,
                "std": np.std,
                "min": np.min,
                "max": np.max,
                "round": np.round,
                "where": np.where,
            }
    
            # ---------------------------------
            # ADD DATAFRAME COLUMNS
            # ---------------------------------
            for c in filtered_df.columns:

                col_data = filtered_df[c]
            
                try:
                    numeric_col = pd.to_numeric(
                        col_data,
                        errors="coerce"
                    )
            
                    # if enough numeric values keep numeric
                    if numeric_col.notna().sum() > 0:
                        safe[c] = numeric_col
                    else:
                        safe[c] = col_data
            
                except:
                    safe[c] = col_data
    
            # ---------------------------------
            # ADD USER ALIASES
            # ---------------------------------
            selected_vars = self.var_selector.value or []
    
            for col in selected_vars:

                if col in self.alias_inputs:
            
                    alias = self.alias_inputs[col].value.strip()
            
                    if alias:
            
                        col_data = filtered_df[col]
            
                        try:
                            numeric_col = pd.to_numeric(
                                col_data,
                                errors="coerce"
                            )
            
                            if numeric_col.notna().sum() > 0:
                                safe[alias] = numeric_col
                            else:
                                safe[alias] = col_data
            
                        except:
                            safe[alias] = col_data
    
            # ---------------------------------
            # EVALUATE EXPRESSION
            # ---------------------------------
            result = eval(
                expr,
                {"__builtins__": {}},
                safe
            )
    
            # ---------------------------------
            # ASSIGN RESULT TO FILTERED ROWS
            # ---------------------------------
            self.df.loc[
                filtered_df.index,
                new_col
            ] = result
    
            self.current_df = self.df
    
            # ---------------------------------
            # GLOBAL JSON SAFE STORAGE
            # ---------------------------------
            self.storage["df_json"] = self.df.to_dict(orient="records")
            self.storage["df_columns"] = list(self.df.columns)
            
            self.storage["parsed_df_json"] = self.storage["df_json"]
            self.storage["parsed_df_columns"] = self.storage["df_columns"]
            
            self.storage["loaded_df_json"] = self.storage["df_json"]
            self.storage["loaded_df_columns"] = self.storage["df_columns"]
            
            self.storage["data_json"] = self.storage["df_json"]
            self.storage["data_columns"] = self.storage["df_columns"]
    
            # ---------------------------------
            # UPDATE FILE CACHE
            # ---------------------------------
            current_file = self.file_selector.value

            if current_file:
            
                if "parsed_cache" not in self.storage:
                    self.storage["parsed_cache"] = {}
            
                self.storage["parsed_cache"][
                    current_file
                ] = self.df.to_dict(
                    orient="records"
                )
    
            # ---------------------------------
            # REFRESH UI
            # ---------------------------------
            self.update_ui()
    
            ui.notify(
                f"Column '{new_col}' created successfully",
                type="info"
            )
    
        except Exception as e:
    
            ui.notify(
                f"Calculation error: {str(e)}",
                type="negative"
            )