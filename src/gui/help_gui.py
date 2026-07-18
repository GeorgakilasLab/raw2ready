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
                "bg-gradient-to-r from-[#64748B] via-[#63B3ED] to-[#4FD1C5] text-white p-8"
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
                            "Documentation, Troubleshooting and Best Practices"
                        ).classes(
                            "text-lg opacity-90 mt-2"
                        )

                    ui.icon(
                        "support_agent"
                    ).classes(
                        "text-7xl"
                    )

            # --------------------------------------------------
            # DIRECTORY PANEL
            # --------------------------------------------------
            with ui.card().classes(
                "w-full rounded-2xl shadow-lg border border-slate-200 bg-white p-6"
            ):
                ui.label("Resources & Contacts").classes(
                    "text-xl font-bold mb-4 text-slate-800"
                )

                with ui.row().classes("w-full gap-8 flex-wrap"):
                    
                    with ui.column().classes("flex-1 min-w-[250px]"):
                        ui.label("Documentation & Repositories").classes(
                            "font-bold text-slate-700 mb-2"
                        )
                        
                        with ui.row().classes("items-center gap-2 mb-2"):
                            ui.icon("code", color="primary")
                            ui.link(
                                "GitHub Repository",
                                "https://github.com/GeorgakilasLab/raw2ready",
                                new_tab=True
                            ).classes("text-blue-600 font-semibold hover:underline")

                        with ui.row().classes("items-center gap-2 mb-2"):
                            ui.icon("description", color="primary")
                            ui.link(
                                "GitHub Pages Documentation",
                                "https://GeorgakilasLab.github.io/raw2ready/",
                                new_tab=True
                            ).classes("text-blue-600 font-semibold hover:underline")

                        with ui.row().classes("items-center gap-2"):
                            ui.icon("bug_report", color="primary")
                            ui.link(
                                "Report an Issue / Bug Tracker",
                                "https://github.com/GeorgakilasLab/raw2ready/issues",
                                new_tab=True
                            ).classes("text-blue-600 font-semibold hover:underline")

                    with ui.column().classes("flex-1 min-w-[250px] border-l border-slate-100 pl-4"):
                        ui.label("Contact Persons").classes(
                            "font-bold text-slate-700 mb-2"
                        )
                        
                        with ui.column().classes("mb-3"):
                            ui.label("George Georgakilas").classes("font-semibold text-slate-800")
                            ui.label("ggeorgakilas@athenarc.gr").classes("text-sm text-slate-500")

                        with ui.column():
                            ui.label("Michael Antoniades").classes("font-semibold text-slate-800")
                            ui.label("antoniades000michael@gmail.com").classes("text-sm text-slate-500")

            # --------------------------------------------------
            # MODULES
            # --------------------------------------------------
            self.section_card(
                "Sidebar Modules Explained",
                "apps",
                [
                    "DASHBOARD  -> Overview of loaded data files.",
                    "LOAD       -> Import data files, fill missing values, clean columns, remove duplicates, standardize columns.",
                    "MERGE      -> Merge loaded datasets together.",
                    "CALCULATE  -> Evaluate custom formulas and create new data columns.",
                    "PLOT       -> Visualize data with interactive plots.",
                    "METADATA   -> Semantically annotate datasets with MIFE.",
                    "LLM        -> Agentic AI assistant for data, experimental conditions, microbial information and literature.",
                    "HELP       -> This help center.",
                ],
                "text-blue-600",
            )

            # --------------------------------------------------
            # FILE FORMAT SUPPORT
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
            # AI CHAT
            # --------------------------------------------------
            self.section_card(
                "AI Assistant Example Prompts",
                "chat",
                [
                    "What is the maximum value of pH in the active dataset?",
                    "What was the average dissolved oxygen (DO) concentration during the first 5 hours of the fermentation?",
                    "Show me the experimental factors and study designs from the loaded MIFE metadata.",
                    "Look up the oxygen requirements and optimum pH of Saccharomyces cerevisiae in BacDive.",
                    "Search CrossRef for papers on carbon source optimization in Pseudomonas putida bioprocesses.",
                    "Find online resources discussing the effect of temperature shifts on recombinant protein expression.",
                ],
                "text-indigo-600",
            )

            # --------------------------------------------------
            # TROUBLESHOOTING
            # --------------------------------------------------
            self.section_card(
                "Troubleshooting",
                "build",
                [
                    "Preview empty -> Check separator / file format.",
                    "Wrong columns -> Re-import using correct delimiter.",
                    "Charts blank -> Need numeric columns.",
                    "Slow system -> Reduce huge files or split datasets.",
                    "AI-assistant gives wrong results -> Try again with simpler phrasing or different wording.",
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
                    "Validate units before applying custom formulas.",
                    "Remember that AI-assistant may make mistakes.",
                ],
                "text-green-700",
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
                ],
                "text-pink-600",
            )
