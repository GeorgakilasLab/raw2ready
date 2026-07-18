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
        parent=None,
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
        self.parent = parent

        self.df = None
        self.alias_inputs = {}
        self.filter_tiers = []
        self.calculated_columns = []

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
    def content_(self):
        """Renders the HTML/CSS contents of the calculation page."""

        self.load_from_storage()

        with ui.column().classes("w-full gap-4"):

            # ============================================
            # CALCULATION SETTINGS CARD (STYLE & LAYOUT MATCHING LOAD PAGE)
            # ============================================
            with ui.card().classes("w-full rounded-xl shadow-md p-6 gap-4"):

                ui.label("Calculate").classes("text-h6 font-bold")

                # Row 1: File selection & Add Filtering Tier button
                with ui.row().classes("w-full gap-4 items-center flex-wrap"):
                    self.file_selector = ui.select(
                        [],
                        label="Loaded Files",
                        with_input=True,
                        on_change=self.load_selected_file,
                    ).classes("w-80 min-w-[250px]")

                    with ui.row().classes("items-center gap-2 mt-4"):
                        ui.button(
                            icon="add",
                            on_click=self.add_filter_tier
                        ).props("round color=primary dense").tooltip("Add filtering tier")
                        ui.label("Add a Filtering Tier").classes("text-sm font-bold text-slate-700")

                # Dynamic filter tiers container
                self.filter_tiers_container = ui.column().classes("w-full gap-4")

                ui.separator()

                # Row 2: Variable selection & aliases
                with ui.row().classes("w-full gap-4 flex-wrap items-start"):
                    self.var_selector = ui.select(
                        [],
                        label="Variables X & Y",
                        multiple=True,
                        with_input=True,
                        on_change=lambda e: self.update_ui(),
                    ).props("use-chips").classes("flex-1 min-w-[250px]")

                    with ui.column().classes("w-80 min-w-[250px] gap-1"):
                        ui.label("Aliases").classes("text-sm font-semibold text-slate-700")
                        self.alias_box = ui.column().classes(
                            "w-full gap-2 bg-slate-50 p-2 rounded border border-slate-200"
                        )

                ui.separator()

                # Row 3: Formula & new column configuration
                with ui.row().classes("w-full gap-4 items-center flex-wrap"):
                    self.new_col = ui.input(
                        label="New Column Name",
                        placeholder="example: growth_rate"
                    ).classes("w-64 min-w-[200px]")

                    self.formula = ui.input(
                        label="Formula",
                        placeholder="example: A / B"
                    ).classes("flex-1 min-w-[250px]")

                    with ui.column().classes("min-w-[250px] gap-0.5 text-xs text-slate-500"):
                        ui.label("Examples:")
                        ui.label("A / B | log(A) | sqrt(B) | A.diff() | A.rolling(5).mean()")

                # Row 4: Action buttons
                with ui.row().classes("w-full gap-4 items-center mt-2 flex-wrap"):
                    ui.button(
                        "CALCULATE",
                        on_click=self.calculate_expression
                    ).classes("w-40")

                    self.info_label = ui.label("").classes("text-slate-600 text-sm")

            # ============================================
            # PREVIEW CARD (STYLE MATCHING ACTIVE DATASET CARD IN LOAD PAGE)
            # ============================================
            with ui.card().classes("w-full rounded-xl shadow-md p-6 gap-4"):

                ui.label("Dataset Preview").classes("text-h6 font-bold")

                self.preview_box = ui.column().classes(
                    "w-full h-[600px] overflow-y-auto overflow-x-auto p-2"
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
                ui.label("No dataset available to preview.")
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
    
        # Variables selector
        if hasattr(self, "var_selector"):
            self.var_selector.options = cols
            self.var_selector.update()

        # Update dynamic filter tiers select columns
        for tier in self.filter_tiers:
            tier["col_select"].options = cols
            tier["col_select"].update()



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
    
            # Reset dynamic filter tiers
            self.filter_tiers = []
            if hasattr(self, "filter_tiers_container") and self.filter_tiers_container:
                self.filter_tiers_container.clear()

            # ================================
            # UPDATE UI
            # ================================
            self.update_selectors()
            self.update_ui()
    
            ui.notify(f"{filename} loaded from cache")
    
        except Exception as e:
            ui.notify(f"Load error: {str(e)}")

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
        self.var_selector.update()

        # Update dynamic filter tiers select columns
        for tier in self.filter_tiers:
            tier["col_select"].options = cols
            tier["col_select"].update()

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
        """Applies dynamic filter tiers and well filters to the current DataFrame.

        Returns:
            A filtered copy of the pandas DataFrame.
        """

        df = self.df.copy()

        # Apply each dynamic tier filter
        for tier in self.filter_tiers:
            col = tier["col_select"].value
            vals = tier["val_select"].value
            if col and vals and col in df.columns:
                df = df[
                    df[col]
                    .astype(str)
                    .isin(vals)
                ]

        return df

    # ---------------------------------------------------
    def add_filter_tier(self):
        """Dynamically adds a new filter tier to the Calculate page settings."""
        if not hasattr(self, "filter_tiers_container") or not self.filter_tiers_container:
            return

        tier_idx = len(self.filter_tiers) + 1
        cols = list(self.df.columns) if self.df is not None else []

        with self.filter_tiers_container:
            with ui.column().classes("w-full gap-1 border-t border-slate-100 pt-2") as tier_col:
                with ui.row().classes("w-full justify-between items-center"):
                    label_el = ui.label(f"Tier {tier_idx} Filtering").classes("text-xs font-bold text-slate-500 uppercase tracking-wider")
                    
                    def remove_this(t_col=tier_col, idx=tier_idx):
                        for t in list(self.filter_tiers):
                            if t["index"] == idx:
                                self.filter_tiers.remove(t)
                                break
                        for i, t in enumerate(self.filter_tiers):
                            new_idx = i + 1
                            t["index"] = new_idx
                            t["label"].text = f"Tier {new_idx} Filtering"
                        t_col.delete()
                        self.show_filtered_table()

                    ui.button(
                        icon="delete",
                        on_click=remove_this
                    ).props("flat round dense color=negative").tooltip("Remove this tier")

                with ui.row().classes("w-full gap-4 items-center"):
                    col_select = ui.select(
                        cols,
                        label="Select Column",
                        with_input=True
                    ).classes("flex-1")

                    val_select = ui.select(
                        [],
                        label="Select Value",
                        multiple=True,
                        with_input=True
                    ).props("use-chips").classes("flex-1")

                tier_data = {
                    "index": tier_idx,
                    "label": label_el,
                    "col_select": col_select,
                    "val_select": val_select,
                    "container": tier_col
                }
                self.filter_tiers.append(tier_data)

                col_select.on_value_change(lambda e, vs=val_select, cs=col_select: self.update_tier_values(cs, vs))
                val_select.on_value_change(lambda e: self.show_filtered_table())

    def update_tier_values(self, col_select, val_select):
        """Updates the value dropdown options for a specific dynamic filter tier."""
        if self.df is None:
            return
        col = col_select.value
        if not col or col not in self.df.columns:
            val_select.options = []
            val_select.value = []
            val_select.update()
            return

        vals = sorted(
            self.df[col]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )
        val_select.options = vals
        val_select.value = []
        val_select.update()

        self.show_filtered_table()

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

        # add calculated columns
        for c in getattr(self, "calculated_columns", []):
            if c in df.columns and c not in visible_cols:
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
    
            with ui.column().style("width: 100%; overflow-x: auto;"):
                ui.table(
                    columns=[
                        {"name": c, "label": c, "field": c}
                        for c in table_df.columns
                    ],
                    rows=table_df.astype(str).to_dict("records"),
                    pagination=10,
                ).classes("w-full").style("min-width: max-content;")

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

            if new_col not in self.calculated_columns:
                self.calculated_columns.append(new_col)
    
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
            if self.parent and hasattr(self.parent, "refresh_all_pages"):
                self.parent.refresh_all_pages()
    
        except Exception as e:
    
            ui.notify(
                f"Calculation error: {str(e)}",
                type="negative"
            )