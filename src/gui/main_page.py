"""Main Dashboard GUI module.

Provides a unified portal showing parsed data files summary stats, key performance
indicators, smart anomaly warnings/recommendations, SQL query console, and a
CoPilot chatbot assistant.
"""

from nicegui import ui, app

import src.utils.theme as theme
from src.utils.logging_config import get_logger

from src.core.ai_analytics import (
    storage_to_df,
    summarize_df,
    detect_anomalies,
    clean_df,
    save_df_to_storage,
)

from src.core.auto_visualizer import AutoVisualizer
from src.core.ai_chat_engine import ask_ai
from src.core.smart_recommendations import recommend_from_storage
from src.core.forecast_engine import ask_forecast
from src.core.report_generator import ask_report

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
        frame_name="Raw2Ready",
        add_page=False,
        storage_container=None,
        dirs=None,
    ):
        """Initializes main_page.

        Args:
            config: Config dictionary containing environment/analytical parameters.
            page_url_path: Route URL path. Defaults to "/".
            frame_name: Title of UI layout frame. Defaults to "Raw2Ready".
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

        self.lbl_files = None
        self.lbl_rows = None
        self.lbl_cols = None
        self.lbl_last = None

        self.preview_container = None
        self.ai_result_container = None
        self.chat_messages_container = None

        self.chat_input = None
        self.chat_history = []

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

            rows_count = len(
                self.storage_container.get(
                    "df_json",
                    [],
                )
            )

            cols_count = len(
                self.storage_container.get(
                    "df_columns",
                    [],
                )
            )

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

            self.render_preview()

            ui.notify(
                "Dashboard refreshed",
                type="info",
            )

        except Exception as e:
            logger.warning(f"refresh error: {e}")

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
            "w-60 rounded-2xl shadow-xl "
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

    # --------------------------------------------------
    # PREVIEW
    # --------------------------------------------------
    def render_preview(self):

        if self.preview_container is None:
            return

        self.preview_container.clear()

        rows = self.storage_container.get(
            "df_json",
            [],
        )[:10]

        columns = self.storage_container.get(
            "df_columns",
            [],
        )

        with self.preview_container:

            if not rows or not columns:

                with ui.card().classes(
                    "w-full rounded-2xl shadow-lg bg-white"
                ):
                    ui.label(
                        "No dataset loaded yet."
                    ).classes(
                        "text-slate-500"
                    )
                return

            cols = []

            for c in columns:
                cols.append(
                    {
                        "name": c,
                        "label": c,
                        "field": c,
                        "align": "left",
                    }
                )

            with ui.card().classes(
                "w-full rounded-2xl shadow-lg bg-white"
            ):

                ui.label(
                    "Dataset Preview (Top 10 Rows)"
                ).classes(
                    "text-xl font-bold mb-4"
                )

                ui.table(
                    rows=rows,
                    columns=cols,
                    row_key=columns[0],
                    pagination=10,
                ).classes("w-full")

    # --------------------------------------------------
    # RESULT PANEL
    # --------------------------------------------------
    def show_ai_result(
        self,
        title,
        lines,
    ):

        if self.ai_result_container is None:
            return

        self.ai_result_container.clear()

        with self.ai_result_container:

            with ui.card().classes(
                "w-full rounded-2xl shadow-lg bg-white"
            ):

                ui.label(title).classes(
                    "text-xl font-bold mb-3"
                )

                for line in lines:
                    ui.label(str(line)).classes(
                        "text-slate-700"
                    )

    # --------------------------------------------------
    # AI ACTIONS
    # --------------------------------------------------
    def ai_summary(self):

        df = storage_to_df(
            self.storage_container
        )

        self.show_ai_result(
            "Dataset Summary",
            summarize_df(df),
        )

    def ai_anomalies(self):

        df = storage_to_df(
            self.storage_container
        )

        self.show_ai_result(
            "Anomaly Detection",
            detect_anomalies(df),
        )

    def ai_clean(self):

      df = storage_to_df(self.storage_container)
  
      if df is None or df.empty:
          self.show_ai_result(
              "Cleaning Complete",
              ["No dataset loaded."]
          )
          return
  
      # ------------------------------------------------
      # STEP 1: Convert blanks to NaN
      # ------------------------------------------------
      df = df.replace(r'^\s*$', pd.NA, regex=True)
  
      # ------------------------------------------------
      # STEP 2: Remove empty rows
      # ------------------------------------------------
      before_rows = len(df)
      df = df.dropna(axis=0, how="all")
  
      # ------------------------------------------------
      # STEP 3: Remove empty columns
      # ------------------------------------------------
      before_cols = len(df.columns)
      df = df.dropna(axis=1, how="all")
  
      # ------------------------------------------------
      # STEP 4: Shift row values left
      # ------------------------------------------------
      rows = []
  
      for _, row in df.iterrows():
          vals = [x for x in row.tolist() if pd.notna(x)]
          vals += [pd.NA] * (len(df.columns) - len(vals))
          rows.append(vals)
  
      df = pd.DataFrame(rows, columns=df.columns)
  
      # ------------------------------------------------
      # STEP 5: Fill remaining blanks
      # ------------------------------------------------
      df = df.fillna("")
  
      # ------------------------------------------------
      # SAVE BACK
      # ------------------------------------------------
      save_df_to_storage(
          df,
          self.storage_container
      )
  
      self.refresh_dashboard()
  
      removed_rows = before_rows - len(df)
      removed_cols = before_cols - len(df.columns)
  
      self.show_ai_result(
          "Cleaning Complete",
          [
              f"Removed empty rows: {removed_rows}",
              f"Removed empty columns: {removed_cols}",
              "Shifted values left",
              "Blank cells cleaned",
              "Dashboard refreshed"
          ]
      )

    def ai_visualizer(self):
        AutoVisualizer(
            self.storage_container
        ).render()

    def ai_recommendations(self):

        lines = recommend_from_storage(
            self.storage_container
        )

        self.show_ai_result(
            "Smart Recommendations",
            lines,
        )

    def ai_forecast(self):

        result = ask_forecast(
            "forecast next 10",
            self.storage_container,
        )

        self.show_ai_result(
            result["title"],
            result["lines"],
        )

    def ai_report(self):

        result = ask_report(
            self.storage_container
        )

        self.show_ai_result(
            result["title"],
            result["lines"],
        )

    # --------------------------------------------------
    # CHAT
    # --------------------------------------------------
    def render_chat_history(self):

        if self.chat_messages_container is None:
            return

        self.chat_messages_container.clear()

        with self.chat_messages_container:

            for role, msg in self.chat_history:

                align = (
                    "justify-end"
                    if role == "user"
                    else "justify-start"
                )

                bubble = (
                    "bg-blue-600 text-white"
                    if role == "user"
                    else
                    "bg-white text-slate-800 "
                    "border border-slate-200"
                )

                with ui.row().classes(
                    f"w-full {align}"
                ):

                    ui.markdown(msg).classes(
                        f"max-w-[75%] px-4 py-3 "
                        f"rounded-2xl shadow {bubble}"
                    )

    def run_copilot(self):

        if self.chat_input is None:
            return

        prompt = self.chat_input.value.strip()

        if prompt == "":
            ui.notify(
                "Type a question first",
                type="warning",
            )
            return

        self.chat_history.append(
            ("user", prompt)
        )

        self.render_chat_history()

        low = prompt.lower()

        if "forecast" in low:
            result = ask_forecast(
                prompt,
                self.storage_container,
            )

        elif "report" in low:
            result = ask_report(
                self.storage_container
            )

        else:
            result = ask_ai(
                prompt,
                self.storage_container,
            )

        answer = "\n".join(
            [str(x) for x in result["lines"]]
        )

        self.chat_history.append(
            ("ai", answer)
        )

        self.render_chat_history()

        self.chat_input.value = ""
        self.chat_input.update()

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
                "bg-gradient-to-r from-blue-700 "
                "via-cyan-500 to-sky-500 text-white"
            ):

                with ui.row().classes(
                    "w-full items-center justify-between"
                ):

                    with ui.column():

                        ui.label(
                            "Raw2Ready AI Analytics Center"
                        ).classes(
                            "text-4xl font-bold"
                        )

                        ui.label(
                            "Enterprise Industrial Intelligence Platform"
                        ).classes(
                            "text-lg opacity-90"
                        )

                    ui.image(
                        "/assets/images/project_logo.jpg"
                    ).classes(
                        "w-24 h-24 rounded-2xl bg-white p-2"
                    )

            with ui.row().classes(
                "w-full gap-4 flex-wrap"
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
                    "w-72 rounded-2xl shadow-xl bg-white"
                ):

                    ui.label(
                        "Last Loaded File"
                    ).classes(
                        "text-sm text-slate-500"
                    )

                    self.lbl_last = ui.label(
                        last_file
                    ).classes(
                        "text-lg font-bold mt-3 break-all"
                    )

            with ui.card().classes(
                "w-full rounded-2xl shadow-lg bg-white"
            ):

                ui.label(
                    "Quick Actions"
                ).classes(
                    "text-xl font-bold mb-4"
                )

                with ui.row().classes(
                    "gap-3 flex-wrap"
                ):

                    ui.button(
                        "Refresh",
                        icon="refresh",
                        on_click=self.refresh_dashboard,
                    )

                    ui.button(
                        "Charts",
                        icon="bar_chart",
                        on_click=self.ai_visualizer,
                    )

                    ui.button(
                        "Forecast",
                        icon="timeline",
                        on_click=self.ai_forecast,
                    )

                    ui.button(
                        "Report",
                        icon="description",
                        on_click=self.ai_report,
                    )

                    ui.button(
                        "Recommendations",
                        icon="auto_awesome",
                        on_click=self.ai_recommendations,
                    )

            self.preview_container = ui.column().classes(
                "w-full"
            )
            self.render_preview()

            with ui.card().classes(
                "w-full rounded-2xl shadow-lg bg-white"
            ):

                ui.label(
                    "AI Assistant"
                ).classes(
                    "text-xl font-bold mb-4"
                )

                with ui.row().classes(
                    "gap-3 flex-wrap"
                ):

                    ui.button(
                        "Summary",
                        icon="smart_toy",
                        on_click=self.ai_summary,
                    )

                    ui.button(
                        "Anomalies",
                        icon="warning",
                        on_click=self.ai_anomalies,
                    )

                    ui.button(
                        "Clean",
                        icon="cleaning_services",
                        on_click=self.ai_clean,
                    )

                    ui.button(
                        "Forecast",
                        icon="timeline",
                        on_click=self.ai_forecast,
                    )

                    ui.button(
                        "Report",
                        icon="description",
                        on_click=self.ai_report,
                    )

            with ui.card().classes(
                "w-full rounded-2xl shadow-lg bg-white"
            ):

                ui.label(
                    "AI Copilot Chat"
                ).classes(
                    "text-xl font-bold mb-4"
                )

                self.chat_messages_container = ui.column().classes(
                    "w-full gap-3 mb-4 max-h-[500px] overflow-auto"
                )

                with ui.row().classes(
                    "w-full gap-3 items-center"
                ):

                    self.chat_input = ui.input(
                        placeholder="Ask anything..."
                    ).classes(
                        "flex-1"
                    ).props("outlined")

                    self.chat_input.on(
                        "keydown.enter",
                        lambda e: self.run_copilot()
                    )

                    ui.button(
                        "Send",
                        icon="send",
                        on_click=self.run_copilot,
                    )

            self.ai_result_container = ui.column().classes(
                "w-full"
            )

    # --------------------------------------------------
    # CONTENT
    # --------------------------------------------------
    def content_(self):
        """Renders the HTML/CSS contents of the main dashboard page, tab bar, and inner panels."""

        ui.add_head_html("""
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
        </style>
        """)

        with ui.row().classes(
            "w-full h-screen no-wrap"
        ):

            # SIDEBAR
            with ui.column().classes(
                "w-72 h-full bg-slate-900 text-white p-4"
            ):

                with ui.row().classes(
                    "items-center gap-3 mb-4"
                ):

                    ui.image(
                        "/assets/images/project_logo.jpg"
                    ).classes(
                        "w-14 h-14 rounded-xl"
                    )

                    with ui.column():

                        ui.label(
                            "Raw2Ready"
                        ).classes(
                            "text-xl font-bold"
                        )

                        ui.label(
                            "Data Platform"
                        ).classes(
                            "text-xs text-slate-300"
                        )

                ui.separator()

            #    ui.label(
            #        f"User: {self.current_user()} ({self.current_role()})"
            #    ).classes(
            #        "text-xs text-cyan-300 mt-2 mb-2"
            #    )

                ui.button(
                    "Logout",
                    icon="logout",
                    color="negative",
                    on_click=lambda: (
                        auth.logout_user(),
                        ui.navigate.to("/login"),
                    ),
                ).classes("w-full mb-3")

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

                ui.label(
                    "Version 2026"
                ).classes(
                    "text-xs text-slate-400 mt-3"
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

                    with ui.tab_panel("dashboard"):
                        self.dashboard()

                    with ui.tab_panel("load"):
                        page = load_gui.loadgui(
                            config=self.config_,
                            storage_container=self.storage_container,
                            dirs=self.dirs
                        )
                        page.content_()

                    with ui.tab_panel("merge"):
                        page = merge_gui.mergegui(
                            config=self.config_,
                            storage_container=self.storage_container,
                        )
                        page.content_()

                    with ui.tab_panel("calculate"):
                        page = calculate_gui.calculategui(
                            config=self.config_,
                            storage_container=self.storage_container,
                        )
                        page.content_()

                    with ui.tab_panel("plot"):
                        page = plot_gui.plotgui(
                            config=self.config_,
                            storage_container=self.storage_container,
                        )
                        page.content_()

                    with ui.tab_panel("metadata"):
                        page = metadata_gui.NewProtocol(
                            storage_container=self.storage_container
                        )
                        page.content_()

                    with ui.tab_panel("llm"):
                        page = llm_gui.LlmGui(
                            config=self.config_,
                            storage_container=self.storage_container,
                        )
                        page.content_()

                  #  if self.is_admin():
                  #      with ui.tab_panel("sql_console"):
                  #          self.sql_console()

                    with ui.tab_panel("help"):
                        page = help_gui.helpgui(
                            config=self.config_,
                            add_page=False,
                        )
                        page.content_()