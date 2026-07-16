"""Help GUI module.

Provides a user-friendly documentation and support page within the application.
"""

# --------------------------------------------------
# PACKAGES
# --------------------------------------------------
from nicegui import ui
import src.utils.theme as theme


# --------------------------------------------------
# CLASS
# --------------------------------------------------
class helpgui:
    """Manages the documentation and help center page interface.

    Attributes:
        config_: Configuration dictionary.
        page_url_path: URL path for the page.
        frame_name: Display name of the page frame.
    """

    def __init__(
        self,
        config,
        page_url_path="/help",
        frame_name="Help Center",
        add_page=False,
    ):
        """Initializes the helpgui.

        Args:
            config: Configuration dictionary.
            page_url_path: URL path for the page. Defaults to "/help".
            frame_name: Display name of the page frame. Defaults to "Help Center".
            add_page: Whether to register the page route immediately. Defaults to False.
        """

        self.config_ = config
        self.page_url_path = page_url_path
        self.frame_name = frame_name

        if add_page:
            self.add_page()

    # --------------------------------------------------
    # ADD PAGE
    # --------------------------------------------------
    def add_page(self, page_url=None, frame_name=None):
        """Adds this page as a distinct route in the application.

        Args:
            page_url: Optional override for the URL path.
            frame_name: Optional override for the frame title.
        """

        if page_url is None:
            page_url = self.page_url_path

        if frame_name is None:
            frame_name = self.frame_name

        @ui.page(page_url)
        def page_():

            with theme.frame(frame_name):
                self.content_()

    # --------------------------------------------------
    # REUSABLE SECTION CARD
    # --------------------------------------------------
    def section_card(
        self,
        title,
        icon,
        lines,
        color="text-blue-600",
    ):
        """Creates a reusable card displaying documentation instructions/steps.

        Args:
            title: Title text for the card.
            icon: Icon identifier.
            lines: List of instruction text lines.
            color: Text color class. Defaults to "text-blue-600".
        """

        with ui.card().classes(
            "w-full rounded-2xl shadow-lg bg-white p-5"
        ):

            with ui.row().classes(
                "items-center gap-3 mb-4"
            ):

                ui.icon(icon).classes(
                    f"text-3xl {color}"
                )

                ui.label(title).classes(
                    "text-xl font-bold text-slate-800"
                )

            for line in lines:
                ui.label(line).classes(
                    "text-slate-700 leading-7"
                )

    # --------------------------------------------------
    # SMALL KPI CARD
    # --------------------------------------------------
    def stat_card(
        self,
        title,
        value,
        icon,
        color,
    ):
        """Creates a reusable metric/status display card.

        Args:
            title: Title of the metric.
            value: Metric value text.
            icon: Icon identifier.
            color: Color class for the icon.
        """

        with ui.card().classes(
            "w-56 rounded-2xl shadow-lg bg-white p-5"
        ):

            with ui.row().classes(
                "items-center justify-between"
            ):

                ui.label(title).classes(
                    "text-sm text-slate-500"
                )

                ui.icon(icon).classes(
                    f"text-2xl {color}"
                )

            ui.label(value).classes(
                "text-3xl font-bold mt-3"
            )

    # --------------------------------------------------
    # CONTENT
    # --------------------------------------------------
    def content_(self):
        """Renders the HTML/CSS contents of the help center page."""

        ui.add_head_html("""
        <style>
        body{
            background:#f8fafc;
            font-family:Inter,Arial,sans-serif;
        }
        .help-scroll{
            scroll-behavior:smooth;
        }
        </style>
        """)

        with ui.column().classes(
            "w-full gap-6 p-4 help-scroll"
        ):

            # --------------------------------------------------
            # HERO HEADER
            # --------------------------------------------------
            with ui.card().classes(
                "w-full rounded-3xl shadow-2xl "
                "bg-gradient-to-r from-blue-700 "
                "via-cyan-500 to-sky-500 text-white p-8"
            ):

                with ui.row().classes(
                    "w-full items-center justify-between"
                ):

                    with ui.column():

                        ui.label(
                            "raw2ready Help Center"
                        ).classes(
                            "text-4xl font-bold"
                        )

                        ui.label(
                            "Official Documentation & AI Guide & Troubleshooting & Best Practices"
                        ).classes(
                            "text-lg opacity-90 mt-2"
                        )

                        ui.label(
                            "Version 2026"
                        ).classes(
                            "text-sm opacity-80 mt-4"
                        )

                    ui.icon(
                        "support_agent"
                    ).classes(
                        "text-7xl"
                    )

            # --------------------------------------------------
            # QUICK KPI INFO
            # --------------------------------------------------
            with ui.row().classes(
                "w-full gap-4 flex-wrap"
            ):

                self.stat_card(
                    "Main Modules",
                    "11+",
                    "dashboard",
                    "text-blue-600",
                )

                self.stat_card(
                    "AI Functions",
                    "8+",
                    "smart_toy",
                    "text-purple-600",
                )

                self.stat_card(
                    "Export / DB",
                    "Ready",
                    "cloud_upload",
                    "text-green-600",
                )

                self.stat_card(
                    "Admin Tools",
                    "Enabled",
                    "admin_panel_settings",
                    "text-red-500",
                )

            # --------------------------------------------------
            # QUICK START
            # --------------------------------------------------
            self.section_card(
                "Quick Start Workflow",
                "rocket_launch",
                [
                    "1. Open LOAD and import CSV / Excel / JSON files.",
                    "2. Validate preview table and dataset structure.",
                    "3. Use PARSE to clean missing values, duplicates and bad column names.",
                    "4. Use MERGE to combine multiple sources.",
                    "5. Use CALCULATE for KPIs, formulas and engineered features.",
                    "6. Use PLOT for charts, trends and distributions.",
                    "7. Use Dashboard AI tools for insights, forecasting and reports.",
                    "8. Export final dataset or save to database.",
                ],
                "text-green-600",
            )

            # --------------------------------------------------
            # MODULES
            # --------------------------------------------------
            self.section_card(
                "Sidebar Modules Explained",
                "apps",
                [
                    "DASHBOARD  -> Main analytics center with KPIs and AI tools.",
                    "LOAD       -> Import source files into memory/database, clean columns, normalize values, remove duplicates.",
                    "MERGE      -> Join multiple datasets together.",
                    "CALCULATE  -> Create formulas, metrics and transformations.",
                    "PLOT       -> Build charts automatically.",
                    "INVESTIGATION   -> Standardized workflow templates.",
                    "LLM        -> AI assistant for data tasks.",
                    "LLM PROTOCOL -> AI automation workflows.",
                    "SQL CONSOLE (Admin) -> SQL + Natural Language to SQL.",
                    "HELP       -> This support center.",
                ],
                "text-blue-600",
            )

            # --------------------------------------------------
            # DASHBOARD GUIDE
            # --------------------------------------------------
            self.section_card(
                "Dashboard Guide",
                "dashboard_customize",
                [
                    "Loaded Files -> Number of imported source files.",
                    "Rows -> Active dataset row count.",
                    "Columns -> Active dataset column count.",
                    "Last Loaded File -> Most recent imported file.",
                    "Preview Table -> Top rows for quick inspection.",
                    "Refresh -> Recalculate dashboard metrics.",
                    "Charts -> Auto visualization engine.",
                    "Forecast -> Predict future values for numeric trends.",
                    "Report -> Executive AI report.",
                    "Recommendations -> Smart next-step suggestions.",
                ],
                "text-cyan-600",
            )

            # --------------------------------------------------
            # AI ANALYTICS
            # --------------------------------------------------
            self.section_card(
                "AI Analytics Tools",
                "psychology",
                [
                    "Summary -> Column types, missing values, data profile.",
                    "Anomalies -> Detect suspicious outliers or invalid values.",
                    "Clean -> Auto cleaning and standardization.",
                    "Forecast -> Predict next N values.",
                    "Report -> Executive management summary.",
                    "Recommendations -> Operational improvements.",
                    "Auto Charts -> Suggested visualizations.",
                    "Copilot Chat -> Natural language assistant.",
                ],
                "text-purple-600",
            )

            # --------------------------------------------------
            # AI CHAT
            # --------------------------------------------------
            self.section_card(
                "AI Copilot Example Prompts",
                "chat",
                [
                    "summarize this dataset",
                    "find anomalies in temperature column",
                    "forecast next 10 values",
                    "which columns are numeric?",
                    "clean missing values",
                    "generate executive report",
                    "what chart should I use?",
                    "which feature is best for prediction?",
                ],
                "text-indigo-600",
            )

            # --------------------------------------------------
            # SQL CONSOLE
            # --------------------------------------------------
            self.section_card(
                "SQL Console (Admin)",
                "terminal",
                [
                    "RAW SQL MODE -> Run manual PostgreSQL queries.",
                    "AI MODE -> Write natural language and convert to SQL.",
                    "Examples:",
                    "show tables",
                    "show latest logs",
                    "how many users",
                    "latest datasets",
                    "all admins",
                    "Security filters block dangerous commands.",
                ],
                "text-red-500",
            )

            # --------------------------------------------------
            # FILE SUPPORT
            # --------------------------------------------------
            self.section_card(
                "Supported Files",
                "folder_open",
                [
                    "CSV files",
                    "Excel (.xlsx / .xls)",
                    "JSON",
                    "Text structured files",
                    "Industrial exports / lab exports",
                    "Merged multi-source datasets",
                ],
                "text-amber-600",
            )

            # --------------------------------------------------
            # TROUBLESHOOTING
            # --------------------------------------------------
            self.section_card(
                "Troubleshooting",
                "build",
                [
                    "No dataset loaded -> Import a file first.",
                    "Preview empty -> Check separator / file format.",
                    "Wrong columns -> Re-import using correct delimiter.",
                    "Charts blank -> Need numeric/date columns.",
                    "Forecast failed -> Select stable numeric series.",
                    "Slow system -> Reduce huge files or split datasets.",
                    "SQL error -> Check table names / permissions.",
                    "AI SQL no result -> Use simpler natural language.",
                ],
                "text-orange-600",
            )

            # --------------------------------------------------
            # BEST PRACTICES
            # --------------------------------------------------
            self.section_card(
                "Best Practices",
                "workspace_premium",
                [
                    "Use clear column names.",
                    "Always clean duplicates first.",
                    "Check null values early.",
                    "Validate units before forecasting.",
                    "Use reports for management decisions.",
                    "Use alerts for production monitoring.",
                    "Backup database regularly.",
                    "Use AI recommendations after cleaning.",
                ],
                "text-green-700",
            )

            # --------------------------------------------------
            # SECURITY
            # --------------------------------------------------
            self.section_card(
                "Security & Roles",
                "verified_user",
                [
                    "Viewer -> Read-only usage.",
                    "User _> Standard analytics access.",
                    "Admin -> SQL console + advanced controls.",
                    "Superadmin -> Full enterprise control.",
                    "Dangerous SQL commands are blocked in AI mode.",
                ],
                "text-sky-700",
            )

            # --------------------------------------------------
            # PERFORMANCE
            # --------------------------------------------------
            self.section_card(
                "Performance Tips",
                "speed",
                [
                    "Prefer CSV for fastest loading.",
                    "Use only required columns.",
                    "Archive old datasets.",
                    "Use filters before plotting huge data.",
                    "Run heavy analytics after cleaning.",
                ],
                "text-pink-600",
            )

            # --------------------------------------------------
            # CONTACT / SUPPORT
            # --------------------------------------------------
            self.section_card(
                "Need Help Fast?",
                "support",
                [
                    "Use Dashboard AI Copilot chat.",
                    "Describe issue naturally.",
                    "Example: Why is my chart blank?",
                    "Example: Clean duplicate rows.",
                    "Example: Show latest failed uploads.",
                ],
                "text-indigo-700",
            )

            # --------------------------------------------------
            # FOOTER
            # --------------------------------------------------
            with ui.card().classes(
                "w-full rounded-2xl bg-white shadow-lg p-5"
            ):

                ui.label(
                    "raw2ready Help Center 2026"
                ).classes(
                    "text-sm text-slate-500"
                )