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
import traceback
from datetime import datetime

import src.utils.theme as theme
from src.utils.logging_config import get_logger
from src.utils.paths import ensure_dirs
from src.agents.agent_orchestrator import AgentOrchestrator
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

        self.selected_datasets = []
        self.selected_metadata_list = []

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
        datasets_mem = []
        for ds in getattr(self, "selected_datasets", []):
            fname = ds.get("file_select").value if ds.get("file_select") else ds.get("filename")
            if fname:
                filter_list = []
                for tier in ds.get("filter_tiers", []):
                    col = tier.get("col_select").value
                    vals = tier.get("val_select").value
                    if col:
                        filter_list.append({"column": col, "values": vals})
                datasets_mem.append({"filename": fname, "filters": filter_list})

        metadata_mem = []
        for md in getattr(self, "selected_metadata_list", []):
            fname = md.get("file_select").value if md.get("file_select") else md.get("filename")
            if fname:
                metadata_mem.append({
                    "filename": fname,
                    "investigation": md.get("investigation_select").value,
                    "study": md.get("study_select").value,
                    "unit": md.get("unit_select").value,
                    "sample": md.get("sample_select").value,
                    "assay": md.get("assay_select").value
                })

        self.storage["llm_memory"] = {
            "selected_datasets_multi": datasets_mem,
            "selected_metadata_multi": metadata_mem,
            "model": (
                self.model_select.value
                if hasattr(self, "model_select")
                else self.mem_model
            ),
            "temperature": (
                self.temperature.value
                if hasattr(self, "temperature")
                else self.mem_temp
            ),
            "selected_microorganisms": getattr(self, "selected_microorganisms", []),
            "use_dataset": self.use_dataset.value if hasattr(self, "use_dataset") else True,
            "use_protocol": self.use_protocol.value if hasattr(self, "use_protocol") else True,
            "use_crossref": self.use_crossref.value if hasattr(self, "use_crossref") else True,
            "use_bacdive": self.use_bacdive.value if hasattr(self, "use_bacdive") else True,
            "use_internet": self.use_internet.value if hasattr(self, "use_internet") else True,
        }

        self.storage["selected_microorganisms"] = getattr(self, "selected_microorganisms", [])

    def load_memory(self):
        """Loads previous GUI selection states from session storage cache."""
        mem = self.storage.get("llm_memory", {})
        self.mem_model = mem.get("model", "llama3:latest")
        self.mem_temp = mem.get("temperature", 0.2)

        saved_microorganisms = mem.get(
            "selected_microorganisms",
            self.storage.get("selected_microorganisms", [])
        )

        if saved_microorganisms is None:
            saved_microorganisms = []

        if isinstance(saved_microorganisms, str):
            saved_microorganisms = [saved_microorganisms]

        self.selected_microorganisms = [
            m
            for m in saved_microorganisms
            if m in self.available_microorganisms
        ]

    def filter_metadata_hierarchy(self, data, inv, study, unit, sample, assay):
        if not data or not isinstance(data, dict):
            return {}
        
        filtered = {
            "File name": data.get("File name", ""),
            "Updated": data.get("Updated", ""),
            "Investigations": {}
        }
        
        invs = data.get("Investigations", {})
        if not inv:
            return data
        
        inv_data = invs.get(inv)
        if not inv_data:
            return filtered
            
        inv_copy = {k: v for k, v in inv_data.items() if k != "Studies"}
        inv_copy["Studies"] = {}
        filtered["Investigations"][inv] = inv_copy
        
        studies = inv_data.get("Studies", {})
        if not study:
            inv_copy["Studies"] = studies
            return filtered
            
        study_data = studies.get(study)
        if not study_data:
            return filtered
            
        study_copy = {k: v for k, v in study_data.items() if k != "observationUnits"}
        study_copy["observationUnits"] = {}
        inv_copy["Studies"][study] = study_copy
        
        units = study_data.get("observationUnits", {})
        if not unit:
            study_copy["observationUnits"] = units
            return filtered
            
        unit_data = units.get(unit)
        if not unit_data:
            return filtered
            
        unit_copy = {k: v for k, v in unit_data.items() if k != "Samples"}
        unit_copy["Samples"] = {}
        study_copy["observationUnits"][unit] = unit_copy
        
        samples = unit_data.get("Samples", {})
        if not sample:
            unit_copy["Samples"] = samples
            return filtered
            
        sample_data = samples.get(sample)
        if not sample_data:
            return filtered
            
        sample_copy = {k: v for k, v in sample_data.items() if k != "Assays"}
        sample_copy["Assays"] = {}
        unit_copy["Samples"][sample] = sample_copy
        
        assays = sample_data.get("Assays", {})
        if not assay:
            sample_copy["Assays"] = assays
            return filtered
            
        assay_data = assays.get(assay)
        if assay_data:
            sample_copy["Assays"][assay] = assay_data
            
        return filtered

    def add_dataset_row(self, initial_val=None, initial_filters=None):
        if not hasattr(self, "datasets_container") or not self.datasets_container:
            return

        with self.datasets_container:
            row_el = ui.card().classes("w-full p-4 border border-slate-200 rounded-lg bg-slate-50 relative gap-3")
            with row_el:
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label("Dataset Configuration").classes("text-sm font-bold text-slate-700")
                    ui.button(
                        icon="delete",
                        on_click=lambda: remove_dataset()
                    ).props("flat round dense color=negative").tooltip("Remove dataset")
                    
                file_select = ui.select(
                    self.get_available_files(),
                    label="Dataset File",
                    with_input=True
                ).classes("w-full")
                
                with ui.row().classes("items-center gap-2 mt-1"):
                    add_tier_btn = ui.button(
                        icon="add",
                    ).props("round color=primary dense").tooltip("Add filtering tier")
                    ui.label("Add a Filtering Tier").classes("text-xs font-bold text-slate-500 uppercase tracking-wider")
                    
                filter_container = ui.column().classes("w-full gap-2 mt-1")
                
            item = {
                "row_element": row_el,
                "file_select": file_select,
                "filter_tiers": [],
                "df": None,
                "filename": ""
            }
            self.selected_datasets.append(item)
            
            def remove_dataset():
                if item in self.selected_datasets:
                    self.selected_datasets.remove(item)
                row_el.delete()
                self.save_memory()
                self.refresh_info()
                
            def on_file_change(e):
                val = file_select.value
                item["filename"] = val or ""
                if val:
                    cached = self.get_cache().get(val)
                    if cached:
                        item["df"] = pd.DataFrame(cached)
                    else:
                        item["df"] = None
                else:
                    item["df"] = None
                    
                item["filter_tiers"].clear()
                filter_container.clear()
                self.save_memory()
                self.refresh_info()
                
            file_select.on_value_change(on_file_change)
            
            def add_tier_click():
                self.add_filter_tier_to_item(item, filter_container)
                
            add_tier_btn.on_click(add_tier_click)
            
            if initial_val:
                file_select.value = initial_val
                cached = self.get_cache().get(initial_val)
                if cached:
                    item["df"] = pd.DataFrame(cached)
                if initial_filters:
                    for f in initial_filters:
                        self.add_filter_tier_to_item(item, filter_container, f.get("column"), f.get("values"))

    def add_filter_tier_to_item(self, item, container, initial_col=None, initial_vals=None):
        df = item["df"]
        cols = list(df.columns) if df is not None else []
        tier_idx = len(item["filter_tiers"]) + 1
        
        with container:
            with ui.column().classes("w-full gap-1 border-t border-slate-100 pt-2") as tier_col:
                with ui.row().classes("w-full justify-between items-center"):
                    label_el = ui.label(f"Tier {tier_idx} Filtering").classes("text-xs font-bold text-slate-500 uppercase tracking-wider")
                    
                    def remove_this(t_col=tier_col, idx=tier_idx):
                        for t in list(item["filter_tiers"]):
                            if t["index"] == idx:
                                item["filter_tiers"].remove(t)
                                break
                        for i, t in enumerate(item["filter_tiers"]):
                            new_idx = i + 1
                            t["index"] = new_idx
                            t["label"].text = f"Tier {new_idx} Filtering"
                        t_col.delete()
                        self.save_memory()
                        
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
            item["filter_tiers"].append(tier_data)
            
            def update_vals():
                col = col_select.value
                if item["df"] is not None and col and col in item["df"].columns:
                    sorted_vals = sorted(
                        item["df"][col]
                        .dropna()
                        .astype(str)
                        .str.strip()
                        .unique()
                        .tolist()
                    )
                    val_select.options = sorted_vals
                else:
                    val_select.options = []
                val_select.value = []
                val_select.update()
                self.save_memory()
                
            col_select.on_value_change(lambda e: update_vals())
            val_select.on_value_change(lambda e: self.save_memory())
            
            if initial_col:
                col_select.value = initial_col
                # update val options before setting initial_vals
                if df is not None and initial_col in df.columns:
                    val_select.options = sorted(
                        df[initial_col]
                        .dropna()
                        .astype(str)
                        .str.strip()
                        .unique()
                        .tolist()
                    )
                if initial_vals:
                    val_select.value = initial_vals

    def add_metadata_row(self, initial_val=None, initial_inv=None, initial_study=None, initial_unit=None, initial_sample=None, initial_assay=None):
        if not hasattr(self, "metadata_container") or not self.metadata_container:
            return

        with self.metadata_container:
            row_el = ui.card().classes("w-full p-4 border border-slate-200 rounded-lg bg-slate-50 relative gap-3")
            with row_el:
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label("Metadata Configuration").classes("text-sm font-bold text-slate-700")
                    ui.button(
                        icon="delete",
                        color="negative",
                        on_click=lambda: remove_metadata()
                    ).props("flat round dense").tooltip("Remove metadata")
                    
                file_select = ui.select(
                    self.saved_protocol_names(),
                    label="Metadata File",
                    with_input=True
                ).classes("w-full")
                
                # Optimized layout row below file selector
                with ui.row().classes("w-full gap-2 mt-2 flex-wrap items-center"):
                    investigation_select = ui.select([], label="Investigation").classes("flex-1 min-w-[120px]")
                    study_select = ui.select([], label="Study").classes("flex-1 min-w-[120px]")
                    unit_select = ui.select([], label="Observation Unit").classes("flex-1 min-w-[120px]")
                    sample_select = ui.select([], label="Sample").classes("flex-1 min-w-[120px]")
                    assay_select = ui.select([], label="Assay").classes("flex-1 min-w-[120px]")
                    
            item = {
                "row_element": row_el,
                "file_select": file_select,
                "investigation_select": investigation_select,
                "study_select": study_select,
                "unit_select": unit_select,
                "sample_select": sample_select,
                "assay_select": assay_select,
                "metadata_data": None,
                "filename": ""
            }
            self.selected_metadata_list.append(item)
            
            def remove_metadata():
                if item in self.selected_metadata_list:
                    self.selected_metadata_list.remove(item)
                row_el.delete()
                self.save_memory()
                self.refresh_info()
                
            def on_file_change(e):
                val = file_select.value
                item["filename"] = val or ""
                if val:
                    cache = self.storage.get("loaded_json_cache", {})
                    cache_key = val
                    if cache_key not in cache and cache_key + ".json" in cache:
                        cache_key = cache_key + ".json"
                    elif cache_key not in cache and cache_key.endswith(".json") and cache_key[:-5] in cache:
                        cache_key = cache_key[:-5]
                        
                    if cache_key in cache:
                        item["metadata_data"] = cache[cache_key]
                    else:
                        path_proto = os.path.join(self.protocol_dir, val + ".json")
                        path_exp = os.path.join(str(ensure_dirs()["exports"]), val + ".json")
                        loaded = False
                        for path in [path_proto, path_exp]:
                            if os.path.exists(path):
                                try:
                                    with open(path, "r", encoding="utf-8") as fp:
                                        item["metadata_data"] = json.load(fp)
                                        loaded = True
                                        break
                                except Exception:
                                    pass
                        if not loaded:
                            item["metadata_data"] = None
                else:
                    item["metadata_data"] = None
                    
                investigation_select.value = None
                investigation_select.options = []
                study_select.value = None
                study_select.options = []
                unit_select.value = None
                unit_select.options = []
                sample_select.value = None
                sample_select.options = []
                assay_select.value = None
                assay_select.options = []
                
                if item["metadata_data"]:
                    invs = item["metadata_data"].get("Investigations", {})
                    investigation_select.options = list(invs.keys())
                    
                investigation_select.update()
                study_select.update()
                unit_select.update()
                sample_select.update()
                assay_select.update()
                self.save_memory()
                self.refresh_info()
                
            file_select.on_value_change(on_file_change)
            
            def on_investigation_change(e):
                inv = investigation_select.value
                study_select.value = None
                study_select.options = []
                unit_select.value = None
                unit_select.options = []
                sample_select.value = None
                sample_select.options = []
                assay_select.value = None
                assay_select.options = []
                
                if item["metadata_data"] and inv:
                    invs = item["metadata_data"].get("Investigations", {})
                    studies = invs.get(inv, {}).get("Studies", {})
                    study_select.options = list(studies.keys())
                    
                study_select.update()
                unit_select.update()
                sample_select.update()
                assay_select.update()
                self.save_memory()
                
            investigation_select.on_value_change(on_investigation_change)
            
            def on_study_change(e):
                inv = investigation_select.value
                study = study_select.value
                unit_select.value = None
                unit_select.options = []
                sample_select.value = None
                sample_select.options = []
                assay_select.value = None
                assay_select.options = []
                
                if item["metadata_data"] and inv and study:
                    invs = item["metadata_data"].get("Investigations", {})
                    studies = invs.get(inv, {}).get("Studies", {})
                    units = studies.get(study, {}).get("observationUnits", {})
                    unit_select.options = list(units.keys())
                    
                unit_select.update()
                sample_select.update()
                assay_select.update()
                self.save_memory()
                
            study_select.on_value_change(on_study_change)
            
            def on_unit_change(e):
                inv = investigation_select.value
                study = study_select.value
                unit = unit_select.value
                sample_select.value = None
                sample_select.options = []
                assay_select.value = None
                assay_select.options = []
                
                if item["metadata_data"] and inv and study and unit:
                    invs = item["metadata_data"].get("Investigations", {})
                    studies = invs.get(inv, {}).get("Studies", {})
                    units = studies.get(study, {}).get("observationUnits", {})
                    samples = units.get(unit, {}).get("Samples", {})
                    sample_select.options = list(samples.keys())
                    
                sample_select.update()
                assay_select.update()
                self.save_memory()
                
            unit_select.on_value_change(on_unit_change)
            
            def on_sample_change(e):
                inv = investigation_select.value
                study = study_select.value
                unit = unit_select.value
                sample = sample_select.value
                assay_select.value = None
                assay_select.options = []
                
                if item["metadata_data"] and inv and study and unit and sample:
                    invs = item["metadata_data"].get("Investigations", {})
                    studies = invs.get(inv, {}).get("Studies", {})
                    units = studies.get(study, {}).get("observationUnits", {})
                    samples = units.get(unit, {}).get("Samples", {})
                    assays = samples.get(sample, {}).get("Assays", {})
                    assay_select.options = list(assays.keys())
                    
                assay_select.update()
                self.save_memory()
                
            sample_select.on_value_change(on_sample_change)
            assay_select.on_value_change(lambda e: self.save_memory())
            
            if initial_val:
                file_select.value = initial_val
                cache = self.storage.get("loaded_json_cache", {})
                cache_key = initial_val
                if cache_key not in cache and cache_key + ".json" in cache:
                    cache_key = cache_key + ".json"
                elif cache_key not in cache and cache_key.endswith(".json") and cache_key[:-5] in cache:
                    cache_key = cache_key[:-5]
                    
                if cache_key in cache:
                    item["metadata_data"] = cache[cache_key]
                else:
                    path_proto = os.path.join(self.protocol_dir, initial_val + ".json")
                    path_exp = os.path.join(str(ensure_dirs()["exports"]), initial_val + ".json")
                    loaded = False
                    for path in [path_proto, path_exp]:
                        if os.path.exists(path):
                            try:
                                with open(path, "r", encoding="utf-8") as fp:
                                    item["metadata_data"] = json.load(fp)
                                    loaded = True
                                    break
                            except Exception:
                                pass
                    if not loaded:
                        item["metadata_data"] = None
                if item["metadata_data"]:
                    invs = item["metadata_data"].get("Investigations", {})
                    investigation_select.options = list(invs.keys())
                    investigation_select.update()
                    if initial_inv:
                        investigation_select.value = initial_inv
                        studies = invs.get(initial_inv, {}).get("Studies", {})
                        study_select.options = list(studies.keys())
                        study_select.update()
                        if initial_study:
                            study_select.value = initial_study
                            units = studies.get(initial_study, {}).get("observationUnits", {})
                            unit_select.options = list(units.keys())
                            unit_select.update()
                            if initial_unit:
                                unit_select.value = initial_unit
                                samples = units.get(initial_unit, {}).get("Samples", {})
                                sample_select.options = list(samples.keys())
                                sample_select.update()
                                if initial_sample:
                                    sample_select.value = initial_sample
                                    assays = samples.get(initial_sample, {}).get("Assays", {})
                                    assay_select.options = list(assays.keys())
                                    assay_select.update()
                                    if initial_assay:
                                        assay_select.value = initial_assay

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
        files = self.get_available_files()
        protocols = self.saved_protocol_names()
        
        for ds in getattr(self, "selected_datasets", []):
            select_el = ds.get("file_select")
            if select_el:
                select_el.options = files
                select_el.update()
                
        for md in getattr(self, "selected_metadata_list", []):
            select_el = md.get("file_select")
            if select_el:
                select_el.options = protocols
                select_el.update()

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
        # 1. From session storage cache
        cache = self.storage.get("loaded_json_cache", {})
        for k in cache.keys():
            if k.endswith(".json"):
                arr.append(k[:-5])
            else:
                arr.append(k)
        # 2. From protocol_dir
        if os.path.isdir(self.protocol_dir):
            for f in os.listdir(self.protocol_dir):
                if f.endswith(".json"):
                    arr.append(f[:-5])
        # 3. From exports_dir
        exports_dir = str(ensure_dirs()["exports"])
        if os.path.isdir(exports_dir):
            for f in os.listdir(exports_dir):
                if f.endswith(".json"):
                    arr.append(f[:-5])
        return sorted(list(set(arr)))

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

        with ui.column().classes("w-full gap-4"):

            # ============================================
            # SETTINGS CARD (STYLE & LAYOUT MATCHING OTHER PAGES)
            # ============================================
            with ui.card().classes("w-full rounded-xl shadow-md p-6 gap-4"):

                with ui.row().classes("w-full justify-between items-start"):
                    with ui.column().classes("gap-1"):
                        ui.label(
                            "Agentic AI-Assisted Bioprocess Exploration"
                        ).classes("text-h6 font-bold")

                        ui.label(
                            "Explore Data, Experimental Conditions, Microbial Information, Literature and More"
                        ).classes(
                            "text-slate-500 text-sm"
                        )
                    
                    self.info_label = ui.label(
                        "No context loaded"
                    ).classes(
                        "text-sm text-slate-700 bg-slate-100 p-2 rounded"
                    )

                ui.separator()

                # Context Sources Header
                ui.label("Datasets & Metadata Contexts").classes("text-sm font-bold text-slate-700")

                # Two-Panel Layout for Dataset and Metadata
                with ui.row().classes("w-full gap-4 items-stretch flex-wrap"):
                    # Panel 1: Dataset Context Panel
                    with ui.card().classes("flex-1 min-w-[300px] p-6 shadow-sm border border-slate-200 bg-white gap-4"):
                        with ui.row().classes("w-full justify-between items-center"):
                            ui.label("Dataset Context").classes("text-lg font-bold text-slate-800")
                            ui.button(
                                "Add Dataset",
                                icon="add",
                                color="primary",
                                on_click=lambda: self.add_dataset_row()
                            ).props("outlined dense")
                        
                        self.datasets_container = ui.column().classes("w-full gap-4 mt-2")
                        
                    # Panel 2: Metadata Context Panel
                    with ui.card().classes("flex-1 min-w-[300px] p-6 shadow-sm border border-slate-200 bg-white gap-4"):
                        with ui.row().classes("w-full justify-between items-center"):
                            ui.label("Metadata Context").classes("text-lg font-bold text-slate-800")
                            ui.button(
                                "Add Metadata",
                                icon="add",
                                color="primary",
                                on_click=lambda: self.add_metadata_row()
                            ).props("outlined dense")
                        
                        self.metadata_container = ui.column().classes("w-full gap-4 mt-2")

                ui.separator()

                # Row 1.5: Microorganisms Selector
                with ui.row().classes("w-full gap-4 items-center flex-wrap"):
                    self.microorganism_select = ui.select(
                        self.available_microorganisms,
                        label="Select Microorganisms",
                        multiple=True,
                        value=self.selected_microorganisms,
                        on_change=self.on_microorganisms_changes
                    ).classes("flex-1 min-w-[250px]")

                ui.separator()

                # Row 2: Agent Toggles
                with ui.row().classes("w-full gap-4 items-center flex-wrap"):
                    ui.label("Available Agents:").classes("font-bold text-sm text-slate-700")
                    
                    self.use_dataset = ui.switch("Dataset", value=True)
                    self.use_protocol = ui.switch("Metadata", value=True)
                    self.use_crossref = ui.switch("CrossRef", value=True)
                    self.use_bacdive = ui.switch("BacDive", value=True)
                    self.use_internet = ui.switch("World Wide Web", value=True)

                ui.separator()

                # Row 3: Model config
                with ui.row().classes("w-full gap-4 items-center flex-wrap"):

                    self.model_select = ui.select(
                        [
                            "llama3:latest",
                            "mistral:latest",
                            "phi3:latest"
                        ],
                        value=self.mem_model,
                        label="Model"
                    ).classes("w-48 min-w-[150px]")

                    with ui.column().classes("flex-1 min-w-[200px] gap-1"):
                        ui.label("Temperature").classes("text-xs text-slate-500 font-bold")
                        self.temperature = ui.slider(
                            min=0,
                            max=1,
                            step=0.1,
                            value=self.mem_temp
                        ).classes("w-full")

            # =================================================
            # CHAT AREA CARD
            # =================================================
            with ui.card().classes("w-full rounded-xl shadow-md p-6 gap-4"):
                
                # Chat window
                self.chat_box = ui.column().classes(
                    "w-full h-[600px] overflow-auto bg-slate-50 p-4 rounded-lg gap-3 border border-slate-100"
                )

                # Input area
                with ui.row().classes("w-full items-end gap-3"):

                    self.user_input = ui.textarea(
                        placeholder=(
                            "Ask about fermentation datasets, "
                            "oxygen limitation, metadata, "
                            "literature, BacDive microorganisms, "
                            "growth conditions, physiology, anomalies..."
                        )
                    ).classes("flex-1")

                    with ui.row().classes("no-wrap items-center gap-2"):
                        self.send_btn = ui.button(
                            "SEND",
                            icon="send",
                            color="primary",
                            on_click=self.send_message
                        ).classes("h-12 w-24")

                        self.export_btn = ui.button(
                            "EXPORT",
                            icon="download",
                            color="secondary",
                            on_click=self.export_chat
                        ).classes("h-12 w-28")

                        self.clear_btn = ui.button(
                            "CLEAR",
                            icon="delete",
                            color="negative",
                            on_click=self.clear_chat
                        ).classes("h-12 w-26")

        # =====================================================
        # INITIAL REFRESH
        # =====================================================
        self.refresh_loaded_files()

        # =====================================================
        # RESTORE MICROORGANISMS FROM STORAGE
        # =====================================================
        saved_microorganisms = self.storage.get(
            "selected_microorganisms",
            self.selected_microorganisms
        )

        if saved_microorganisms:
            if isinstance(saved_microorganisms, str):
                saved_microorganisms = [saved_microorganisms]
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
                print(f"[MICROORGANISM RESTORE ERROR] {ex}")

        # =====================================================
        # RESTORE DATASET & METADATA SELECTIONS
        # =====================================================
        mem = self.storage.get("llm_memory", {})
        saved_ds = mem.get("selected_datasets_multi", [])
        if saved_ds and len(saved_ds) > 0:
            for ds in saved_ds:
                self.add_dataset_row(ds.get("filename"), ds.get("filters"))
        else:
            # Fallback to single last loaded dataset if present, or add one empty row
            last_file = self.storage.get("last_loaded_file", self.mem_file)
            if last_file and last_file in self.get_available_files():
                self.add_dataset_row(last_file)
            else:
                self.add_dataset_row()

        saved_md = mem.get("selected_metadata_multi", [])
        if saved_md and len(saved_md) > 0:
            for md in saved_md:
                self.add_metadata_row(
                    md.get("filename"),
                    md.get("investigation"),
                    md.get("study"),
                    md.get("unit"),
                    md.get("sample"),
                    md.get("assay")
                )
        else:
            # Fallback to single last loaded protocol if present, or add one empty row
            last_proto = self.storage.get("selected_protocol", self.mem_protocol)
            if last_proto and last_proto in self.saved_protocol_names():
                self.add_metadata_row(last_proto)
            else:
                self.add_metadata_row()

        # =====================================================
        # REFRESH STATUS
        # =====================================================
        self.refresh_info()

    # =====================================================
    # INFO
    # =====================================================
    def refresh_info(self):
        parts = []
        datasets_count = len([d for d in getattr(self, "selected_datasets", []) if d.get("filename")])
        if datasets_count > 0:
            parts.append(f"Datasets: {datasets_count}")
            
        metadata_count = len([m for m in getattr(self, "selected_metadata_list", []) if m.get("filename")])
        if metadata_count > 0:
            parts.append(f"Metadata Files: {metadata_count}")

        if getattr(self, "selected_microorganisms", None):
            parts.append("Microorganisms: " + ", ".join(self.selected_microorganisms))

        if not parts:
            parts.append("No context loaded")

        if hasattr(self, "info_label"):
            self.info_label.text = " | ".join(parts)

    # =====================================================
    # CHAT
    # =====================================================
    def clear_chat(self):
        if hasattr(self, "chat_history"):
            self.chat_history.clear()
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
        if not hasattr(self, "chat_history"):
            self.chat_history = []
        self.chat_history.append((role, text))

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
        self.chat_box.run_method("scrollTo", {"top": 99999, "behavior": "smooth"})

    def add_agent_card(
        self,
        title,
        status,
        inputs=None,
        outputs=None,
        summary="",
        reasoning=""
    ):
        if not hasattr(self, "chat_history"):
            self.chat_history = []
        
        hist_text = f"=== {title.upper()} ===\n"
        hist_text += f"Status: {status}\n"
        if inputs:
            hist_text += f"Inputs: {inputs}\n"
        if outputs:
            hist_text += f"Outputs: {outputs}\n"
        if summary:
            hist_text += f"Summary: {summary}\n"
        if reasoning:
            hist_text += f"Reasoning: {reasoning}\n"
        self.chat_history.append((title, hist_text))
        
        if not hasattr(self, "chat_box"):
            print(hist_text)
            return

        status_lower = status.lower()
        if status_lower == "success":
            status_bg = "bg-emerald-50"
            status_text_color = "text-emerald-700"
            status_border = "border-emerald-200"
        elif status_lower == "skipped":
            status_bg = "bg-slate-100"
            status_text_color = "text-slate-600"
            status_border = "border-slate-300"
        else: # failed
            status_bg = "bg-rose-50"
            status_text_color = "text-rose-700"
            status_border = "border-rose-200"
            
        icon_map = {
            "Dataset Analyst": "analytics",
            "Metadata Analyst": "description",
            "BacDive Explorer": "biotech",
            "CrossRef Explorer": "find_in_page",
            "World Wide Web Explorer": "language",
            "Master Summarizer": "psychology",
            "System": "settings"
        }
        icon = icon_map.get(title, "smart_toy")

        with self.chat_box:
            with ui.card().classes(f"w-full shadow-md border {status_border} rounded-xl p-4 bg-white"):
                # Header row
                with ui.row().classes("w-full justify-between items-center no-wrap"):
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.icon(icon, size="sm").classes("text-slate-700")
                        ui.label(title).classes("text-lg font-bold text-slate-800")
                    # Status badge
                    ui.label(status.upper()).classes(f"text-xs font-bold px-2.5 py-1 rounded-full {status_bg} {status_text_color} border border-current")
                
                ui.separator().classes("my-2")
                
                # Content
                if inputs:
                    with ui.row().classes("w-full gap-2 items-start mt-1"):
                        ui.label("📥 Inputs:").classes("font-semibold text-slate-700 text-sm shrink-0")
                        ui.label(str(inputs)).classes("text-slate-600 text-sm whitespace-pre-wrap")
                
                if outputs:
                    with ui.row().classes("w-full gap-2 items-start mt-1"):
                        ui.label("📤 Outputs:").classes("font-semibold text-slate-700 text-sm shrink-0")
                        ui.label(str(outputs)).classes("text-slate-600 text-sm whitespace-pre-wrap")
                
                if summary:
                    with ui.column().classes("w-full gap-1 mt-2"):
                        ui.label("📝 Summary:").classes("font-semibold text-slate-700 text-sm")
                        ui.label(str(summary)).classes("text-slate-600 text-sm italic whitespace-pre-wrap")
                
                if reasoning:
                    with ui.expansion("🧠 View Detailed Reasoning & Analysis", icon="psychology").classes("w-full mt-3 border border-slate-100 rounded-lg bg-slate-50 text-sm"):
                        ui.markdown(reasoning).classes("text-slate-700 p-3 whitespace-pre-wrap")
        
        self.chat_box.run_method("scrollTo", {"top": 99999, "behavior": "smooth"})

    def add_master_card(
        self,
        title,
        status,
        inputs=None,
        outputs=None,
        summary="",
        reasoning=""
    ):
        if not hasattr(self, "chat_history"):
            self.chat_history = []
        
        hist_text = f"=== {title.upper()} ===\n"
        hist_text += f"Status: {status}\n"
        if inputs:
            hist_text += f"Inputs: {inputs}\n"
        if outputs:
            hist_text += f"Outputs: {outputs}\n"
        if summary:
            hist_text += f"Summary: {summary}\n"
        if reasoning:
            hist_text += f"Reasoning: {reasoning}\n"
        self.chat_history.append((title, hist_text))
        
        if not hasattr(self, "chat_box"):
            print(hist_text)
            return

        with self.chat_box:
            with ui.card().classes("w-full shadow-lg border border-blue-200 rounded-xl p-5 bg-white"):
                # Header row
                with ui.row().classes("w-full justify-between items-center no-wrap"):
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.icon("psychology", size="md").classes("text-blue-600")
                        ui.label(title).classes("text-xl font-bold text-blue-900")
                    # Status badge
                    ui.label(status.upper()).classes("text-xs font-bold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200")
                
                ui.separator().classes("my-3")
                
                # Content
                if summary:
                    ui.label(str(summary)).classes("text-slate-800 text-sm font-semibold mb-2")
                
                if reasoning:
                    ui.markdown(reasoning).classes("text-slate-800 text-base leading-relaxed")
        
        self.chat_box.run_method("scrollTo", {"top": 99999, "behavior": "smooth"})

    def add_workflow_start_card(self, query, participating):
        if not hasattr(self, "chat_history"):
            self.chat_history = []
        self.chat_history.append(("User", query))
        self.chat_history.append(("System", f"Starting multi-agent workflow. Participating: {', '.join(participating)}"))
        
        if not hasattr(self, "chat_box"):
            return
            
        with self.chat_box:
            # First, display the user prompt nicely in a right-aligned card
            with ui.row().classes("w-full justify-end"):
                with ui.card().classes("max-w-[80%] bg-indigo-50 border border-indigo-100 rounded-xl p-4 shadow-sm"):
                    ui.label("User Request").classes("text-xs font-bold text-indigo-700 uppercase tracking-wider")
                    ui.label(query).classes("text-slate-800 text-base whitespace-pre-wrap mt-1")
            
            # Then show workflow start card
            with ui.card().classes("w-full shadow-sm border border-slate-200 rounded-xl p-4 bg-slate-50"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("play_circle", size="sm").classes("text-slate-700")
                    ui.label("Starting Multi-Agent Workflow").classes("text-base font-bold text-slate-800")
                
                ui.separator().classes("my-2")
                ui.label("Participating Agents:").classes("text-sm font-semibold text-slate-700")
                
                for agent in participating:
                    with ui.row().classes("items-center gap-2 ml-4 mt-1"):
                        ui.icon("check_circle", size="xs").classes("text-green-500")
                        ui.label(agent).classes("text-slate-600 text-sm")
        
        self.chat_box.run_method("scrollTo", {"top": 99999, "behavior": "smooth"})

    async def export_chat(self):
        if not hasattr(self, "chat_history") or not self.chat_history:
            ui.notify("Chat is empty", type="warning")
            return
            
        fname = "chat_export.txt"
        
        # Format history
        export_text = ""
        for role, text in self.chat_history:
            export_text += f"=== {role.upper()} ===\n{text}\n\n"
            
        js_code = f"""
        (async () => {{
            const content = {json.dumps(export_text)};
            const filename = {json.dumps(fname)};
            
            if (window.showSaveFilePicker) {{
                try {{
                    const handle = await window.showSaveFilePicker({{
                        suggestedName: filename,
                        types: [{{
                            description: 'Text Files',
                            accept: {{
                                'text/plain': ['.txt'],
                            }},
                        }}],
                    }});
                    const writable = await handle.createWritable();
                    await writable.write(content);
                    await writable.close();
                    return "picker_success";
                }} catch (err) {{
                    if (err.name === 'AbortError') {{
                        return "picker_cancelled";
                    }}
                    console.warn("showSaveFilePicker failed, falling back", err);
                }}
            }}
            
            // Fallback: standard web download
            const blob = new Blob([content], {{ type: 'text/plain;charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            return "fallback_success";
        }})()
        """
        try:
            res = await ui.run_javascript(js_code, timeout=60.0)
            if res == "picker_success":
                ui.notify("Chat successfully exported via file browser", type="positive")
            elif res == "picker_cancelled":
                ui.notify("Export cancelled by user", type="warning")
            elif res == "fallback_success":
                ui.notify("Chat exported (downloaded to default location)", type="positive")
        except Exception as e:
            # Fallback in case of JS runtime error or security context issue
            ui.download(export_text.encode("utf-8"), filename=fname)
            ui.notify("Chat exported (fallback download)", type="positive")

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
        await self.run_multi_agent_pipeline()

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

        self.user_input.value = ""

        self.send_btn.disable()
        if hasattr(self, "export_btn"):
            self.export_btn.disable()
        if hasattr(self, "clear_btn"):
            self.clear_btn.disable()

        try:
            self.save_memory()

            datasets = {}
            for ds in getattr(self, "selected_datasets", []):
                fname = ds.get("filename")
                df = ds.get("df")
                if fname and df is not None:
                    # apply filters
                    filtered_df = df.copy()
                    for tier in ds.get("filter_tiers", []):
                        col = tier.get("col_select").value
                        vals = tier.get("val_select").value
                        if col and vals:
                            filtered_df = filtered_df[
                                filtered_df[col]
                                .astype(str)
                                .isin(vals)
                            ]
                    datasets[fname] = filtered_df

            metadata_files = {}
            for md in getattr(self, "selected_metadata_list", []):
                fname = md.get("filename")
                mdata = md.get("metadata_data")
                if fname and mdata:
                    inv = md.get("investigation_select").value
                    study = md.get("study_select").value
                    unit = md.get("unit_select").value
                    sample = md.get("sample_select").value
                    assay = md.get("assay_select").value
                    
                    filtered_md = self.filter_metadata_hierarchy(mdata, inv, study, unit, sample, assay)
                    metadata_files[fname] = filtered_md

            use_dataset = hasattr(self, "use_dataset") and self.use_dataset.value
            use_protocol = hasattr(self, "use_protocol") and self.use_protocol.value
            use_crossref = hasattr(self, "use_crossref") and self.use_crossref.value
            use_internet = hasattr(self, "use_internet") and self.use_internet.value
            run_bacdive = hasattr(self, "use_bacdive") and self.use_bacdive.value

            participating = []
            if use_dataset:
                participating.append("Dataset Analyst")
            if use_protocol:
                participating.append("Metadata Analyst")
            if run_bacdive:
                participating.append("BacDive Explorer")
            if use_crossref:
                participating.append("CrossRef Explorer")
            if use_internet:
                participating.append("World Wide Web Explorer")
            participating.append("Master Summarizer")

            self.add_workflow_start_card(prompt, participating)
            print(f"\n[LLM CoPilot] STARTING PIPELINE: query='{prompt}'")

            orchestrator = AgentOrchestrator(
                model_name=self.model_select.value,
                temperature=self.temperature.value
            )

            outputs = {"query": prompt}

            # 1. Dataset analyst
            df_to_analyze = None
            if datasets and isinstance(datasets, dict) and len(datasets) > 0:
                df_to_analyze = list(datasets.values())[0]

            placeholder1 = ui.column().classes("w-full")
            if use_dataset:
                with placeholder1:
                    spinner = ui.row().classes("items-center gap-2 p-3 bg-slate-100 rounded-lg border border-slate-200 w-full")
                    with spinner:
                        ui.spinner(size="sm", color="primary")
                        ui.label("Dataset Analyst is running...").classes("text-slate-600 text-sm font-medium")
                
                print(f"[LLM CoPilot] DATA_ANALYST: starting")
                
                result = await asyncio.to_thread(
                    orchestrator.safe_run,
                    "DATA_ANALYST",
                    orchestrator.data_agent.run,
                    query=prompt,
                    dataframe=df_to_analyze,
                    use_llm=True
                )
                
                outputs["data_analyst"] = result
                print(f"[LLM CoPilot] DATA_ANALYST: completed (Status: {result.get('agent_status', 'unknown')})")
                
                placeholder1.clear()
                with placeholder1:
                    status = result.get("agent_status", "skipped")
                    inputs_str = f"Dataset: {list(datasets.keys())[0]} ({df_to_analyze.shape[0]} rows x {df_to_analyze.shape[1]} columns)" if df_to_analyze is not None else "None"
                    outputs_str = f"Columns: {result.get('summary', {}).get('columns', 0)}, Anomalies: {result.get('summary', {}).get('anomaly_groups', 0)}" if status == "success" else "None"
                    self.add_agent_card(
                        "Dataset Analyst",
                        status=status,
                        inputs=inputs_str,
                        outputs=outputs_str,
                        summary=result.get("agent_summary", ""),
                        reasoning=result.get("assessment", "")
                    )
            else:
                outputs["data_analyst"] = orchestrator.skipped_agent("DATA_ANALYST", "Dataset analysis skipped.")

            # 2. Metadata analyst
            meta_to_analyze = None
            if metadata_files and isinstance(metadata_files, dict) and len(metadata_files) > 0:
                meta_to_analyze = list(metadata_files.values())[0]

            placeholder2 = ui.column().classes("w-full")
            if use_protocol:
                with placeholder2:
                    spinner = ui.row().classes("items-center gap-2 p-3 bg-slate-100 rounded-lg border border-slate-200 w-full")
                    with spinner:
                        ui.spinner(size="sm", color="primary")
                        ui.label("Metadata Analyst is running...").classes("text-slate-600 text-sm font-medium")
                
                print(f"[LLM CoPilot] METADATA_ANALYST: starting")
                
                result = await asyncio.to_thread(
                    orchestrator.safe_run,
                    "METADATA_ANALYST",
                    orchestrator.metadata_agent.run,
                    metadata=meta_to_analyze,
                    use_llm=True
                )
                
                outputs["metadata_analyst"] = result
                print(f"[LLM CoPilot] METADATA_ANALYST: completed (Status: {result.get('agent_status', 'unknown')})")
                
                placeholder2.clear()
                with placeholder2:
                    status = result.get("agent_status", "skipped")
                    inputs_str = f"Metadata: {list(metadata_files.keys())[0]}" if meta_to_analyze is not None else "None"
                    outputs_str = f"Investigation: {result.get('summary', {}).get('investigation', 'unknown')}, Study: {result.get('summary', {}).get('study', 'unknown')}" if status == "success" else "None"
                    self.add_agent_card(
                        "Metadata Analyst",
                        status=status,
                        inputs=inputs_str,
                        outputs=outputs_str,
                        summary=result.get("agent_summary", ""),
                        reasoning=result.get("assessment", "")
                    )
            else:
                outputs["metadata_analyst"] = orchestrator.skipped_agent("METADATA_ANALYST", "Metadata analysis skipped.")

            # 3. BacDive Explorer
            placeholder3 = ui.column().classes("w-full")
            resolved_organisms = []
            if run_bacdive:
                with placeholder3:
                    spinner = ui.row().classes("items-center gap-2 p-3 bg-slate-100 rounded-lg border border-slate-200 w-full")
                    with spinner:
                        ui.spinner(size="sm", color="primary")
                        ui.label("BacDive Explorer: Resolving organisms...").classes("text-slate-600 text-sm font-medium")
                
                print(f"[LLM CoPilot] BACDIVE_EXPLORER: resolving organisms")
                resolved_organisms = await asyncio.to_thread(
                    orchestrator.resolve_bacdive_organisms,
                    query=prompt,
                    protocol=meta_to_analyze,
                    metadata=meta_to_analyze,
                    dataframe=df_to_analyze,
                    selected_microorganisms=self.selected_microorganisms
                )
                
                outputs["detected_organisms"] = {
                    "agent_name": "DETECTED_ORGANISMS",
                    "agent_status": "success" if resolved_organisms else "skipped",
                    "organisms": resolved_organisms
                }

                if resolved_organisms:
                    placeholder3.clear()
                    with placeholder3:
                        spinner = ui.row().classes("items-center gap-2 p-3 bg-slate-100 rounded-lg border border-slate-200 w-full")
                        with spinner:
                            ui.spinner(size="sm", color="primary")
                            ui.label(f"BacDive Explorer: Querying database for {', '.join(resolved_organisms)}...").classes("text-slate-600 text-sm font-medium")
                    
                    bacdive_results = {}
                    for org in resolved_organisms:
                        print(f"[LLM CoPilot] BACDIVE_EXPLORER: querying BacDive for '{org}'")
                        res = await asyncio.to_thread(
                            orchestrator.safe_run,
                            "BACDIVE_EXPLORER",
                            orchestrator.bacdive_agent.run,
                            query=prompt,
                            microorganism=org,
                            use_llm=False,
                            max_results=None
                        )
                        bacdive_results[org] = res
                    
                    result = {
                        "agent_name": "BACDIVE_EXPLORER",
                        "agent_status": "success",
                        "results": bacdive_results,
                        "agent_summary": f"Executed BacDive search for {', '.join(resolved_organisms)}."
                    }
                    outputs["bacdive_explorer"] = result
                    print(f"[LLM CoPilot] BACDIVE_EXPLORER: completed (Status: success, found {len(resolved_organisms)} organisms)")
                    
                    placeholder3.clear()
                    with placeholder3:
                        reasoning_str = ""
                        for org, org_res in bacdive_results.items():
                            reasoning_str += f"### {org}\n{org_res.get('assessment', 'No details available.')}\n\n"
                        
                        self.add_agent_card(
                            "BacDive Explorer",
                            status="success",
                            inputs=f"Organisms: {', '.join(resolved_organisms)}",
                            outputs=f"Found database records for: {', '.join(bacdive_results.keys())}",
                            summary=result.get("agent_summary", ""),
                            reasoning=reasoning_str
                        )
                else:
                    outputs["bacdive_explorer"] = orchestrator.skipped_agent("BACDIVE_EXPLORER", "BacDive query skipped (no organisms detected).")
                    placeholder3.clear()
                    with placeholder3:
                        self.add_agent_card(
                            "BacDive Explorer",
                            status="skipped",
                            summary="BacDive query skipped: no organisms detected."
                        )
            else:
                outputs["bacdive_explorer"] = orchestrator.skipped_agent("BACDIVE_EXPLORER", "BacDive query skipped.")

            # 4. Crossref Explorer
            placeholder4 = ui.column().classes("w-full")
            if use_crossref:
                with placeholder4:
                    spinner = ui.row().classes("items-center gap-2 p-3 bg-slate-100 rounded-lg border border-slate-200 w-full")
                    with spinner:
                        ui.spinner(size="sm", color="primary")
                        ui.label("CrossRef Explorer is running...").classes("text-slate-600 text-sm font-medium")
                
                print(f"[LLM CoPilot] CROSSREF_EXPLORER: starting")
                
                result = await asyncio.to_thread(
                    orchestrator.safe_run,
                    "CROSSREF_EXPLORER",
                    orchestrator.crossref_agent.run,
                    query=prompt,
                    use_llm=True
                )
                
                outputs["crossref_explorer"] = result
                print(f"[LLM CoPilot] CROSSREF_EXPLORER: completed (Status: {result.get('agent_status', 'unknown')})")
                
                placeholder4.clear()
                with placeholder4:
                    status = result.get("agent_status", "skipped")
                    outputs_str = f"Papers found: {len(result.get('papers', []))}" if status == "success" else "None"
                    self.add_agent_card(
                        "CrossRef Explorer",
                        status=status,
                        inputs=f"Query: '{prompt}'",
                        outputs=outputs_str,
                        summary=result.get("agent_summary", ""),
                        reasoning=result.get("assessment", "")
                    )
            else:
                outputs["crossref_explorer"] = orchestrator.skipped_agent("CROSSREF_EXPLORER", "CrossRef search skipped.")

            # 5. Internet Explorer
            placeholder5 = ui.column().classes("w-full")
            if use_internet:
                with placeholder5:
                    spinner = ui.row().classes("items-center gap-2 p-3 bg-slate-100 rounded-lg border border-slate-200 w-full")
                    with spinner:
                        ui.spinner(size="sm", color="primary")
                        ui.label("World Wide Web Explorer is running...").classes("text-slate-600 text-sm font-medium")
                
                print(f"[LLM CoPilot] INTERNET_EXPLORER: starting")
                
                result = await asyncio.to_thread(
                    orchestrator.safe_run,
                    "INTERNET_EXPLORER",
                    orchestrator.internet_agent.run,
                    query=prompt,
                    use_llm=True
                )
                
                outputs["internet_explorer"] = result
                print(f"[LLM CoPilot] INTERNET_EXPLORER: completed (Status: {result.get('agent_status', 'unknown')})")
                
                placeholder5.clear()
                with placeholder5:
                    status = result.get("agent_status", "skipped")
                    outputs_str = f"PubMed: {len(result.get('results', {}).get('pubmed', []))}, Web: {len(result.get('results', {}).get('web', []))}" if status == "success" else "None"
                    self.add_agent_card(
                        "World Wide Web Explorer",
                        status=status,
                        inputs=f"Query: '{prompt}'",
                        outputs=outputs_str,
                        summary=result.get("agent_summary", ""),
                        reasoning=result.get("assessment", "")
                    )
            else:
                outputs["internet_explorer"] = orchestrator.skipped_agent("INTERNET_EXPLORER", "Internet search skipped.")

            # 6. Build combined agent summaries
            outputs["agent_summaries"] = {
                "agent_name": "AGENT_SUMMARIES",
                "agent_status": "success",
                "summaries": orchestrator.collect_agent_summaries(outputs),
                "agent_summary": "Collected summaries from sequential execution."
            }

            # 7. Master Summarizer
            placeholder6 = ui.column().classes("w-full")
            with placeholder6:
                spinner = ui.row().classes("items-center gap-2 p-3 bg-slate-100 rounded-lg border border-slate-200 w-full")
                with spinner:
                    ui.spinner(size="sm", color="primary")
                    ui.label("Master Summarizer is synthesizing...").classes("text-slate-600 text-sm font-medium")
            
            print(f"[LLM CoPilot] MASTER_SUMMARIZER: synthesizing findings...")
            
            master_result = await asyncio.to_thread(
                orchestrator.safe_run,
                "MASTER_SUMMARIZER",
                orchestrator.master_agent.run,
                agent_outputs=outputs
            )
            
            outputs["master_summarizer"] = master_result
            outputs["assessment"] = master_result.get("final_summary", "")
            
            print(f"[LLM CoPilot] MASTER_SUMMARIZER: completed")
            
            placeholder6.clear()
            with placeholder6:
                self.add_master_card(
                    "Master Summarizer",
                    status=master_result.get("agent_status", "success"),
                    summary="Final consensus summary synthesis",
                    reasoning=master_result.get("final_summary", "")
                )

            # Build final system summary
            successful_agents = len([
                v for v in outputs.values()
                if isinstance(v, dict) and v.get("agent_status") == "success"
            ])
            failed_agents = len([
                v for v in outputs.values()
                if isinstance(v, dict) and v.get("agent_status") == "failed"
            ])
            skipped_agents = len([
                v for v in outputs.values()
                if isinstance(v, dict) and v.get("agent_status") == "skipped"
            ])

            outputs["system_summary"] = {
                "agents_executed": [k for k, v in outputs.items() if isinstance(v, dict) and v.get("agent_status") != "skipped"],
                "successful_agents": successful_agents,
                "failed_agents": failed_agents,
                "skipped_agents": skipped_agents,
                "model": orchestrator.model_name,
                "temperature": orchestrator.temperature,
                "mode": "sequential_multi_agent",
                "run_started_at": datetime.now().isoformat(),
                "run_finished_at": datetime.now().isoformat(),
                "log_directory": orchestrator.log_dir
            }

            orchestrator.log_system_step("run_completed", outputs["system_summary"])
            print(f"[LLM CoPilot] PIPELINE COMPLETE: success={successful_agents}, failed={failed_agents}, skipped={skipped_agents}\n")

        except Exception as e:
            traceback.print_exc()
            self.add_message(
                "SYSTEM ERROR",
                str(e)
            )

        finally:
            self.send_btn.enable()
            if hasattr(self, "export_btn"):
                self.export_btn.enable()
            if hasattr(self, "clear_btn"):
                self.clear_btn.enable()

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
            hasattr(self, "use_dataset")
            and self.use_dataset.value
        ):
            for ds in getattr(self, "selected_datasets", []):
                fname = ds.get("filename")
                df = ds.get("df")
                if fname and df is not None:
                    filtered_df = df.copy()
                    for tier in ds.get("filter_tiers", []):
                        col = tier.get("col_select").value
                        vals = tier.get("val_select").value
                        if col and vals:
                            filtered_df = filtered_df[
                                filtered_df[col]
                                .astype(str)
                                .isin(vals)
                            ]
                    blocks.append(
                        f"DATASET '{fname}' COLUMNS:\n"
                        + ", ".join(filtered_df.columns.astype(str))
                    )
                    blocks.append(
                        f"DATASET '{fname}' ROWS: {len(filtered_df)}"
                    )

        if (
            hasattr(self, "use_protocol")
            and self.use_protocol.value
        ):
            for md in getattr(self, "selected_metadata_list", []):
                fname = md.get("filename")
                mdata = md.get("metadata_data")
                if fname and mdata:
                    inv = md.get("investigation_select").value
                    study = md.get("study_select").value
                    unit = md.get("unit_select").value
                    sample = md.get("sample_select").value
                    assay = md.get("assay_select").value
                    
                    filtered_md = self.filter_metadata_hierarchy(mdata, inv, study, unit, sample, assay)
                    blocks.append(
                        f"METADATA '{fname}' CONTEXT:\n"
                        + json.dumps(filtered_md, indent=2, default=str)
                    )

        if getattr(self, "selected_microorganisms", None):
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