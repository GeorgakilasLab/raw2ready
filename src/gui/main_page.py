"""Main Dashboard GUI module.

Provides a unified portal showing parsed data files summary stats, key performance
indicators, smart anomaly warnings/recommendations, SQL query console, and a
CoPilot chatbot assistant.
"""

from nicegui import ui, app

import pandas as pd
import numpy as np
import src.utils.theme as theme
from src.utils.logging_config import get_logger



import src.gui.load_gui as load_gui
import src.gui.merge_gui as merge_gui
import src.gui.calculate_gui as calculate_gui
import src.gui.plot_gui as plot_gui
import src.gui.metadata_gui as metadata_gui
import src.gui.help_gui as help_gui
import src.gui.llm_gui as llm_gui
import pandas as pd


# --------------------------------------------------
# LOGGER
# --------------------------------------------------
logger = get_logger("main_page")


# --------------------------------------------------
# CLASS
# --------------------------------------------------
class main_page:
    """Manages the main portal layout, dashboard statistics, and integrated sub-tools.

    Attributes:
        config_: Application configuration dict.
        page_url_path: URL route path for the home/dashboard page.
        frame_name: Title of the application layout frame.
        dirs: Dict of directories configured for system paths.
        storage_container: Reference to general shared data dictionary in app storage.
        storage: Data storage container dict.
        main_tabs: NiceGUI tabs component.
        main_panels: NiceGUI tab panels component.
        lbl_files: NiceGUI label showing loaded files count.
        lbl_rows: NiceGUI label showing loaded rows count.
        lbl_cols: NiceGUI label showing loaded columns count.
        lbl_last: NiceGUI label showing the name of the last loaded file.
        preview_container: NiceGUI column containing the active dataset table.
        ai_result_container: NiceGUI column containing AI anomaly detection or summary outputs.
        chat_messages_container: NiceGUI column containing the CoPilot chat history bubbles.
        chat_input: NiceGUI input text field for the copilot chat.
        chat_history: List of tuples representing the chat history (role, message).
        sql_input: NiceGUI textarea for entering SQL query.
        sql_results_container: NiceGUI column containing SQL console output table or errors.
        sql_mode: Selected console query execution mode ('sql' or 'ai').
    """

    def __init__(
        self,
        config: dict,
        page_url_path="/",
        frame_name="raw2ready",
        add_page=False,
        storage_container=None,
        dirs=None,
    ):
        """Initializes main_page.

        Args:
            config: Config dictionary containing environment/analytical parameters.
            page_url_path: Route URL path. Defaults to "/".
            frame_name: Title of UI layout frame. Defaults to "raw2ready".
            add_page: Whether to automatically register the route page. Defaults to False.
            storage_container: Optional storage dictionary container.
            dirs: Optional dictionary containing upload/output paths.
        """

        logger.info("initialising main_page")

        self.config_ = config
        self.page_url_path = page_url_path
        self.frame_name = frame_name
        self.dirs = dirs or {}

        self.storage_container = {}
        self.storage = storage_container or {}

        self.main_tabs = None
        self.main_panels = None
        self.current_tab = "dashboard"

        self.lbl_files = None
        self.lbl_rows = None
        self.lbl_cols = None
        self.lbl_last = None

        self.load_page = None
        self.merge_page = None
        self.calculate_page = None
        self.plot_page = None
        self.metadata_page = None
        self.llm_page = None



        self.files_table = None

        self.sql_input = None
        self.sql_results_container = None
        self.sql_mode = "sql"

        if add_page:
            self.add_page()

    # --------------------------------------------------
    # AUTH
    # --------------------------------------------------
    #def require_login(self):

    #    if not auth.is_logged_in():
    #        ui.navigate.to("/login")
    #        return False

    #    return True

    #def current_role(self):
    #    return auth.current_user().get(
    #        "role",
    #        "viewer",
    #    )

    #def current_user(self):
    #    return auth.current_user().get(
    #        "username",
    #        "guest",
    #    )

    #def is_admin(self):
    #    return self.current_role() in [
    #        "admin",
    #        "superadmin",
    #    ]

    # --------------------------------------------------
    # PAGE
    # --------------------------------------------------
    def add_page(self, page_url=None, frame_name=None):
        """Adds this page as a distinct route in the application.

        Args:
            page_url: Optional route path. Defaults to self.page_url_path.
            frame_name: Optional frame title. Defaults to self.frame_name.
        """

        if page_url is None:
            page_url = self.page_url_path

        if frame_name is None:
            frame_name = self.frame_name

        @ui.page(page_url)
        async def page_():

            logger.info("opening main page")

            if not self.require_login():
                return

            if "shared_data" not in app.storage.general:
                app.storage.general["shared_data"] = {}

            self.storage_container = app.storage.general["shared_data"]

            with theme.frame(frame_name):
                self.content_()

    async def add_page_runtime(self):

     #   if not self.require_login():
     #       return

        if "shared_data" not in app.storage.general:
            app.storage.general["shared_data"] = {}

        self.storage_container = app.storage.general["shared_data"]

        with theme.frame(self.frame_name):
            self.content_()

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------
    def go_tab(self, tab_name):

        try:
            if self.main_tabs:
                self.main_tabs.value = tab_name
                self.main_tabs.update()

            if self.main_panels:
                self.main_panels.value = tab_name
                self.main_panels.update()

        except Exception as e:
            logger.warning(f"tab switch error: {e}")

    def get_stats(self):

        files_count = 0
        rows_count = 0
        cols_count = 0
        last_file = "-"

        try:
            files_obj = self.storage_container.get(
                "files",
                {},
            )

            if isinstance(files_obj, dict):
                files_count = len(files_obj)

                if files_count > 0:
                    last_file = list(
                        files_obj.keys()
                    )[-1]

            # Sum rows and columns from all loaded datasets
            parsed_cache = self.storage_container.get("parsed_cache", {})
            for records in parsed_cache.values():
                num_rows = len(records)
                rows_count += num_rows
                if num_rows > 0:
                    cols_count += len(records[0])

        except Exception as e:
            logger.warning(f"stats error: {e}")

        return (
            files_count,
            rows_count,
            cols_count,
            last_file,
        )

    def refresh_dashboard(self):

        (
            files_count,
            rows_count,
            cols_count,
            last_file,
        ) = self.get_stats()

        try:
            if self.lbl_files:
                self.lbl_files.text = str(files_count)

            if self.lbl_rows:
                self.lbl_rows.text = str(rows_count)

            if self.lbl_cols:
                self.lbl_cols.text = str(cols_count)

            if self.lbl_last:
                self.lbl_last.text = last_file

            if self.files_table:
                self.files_table.rows = self.get_files_matrix()
                self.files_table.update()

            ui.notify(
                "Dashboard refreshed",
                type="info",
            )

        except Exception as e:
            logger.warning(f"refresh error: {e}")

    def refresh_all_pages(self):
        """Refreshes all page components, lists, and selectors when data is modified."""
        logger.info("Triggering refresh of all pages...")
        
        # 1. Refresh dashboard stats and matrix
        try:
            self.refresh_dashboard()
        except Exception as e:
            logger.warning(f"Dashboard refresh error: {e}")
            
        # 2. Refresh Load page files list and status
        if hasattr(self, "load_page") and self.load_page:
            try:
                self.load_page.show_uploaded_files()
                self.load_page.refresh_status()
            except Exception as e:
                logger.warning(f"Load page refresh error: {e}")
                
        # 3. Refresh Merge page dropdowns
        if hasattr(self, "merge_page") and self.merge_page:
            try:
                self.merge_page.refresh_loaded_files()
            except Exception as e:
                logger.warning(f"Merge page refresh error: {e}")
                
        # 4. Refresh Calculate page dropdowns
        if hasattr(self, "calculate_page") and self.calculate_page:
            try:
                self.calculate_page.refresh_files()
            except Exception as e:
                logger.warning(f"Calculate page refresh error: {e}")
                
        # 5. Refresh Plot page dropdowns
        if hasattr(self, "plot_page") and self.plot_page:
            try:
                self.plot_page.refresh_loaded_files()
            except Exception as e:
                logger.warning(f"Plot page refresh error: {e}")
                
        # 6. Refresh Metadata page dropdowns
        if hasattr(self, "metadata_page") and self.metadata_page:
            try:
                self.metadata_page.refresh_json_dropdown()
            except Exception as e:
                logger.warning(f"Metadata page refresh error: {e}")
                
        # 7. Refresh LLM page dropdowns
        if hasattr(self, "llm_page") and self.llm_page:
            try:
                self.llm_page.refresh_loaded_files()
            except Exception as e:
                logger.warning(f"LLM page refresh error: {e}")

    # --------------------------------------------------
    # KPI CARD
    # --------------------------------------------------
    def stat_card(
        self,
        title,
        value,
        icon,
        color,
        ref_name=None,
    ):

        with ui.card().classes(
            "flex-1 min-w-[200px] rounded-2xl shadow-xl "
            "border border-slate-200 bg-white"
        ):

            with ui.row().classes(
                "w-full items-center justify-between"
            ):

                ui.label(title).classes(
                    "text-sm text-slate-500"
                )

                ui.icon(icon).classes(
                    f"text-2xl {color}"
                )

            label = ui.label(str(value)).classes(
                "text-4xl font-bold mt-3"
            )

            if ref_name == "files":
                self.lbl_files = label
            elif ref_name == "rows":
                self.lbl_rows = label
            elif ref_name == "cols":
                self.lbl_cols = label

    def get_files_matrix(self):

        files_obj = self.storage_container.get("files", {})
        parsed_cache = self.storage_container.get("parsed_cache", {})

        rows_data = []

        for filename in files_obj.keys():

            records = parsed_cache.get(filename, [])
            num_rows = len(records)

            if num_rows > 0:

                num_cols = len(records[0])

                try:
                    df = pd.DataFrame(records)
                    memory_bytes = df.memory_usage(deep=True).sum()
                    memory_mb = round(memory_bytes / (1024 * 1024), 2)

                except Exception:
                    memory_mb = 0.0

            else:

                num_cols = 0
                memory_mb = 0.0

            rows_data.append(
                {
                    "filename": filename,
                    "rows": num_rows,
                    "cols": num_cols,
                    "memory": memory_mb,
                }
            )

        return rows_data



    # --------------------------------------------------
    # SQL CONSOLE
    # --------------------------------------------------
    def run_sql_console(self):

        if self.sql_input is None:
            return
    
        prompt = self.sql_input.value.strip()
    
        if prompt == "":
            ui.notify(
                "Enter query",
                type="warning",
            )
            return
    
        # ------------------------
        # RAW SQL MODE
        # ------------------------
        if self.sql_mode == "sql":
    
            result = db.run_sql(prompt)
            self.render_sql_result(result)
            return
    
        # ------------------------
        # AI MODE
        # ------------------------
        ai_result = ai_sql.ask(prompt)
    
        if not ai_result["success"]:
    
            self.sql_results_container.clear()
    
            with self.sql_results_container:
                with ui.card().classes(
                    "w-full rounded-2xl shadow-lg bg-white"
                ):
                    ui.label(
                        ai_result["message"]
                    ).classes("text-red-600")
    
            return
    
        self.sql_results_container.clear()
    
        with self.sql_results_container:
    
            with ui.card().classes(
                "w-full rounded-2xl shadow-lg bg-white mb-4"
            ):
    
                ui.label(
                    "Generated SQL"
                ).classes(
                    "text-sm text-slate-500"
                )
    
                ui.code(
                    ai_result["sql"]
                ).classes("w-full")
    
        self.render_sql_result(
            ai_result["result"]
        )
    
    
    def render_sql_result(self, result):

        self.sql_results_container.clear()
    
        with self.sql_results_container:
    
            with ui.card().classes(
                "w-full rounded-2xl shadow-lg bg-white"
            ):
    
                if not result["success"]:
                    ui.label(
                        result["error"]
                    ).classes("text-red-600")
                    return
    
                ui.label(
                    f"Affected Rows: {result['rowcount']}"
                ).classes(
                    "text-sm text-slate-500 mb-3"
                )
    
                if result["rows"]:
    
                    cols = []
    
                    for c in result["columns"]:
                        cols.append(
                            {
                                "name": c,
                                "label": c,
                                "field": c,
                                "align": "left",
                            }
                        )
    
                    ui.table(
                        rows=result["rows"],
                        columns=cols,
                        pagination=20,
                    ).classes("w-full")
    
                else:
                    ui.label(
                        "Query executed successfully."
                    )
                
    def sql_console(self):

        with ui.column().classes(
            "w-full gap-6"
        ):
    
            with ui.card().classes(
                "w-full rounded-2xl shadow-lg bg-white"
            ):
    
                ui.label(
                    "AI SQL Console"
                ).classes(
                    "text-2xl font-bold mb-4"
                )
    
                # FIXED: bind only (NO .on event crash)
                ui.toggle(
                    {
                        "sql": "RAW SQL",
                        "ai": "AI MODE",
                    },
                    value="sql",
                ).bind_value(
                    self,
                    "sql_mode",
                ).classes("mb-4")
    
                self.sql_input = ui.textarea(
                    label="Query",
                    value="SELECT * FROM datasets LIMIT 20;",
                ).classes(
                    "w-full mt-2"
                ).props(
                    "autogrow outlined"
                )
    
                with ui.row().classes(
                    "gap-3 mt-4 flex-wrap"
                ):
    
                    ui.button(
                        "Run",
                        icon="play_arrow",
                        on_click=self.run_sql_console,
                    )
    
                    ui.button(
                        "Show Tables",
                        icon="table_chart",
                        on_click=lambda:
                        self.sql_input.set_value(
                            "show tables"
                            if self.sql_mode == "ai"
                            else
                            "SELECT tablename FROM pg_tables WHERE schemaname='public';"
                        ),
                    )
    
                    ui.button(
                        "Admins",
                        icon="admin_panel_settings",
                        on_click=lambda:
                        self.sql_input.set_value(
                            "who are all admins"
                            if self.sql_mode == "ai"
                            else
                            "SELECT * FROM users WHERE role='admin';"
                        ),
                    )
    
                    ui.button(
                        "Logs",
                        icon="history",
                        on_click=lambda:
                        self.sql_input.set_value(
                            "show latest logs"
                            if self.sql_mode == "ai"
                            else
                            "SELECT * FROM system_logs ORDER BY id DESC LIMIT 100;"
                        ),
                    )
    
                    ui.button(
                        "Datasets",
                        icon="dataset",
                        on_click=lambda:
                        self.sql_input.set_value(
                            "show latest datasets"
                            if self.sql_mode == "ai"
                            else
                            "SELECT * FROM datasets ORDER BY id DESC LIMIT 50;"
                        ),
                    )
    
            self.sql_results_container = ui.column().classes(
                "w-full"
            )

    # --------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------
    def dashboard(self):

        (
            files_count,
            rows_count,
            cols_count,
            last_file,
        ) = self.get_stats()

        with ui.column().classes(
            "w-full gap-6"
        ):

            with ui.card().classes(
                "w-full rounded-3xl shadow-2xl "
                "bg-gradient-to-r from-[#64748B] via-[#63B3ED] to-[#4FD1C5] text-white"
            ):

                with ui.row().classes(
                    "w-full items-center justify-between"
                ):

                    with ui.column():

                        ui.label(
                            "raw2ready"
                        ).classes(
                            "text-4xl font-bold"
                        )

                        ui.label(
                            "Bioprocess Data Curation Platform with AI-Assisted Exploration"
                        ).classes(
                            "text-lg opacity-90"
                        )

                    ui.image(
                        "/assets/images/raw2ready.svg"
                    ).classes(
                        "w-72 h-16 rounded-2xl bg-white p-2"
                    ).props("fit=contain")

            with ui.row().classes(
                "w-full gap-4 flex-wrap items-stretch"
            ):

                self.stat_card(
                    "Loaded Files",
                    files_count,
                    "folder",
                    "text-blue-600",
                    "files",
                )

                self.stat_card(
                    "Rows",
                    rows_count,
                    "table_rows",
                    "text-green-600",
                    "rows",
                )

                self.stat_card(
                    "Columns",
                    cols_count,
                    "view_column",
                    "text-purple-600",
                    "cols",
                )

                with ui.card().classes(
                    "flex-1 min-w-[200px] rounded-2xl shadow-xl "
                    "border border-slate-200 bg-white"
                ):

                    with ui.row().classes(
                        "w-full items-center justify-between"
                    ):
                        ui.label(
                            "Last Loaded File"
                        ).classes(
                            "text-sm text-slate-500"
                        )
                        ui.icon("event_note").classes(
                            "text-2xl text-orange-600"
                        )

                    self.lbl_last = ui.label(
                        last_file
                    ).classes(
                        "text-lg font-bold mt-3 break-all"
                    )

            with ui.card().classes(
                "w-full rounded-2xl shadow-lg border border-slate-200 bg-white p-6"
            ):

                ui.label(
                    "Loaded Datasets"
                ).classes("text-h6 font-bold")

                columns = [
                    {
                        "name": "filename",
                        "label": "File Name",
                        "field": "filename",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "rows",
                        "label": "Number of Rows",
                        "field": "rows",
                        "sortable": False,
                        "align": "right",
                    },
                    {
                        "name": "cols",
                        "label": "Number of Columns",
                        "field": "cols",
                        "sortable": False,
                        "align": "right",
                    },
                    {
                        "name": "memory",
                        "label": "Memory Footprint (MBs)",
                        "field": "memory",
                        "sortable": True,
                        "align": "right",
                    },
                ]

                self.files_table = ui.table(
                    columns=columns,
                    rows=self.get_files_matrix(),
                    row_key="filename",
                ).classes("w-full")



    # --------------------------------------------------
    # CONTENT
    # --------------------------------------------------
    def content_(self):
        """Renders the HTML/CSS contents of the main dashboard page, tab bar, and inner panels."""

        ui.add_head_html("""
        <link rel="icon" type="image/svg+xml" href="/assets/images/raw2ready_favicon.svg?v=3">
        <style>
        body{
            background:#f8fafc;
            font-family:Inter,Arial,sans-serif;
        }
        .nicegui-content{
            padding:0 !important;
        }
        .q-tab{
            border-radius:14px;
            margin-bottom:6px;
            min-height:58px;
            justify-content:flex-start !important;
            padding-left:14px;
        }
        .q-tab__icon{
            font-size:22px !important;
            margin-right:10px !important;
        }
        .q-tab__label{
            font-size:15px;
            font-weight:600;
        }
        .q-tab--active{
            background:rgba(255,255,255,0.12);
        }
        .q-uploader__list {
            display: none !important;
        }
        </style>
        """)

        with ui.row().classes(
            "w-full h-screen no-wrap"
        ):

            # SIDEBAR
            with ui.column().classes(
                "w-72 h-full bg-[#2e2e2e] text-white p-4"
            ):

                with ui.row().classes(
                    "items-center gap-3 mb-4 w-full justify-center"
                ):

                    ui.image(
                        "/assets/images/raw2ready.svg"
                    ).classes(
                        "w-full h-14"
                    ).props("fit=contain")

                ui.separator()

                with ui.scroll_area().classes(
                    "w-full flex-1"
                ):

                    with ui.tabs().props(
                        "vertical inline-label"
                    ).classes(
                        "w-full text-white"
                    ) as tabs:

                        self.main_tabs = tabs

                        items = [
                            ("dashboard", "dashboard"),
                            ("load", "upload_file"),
                            ("merge", "merge"),
                            ("calculate", "calculate"),
                            ("plot", "bar_chart"),
                            ("metadata", "menu_book"),
                            ("llm", "smart_toy"),
                        ]

                      #  if self.is_admin():
                      #      items.append(
                      #          ("sql_console", "terminal")
                      #      )

                        items.append(
                            ("help", "help")
                        )

                        for name, icon in items:

                            ui.tab(
                                name=name,
                                label=name.replace(
                                    "_",
                                    " ",
                                ).title(),
                                icon=icon,
                            )

                ui.separator().classes("my-2")

                with ui.row().classes(
                    "w-full bg-white p-2 rounded-xl mt-2 justify-center items-center"
                ):
                    ui.image(
                        f"/{theme.themes_['funding_logo']}"
                    ).classes(
                        "w-full h-10"
                    ).props("fit=contain")

                ui.label(
                    "Version 1.0"
                ).classes(
                    "text-xs text-slate-400 mt-1 text-center w-full"
                )

            # MAIN AREA
            with ui.column().classes(
                "flex-1 h-full overflow-auto p-6"
            ):

                with ui.tab_panels(
                    tabs,
                    value="dashboard",
                ).classes(
                    "w-full bg-transparent"
                ) as panels:

                    self.main_panels = panels

                    def on_tab_change(e):
                        prev = self.current_tab
                        self.current_tab = e.value
                        if prev == "merge" and hasattr(self, "merge_page") and self.merge_page:
                            try:
                                self.merge_page.reset()
                            except Exception as ex:
                                logger.warning(f"Error resetting merge page: {ex}")

                    panels.on_value_change(on_tab_change)

                    with ui.tab_panel("dashboard"):
                        self.dashboard()

                    with ui.tab_panel("load"):
                        self.load_page = load_gui.loadgui(
                            config=self.config_,
                            storage_container=self.storage_container,
                            dirs=self.dirs,
                            parent=self
                        )
                        self.load_page.content_()

                    with ui.tab_panel("merge"):
                        self.merge_page = merge_gui.mergegui(
                            config=self.config_,
                            storage_container=self.storage_container,
                            parent=self
                        )
                        self.merge_page.content_()

                    with ui.tab_panel("calculate"):
                        self.calculate_page = calculate_gui.calculategui(
                            config=self.config_,
                            storage_container=self.storage_container,
                            parent=self
                        )
                        self.calculate_page.content_()

                    with ui.tab_panel("plot"):
                        self.plot_page = plot_gui.plotgui(
                            config=self.config_,
                            storage_container=self.storage_container,
                            parent=self
                        )
                        self.plot_page.content_()

                    with ui.tab_panel("metadata"):
                        self.metadata_page = metadata_gui.NewProtocol(
                            storage_container=self.storage_container,
                            parent=self
                        )
                        self.metadata_page.content_()

                    with ui.tab_panel("llm"):
                        self.llm_page = llm_gui.LlmGui(
                            config=self.config_,
                            storage_container=self.storage_container,
                            parent=self
                        )
                        self.llm_page.content_()

                  #  if self.is_admin():
                  #      with ui.tab_panel("sql_console"):
                  #          self.sql_console()

                    with ui.tab_panel("help"):
                        page = help_gui.helpgui(
                            config=self.config_,
                            add_page=False,
                        )
                        page.content_()