"""LLM GUI module.

Provides a user interface for conversing with LLM src.agents about datasets,
extracting protocol information, and exploring microorganism databases like BacDive.
"""

from nicegui import ui, app
import pandas as pd
import numpy as np
import requests
import ollama
import asyncio
import json
import os
import re
import html
import time

import src.utils.theme as theme
from src.utils.logging_config import get_logger
from src.utils.paths import ensure_dirs
from src.agents.agent_orchestrator import AgentOrchestrator
from langchain_ollama import OllamaLLM
from src.agents.bacdive_explorer import BacDiveExplorerAgent
from src.agents.microorganism_router import MicroorganismRouter


logger = get_logger("llm_gui")


class LlmGui:
    """Manages the LLM dataset exploration and agent chat interface.

    Attributes:
        config: Application configuration dictionary.
        page_url_path: URL route path for this page.
        frame_name: Title of the page frame.
        storage: Data storage container dict.
        protocol_dir: Directory where protocol JSONs are stored.
        df: Loaded active pandas DataFrame.
        current_df: Copy of the active DataFrame.
        protocol_data: Loaded protocol JSON data.
        mem_file: Saved active filename in memory.
        mem_protocol: Saved active protocol name in memory.
        mem_model: Saved active LLM model name in memory.
        mem_temp: Saved active LLM temperature in memory.
        DEBUG_CROSSREF: Flag indicating if CrossRef debug mode is active.
        available_microorganisms: List of supported microorganisms.
        selected_microorganisms: Selected microorganism values from dropdown.
        no_microorganism_info_message: Fallback message for empty microorganism queries.
        router_llm: Ollama LLM client for routing decisions.
        orchestrator: Main agent orchestrator instance.
        bacdive_agent: Agent for searching BacDive database.
        microorganism_router: Router agent to classify microorganism questions.
    """

    # =====================================================
    # INIT
    # =====================================================
    def __init__(
        self,
        config,
        page_url_path="/llm",
        frame_name="LLM Dataset",
        add_page=False,
        storage_container=None,
        storage_container_=None,
        parent=None,
    ):
        """Initializes LlmGui.

        Args:
            config: Config dictionary containing LLM parameters.
            page_url_path: Route URL path. Defaults to "/llm".
            frame_name: UI layout frame name. Defaults to "LLM Dataset".
            add_page: Whether to automatically register the route page. Defaults to False.
            storage_container: Optional primary storage container dict.
            storage_container_: Optional secondary storage container dict.
        """

        # =============================================
        # STORAGE COMPATIBILITY
        # =============================================
        if (
            storage_container is None
            and storage_container_ is not None
        ):

            storage_container = storage_container_

        if storage_container is None:

            storage_container = {}

        # =============================================
        # BASIC PAGE CONFIG
        # =============================================
        self.config = config

        self.page_url_path = page_url_path

        self.frame_name = frame_name

        self.storage = storage_container

        self.parent = parent

        # =============================================
        # SAVED PROTOCOL DIRECTORY
        # =============================================
        self.protocol_dir = str(ensure_dirs()["protocols"])

        # =============================================
        # DATA MEMORY
        # =============================================
        self.df = None

        self.current_df = None

        self.protocol_data = {}

        self.mem_file = ""

        self.mem_protocol = ""

        self.mem_model = "llama3:latest"

        self.mem_temp = 0.2

        # =============================================
        # CROSSREF / DEBUG
        # =============================================
        self.DEBUG_CROSSREF = True

        # =============================================
        # MICROORGANISM DROPDOWN MEMORY
        # =============================================
        self.available_microorganisms = [

            "Escherichia coli",

            "Bacillus subtilis",

            "Saccharomyces cerevisiae",

            "Pichia pastoris",

            "Komagataella phaffii",

            "Corynebacterium glutamicum",

            "Pseudomonas putida",

            "Clostridium acetobutylicum",

            "Lactobacillus plantarum",

            "Lactococcus lactis",

            "Streptomyces coelicolor",

            "Aspergillus niger",

            "Cupriavidus necator",

            "Zymomonas mobilis",

            "Clostridium beijerinckii",

            "Bacillus licheniformis",

            "Bacillus megaterium",

            "Pseudomonas fluorescens",

            "Yarrowia lipolytica",

            "Rhodosporidium toruloides"
        ]

        self.selected_microorganisms = []

        self.no_microorganism_info_message = (
            "Based on what the user asked, no information can be found "
            "and there is no information regarding the specific microorganism"
        )

        # =============================================
        # LOAD SAVED MEMORY BEFORE LLM INIT
        # =============================================
        self.load_memory()

        # =============================================
        # OLLAMA ROUTER LLM
        # =============================================
        self.router_llm = OllamaLLM(

            model=self.mem_model,

            temperature=0.0
        )

        # =============================================
        # MAIN ORCHESTRATOR
        # =============================================
        self.orchestrator = AgentOrchestrator(

            model_name=self.mem_model,

            temperature=self.mem_temp
        )

        # =============================================
        # BACDIVE AGENT
        # =============================================
        self.bacdive_agent = BacDiveExplorerAgent(

            model_name=self.mem_model,

            temperature=self.mem_temp
        )

        # =============================================
        # MICROORGANISM ROUTER
        # =============================================
        self.microorganism_router = MicroorganismRouter(

            model_name=self.mem_model,

            temperature=0.0
        )

        # =============================================
        # OPTIONAL PAGE REGISTRATION
        # =============================================
        if add_page:

            self.add_page()

    # =====================================================
    # AVAILABLE FILES
    # =====================================================
    def get_cache(self):
        """Gets the parsed datasets cache from the storage dictionary.

        Returns:
            Dictionary containing the parsed dataset cache.
        """

        return self.storage.setdefault(
            "parsed_cache",
            {}
        )

    def get_available_files(self):
        """Gets the list of names of files currently stored in cache.

        Returns:
            List of cached file names.
        """

        return list(
            self.storage.get(
                "parsed_cache",
                {}
            ).keys()
        )

    # =====================================================
    # PAGE
    # =====================================================
    def add_page(self):
        """Adds this page as a distinct route in the application."""

        @ui.page(self.page_url_path)
        def page():

            if "shared_data" not in app.storage.general:

                app.storage.general[
                    "shared_data"
                ] = {}

            self.storage = app.storage.general[
                "shared_data"
            ]

            with theme.frame(
                self.frame_name
            ):

                self.content_()

    # =====================================================
    # MEMORY
    # =====================================================
    def save_memory(self):
        """Saves current GUI selection state to session storage cache."""

        self.storage["llm_memory"] = {

            "selected_file":
                self.file_select.value
                if hasattr(
                    self,
                    "file_select"
                )
                else "",

            "selected_protocol":
                self.protocol_select.value
                if hasattr(
                    self,
                    "protocol_select"
                )
                else "",

            "model":
                self.model_select.value
                if hasattr(
                    self,
                    "model_select"
                )
                else self.mem_model,

            "temperature":
                self.temperature.value
                if hasattr(
                    self,
                    "temperature"
                )
                else self.mem_temp,

            "selected_microorganisms":
                self.selected_microorganisms
        }

        self.storage[
            "selected_microorganisms"
        ] = self.selected_microorganisms

    def load_memory(self):
        """Loads previous GUI selection states from session storage cache."""

        mem = self.storage.get(
            "llm_memory",
            {}
        )

        self.mem_file = mem.get(
            "selected_file",
            ""
        )

        self.mem_protocol = mem.get(
            "selected_protocol",
            ""
        )

        self.mem_model = mem.get(
            "model",
            "llama3:latest"
        )

        self.mem_temp = mem.get(
            "temperature",
            0.2
        )

        saved_microorganisms = mem.get(
            "selected_microorganisms",
            self.storage.get(
                "selected_microorganisms",
                []
            )
        )

        if saved_microorganisms is None:

            saved_microorganisms = []

        if isinstance(
            saved_microorganisms,
            str
        ):

            saved_microorganisms = [
                saved_microorganisms
            ]

        self.selected_microorganisms = [
            m
            for m in saved_microorganisms
            if m in self.available_microorganisms
        ]

    # =====================================================
    # DATASETS
    # =====================================================
    def get_loaded_files(self):

        arr = []

        if (
            "df_json" in self.storage
            and self.storage["df_json"]
        ):

            arr.append(
                "Parsed Dataset"
            )

        files = self.storage.get(
            "files",
            {}
        )

        if isinstance(
            files,
            dict
        ):

            for fname in files.keys():

                low = str(
                    fname
                ).lower()

                if low.endswith(
                    (
                        ".csv",
                        ".tsv",
                        ".xlsx",
                        ".xls"
                    )
                ):

                    arr.append(
                        fname
                    )

        return sorted(
            list(
                set(
                    arr
                )
            )
        )

    def refresh_loaded_files(self):

        if not hasattr(
            self,
            "file_select"
        ):

            return

        files = self.get_available_files()

        self.file_select.options = files

        last = self.storage.get(
            "last_loaded_file"
        )

        if self.mem_file in files:

            self.file_select.value = self.mem_file

        elif last in files:

            self.file_select.value = last

        elif files:

            self.file_select.value = files[0]

        else:

            self.file_select.value = None

        self.file_select.update()

    def use_selected_file(self):

        try:

            if not hasattr(
                self,
                "file_select"
            ):

                return

            selected = self.file_select.value

            if not selected:

                return

            cached = self.storage.get(
                "parsed_cache",
                {}
            ).get(
                selected
            )

            if not cached:

                ui.notify(
                    "Dataset not found in cache",
                    type="negative"
                )

                return

            self.df = pd.DataFrame(
                cached
            )

            self.current_df = self.df

            self.storage[
                "last_loaded_file"
            ] = selected

            self.storage[
                "parsed_df_json"
            ] = cached

            ui.notify(
                f"{selected} loaded",
                type="info"
            )

        except Exception as e:

            ui.notify(
                f"Load error: {str(e)}",
                type="negative"
            )

        self.save_memory()

        self.refresh_info()

    # =====================================================
    # PROTOCOLS
    # =====================================================
    def saved_protocol_names(self):

        arr = []

        for f in os.listdir(
            self.protocol_dir
        ):

            if f.endswith(
                ".json"
            ):

                arr.append(
                    f[:-5]
                )

        return sorted(
            arr
        )

    def refresh_protocols(self):

        if not hasattr(
            self,
            "protocol_select"
        ):

            return

        opts = self.saved_protocol_names()

        self.protocol_select.options = opts

        if self.mem_protocol in opts:

            self.protocol_select.value = self.mem_protocol

        elif opts:

            self.protocol_select.value = opts[0]

        else:

            self.protocol_select.value = None

        self.protocol_select.update()

    def use_selected_protocol(self):

        try:

            if not hasattr(
                self,
                "protocol_select"
            ):

                return

            name = self.protocol_select.value

            if not name:

                self.protocol_data = {}

                self.refresh_info()

                return

            path = os.path.join(
                self.protocol_dir,
                name + ".json"
            )

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as fp:

                self.protocol_data = json.load(
                    fp
                )

            ui.notify(
                f"{name} loaded",
                type="info"
            )

        except Exception as e:

            self.protocol_data = {}

            ui.notify(
                str(e),
                type="negative"
            )

        self.save_memory()

        self.refresh_info()

    # =====================================================
    # MICROORGANISMS
    # =====================================================
    def on_microorganisms_changes(
        self,
        e=None
    ):

        try:

            selected = None

            if (
                e is not None
                and hasattr(
                    e,
                    "value"
                )
            ):

                selected = e.value

            if (
                selected is None
                and hasattr(
                    self,
                    "microorganism_select"
                )
            ):

                selected = self.microorganism_select.value

            if selected is None:

                selected = []

            if isinstance(
                selected,
                str
            ):

                selected = [
                    selected
                ]

            selected = [
                str(x)
                for x in selected
                if x
            ]

            selected = [
                x
                for x in selected
                if x in self.available_microorganisms
            ]

            self.selected_microorganisms = selected

            self.storage[
                "selected_microorganisms"
            ] = selected

            self.save_memory()

            print(
                "[MICROORGANISMS SELECTED]",
                self.selected_microorganisms
            )

            self.refresh_info()

        except Exception as ex:

            print(
                f"[MICROORGANISM CHANGE ERROR] {ex}"
            )

            ui.notify(
                f"Failed to update microorganisms: {ex}",
                type="negative"
            )

    def update_selected_microorganisms(
        self,
        e=None
    ):

        return self.on_microorganisms_changes(
            e
        )

    def microorganism_keywords(
        self,
        microorganism
    ):

        m = microorganism.lower()

        aliases = {

            "escherichia coli": [
                "escherichia coli",
                "e. coli",
                "e coli",
                "ecoli"
            ],

            "bacillus subtilis": [
                "bacillus subtilis",
                "b. subtilis",
                "b subtilis"
            ],

            "saccharomyces cerevisiae": [
                "saccharomyces cerevisiae",
                "s. cerevisiae",
                "s cerevisiae",
                "yeast"
            ],

            "pichia pastoris": [
                "pichia pastoris",
                "p. pastoris",
                "p pastoris"
            ],

            "komagataella phaffii": [
                "komagataella phaffii",
                "k. phaffii",
                "k phaffii"
            ],

            "corynebacterium glutamicum": [
                "corynebacterium glutamicum",
                "c. glutamicum",
                "c glutamicum"
            ],

            "pseudomonas putida": [
                "pseudomonas putida",
                "p. putida",
                "p putida"
            ],

            "clostridium acetobutylicum": [
                "clostridium acetobutylicum",
                "c. acetobutylicum",
                "c acetobutylicum"
            ],

            "lactobacillus plantarum": [
                "lactobacillus plantarum",
                "l. plantarum",
                "l plantarum"
            ],

            "lactococcus lactis": [
                "lactococcus lactis",
                "l. lactis",
                "l lactis"
            ],

            "streptomyces coelicolor": [
                "streptomyces coelicolor",
                "s. coelicolor",
                "s coelicolor"
            ],

            "aspergillus niger": [
                "aspergillus niger",
                "a. niger",
                "a niger"
            ],

            "cupriavidus necator": [
                "cupriavidus necator",
                "c. necator",
                "c necator"
            ],

            "zymomonas mobilis": [
                "zymomonas mobilis",
                "z. mobilis",
                "z mobilis"
            ],

            "clostridium beijerinckii": [
                "clostridium beijerinckii",
                "c. beijerinckii",
                "c beijerinckii"
            ],

            "bacillus licheniformis": [
                "bacillus licheniformis",
                "b. licheniformis",
                "b licheniformis"
            ],

            "bacillus megaterium": [
                "bacillus megaterium",
                "b. megaterium",
                "b megaterium"
            ],

            "pseudomonas fluorescens": [
                "pseudomonas fluorescens",
                "p. fluorescens",
                "p fluorescens"
            ],

            "yarrowia lipolytica": [
                "yarrowia lipolytica",
                "y. lipolytica",
                "y lipolytica"
            ],

            "rhodosporidium toruloides": [
                "rhodosporidium toruloides",
                "r. toruloides",
                "r toruloides"
            ]
        }

        return aliases.get(
            m,
            [
                m
            ]
        )

    def query_mentions_selected_microorganism(
        self,
        query
    ):

        q = query.lower()

        matched = []

        for microorganism in self.selected_microorganisms:

            for alias in self.microorganism_keywords(
                microorganism
            ):

                if alias.lower() in q:

                    if microorganism not in matched:

                        matched.append(
                            microorganism
                        )

                    break

        return matched

    def query_is_general_selected_microorganism_question(
        self,
        query
    ):

        q = query.lower()

        phrases = [

            "selected microorganisms",

            "these microorganisms",

            "those microorganisms",

            "all microorganisms",

            "compare them",

            "compare these",

            "compare selected",

            "for each microorganism",

            "for all microorganisms",

            "for all selected",

            "all selected microorganisms",

            "these selected microorganisms"
        ]

        return any(
            phrase in q
            for phrase in phrases
        )

    def ollama_microorganism_router(
        self,
        query
    ):

        try:

            selected_microorganisms = self.selected_microorganisms

            if selected_microorganisms is None:

                selected_microorganisms = []

            if isinstance(
                selected_microorganisms,
                str
            ):

                selected_microorganisms = [
                    selected_microorganisms
                ]

            selected_microorganisms = [
                str(m).strip()
                for m in selected_microorganisms
                if str(m).strip()
            ]

            selected_microorganisms = [
                m
                for m in selected_microorganisms
                if m in self.available_microorganisms
            ]

            self.selected_microorganisms = selected_microorganisms

            if not selected_microorganisms:

                return {
                    "use_bacdive": False,
                    "matched_microorganisms": [],
                    "reason": "No microorganisms selected."
                }

            keyword_matches = self.query_mentions_selected_microorganism(
                query
            )

            if keyword_matches:

                return {
                    "use_bacdive": True,
                    "matched_microorganisms": keyword_matches,
                    "reason": "Question mentions selected microorganism alias."
                }

            if self.query_is_general_selected_microorganism_question(
                query
            ):

                return {
                    "use_bacdive": True,
                    "matched_microorganisms": list(
                        selected_microorganisms
                    ),
                    "reason": "Question refers to selected microorganisms generally."
                }

            model_name = (
                self.model_select.value
                if hasattr(
                    self,
                    "model_select"
                )
                and self.model_select.value
                else self.mem_model
            )

            if not hasattr(
                self,
                "microorganism_router"
            ):

                self.microorganism_router = MicroorganismRouter(

                    model_name=model_name,

                    temperature=0.0
                )

            self.microorganism_router.update_model(

                model_name=model_name,

                temperature=0.0
            )

            route = self.microorganism_router.route(

                query=query,

                selected_microorganisms=selected_microorganisms
            )

            if not isinstance(
                route,
                dict
            ):

                return {
                    "use_bacdive": False,
                    "matched_microorganisms": [],
                    "reason": "Microorganism router returned invalid output."
                }

            use_bacdive = bool(
                route.get(
                    "use_bacdive",
                    False
                )
            )

            matched = route.get(
                "matched_microorganisms",
                []
            )

            if matched is None:

                matched = []

            if isinstance(
                matched,
                str
            ):

                matched = [
                    matched
                ]

            valid_selected = []

            for candidate in matched:

                for selected in selected_microorganisms:

                    if (
                        str(candidate).lower().strip()
                        == str(selected).lower().strip()
                    ):

                        if selected not in valid_selected:

                            valid_selected.append(
                                selected
                            )

            if (
                use_bacdive
                and not valid_selected
                and self.query_is_general_selected_microorganism_question(
                    query
                )
            ):

                valid_selected = list(
                    selected_microorganisms
                )

            if use_bacdive and not valid_selected:

                valid_selected = self.query_mentions_selected_microorganism(
                    query
                )

            if use_bacdive and not valid_selected:

                return {
                    "use_bacdive": False,
                    "matched_microorganisms": [],
                    "reason": (
                        "Router approved BacDive but no selected "
                        "microorganism could be matched."
                    )
                }

            return {
                "use_bacdive": use_bacdive,
                "matched_microorganisms": valid_selected,
                "reason": route.get(
                    "reason",
                    ""
                )
            }

        except Exception as ex:

            print(
                f"[MICROORGANISM ROUTER ERROR] {ex}"
            )

            try:

                keyword_matches = self.query_mentions_selected_microorganism(
                    query
                )

            except Exception:

                keyword_matches = []

            if keyword_matches:

                return {
                    "use_bacdive": True,
                    "matched_microorganisms": keyword_matches,
                    "reason": "Fallback keyword match."
                }

            return {
                "use_bacdive": False,
                "matched_microorganisms": [],
                "reason": str(
                    ex
                )
            }

    def route_bacdive_with_ollama(
        self,
        query
    ):

        return self.ollama_microorganism_router(
            query
        )

    def answer_microorganism_question(
        self,
        query,
        route=None
    ):

        try:

            if route is None:

                route = self.ollama_microorganism_router(
                    query
                )

            print(
                "\n========== MICROORGANISM ROUTE =========="
            )

            print(
                json.dumps(
                    route,
                    indent=2,
                    default=str
                )
            )

            if not route.get(
                "use_bacdive",
                False
            ):

                return {
                    "used": False,
                    "message": self.no_microorganism_info_message,
                    "route": route
                }

            matched = route.get(
                "matched_microorganisms",
                []
            )

            if not matched:

                return {
                    "used": False,
                    "message": self.no_microorganism_info_message,
                    "route": route
                }

            outputs = {}

            for microorganism in matched:

                try:

                    try:

                        result = self.bacdive_agent.run(

                            query=query,

                            microorganism=microorganism
                        )

                    except TypeError:

                        bacdive_query = f"""
User question:
{query}

Selected microorganism:
{microorganism}

Instruction:
Answer only using BacDive evidence returned for this selected microorganism.
If BacDive evidence is missing, say that clearly.
"""

                        result = self.bacdive_agent.run(
                            bacdive_query
                        )

                    outputs[
                        microorganism
                    ] = result

                except Exception as ex:

                    outputs[
                        microorganism
                    ] = {
                        "error": str(
                            ex
                        )
                    }

            return {
                "used": True,
                "route": route,
                "results": outputs
            }

        except Exception as ex:

            return {
                "used": False,
                "message": self.no_microorganism_info_message,
                "route": {
                    "use_bacdive": False,
                    "matched_microorganisms": [],
                    "reason": str(
                        ex
                    )
                }
            }

    def run_bacdive_if_relevant(
        self,
        query
    ):

        return self.answer_microorganism_question(
            query
        )

    async def handle_microorganism_question(
        self,
        prompt
    ):

        try:

            if not hasattr(
                self,
                "use_bacdive"
            ):

                return {
                    "used": False,
                    "text": "",
                    "result": None
                }

            if not self.use_bacdive.value:

                return {
                    "used": False,
                    "text": "",
                    "result": None
                }

            if not self.selected_microorganisms:

                return {
                    "used": False,
                    "text": "",
                    "result": None
                }

            route = await asyncio.to_thread(
                self.ollama_microorganism_router,
                prompt
            )

            result = await asyncio.to_thread(
                self.answer_microorganism_question,
                prompt,
                route
            )

            if result.get(
                "used",
                False
            ):

                text = self.format_bacdive_only_output(
                    result
                )

                return {
                    "used": True,
                    "text": text,
                    "result": result,
                    "route": route
                }

            return {
                "used": False,
                "text": result.get(
                    "message",
                    self.no_microorganism_info_message
                ),
                "result": result,
                "route": route
            }

        except Exception as ex:

            return {
                "used": False,
                "text": f"Microorganism handler error: {ex}",
                "result": {
                    "error": str(
                        ex
                    )
                },
                "route": {
                    "use_bacdive": False,
                    "matched_microorganisms": [],
                    "reason": str(
                        ex
                    )
                }
            }

    # =====================================================
    # MULTI-AGENT BACDIVE ROUTE HELPER
    # =====================================================
    def get_bacdive_route_for_multi_agent(
        self,
        prompt
    ):

        if (
            not hasattr(
                self,
                "use_bacdive"
            )
            or not self.use_bacdive.value
        ):

            return {
                "use_bacdive": False,
                "matched_microorganisms": [],
                "reason": "BacDive switch is off."
            }

        if not self.selected_microorganisms:

            return {
                "use_bacdive": False,
                "matched_microorganisms": [],
                "reason": "No microorganisms selected."
            }

        return self.ollama_microorganism_router(
            prompt
        )

    # =====================================================
    # UI
    # =====================================================
    def content_(self):
        """Renders the HTML/CSS contents of the LLM Dataset page."""

        with ui.row().classes(
            "w-full no-wrap"
        ):

            # =================================================
            # LEFT SIDEBAR
            # =================================================
            with ui.column().classes(
                "w-[390px] p-4 gap-3 bg-slate-100"
            ):

                ui.label(
                    "Industrial AI Copilot"
                ).classes(
                    "text-h5 font-bold"
                )

                ui.label(
                    "Multi-Agent Fermentation Intelligence System"
                ).classes(
                    "text-slate-500 text-sm"
                )

                ui.separator()

                # =============================================
                # DATASETS
                # =============================================
                ui.label(
                    "Datasets"
                ).classes(
                    "font-bold"
                )

                with ui.row().classes(
                    "w-full items-center gap-2"
                ):

                    self.file_select = ui.select(
                        [],
                        label="Loaded Files"
                    ).classes(
                        "flex-1"
                    )

                    ui.button(
                        "REFRESH",
                        icon="refresh",
                        on_click=self.refresh_loaded_files
                    )

                ui.button(
                    "LOAD DATASET",
                    icon="dataset",
                    color="primary",
                    on_click=self.use_selected_file
                ).classes(
                    "w-full"
                )

                ui.separator()

                # =============================================
                # PROTOCOLS
                # =============================================
                ui.label(
                    "Protocols"
                ).classes(
                    "font-bold"
                )

                with ui.row().classes(
                    "w-full items-center gap-2"
                ):

                    self.protocol_select = ui.select(
                        [],
                        label="Saved Protocols"
                    ).classes(
                        "flex-1"
                    )

                    ui.button(
                        "REFRESH",
                        icon="refresh",
                        on_click=self.refresh_protocols
                    )

                ui.button(
                    "LOAD PROTOCOL",
                    icon="description",
                    color="primary",
                    on_click=self.use_selected_protocol
                ).classes(
                    "w-full"
                )

                ui.separator()

                # =============================================
                # MICROORGANISMS
                # =============================================
                ui.label(
                    "Microorganisms"
                ).classes(
                    "font-bold"
                )

                self.microorganism_select = ui.select(

                    self.available_microorganisms,

                    label="Select Microorganisms",

                    multiple=True,

                    value=self.selected_microorganisms

                ).classes(
                    "w-full"
                )

                self.microorganism_select.on(
                    "update:model-value",
                    self.on_microorganisms_changes
                )

                ui.label(
                    (
                        "Select one or more microorganisms. "
                        "In multi-agent mode, BacDive will be included "
                        "together with the other src.agents when the question "
                        "is relevant to the selected microorganisms."
                    )
                ).classes(
                    "text-xs text-slate-500"
                )

                ui.separator()

                # =============================================
                # CONTEXT STATUS
                # =============================================
                self.info_label = ui.label(
                    "No context loaded"
                ).classes(
                    "text-sm text-slate-700"
                )

                ui.separator()

                # =============================================
                # AGENT TOGGLES
                # =============================================
                ui.label(
                    "Agent Controls"
                ).classes(
                    "font-bold"
                )

                self.use_dataset = ui.switch("Use Dataset", value=True)

                self.use_protocol = ui.switch("Use Protocol", value=True)
                
                self.use_crossref = ui.switch("Use Crossref", value=True)
                
                self.use_bacdive = ui.switch("Use BacDive", value=True)
                
                self.use_literature = ui.switch("Use Literature", value=True)
                
                self.use_internet = ui.switch("Use Internet", value=True)

                ui.separator()

                # =============================================
                # MODEL
                # =============================================
                self.model_select = ui.select(

                    [
                        "llama3:latest",
                        "mistral:latest",
                        "phi3:latest"
                    ],

                    value=self.mem_model,

                    label="Model"

                ).classes(
                    "w-full"
                )

                ui.label(
                    "Temperature"
                ).classes(
                    "font-bold"
                )

                self.temperature = ui.slider(

                    min=0,

                    max=1,

                    step=0.1,

                    value=self.mem_temp

                ).classes(
                    "w-full"
                )

                ui.separator()

                # =============================================
                # CLEAR CHAT
                # =============================================
                ui.button(

                    "CLEAR CHAT",

                    icon="delete",

                    color="negative",

                    on_click=self.clear_chat

                ).classes(
                    "w-full"
                )

            # =================================================
            # MAIN CHAT AREA
            # =================================================
            with ui.column().classes(
                "flex-1 p-4 gap-3"
            ):

                # =============================================
                # CHAT WINDOW
                # =============================================
                self.chat_box = ui.column().classes(

                    "w-full h-[720px] overflow-auto "
                    "bg-white p-4 rounded shadow gap-3"

                )

                # =============================================
                # USER INPUT
                # =============================================
                with ui.row().classes(
                    "w-full items-end gap-3"
                ):

                    self.user_input = ui.textarea(

                        placeholder=(
                            "Ask about fermentation datasets, "
                            "oxygen limitation, metadata, "
                            "literature, BacDive microorganisms, "
                            "growth conditions, physiology, anomalies..."
                        )

                    ).classes(
                        "flex-1"
                    )

                    self.send_btn = ui.button(

                        "SEND",

                        icon="send",

                        color="primary",

                        on_click=self.send_message

                    )

                    ui.button(

                        "RUN MULTI-AGENT",

                        icon="smart_toy",

                        color="secondary",

                        on_click=self.run_multi_agent_pipeline

                    )

        # =====================================================
        # INITIAL REFRESH
        # =====================================================
        self.refresh_loaded_files()

        self.refresh_protocols()

        # =====================================================
        # RESTORE MICROORGANISMS FROM STORAGE
        # =====================================================
        saved_microorganisms = self.storage.get(
            "selected_microorganisms",
            self.selected_microorganisms
        )

        if saved_microorganisms:

            if isinstance(
                saved_microorganisms,
                str
            ):

                saved_microorganisms = [
                    saved_microorganisms
                ]

            saved_microorganisms = [
                m
                for m in saved_microorganisms
                if m in self.available_microorganisms
            ]

            self.selected_microorganisms = saved_microorganisms

            try:

                self.microorganism_select.value = saved_microorganisms

                self.microorganism_select.update()

            except Exception as ex:

                print(
                    f"[MICROORGANISM RESTORE ERROR] {ex}"
                )

        # =====================================================
        # AUTO LOAD LAST DATASET
        # =====================================================
        last = self.storage.get(
            "last_loaded_file"
        )

        if (
            last
            and hasattr(
                self,
                "file_select"
            )
            and last in self.file_select.options
        ):

            self.file_select.value = last

            self.file_select.update()

            cached = self.storage.get(
                "parsed_cache",
                {}
            ).get(
                last
            )

            if cached:

                self.df = pd.DataFrame(
                    cached
                )

                self.current_df = self.df

                self.storage[
                    "parsed_df_json"
                ] = cached

        elif (
            hasattr(
                self,
                "file_select"
            )
            and self.file_select.value
        ):

            self.use_selected_file()

        # =====================================================
        # RESTORE PROTOCOL
        # =====================================================
        self.use_selected_protocol()

        # =====================================================
        # REFRESH STATUS
        # =====================================================
        self.refresh_info()

    # =====================================================
    # INFO
    # =====================================================
    def refresh_info(self):

        parts = []

        if self.df is not None:

            parts.append(
                f"Dataset: {len(self.df)}x{len(self.df.columns)}"
            )

        if self.protocol_data:

            parts.append(
                "Protocol Loaded"
            )

        if self.selected_microorganisms:

            parts.append(
                "Microorganisms: "
                + ", ".join(
                    self.selected_microorganisms
                )
            )

        if not parts:

            parts.append(
                "No context loaded"
            )

        if hasattr(
            self,
            "info_label"
        ):

            self.info_label.text = " | ".join(
                parts
            )

    # =====================================================
    # CHAT
    # =====================================================
    def clear_chat(self):

        if hasattr(
            self,
            "chat_box"
        ):

            self.chat_box.clear()

    def add_message(
        self,
        role,
        text
    ):

        if not hasattr(
            self,
            "chat_box"
        ):

            print(
                f"[{role}] {text}"
            )

            return

        with self.chat_box:

            with ui.card().classes(
                "w-full"
            ):

                ui.label(
                    role
                ).classes(
                    "text-bold"
                )

                ui.label(
                    str(
                        text
                    )
                ).classes(
                    "whitespace-pre-wrap"
                )

    # =====================================================
    # BACDIVE-ONLY FORMATTER
    # =====================================================
    def format_bacdive_only_output(
        self,
        result
    ):

        if result is None:

            return "No BacDive output returned."

        if isinstance(
            result,
            str
        ):

            return result

        if not isinstance(
            result,
            dict
        ):

            return str(
                result
            )

        if "error" in result:

            return f"BACDIVE ERROR:\n{result['error']}"

        if (
            "results" in result
            and isinstance(
                result["results"],
                dict
            )
        ):

            blocks = []

            for microorganism, sub_result in result[
                "results"
            ].items():

                blocks.append(
                    f"# BacDive Evidence for {microorganism}"
                )

                blocks.append(
                    self.format_bacdive_only_output(
                        sub_result
                    )
                )

            return "\n\n".join(
                blocks
            )

        if "final_summary" in result:

            return str(
                result["final_summary"]
            )

        if "assessment" in result:

            return str(
                result["assessment"]
            )

        if "answer" in result:

            return str(
                result["answer"]
            )

        if "message" in result:

            return str(
                result["message"]
            )

        if "summary" in result:

            return (
                "# BacDive Summary\n\n"
                + json.dumps(
                    result["summary"],
                    indent=2,
                    default=str
                )
            )

        return json.dumps(
            result,
            indent=2,
            default=str
        )

    # =====================================================
    # FORMAT AGENT OUTPUT
    # =====================================================
    def format_agent_output(
        self,
        agent_name,
        result
    ):

        if str(
            agent_name
        ).lower() in [
            "bacdive",
            "bacdive_explorer",
            "bacdiveexploreragent"
        ]:

            return self.format_bacdive_only_output(
                result
            )

        if result is None:

            return "No output returned."

        if isinstance(
            result,
            str
        ):

            return result

        if not isinstance(
            result,
            dict
        ):

            return str(
                result
            )

        txt = []

        if "error" in result:

            txt.append(
                f"ERROR:\n{result['error']}"
            )

        if "message" in result:

            txt.append(
                str(
                    result["message"]
                )
            )

        if "summary" in result:

            txt.append(
                "SUMMARY"
            )

            txt.append(
                json.dumps(
                    result["summary"],
                    indent=2,
                    default=str
                )
            )

        if "structured" in result:

            txt.append(
                "\nSTRUCTURED"
            )

            txt.append(
                json.dumps(
                    result["structured"],
                    indent=2,
                    default=str
                )
            )

        if "papers" in result:

            txt.append(
                "\nPAPERS"
            )

            for p in result["papers"]:

                title = p.get(
                    "title",
                    "No title"
                )

                url = p.get(
                    "url",
                    ""
                )

                txt.append(
                    f"- {title}"
                )

                if url:

                    txt.append(
                        f"  {url}"
                    )

        if "results" in result:

            if isinstance(
                result["results"],
                dict
            ):

                for name, sub_result in result[
                    "results"
                ].items():

                    txt.append(
                        f"\nRESULT FOR {name}"
                    )

                    txt.append(
                        self.format_agent_output(
                            agent_name,
                            sub_result
                        )
                    )

            else:

                txt.append(
                    "\nRESULTS"
                )

                txt.append(
                    json.dumps(
                        result["results"],
                        indent=2,
                        default=str
                    )
                )

        if "assessment" in result:

            txt.append(
                "\nASSESSMENT"
            )

            txt.append(
                str(
                    result["assessment"]
                )
            )

        if "final_summary" in result:

            txt.append(
                "\nFINAL SUMMARY"
            )

            txt.append(
                str(
                    result["final_summary"]
                )
            )

        if not txt:

            txt.append(
                json.dumps(
                    result,
                    indent=2,
                    default=str
                )
            )

        return "\n".join(
            txt
        )

    def add_crossref_cards(
        self,
        refs
    ):

        if not hasattr(
            self,
            "chat_box"
        ):

            return

        with self.chat_box:

            for item in refs:

                with ui.card().classes(
                    "w-full"
                ):

                    ui.label(
                        item["title"]
                    ).classes(
                        "text-bold"
                    )

                    ui.label(
                        f'{item["authors"]} | {item["journal"]} | {item["year"]}'
                    ).classes(
                        "text-sm"
                    )

                    if item["doi_url"]:

                        ui.link(
                            item["doi_url"],
                            item["doi_url"],
                            new_tab=True
                        )

    # =====================================================
    # SEND
    # =====================================================
    async def send_message(self):

        prompt = self.user_input.value.strip()

        if not prompt:

            return

        self.add_message(
            "User",
            prompt
        )

        self.user_input.value = ""

        self.send_btn.disable()

        try:

            self.save_memory()

            self.router_llm = OllamaLLM(

                model=self.model_select.value,

                temperature=0.0
            )

            # =============================================
            # NORMAL SEND:
            # This can use BacDive as extra context,
            # but it does not replace the general assistant unless
            # the question is clearly BacDive/microorganism-specific.
            # =============================================
            bacdive_context = ""

            if (
                hasattr(
                    self,
                    "use_bacdive"
                )
                and self.use_bacdive.value
            ):

                micro_result = await self.handle_microorganism_question(
                    prompt
                )

                if micro_result.get(
                    "used",
                    False
                ):

                    bacdive_context = micro_result.get(
                        "text",
                        ""
                    )

            if (
                hasattr(
                    self,
                    "use_crossref"
                )
                and self.use_crossref.value
            ):

                refs = self.crossref_fetch(
                    prompt
                )

                if refs:

                    self.add_crossref_cards(
                        refs
                    )

            final_prompt = self.build_context(
                prompt,
                bacdive_context=bacdive_context
            )

            answer = await asyncio.to_thread(
                self.query_ollama,
                final_prompt
            )

            self.add_message(
                "Assistant",
                answer
            )

        except Exception as e:

            self.add_message(
                "Assistant",
                f"Error: {str(e)}"
            )

        finally:

            self.send_btn.enable()

    # =====================================================
    # MULTI AGENT PIPELINE
    # =====================================================
    async def run_multi_agent_pipeline(self):

        prompt = self.user_input.value.strip()

        if not prompt:

            ui.notify(
                "Enter a prompt",
                type="warning"
            )

            return

        self.add_message(
            "User",
            f"[MULTI-AGENT]\n{prompt}"
        )

        self.user_input.value = ""

        self.send_btn.disable()

        try:

            self.save_memory()

            # =============================================
            # CRITICAL FIX:
            # Do NOT stop at BacDive.
            # Determine whether BacDive should be included,
            # then run the full orchestrator.
            # =============================================
            bacdive_route = await asyncio.to_thread(
                self.get_bacdive_route_for_multi_agent,
                prompt
            )

            run_bacdive = (
                hasattr(self, "use_bacdive")
                and self.use_bacdive.value
                
            )

            print(
                "\n========== MULTI-AGENT BACDIVE ROUTE =========="
            )

            print(
                json.dumps(
                    bacdive_route,
                    indent=2,
                    default=str
                )
            )

            orchestrator = AgentOrchestrator(

                model_name=self.model_select.value,

                temperature=self.temperature.value
            )

            # =============================================
            # FULL MULTI-AGENT RUN
            # This should execute:
            # - data analyst
            # - internet explorer
            # - crossref explorer
            # - literature reviewer
            # - bacdive explorer when run_bacdive=True
            # - metadata analyst
            # - master summarizer
            # =============================================
            try:

                results = await asyncio.to_thread(
                    orchestrator.run,
                
                    query=prompt,
                
                    dataframe=(
                        self.df
                        if hasattr(self, "use_dataset") and self.use_dataset.value
                        else None
                    ),
                
                    metadata=(
                        self.storage.get("metadata", {})
                        if hasattr(self, "use_protocol") and self.use_protocol.value
                        else None
                    ),
                
                    protocol=(
                        self.protocol_data
                        if hasattr(self, "use_protocol") and self.use_protocol.value
                        else None
                    ),
                
                    selected_microorganisms=self.selected_microorganisms,
                
                    use_dataset=(
                        hasattr(self, "use_dataset") and self.use_dataset.value
                    ),
                
                    use_protocol=(
                        hasattr(self, "use_protocol") and self.use_protocol.value
                    ),
                
                    use_crossref=(
                        hasattr(self, "use_crossref") and self.use_crossref.value
                    ),
                
                    use_internet=(
                        hasattr(self, "use_internet") and self.use_internet.value
                    ),
                    
                    use_literature=(
                        hasattr(self, "use_literature") and self.use_literature.value
                    ),
                
                    run_bacdive=(
                        hasattr(self, "use_bacdive")
                        and self.use_bacdive.value
                    ),
                
                    bacdive_result=None,
                
                    use_all_agents=False
                )

            except TypeError:

                # =============================================
                # BACKWARD COMPATIBILITY:
                # If your AgentOrchestrator.run() does not yet
                # accept run_bacdive/bacdive_result, update it.
                # This fallback prevents total crash but BacDive
                # may not be included.
                # =============================================
                results = await asyncio.to_thread(

                    orchestrator.run,

                    query=prompt,

                    dataframe=self.df,

                    metadata=self.storage.get(
                        "metadata",
                        {}
                    ),

                    protocol=self.protocol_data
                )

            if not isinstance(
                results,
                dict
            ):

                self.add_message(
                    "MULTI-AGENT",
                    str(
                        results
                    )
                )

                return

            # =============================================
            # Prefer master summarizer final answer if present.
            # =============================================
            master_keys = [
                "master_summarizer",
                "master_summary",
                "MASTER_SUMMARIZER",
                "MASTER_SUMMARY",
                "summary_agent"
            ]

            displayed_master = False

            for key in master_keys:

                if key in results:

                    formatted = self.format_agent_output(
                        key,
                        results[key]
                    )

                    self.add_message(
                        "MASTER SUMMARIZER",
                        formatted
                    )

                    displayed_master = True

                    break

            # =============================================
            # Also show individual src.agents so you can verify
            # that all 7 src.agents actually ran.
            # =============================================
            for agent_name, result in results.items():

                if agent_name in master_keys:

                    continue

                formatted = self.format_agent_output(
                    agent_name,
                    result
                )

                self.add_message(
                    str(
                        agent_name
                    ).upper(),
                    formatted
                )

            if not displayed_master:

                self.add_message(
                    "SYSTEM",
                    (
                        "Multi-agent run completed, but no master "
                        "summarizer key was found in the orchestrator output."
                    )
                )

        except Exception as e:

            self.add_message(
                "SYSTEM ERROR",
                str(e)
            )

        finally:

            self.send_btn.enable()

    # =====================================================
    # CONTEXT
    # =====================================================
    def build_context(
        self,
        user_prompt,
        bacdive_context=""
    ):

        blocks = []

        if (
            hasattr(
                self,
                "use_dataset"
            )
            and self.use_dataset.value
            and self.df is not None
        ):

            blocks.append(
                "DATASET COLUMNS:\n"
                + ", ".join(
                    self.df.columns.astype(
                        str
                    )
                )
            )

            blocks.append(
                f"ROWS: {len(self.df)}"
            )

        if (
            hasattr(
                self,
                "use_protocol"
            )
            and self.use_protocol.value
            and self.protocol_data
        ):

            blocks.append(
                "PROTOCOL CONTEXT:\n"
                + json.dumps(
                    self.protocol_data,
                    indent=2,
                    default=str
                )
            )

        if self.selected_microorganisms:

            blocks.append(
                "SELECTED MICROORGANISMS:\n"
                + "\n".join(
                    [
                        f"- {m}"
                        for m in self.selected_microorganisms
                    ]
                )
            )

        if bacdive_context:

            blocks.append(
                "BACDIVE EVIDENCE CONTEXT:\n"
                + str(
                    bacdive_context
                )
            )

        if (
            hasattr(
                self,
                "use_crossref"
            )
            and self.use_crossref.value
        ):

            blocks.append(
                "LITERATURE CONTEXT:\n"
                + self.crossref_search(
                    user_prompt
                )
            )

        blocks.append(f"""
USER QUESTION:
{user_prompt}

RULES:
1. Use supplied evidence only.
2. If uncertain say so.
3. Prefer industrial fermentation answers.
4. Use literature carefully.
5. Never hallucinate data.
6. Explain references when shown.
7. If BacDive evidence is missing or weak, explicitly say so.
8. Do not invent microorganism traits.
9. If BacDive evidence is supplied, treat it as evidence, not as a complete organism profile.
""")

        return "\n\n".join(
            blocks
        )

    # =====================================================
    # OLLAMA
    # =====================================================
    def query_ollama(
        self,
        prompt
    ):

        model = (
            self.model_select.value
            if hasattr(
                self,
                "model_select"
            )
            else self.mem_model
        )

        temperature = (
            self.temperature.value
            if hasattr(
                self,
                "temperature"
            )
            else self.mem_temp
        )

        response = ollama.chat(

            model=model,

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            options={
                "temperature": temperature
            }
        )

        return response[
            "message"
        ][
            "content"
        ]

    # =====================================================
    # CROSSREF
    # =====================================================
    def build_crossref_query(
        self,
        prompt
    ):

        p = prompt.lower()

        if "oxygen" in p:

            return "dissolved oxygen fermentation"

        if (
            "fed" in p
            and "coli" in p
        ):

            return "fed-batch Escherichia coli fermentation"

        if "recombinant" in p:

            return "recombinant protein fermentation"

        if "bacillus" in p:

            return "Bacillus subtilis fermentation"

        if "yeast" in p:

            return "yeast fermentation"

        if "ph" in p:

            return "pH control fermentation"

        words = re.findall(
            r"[a-z0-9]+",
            p
        )

        return " ".join(
            words[:8]
        )

    def crossref_fetch(
        self,
        user_prompt
    ):

        try:

            query = self.build_crossref_query(
                user_prompt
            )

            payload = {

                "query": query,

                "rows": 5,

                "sort": "relevance",

                "order": "desc"
            }

            if self.DEBUG_CROSSREF:

                print(
                    "\n========== CROSSREF REQUEST =========="
                )

                print(
                    "URL: https://api.crossref.org/works"
                )

                print(
                    "Payload:",
                    payload
                )

            start = time.time()

            r = requests.get(

                "https://api.crossref.org/works",

                params=payload,

                timeout=8
            )

            if self.DEBUG_CROSSREF:

                print(
                    "\n========== CROSSREF RESPONSE =========="
                )

                print(
                    "Status:",
                    r.status_code
                )

                print(
                    "Time:",
                    round(
                        time.time() - start,
                        2
                    ),
                    "sec"
                )

                print(
                    "Preview:"
                )

                print(
                    r.text[:2500]
                )

            items = r.json()[
                "message"
            ][
                "items"
            ]

            refs = []

            for item in items:

                title = html.unescape(
                    item.get(
                        "title",
                        [
                            ""
                        ]
                    )[0]
                )

                doi = item.get(
                    "DOI",
                    ""
                )

                doi_url = (
                    f"https://doi.org/{doi}"
                    if doi
                    else ""
                )

                year = ""

                try:

                    year = str(
                        item["published"][
                            "date-parts"
                        ][0][0]
                    )

                except Exception:

                    pass

                journal = item.get(
                    "container-title",
                    [
                        ""
                    ]
                )[0]

                authors = ""

                try:

                    auth = item.get(
                        "author",
                        []
                    )[:3]

                    names = []

                    for a in auth:

                        names.append(
                            (
                                a.get(
                                    "given",
                                    ""
                                )
                                + " "
                                + a.get(
                                    "family",
                                    ""
                                )
                            ).strip()
                        )

                    authors = ", ".join(
                        names
                    )

                except Exception:

                    pass

                if self.DEBUG_CROSSREF:

                    print(
                        "\nParsed Reference:"
                    )

                    print(
                        "Title:",
                        title
                    )

                    print(
                        "DOI:",
                        doi
                    )

                    print(
                        "Year:",
                        year
                    )

                refs.append(
                    {
                        "title": title,
                        "authors": authors,
                        "journal": journal,
                        "year": year,
                        "doi_url": doi_url,
                    }
                )

            return refs

        except Exception as e:

            print(
                "Crossref ERROR:",
                str(e)
            )

            return []

    def crossref_search(
        self,
        user_prompt
    ):

        refs = self.crossref_fetch(
            user_prompt
        )

        if not refs:

            return "No literature found."

        rows = []

        for r in refs:

            rows.append(
                f'{r["title"]} | {r["journal"]} | '
                f'{r["year"]} | {r["doi_url"]}'
            )

        return "\n".join(
            rows
        )