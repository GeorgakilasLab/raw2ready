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

        with ui.row().classes("w-full no-wrap"):

            # ==========================================
            # LEFT PANEL
            # ==========================================
            with ui.column().classes("w-[370px] p-4 gap-3 bg-slate-100"):

                ui.label("Plot Data").classes("text-h5")

                ui.label("Select Data File").classes("text-h6")

                with ui.row().classes("w-full items-center gap-2"):

                    self.file_selector = ui.select(
                        [],
                        label="Loaded Files",
                        with_input=True,
                        on_change=lambda e: self.load_selected_file(),
                    ).classes("flex-1")

                    ui.button(
                        "Refresh",
                        on_click=self.refresh_loaded_files
                    ).classes("w-24")

                self.preview_box = ui.column().classes(
                    "w-full h-[180px] overflow-auto bg-white p-2 rounded shadow"
                )

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
                ).props("use-chips").classes("w-full")

                self.well_selector = ui.select(
                    [],
                    label="Wells",
                    multiple=True,
                    with_input=True,
                ).props("use-chips").classes("w-full")

                self.x_selector = ui.select(
                    [],
                    label="X Variable",
                    value=None,
                    with_input=True,
                ).props("clearable use-input").classes("w-full")

                self.y_selector = ui.select(
                    [],
                    label="Y Variables",
                    multiple=True,
                    with_input=True,
                ).props("use-chips").classes("w-full")

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
                ).classes("w-full")

                ui.button(
                    "Plot",
                    on_click=self.plot
                ).classes("w-full")

                ui.button(
                    "Clear",
                    on_click=lambda: self.plot_area.clear()
                ).classes("w-full")

            # ==========================================
            # RIGHT PANEL
            # ==========================================
            with ui.column().classes("flex-1 p-4"):
                self.plot_area = ui.column().classes("w-full")

        self.refresh_loaded_files()

    # ---------------------------------------------------
    def refresh_loaded_files(self):
        """Refreshes the file selection dropdown options from storage cache."""

        files = self.get_available_files()
    
        self.file_selector.options = files
        self.file_selector.update()
    
        if not files:
            ui.notify("No parsed datasets available")
            return
    
        last = self.storage.get("last_loaded_file")
    
        if last in files:
            self.file_selector.value = last
        else:
            self.file_selector.value = files[0]
    
        self.file_selector.update()
    
        # AUTO LOAD
        self.load_selected_file()

    # ---------------------------------------------------
    def load_selected_file(self):
        """Loads the currently selected file data from the cache into memory."""

        try:
    
            fname = self.file_selector.value
    
            if not fname:
                return
    
            # SAVE ACTIVE FILE
            self.storage["last_loaded_file"] = fname
    
            # LOAD FROM CACHE (NO PARSE)
            cached = self.storage.get("parsed_cache", {}).get(fname)
    
            if not cached:
                ui.notify("Dataset not found in cache")
                return
    
            df = pd.DataFrame(cached)
    
            self.df = df.copy()
            self.current_df = df.copy()
    
            self.df.columns = (
                self.df.columns.astype(str).str.strip()
            )
    
            self.update_selectors()
    
            # ----------------------------
            # PREVIEW TABLE
            # ----------------------------
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
    
            ui.notify(f"Loaded: {fname}")
    
        except Exception as e:
            ui.notify(f"Load error: {str(e)}")

    # ---------------------------------------------------
    def update_selectors(self):
        """Updates options for x, y, wells, and experiment dropdowns based on loaded DataFrame columns."""

        if self.df is None:
            return

        cols = list(self.df.columns)

        self.exp_col.options = cols
        self.x_selector.options = cols
        self.y_selector.options = cols

        self.exp_col.update()
        self.x_selector.update()
        self.y_selector.update()

        # auto time column
        for c in cols:
            if "time" in c.lower():
                self.x_selector.value = c
                self.x_selector.update()
                break

        # wells
        well_col = None
        for c in cols:
            if "well" in c.lower():
                well_col = c
                break

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

        # numeric Y
        numeric = self.df.select_dtypes(include=np.number).columns.tolist()
        numeric = [c for c in numeric if "time" not in c.lower()]

        if numeric:
            self.y_selector.value = [numeric[0]]
            self.y_selector.update()

        # experiment column
        for c in cols:
            if "protocol" in c.lower() or "experiment" in c.lower():
                self.exp_col.value = c
                self.exp_col.update()
                self.update_experiment_values()
                break

    # ---------------------------------------------------
    def update_experiment_values(self):
        """Updates available values for the experiment column filter based on selection."""

        if self.df is None:
            return

        col = self.exp_col.value

        if not col:
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
    
        df = self.df.copy()
        
        for c in df.columns:
            try:
                df[c] = pd.to_numeric(df[c])
            except:
                pass
    
        # -----------------------------------------
        # FILTER EXPERIMENTS
        # -----------------------------------------
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
    
        # -----------------------------------------
        # WELL COLUMN
        # -----------------------------------------
        well_col = None
    
        for c in df.columns:
            if "well" in c.lower():
                well_col = c
                break
    
        if self.well_selector.value and well_col:
            df = df[
                df[well_col]
                .astype(str)
                .isin(self.well_selector.value)
            ]
    
        # -----------------------------------------
        # GROUP COLUMN
        # -----------------------------------------
        group_col = well_col if well_col else None
    
        if not group_col and self.exp_col.value in df.columns:
            group_col = self.exp_col.value
    
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