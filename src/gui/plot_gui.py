"""Plot GUI module.

Provides a user interface for creating visualizations (Line, Scatter, Bar, Histogram,
Boxplot, Violin) of loaded experimental datasets using Plotly.
"""

from nicegui import ui, app
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

import src.utils.theme as theme
from src.utils.logging_config import get_logger
import src.utils.tools as ut_tools

logger = get_logger("plot_gui")


class plotgui:
    """Manages the plot page interface and visualization options.

    Attributes:
        config_: Configuration dictionary.
        frame_name: Display name of the page frame.
        page_url_path: URL path for the page.
        storage: Data storage container dict.
        df: The currently loaded pandas DataFrame.
        current_df: Active DataFrame matching storage state.
    """

    def __init__(
        self,
        config,
        page_url_path="/plot",
        frame_name="Plot",
        add_page=False,
        storage_container=None,
        storage_container_=None,
        parent=None,
    ):
        """Initializes the plotgui.

        Args:
            config: Configuration dictionary.
            page_url_path: URL path for the page. Defaults to "/plot".
            frame_name: Display name of the page frame. Defaults to "Plot".
            add_page: Whether to register the page route. Defaults to False.
            storage_container: Primary data storage dictionary. Defaults to None.
            storage_container_: Alternate storage container dictionary. Defaults to None.
        """

        logger.info("initialising plotgui")

        if storage_container is None and storage_container_ is not None:
            storage_container = storage_container_

        if storage_container is None:
            storage_container = {}

        self.config_ = config
        self.frame_name = frame_name
        self.page_url_path = page_url_path
        self.storage = storage_container
        self.parent = parent

        self.df = None
        self.current_df = None
        self.filter_tiers = []

        if self.storage is None:
            self.storage = {}

        if not isinstance(self.storage, dict):
            self.storage = {}

        # ===============================
        # Load dataframe safely
        # ===============================
        try:

            if (
                "df_json" in self.storage
                and self.storage["df_json"]
            ):
        
                self.df = pd.DataFrame(
                    self.storage["df_json"]
                )
        
                if "df_columns" in self.storage:
                    self.df = self.df[
                        self.storage["df_columns"]
                    ]
        
        except Exception:
            self.df = None

        self.current_df = self.df

        if add_page:
            self.add_page()
            
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
    def add_page(self):
        """Adds this page as a distinct route in the application."""

        @ui.page(self.page_url_path)
        def page_():
        
            if "shared_data" not in  app.storage.general:
                app.storage.general["shared_data"] = {}
            
            self.storage = app.storage.general["shared_data"]
            with theme.frame(self.frame_name):
                self.content_()

    # ---------------------------------------------------
    def content_(self):
        """Renders the HTML/CSS contents of the plot page."""

        with ui.column().classes("w-full gap-4"):

            # ==========================================
            # PLOT SETTINGS CARD (STYLE & LAYOUT MATCHING LOAD PAGE)
            # ==========================================
            with ui.card().classes("w-full rounded-xl shadow-md p-6 gap-4"):

                ui.label("Plot Data Visualizations").classes("text-h6 font-bold")

                # Row 1: File selector & Add Filtering Tier button
                with ui.row().classes("w-full gap-4 items-center flex-wrap"):
                    self.file_selector = ui.select(
                        [],
                        label="Select Dataset",
                        with_input=True,
                        on_change=lambda e: self.load_selected_file(),
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

                # Row 2: Plot Parameters & Selection
                with ui.row().classes("w-full gap-4 items-center flex-wrap"):
                    self.x_selector = ui.select(
                        [],
                        label="X Variable",
                        value=None,
                        with_input=True,
                    ).props("clearable use-input").classes("w-64 min-w-[200px]")

                    self.y_selector = ui.select(
                        [],
                        label="Y Variables",
                        multiple=True,
                        with_input=True,
                    ).props("use-chips").classes("flex-1 min-w-[250px]")

                    self.plot_type = ui.select(
                        [
                            "Line",
                            "Scatter",
                            "Bar",
                            "Histogram",
                            "Boxplot",
                            "Violin",
                        ],
                        value="Line",
                        label="Plot Type",
                    ).classes("w-64 min-w-[200px]")

                # Row 3: Action Buttons
                with ui.row().classes("w-full gap-4 items-center mt-2 flex-wrap"):
                    ui.button(
                        "Plot",
                        on_click=self.plot
                    ).classes("w-40")

            # ============================================
            # PREVIEW CARD (STYLE MATCHING ACTIVE DATASET CARD IN LOAD PAGE)
            # ============================================
            with ui.card().classes("w-full rounded-xl shadow-md p-6 gap-4"):
                ui.label("Dataset Preview").classes("text-h6 font-bold")
                self.preview_box = ui.column().classes("w-full gap-4")

            # ==========================================
            # PLOT / VISUALIZATION AREA CARD
            # ==========================================
            with ui.card().classes("w-full rounded-xl shadow-md p-6 gap-4"):
                ui.label("Visualization").classes("text-h6 font-bold")
                self.plot_area = ui.column().classes("w-full")

        self.refresh_loaded_files()

    # ---------------------------------------------------
    def refresh_loaded_files(self):
        """Refreshes the file selection dropdown options from storage cache without auto-selecting."""

        files = self.get_available_files()
    
        self.file_selector.options = files
        self.file_selector.value = None
        self.file_selector.update()
        
        # Reset state explicitly on page visit
        self.df = None
        self.current_df = None
        self.filter_tiers = []
        if hasattr(self, "filter_tiers_container") and self.filter_tiers_container:
            self.filter_tiers_container.clear()
            
        self.x_selector.value = None
        self.x_selector.update()
        self.y_selector.value = []
        self.y_selector.update()
        
        if hasattr(self, "plot_area") and self.plot_area:
            self.plot_area.clear()
            
        self.show_filtered_table()

    # ---------------------------------------------------
    def load_selected_file(self):
        """Loads the currently selected file data from the cache into memory."""

        try:
    
            fname = self.file_selector.value
    
            if not fname:
                # Reset if no file is selected
                self.df = None
                self.current_df = None
                self.filter_tiers = []
                if hasattr(self, "filter_tiers_container") and self.filter_tiers_container:
                    self.filter_tiers_container.clear()
                self.x_selector.value = None
                self.x_selector.update()
                self.y_selector.value = []
                self.y_selector.update()
                if hasattr(self, "plot_area") and self.plot_area:
                    self.plot_area.clear()
                self.show_filtered_table()
                return
    
            # SAVE ACTIVE FILE
            self.storage["last_loaded_file"] = fname
    
            # LOAD FROM CACHE (NO PARSE)
            cached = self.storage.get("parsed_cache", {}).get(fname)
    
            if not cached:
                ui.notify("Dataset not found in cache")
                return
    
            cached_dtypes = self.storage.get("parsed_cache_dtypes", {}).get(fname, {})
            df = ut_tools.restore_dataframe(cached, cached_dtypes)
    
            self.df = df.copy()
            self.current_df = df.copy()
    
            self.df.columns = (
                self.df.columns.astype(str).str.strip()
            )
    
            # Reset dynamic filter tiers
            self.filter_tiers = []
            if hasattr(self, "filter_tiers_container") and self.filter_tiers_container:
                self.filter_tiers_container.clear()

            self.update_selectors()
            self.show_filtered_table()
    
            ui.notify(f"Loaded: {fname}")
    
        except Exception as e:
            ui.notify(f"Load error: {str(e)}")

    # ---------------------------------------------------
    def update_selectors(self):
        """Updates options for the dropdown selectors based on active dataframe columns."""

        if self.df is None:
            return

        cols = list(self.df.columns)

        self.x_selector.options = cols
        self.y_selector.options = cols

        self.x_selector.value = None
        self.y_selector.value = []

        self.x_selector.update()
        self.y_selector.update()

        # Update dynamic filter tiers select columns
        for tier in self.filter_tiers:
            tier["col_select"].options = cols
            tier["col_select"].update()

    # ---------------------------------------------------
    def get_filtered_df(self):
        """Applies dynamic filter tiers to the current DataFrame.

        Returns:
            A filtered copy of the pandas DataFrame.
        """
        if self.df is None:
            return pd.DataFrame()

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
        """Dynamically adds a new filter tier to the Plot page settings."""
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

    # ---------------------------------------------------
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
    def show_filtered_table(self):
        """Refreshes the dataset preview table."""
        if not self.preview_box:
            return

        self.preview_box.clear()

        with self.preview_box:
            if self.df is None:
                ui.label("No dataset available to preview.")
                return

            df = self.get_filtered_df()

            ui.label(
                f"{len(df)} rows | {len(df.columns)} columns"
            ).classes("text-xs font-semibold")

            with ui.column().style("width: 100%; overflow-x: auto;"):
                ui.table(
                    columns=[
                        {"name": c, "label": c, "field": c}
                        for c in df.columns
                    ],
                    rows=df.head(200).astype(str).to_dict("records"),
                    pagination=5,
                ).classes("w-full text-xs").style("min-width: max-content;")

    # ---------------------------------------------------
    def plot(self):
        """Generates the selected Plotly chart based on active configurations and filters."""

        if self.df is None:
            ui.notify("No data loaded")
            return
    
        x = self.x_selector.value
        y_cols = self.y_selector.value
        ptype = self.plot_type.value
    
        # -----------------------------------------
        # RULES
        # -----------------------------------------
        if x and not y_cols:
            ui.notify("Only X selected. No plot can be created.")
            return
    
        if x and y_cols:
            if ptype not in ["Line", "Scatter"]:
                ui.notify("With X and Y selected use Line or Scatter.")
                return
    
        if (not x) and y_cols:
            if ptype not in ["Bar", "Histogram", "Boxplot", "Violin"]:
                ui.notify("With only Y selected use Bar / Histogram / Boxplot / Violin.")
                return
    
        df = self.get_filtered_df()

        if df.empty:
            ui.notify("No rows match current filters")
            return

        # -----------------------------------------
        # WELL COLUMN
        # -----------------------------------------
        well_col = None
    
        for c in df.columns:
            if "well" in c.lower():
                well_col = c
                break
    
        # -----------------------------------------
        # GROUP COLUMN
        # -----------------------------------------
        group_col = well_col if well_col else None
    
        if not group_col:
            for c in df.columns:
                if "protocol" in c.lower() or "experiment" in c.lower():
                    group_col = c
                    break
    
        fig = go.Figure()
    
        # =====================================================
        # LINE / SCATTER
        # =====================================================
        if ptype in ["Line", "Scatter"]:
    
            for y in y_cols:
    
                if group_col:
    
                    for g, part in df.groupby(group_col):
    
                        fig.add_trace(go.Scatter(
                            x=part[x],
                            y=part[y],
                            mode="lines" if ptype == "Line" else "markers",
                            name=f"{y} | {g}"
                        ))
    
                else:
    
                    fig.add_trace(go.Scatter(
                        x=df[x],
                        y=df[y],
                        mode="lines" if ptype == "Line" else "markers",
                        name=y
                    ))
    
            fig.update_layout(
                xaxis_title=x,
                yaxis_title=", ".join(y_cols)
            )
    
        # =====================================================
        # BAR
        # =====================================================
        elif ptype == "Bar":

            y = y_cols[0]
        
            if group_col:
        
                stats = (
                    df.groupby(group_col)[y]
                    .agg(["mean", "std", "count"])
                    .reset_index()
                )
        
                stats["std"] = stats["std"].fillna(0)
        
                fig = go.Figure()
        
                fig.add_trace(
                    go.Bar(
                        x=stats[group_col],
                        y=stats["mean"],
                        error_y=dict(
                            type="data",
                            array=stats["std"],
                            visible=True
                        ),
                        text=stats["mean"].round(3),
                        textposition="outside",
                        name=y,
                    )
                )
        
                fig.update_layout(
                    xaxis_title=group_col,
                    yaxis_title=f"{y} (mean +/- std)",
                )
        
            else:
        
                mean_val = df[y].mean()
                std_val = df[y].std()
        
                fig = go.Figure()
        
                fig.add_trace(
                    go.Bar(
                        x=[y],
                        y=[mean_val],
                        error_y=dict(
                            type="data",
                            array=[0 if pd.isna(std_val) else std_val],
                            visible=True
                        ),
                        text=[round(mean_val, 3)],
                        textposition="outside",
                        name=y,
                    )
                )
        
                fig.update_layout(
                    xaxis_title="Variable",
                    yaxis_title=f"{y} (mean +/- std)",
                )
    
        # =====================================================
        # HISTOGRAM
        # =====================================================
        elif ptype == "Histogram":
    
            y = y_cols[0]
    
            fig = px.histogram(
                df,
                x=y,
                color=group_col if group_col else None,
                marginal="box",
                barmode="overlay",
                opacity=0.65,
            )
    
            fig.update_layout(
                xaxis_title=y,
                yaxis_title="Count"
            )
    
        # =====================================================
        # BOXPLOT
        # =====================================================
        elif ptype == "Boxplot":
    
            y = y_cols[0]
    
            if group_col:
                fig = px.box(
                    df,
                    x=group_col,
                    y=y,
                    color=group_col,
                    points="all",
                    notched=True
                )
    
                fig.update_layout(
                    xaxis_title=group_col,
                    yaxis_title=y
                )
                
                fig.update_traces(marker_size=4)
    
            else:
                fig = px.box(df, y=y)
    
                fig.update_layout(
                    xaxis_title="Distribution",
                    yaxis_title=y
                )
    
        # =====================================================
        # VIOLIN
        # =====================================================
        elif ptype == "Violin":
    
            y = y_cols[0]
    
            if group_col:
                fig = px.violin(
                    df,
                    x=group_col,
                    y=y,
                    color=group_col,
                    box=True,
                    points="all",
                )
    
                fig.update_layout(
                    xaxis_title=group_col,
                    yaxis_title=y
                )
    
            else:
                fig = px.violin(df, y=y)
    
                fig.update_layout(
                    xaxis_title="Distribution",
                    yaxis_title=y
                )
        
                
        # =====================================================
        # AUTO TITLE
        # =====================================================
        
        if ptype in ["Line", "Scatter"]:
        
            if x and y_cols:
                title_txt = f"{x} vs {' , '.join(y_cols)}"
            else:
                title_txt = f"{ptype} Plot"
        
        elif ptype in ["Histogram", "Boxplot", "Violin", "Bar"]:
        
            y = y_cols[0] if y_cols else ""
        
            if group_col:
                title_txt = f"{y} by {group_col}"
            else:
                title_txt = f"{ptype} of {y}"
        
        else:
            title_txt = f"{ptype} Plot"
        # =====================================================
        # FINAL LAYOUT
        # =====================================================
        fig.update_layout(
            height=760,
            title=title_txt,
            hovermode="x unified",
        )
    
        self.plot_area.clear()
    
        with self.plot_area:
            ui.plotly(fig).classes("w-full")