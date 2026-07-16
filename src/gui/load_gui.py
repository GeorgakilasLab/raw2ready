"""Dataset Loading GUI module.

Provides a user interface for uploading datasets, parsing equipment-specific raw
bioreactor files (e.g., Gas Analyzer, BioLectorXT), performing data cleaning,
and configuring data columns before exporting or analysis.
"""

from nicegui import ui, app
import pandas as pd
import numpy as np
import traceback
import tempfile
import os
import json
from pathlib import Path

pd.set_option("future.no_silent_downcasting", True)

import src.utils.theme as theme
from src.utils.logging_config import get_logger
from src.utils.paths import ensure_dirs


# REAL BACKEND PARSER
from src.core.parse import (parse_gas_analyzer, parse_biolector_xt, parse_other)
from src.core.parse import run_parse

# OPTIONAL CLEANING TOOLS
try:
    from src.utils.parse_tools import (
        remove_empty_rows,
        remove_duplicates,
        trim_whitespace,
        fill_values,
    )
except Exception:
    remove_empty_rows = None
    remove_duplicates = None
    trim_whitespace = None
    fill_values = None


# --------------------------------------------------
# LOGGER
# --------------------------------------------------
logger = get_logger("load_gui")


# --------------------------------------------------
# CLASS
# --------------------------------------------------
class loadgui:
    """Manages the UI flow for uploading, parsing, and cleaning data files.

    Attributes:
        config_: Application configuration dict.
        page_url_path: URL route path for this page.
        frame_name: Title of the page frame.
        storage: Data storage container dict.
        DIRS: Dict of directories for file storage/upload operations.
        filename: Active file's name.
        file_content: Bytes of the uploaded active file.
        df: Parsed DataFrame representation.
        current_df: Active working copy of DataFrame under cleaning operations.
        original_df: Immutable backup copy of the parsed DataFrame.
        files_label: UI label indicating loaded files count/state.
        stats_label: UI label showing loaded dataset statistics.
        validation_label: UI label displaying validation checklist status.
        output_format: Output format dropdown.
        file_type_select: NiceGUI select widget for selecting raw file type.
        delimiter_select: NiceGUI select widget for specifying file text delimiters.
        raw_format_select: NiceGUI select widget for specifying raw parser format.
        delimiter_row: NiceGUI row containing delimiter settings.
        selected_json_config: Parsed active JSON configuration dict.
        preview_container: NiceGUI column for dataset table preview.
        cleaning_container: NiceGUI column containing data cleaning buttons.
        column_container: NiceGUI column containing column validation configurations.
        files_container: NiceGUI column listing loaded files.
        upload_component: NiceGUI upload widget.
        column_types: Dict mapping column names to parsed data types.
        file_buffers: Dict caching binary file buffers by filename.
        time_format: Selected datetime parsing format/rule.
    """

    # ==================================================
    # INIT
    # ==================================================
    def __init__(
        self,
        config,
        page_url_path="/load",
        frame_name="Load Window",
        add_page=False,
        storage_container=None,
        storage_container_=None,
        dirs=None,
    ):
        """Initializes loadgui.

        Args:
            config: Config dictionary containing environment/parsing parameters.
            page_url_path: Route URL path. Defaults to "/load".
            frame_name: Title of the page frame. Defaults to "Load Window".
            add_page: Whether to automatically register the route page. Defaults to False.
            storage_container: Optional primary storage container dict.
            storage_container_: Optional secondary storage container dict.
            dirs: Dict containing output and upload paths.
        """

        logger.info("initialising loadgui")

        if storage_container is None and storage_container_ is not None:
            storage_container = storage_container_

        if storage_container is None:
            storage_container = {}

        self.config_ = config
        self.page_url_path = page_url_path
        self.frame_name = frame_name
        self.storage = storage_container
        
        if dirs is None:
            raise RuntimeError("DIRS not passed to load_gui")
        
        self.DIRS = dirs

        self.filename = ""
        self.file_content = None

        self.df = None
        self.current_df = None
        self.original_df = None

        self.files_label = None
        self.stats_label = None
        self.validation_label = None

        self.output_format = None
        self.file_type_select = None
        self.delimiter_select = None
        self.raw_format_select = None
        self.delimiter_row = None
        self.selected_json_config = None

        self.preview_container = None
        self.cleaning_container = None
        self.column_container = None
        self.files_container = None
        self.upload_component = None

        self.column_types = {}
        self.file_buffers = {}
        self.time_format = "auto"

        self.init_storage()

        if add_page:
            self.add_page(
                page_url=self.page_url_path,
                frame_name=self.frame_name,
            )

    # ==================================================
    # STORAGE
    # ==================================================
    def init_storage(self):
        """Initializes default dictionary keys within the storage container."""

        defaults = {
            "files": {},
            "parsed_df_json": [],
            "parsed_df_columns": [],
            "parsed_filename": "",
            "df_json": [],
            "df_columns": [],
            "last_loaded_file": "",
            "dataset_id": None,
            
            "json_cache": {},
            "last_json_file": "",
            "current_json_data": {},
        }

        for k, v in defaults.items():
            if k not in self.storage:
                self.storage[k] = v
    
    def get_available_files(self):
        """Gets lists of all parsed dataset filenames cached in memory.

        Returns:
            List of cached file name strings.
        """

        return list(
            self.storage.get("parsed_cache", {}).keys()
        )
        
    def get_available_json_files(self_):
        """Gets list of uploaded config JSON files cached in memory.

        Returns:
            List of cached JSON configuration file name strings.
        """
    
        return list(
            self_ .storage.get("json_cache", {}).keys()
        )  
    # ==================================================
    # PAGE
    # ==================================================
    def add_page(self, page_url="/load", frame_name="Load Window"):
        """Adds this page as a distinct route in the application.

        Args:
            page_url: Route path. Defaults to "/load".
            frame_name: Title of UI frame. Defaults to "Load Window".
        """

        @ui.page(page_url)
        async def page():

            if "shared_data" not in app.storage.general:
                app.storage.general["shared_data"] = {}
            
            app.storage.general["shared_data"].update(self.storage)
            self.storage = app.storage.general["shared_data"]
            self.init_storage()

            with theme.frame(frame_name):
                self.content_()

    # ==================================================
    # CONTENT
    # ==================================================
    def content_(self):
        """Renders the HTML/CSS contents of the loading interface page."""

        with ui.column().classes("w-full p-4 gap-6"):
            self.section_load()
            self.section_validator()
            self.section_active_dataset()
            self.section_status()

    # ==================================================
    # LOAD SECTION
    # ==================================================
    def section_load(self):

        with ui.card().classes("w-full rounded-xl shadow-md"):
    
            ui.label("Upload Dataset").classes("text-h6 font-bold")
    
            # =========================
            # SETTINGS ROW
            # =========================
            with ui.row().classes("gap-4 flex-wrap"):
    
                # FILE TYPE
                self.file_type_select = ui.select(
                    ["XLS(X)", "Text"],
                    value="XLS(X)",
                    label="File Type",
                ).classes("w-44")
    
                # RAW FORMAT
                self.raw_format_select = ui.select(
                    ["Other", "Gas Analyzer", "BioLectorXT"],
                    value="Other",
                    label="Raw Bioreactor Files",
                ).classes("w-64")
    
            # =========================
            # DELIMITER + JSON (SAME ROW)
            # =========================
            with ui.row().classes("gap-4 flex-wrap") as self.delimiter_row:
    
                # DELIMITER
                self.delimiter_select = ui.select(
                    ["Comma", "Tab", "Space"],
                    value="Comma",
                    label="Delimiter",
                ).classes("w-44")
    
                # JSON DROPDOWN (NEXT TO DELIMITER)
                with ui.column().classes("gap-2"):

                    ui.label(
                        "Gas Analyzer Config (JSON)"
                    ).classes("text-sm")
                
                    # ======================================
                    # JSON FILE SELECTOR
                    # ======================================
                    with ui.row().classes("items-center gap-2"):
                
                        self.json_selector = ui.select(
                            [],
                            label="Saved JSON Files",
                            with_input=True,
                            on_change=lambda e: self.load_selected_json()
                        ).classes("w-64")
                
                        ui.button(
                            "+ NEW",
                            icon="add",
                            color="primary",
                            on_click=self.create_new_json
                        )
                
                        ui.button(
                            "REFRESH",
                            icon="refresh",
                            on_click=self.refresh_json_files
                        )
                
                    # ======================================
                    # JSON UPLOAD
                    # ======================================
                    ui.upload(
                        on_upload=self.handle_json_upload,
                        auto_upload=True,
                        multiple=False,
                    ).props(
                        "accept=.json"
                    ).classes("w-64")
                
                    self.json_status = ui.label(
                        "No config loaded"
                    ).classes("text-xs text-gray-500")
    
            # =========================
            # EVENT HANDLERS (AFTER CREATION)
            # =========================
            self.file_type_select.on_value_change(
                lambda e: self._on_type_change()
            )
    
            self.raw_format_select.on_value_change(
                lambda e: self._on_type_change()
            )
    
            # =========================
            # INITIAL STATE
            # =========================
            self.toggle_delimiter()
    
            # =========================
            # UPLOAD AREA
            # =========================
            self.upload_component = ui.upload(
                on_upload=self.handle_upload,
                auto_upload=True,
                multiple=False,
                label=""
            ).props(
                "accept=.csv,.tsv,.xls,.xlsx,.txt"
            ).classes("w-full mt-4")
    
            ui.label(
                "Click or drag files here\nAllowed Files: CSV / TSV / XLS / XLSX / TXT"
            )
    
            # =========================
            # FILE LIST
            # =========================
            self.files_container = ui.column().classes("w-full mt-3")
            self.show_uploaded_files()
    
            # =========================
            # CLEAR MEMORY
            # =========================
            
            with ui.row().classes("mt-3 gap-3 items-center"):
            
                ui.button(
                    "CLEAR MEMORY",
                    icon="delete",
                    color="negative",
                    on_click=self.clear_memory
                )
                
                ui.button(
                    "REFRESH",
                    icon="refresh",
                    on_click=self.force_refresh
                )
    # ==================================================
    # FILE LIST UI
    # ==================================================        
    def show_uploaded_files(self):

        if self.files_container is None:
            return
    
        self.files_container.clear()
    
        files = self.get_available_files()
        active = self.storage.get("last_loaded_file")
    
        with self.files_container:
    
            if not files:
                ui.label("No parsed files loaded.")
                return
    
            for fname in files:
    
                is_active = fname == active
    
                ui.button(
                    f"{'? ' if is_active else ''}{fname}",
                    on_click=lambda e, f=fname: self.select_file(f),
                ).props("flat").classes(
                    "w-full text-left "
                    + ("bg-blue-100" if is_active else "")
                )
                    
    def select_file(self, filename):

        # set active file
        self.storage["last_loaded_file"] = filename
    
        # =========================
        # LOAD FROM CACHE (NO PARSE)
        # =========================
        cached = self.storage.get("parsed_cache", {}).get(filename)
    
        if cached:
            df = pd.DataFrame(cached)
    
            df = self.make_json_safe(df)
    
            self.current_df = df.copy()
            self.original_df = df.copy()
    
            self.save_global_df()
            self.save_current_to_cache()
            self.refresh_status()
    
            ui.notify(f"{filename} loaded instantly (cached)", type="info")
    
        else:
            # fallback (first time only)
            self.filename = filename
            self.file_content = self.file_buffers.get(filename)
    
            ui.notify(f"{filename} not cached ? parsing...", type="warning")
            self.run_parse()
    
        # refresh UI highlight
        self.show_uploaded_files()
        
    # ==================================================
    # VALIDATOR
    # ==================================================
    def section_validator(self):

        with ui.card().classes("w-full rounded-xl shadow-md"):
    
            ui.label("Dataset Accepted Messages").classes(
                "text-h6 font-bold"
            )
    
            self.validation_label = ui.label(
                "No dataset loaded."
            )
            
    def section_active_dataset(self):

        with ui.card().classes("w-full rounded-xl shadow-md"):
    
            # ============================================
            # HEADER ROW
            # ============================================
            with ui.row().classes(
                "w-full items-center justify-between"
            ):
    
                ui.label(
                    "Active Dataset"
                ).classes(
                    "text-h6 font-bold"
                )
    
                ui.button(
    
                    "Check Missing Values",
    
                    icon="search",
    
                    color="warning",
    
                    on_click=self.show_missing_values
    
                )
    
            # ============================================
            # PREVIEW AREA
            # ============================================
            self.preview_container = ui.column().classes(
                "w-full"
            )
    
            self.refresh_preview()
            
    # ==================================================
    # STATUS
    # ==================================================
    def section_status(self):

        with ui.card().classes("w-full rounded-xl shadow-md"):
        
            ui.label("Data Cleaning & Column Settings").classes("text-h6 font-bold")

            self.cleaning_container = ui.column().classes("w-full")
            self.column_container = ui.column().classes("w-full")

            self.show_data_cleaning()
            self.show_column_config()

    # ==================================================
    # HELPERS
    # ==================================================
    def get_dir(self, key):
        if key not in self.DIRS:
            raise ValueError(f"Missing DIRS['{key}'] in configuration. Available: {list(self.DIRS.keys())}")
        return self.DIRS[key]
    
    def toggle_delimiter(self):
        if self.file_type_select.value == "Text":
            self.delimiter_row.set_visibility(True)
        else:
            self.delimiter_row.set_visibility(False)

    def _on_type_change(self):
        self.toggle_delimiter()

    def get_parse_equipment(self):

        val = self.raw_format_select.value

        if val == "Other":
            return "Other"

        if val == "Gas Analyzer":
            return "Gas Analyzer"

        if val == "BioLectorXT":
            return "BioLectorXT"

        return "Generic"
    
    def extract_biolector_name(self, filepath):

        try:
            meta = pd.read_excel(
                filepath,
                sheet_name="MetaData",
                header=None
            )
    
            for i in range(len(meta)):
                key = str(meta.iloc[i, 0]).strip()
    
                if key.lower() == "protocol name":
                    val = str(meta.iloc[i, 1]).strip()
                    if val and val.lower() != "nan":
                        return val
    
        except:
            pass
    
        return os.path.splitext(self.filename)[0]
            
    async def handle_json_upload(self, e):

        try:
    
            # ======================================
            # READ FILE
            # ======================================
            content = await e.file.read()
    
            # ======================================
            # PARSE JSON
            # ======================================
            self.selected_json_config = json.loads(
                content.decode("utf-8")
            )
    
            # ======================================
            # INIT CACHE
            # ======================================
            if "json_cache" not in self.storage:
                self.storage["json_cache"] = {}
    
            # ======================================
            # SAVE JSON TO CACHE
            # ======================================
            self.storage["json_cache"][e.file.name] = (
                self.selected_json_config
            )
    
            # ======================================
            # SAVE ACTIVE JSON
            # ======================================
            self.storage["last_json_file"] = (
                e.file.name
            )
    
            self.storage["current_json_data"] = (
                self.selected_json_config
            )
    
            # ======================================
            # UPDATE STATUS
            # ======================================
            self.json_status.text = (
                f"Loaded: {e.file.name}"
            )
    
            # ======================================
            # REFRESH SELECTOR
            # ======================================
            self.refresh_json_files()
    
            # ======================================
            # AUTO SELECT CURRENT JSON
            # ======================================
            if hasattr(self, "json_selector"):
    
                self.json_selector.value = e.file.name
                self.json_selector.update()
    
            # ======================================
            # NOTIFY
            # ======================================
            ui.notify(
                "JSON config loaded successfully",
                type="info"
            )
    
        except Exception as ex:
    
            ui.notify(
                f"Invalid JSON: {str(ex)}",
                type="negative"
            )
    
            self.selected_json_config = None  
    
            
    def refresh_json_files(self):

        if not hasattr(self, "json_selector"):
            return
    
        files = self.get_available_json_files()
    
        self.json_selector.options = files
        self.json_selector.update()
    
        if not files:
            self.json_selector.value = None
            return
    
        last = self.storage.get("last_json_file")
    
        if last in files:
            selected = last
        else:
            selected = files[0]
    
        self.json_selector.value = selected
        self.json_selector.update()
    
    def load_selected_json(self):

        try:
    
            filename = self.json_selector.value
    
            if not filename:
                return
    
            cached = self.storage.get(
                "json_cache",
                {}
            ).get(filename)
    
            if not cached:
    
                ui.notify(
                    "JSON not found",
                    type="warning"
                )
                return
    
            self.selected_json_config = cached
    
            self.storage["current_json_data"] = cached
            self.storage["last_json_file"] = filename
    
            self.json_status.text = (
                f"Loaded: {filename}"
            )
    
            # IMPORTANT
            # refresh your form UI here
            self.refresh_json_form()
    
            ui.notify(
                f"{filename} loaded",
                type="info"
            )
    
        except Exception as e:
    
            ui.notify(
                f"JSON load failed: {str(e)}",
                type="negative"
            )
    
    def create_new_json(self):

        # =====================================
        # DISASSOCIATE OLD JSON
        # =====================================
        self.selected_json_config = {}
    
        self.storage["current_json_data"] = {}
        self.storage["last_json_file"] = ""
    
        # =====================================
        # CLEAR SELECTOR
        # =====================================
        if hasattr(self, "json_selector"):
    
            self.json_selector.value = None
            self.json_selector.update()
    
        # =====================================
        # RESET FORM
        # =====================================
        self.reset_json_form()
    
        self.json_status.text = (
            "Creating new JSON config..."
        )
    
        ui.notify(
            "New JSON form created",
            type="info"
        )
    def reset_json_form(self):

        """
        Clears all JSON form fields
        """
    
        # Example:
        # self.start_date.value = ""
        # self.target_channel.value = ""
        # etc...
    
        pass   
    
    def refresh_json_form(self):

        """
        Reloads UI fields from selected_json_config
        """
    
        data = self.selected_json_config
    
        # Example:
        # self.start_date.value = data.get("start_date", "")
        # self.target_channel.value = data.get("target", "")
    
        pass 
        
    def mark_dirty(self):
        if hasattr(self, "reset_btn") and self.reset_btn:
            self.reset_btn.props("color=primary")        
    # ==================================================
    # HANDLE UPLOAD
    # ==================================================
    
    async def handle_upload(self, e):

        try:
            self.filename = e.file.name
            self.file_content = await e.file.read()
            
            upload_dir = self.DIRS.get("uploads", os.path.expanduser("~/.raw2ready/uploads"))
            os.makedirs(upload_dir, exist_ok=True)
            
            upload_path = os.path.join(upload_dir, self.filename)
            
            
            with open(upload_path, "wb") as f:
                f.write(self.file_content)
            self.show_uploaded_files()
            
            self.file_buffers[self.filename] = self.file_content
    
            # STORE CONTENT (IMPORTANT FIX)
            self.storage["files"][self.filename] = {
                "file name": self.filename,
            }
    
            self.storage["last_loaded_file"] = self.filename
    
            ui.notify(f"{self.filename} loaded & selected", type="info")
    
            if self.upload_component:
                self.upload_component.disable()
    
            ui.notify("Starting automatic parsing...", type="info")
    
            self.run_parse()
    
            self.show_uploaded_files()   # UPDATE LIST
            self.refresh_status()
    
            if self.upload_component:
                self.upload_component.enable()
    
        except Exception as ex:
            logger.error(traceback.format_exc())
            ui.notify(f"Upload failed: {str(ex)}", type="negative")
            
    def make_json_safe(self, df):
        df = df.copy()
    
        # Only convert datetime columns
        datetime_cols = df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns
        
        for col in datetime_cols:
            df[col] = df[col].astype(str)
    
        return df
    # ==================================================
    # RUN PARSER
    # ==================================================
    def run_parse(self):

        try:
    
            if not self.filename:
                ui.notify("Upload file first")
                return
    
            parse_type = self.raw_format_select.value
            equipment = self.get_parse_equipment()
            
            print("DEBUG parse_type:", parse_type)
            print("DEBUG equipment:", equipment)
            
            ext = os.path.splitext(self.filename)[1].lower()
    
            # -------------------------
            # VALIDATION
            # -------------------------
            if parse_type == "BioLectorXT" and ext not in [".xlsx", ".xls"]:
                ui.notify("BiolectorXT requires XLS/XLSX file.", type="negative")
                return
    
            if parse_type == "Gas Analyzer" and ext not in [".txt", ".csv", ".tsv"]:
                ui.notify("Gas Analyzer requires TXT/CSV/TSV file.", type="negative")
                return
    
            # -------------------------
            # SAVE TEMP FILE (ONLY RAW INPUT)
            # -------------------------
            temp_dir = tempfile.mkdtemp(dir=self.get_dir("temp"))
            raw_path = os.path.join(temp_dir, self.filename)
    
            with open(raw_path, "wb") as f:
                f.write(self.file_content)
    
            equipment = self.get_parse_equipment()
    
            # -------------------------
            # PARSE DIRECTLY ? DATAFRAME
            # -------------------------
            if equipment == "Gas Analyzer":

                if not hasattr(self, "selected_json_config") or not self.selected_json_config:
                    ui.notify("Select JSON config first", type="warning")
                    return
            
                params = self.selected_json_config
            
                df = parse_gas_analyzer(
                    file_path=raw_path,
                    experiment_start_date=params["start_date"],
                    target_channel=params["target"],
                    reference_channel=params["reference"],
                )
    
            elif equipment == "BioLectorXT":
    
                df = parse_biolector_xt(raw_path)
    
            else:  # OTHER
    
                delimiter_map = {
                    "Comma": ",",
                    "Tab": "\t",
                    "Space": " "
                }
    
                delimiter = delimiter_map.get(
                    self.delimiter_select.value,
                    ","
                )
    
                df = parse_other(
                    file_path=raw_path,
                    delimiter=delimiter
                )
    
            # -------------------------
            # CACHE
            # -------------------------
            if "parsed_cache" not in self.storage:
                self.storage["parsed_cache"] = {}
            
            df_safe = self.make_json_safe(df)
            
            self.storage["parsed_cache"][self.filename] = df_safe.to_dict(
                orient="records"
            )
            
            # -------------------------
            # STORE ORIGINAL SNAPSHOT (NEW)
            # -------------------------
            if "original_cache" not in self.storage:
                self.storage["original_cache"] = {}
            
            df_original = df_safe.copy()
            
            self.storage["original_cache"][self.filename] = df_original.to_dict(
                orient="records"
            )
    
            # -------------------------
            # SET ACTIVE DF
            # -------------------------
            df = self.make_json_safe(df)
            
            print("DEBUG DF SHAPE IN GUI:", df.shape)
            
            self.df = df.copy()
            self.current_df = df.copy()
            self.original_df = df.copy()
    
            self.save_global_df()
            self.validate_dataset()
            self.refresh_status()
            
            self.show_uploaded_files()
            self.refresh_preview()
    
            ui.notify("Parsing completed successfully", type="info")
    
        except Exception as ex:
    
            logger.error(traceback.format_exc())
    
            ui.notify(
                f"Parse failed: {str(ex)}",
                type="negative"
            )

    # ==================================================
    # SAVE GLOBAL DF
    # ==================================================
    def save_global_df(self):
    
        if self.current_df is None:
            return
    
        df = self.current_df
    
        df = self.make_json_safe(df)
    
        self.storage["parsed_df_json"] = df.to_dict(
            orient="records"
        )
    
        self.storage["parsed_df_columns"] = list(df.columns)
        self.storage["parsed_filename"] = self.filename
    
        self.storage["df_json"] = self.storage["parsed_df_json"]
        self.storage["df_columns"] = self.storage["parsed_df_columns"]
        
    # ==================================================
    # SAVE TO CACHE (NEW FUNCTION)
    # ==================================================
    def save_current_to_cache(self):
    
        if not self.filename or self.current_df is None:
            return
    
        if "parsed_cache" not in self.storage:
            self.storage["parsed_cache"] = {}
        
        df_safe = self.make_json_safe(self.current_df)
        
        self.storage["parsed_cache"][self.filename] = df_safe.to_dict(orient="records")
        
        # ALSO UPDATE ACTIVE STORAGE (IMPORTANT)
        self.storage["parsed_df_json"] = df_safe.to_dict(orient="records")
        self.storage["parsed_df_columns"] = list(df_safe.columns)
        self.storage["parsed_filename"] = self.filename
        
        self.show_uploaded_files()
        self.refresh_preview()

    # ==================================================
    # DATA CLEANING
    # ==================================================
    def show_data_cleaning(self):

        if self.cleaning_container is None:
            return

        self.cleaning_container.clear()

        with self.cleaning_container:

            ui.separator()

            # =========================
            # FIRST ROW
            # =========================
            with ui.row().classes("w-full items-center gap-2"):
            
                ui.button(
                    "REMOVE EMPTY ROWS",
                    icon="cleaning_services",
                    on_click=self.remove_empty_rows_ui,
                )
            
                ui.button(
                    "REMOVE DUPLICATES",
                    icon="content_copy",
                    on_click=self.remove_duplicates_ui,
                )
            
                ui.button(
                    "TRIM WHITESPACE",
                    icon="format_clear",
                    on_click=self.trim_whitespace_ui,
                )
            
                ui.button(
                    "FILL VALUES",
                    icon="auto_fix_high",
                    on_click=self.open_fill_dialog,
                )
            
            # =========================
            # SECOND ROW
            # =========================
            with ui.row().classes("w-full items-center gap-2"):
            
                ui.button(
                    "RESET ORIGINAL",
                    icon="restart_alt",
                    on_click=self.reset_original,
                ).classes("transition-all")
            
                ui.button(
                    "CHECK DATA TYPES",
                    on_click=self.check_column_types
                )
            
                ui.button(
                    "AUTO FIX DATASET",
                    icon="build",
                    color="orange",
                    on_click=self.auto_fix_dataset,
                ).classes("text-white")
            
                ui.space()
                
                self.output_format = ui.select(
                    ["CSV", "TSV", "XLSX", "JSON"],
                    value="CSV",
                    label="Convert To",
                ).classes("w-44")
            
                ui.button(
                    icon="download",
                    color="negative",
                    on_click=self.convert_and_download,
                )
                
    def check_column_types(self):

        if self.current_df is None or self.current_df.empty:
            ui.notify("No dataset loaded", type="warning")
            return
    
        df = self.current_df.copy()
    
        inconsistent_cols = []
    
        for col in df.columns:
    
            # drop NaN
            values = df[col].dropna()
    
            if values.empty:
                continue
    
            # get unique types
            types = set(type(v) for v in values)
    
            # normalize numpy types
            normalized_types = set()
    
            for t in types:
                name = t.__name__
    
                if "int" in name:
                    normalized_types.add("int")
                elif "float" in name:
                    normalized_types.add("float")
                elif "str" in name:
                    normalized_types.add("str")
                else:
                    normalized_types.add(name)
    
            # detect inconsistency
            if len(normalized_types) > 1:
                inconsistent_cols.append((col, list(normalized_types)))
    
        # -----------------------------
        # RESULT
        # -----------------------------
        if not inconsistent_cols:
            ui.notify("All columns have consistent data types", type="info")
            return
    
        # build message
        msg = "\n".join([
            f"{col}: {types}" for col, types in inconsistent_cols
        ])
    
        ui.notify(f"Inconsistent columns:\n{msg}", type="warning")
        
    # ==================================================
    # COLUMN CONFIG
    # ==================================================
    def show_column_config(self):
    
        # -------------------------
        # SAFETY
        # -------------------------
        if self.column_container is None:
            return
    
        self.column_container.clear()
    
        if self.current_df is None:
            return
    
        df = self.current_df
    
        # ==================================================
        # UI
        # ==================================================
        with self.column_container:
    
            ui.separator()
    
            ui.label("Column Renaming").classes(
                "text-h6 font-bold"
            )
    
            # ==================================================
            # HEADER
            # ==================================================
            with ui.row().classes(
                "w-full items-center gap-2 mb-2"
            ):
    
                ui.label("Column").classes(
                    "font-bold min-w-[220px]"
                )
    
                ui.label("Rename").classes(
                    "font-bold flex-grow"
                )
    
                ui.label("Delete").classes(
                    "font-bold w-16 text-center"
                )
    
            ui.separator()
    
            # ==================================================
            # COLUMN ROWS
            # ==================================================
            with ui.column().classes(
                "w-full gap-2"
            ):
    
                for col in df.columns:
    
                    with ui.row().classes(
                        "w-full items-center gap-2"
                    ):
    
                        # -------------------------
                        # COLUMN NAME
                        # -------------------------
                        ui.label(str(col)).classes(
                            "min-w-[220px]"
                        )
    
                        # -------------------------
                        # RENAME INPUT
                        # -------------------------
                        ui.input(
                            value=str(col),
    
                            on_change=lambda e, c=col:
                            self.rename_column(
                                c,
                                e.value,
                            ),
    
                        ).classes(
                            "flex-grow"
                        )
    
                        # -------------------------
                        # DELETE COLUMN BUTTON
                        # -------------------------
                        ui.button(
    
                            icon="delete",
    
                            color="negative",
    
                            on_click=lambda _, c=col:
                            self.delete_column(c),
    
                        ).props(
                            "flat round dense"
                        ).tooltip(
                            f"Delete column: {col}"
                        )

    def set_col_type(self, col, val):
        self.column_types[col] = val

    def rename_column(self, old, new):

        if self.current_df is None:
            return
    
        new = str(new).strip()
    
        if not new:
            return
    
        if old == new:
            return
    
        if new in self.current_df.columns:
            return
    
        self.current_df = self.current_df.rename(
            columns={old: new}
        )
    
        self.df = self.current_df
    
        self.save_global_df()
        self.save_current_to_cache()
        self.mark_dirty()
        self.refresh_status()
        
    def delete_column(self, col):

        try:
    
            if self.current_df is None:
                self.safe_notify("No dataset loaded", "warning")
                return
    
            if col not in self.current_df.columns:
                self.safe_notify(f"Column '{col}' not found", "warning")
                return
    
            # -------------------------
            # DELETE COLUMN
            # -------------------------
            self.current_df = self.current_df.drop(columns=[col])
    
            self.df = self.current_df.copy()
    
            # -------------------------
            # UPDATE STORAGE
            # -------------------------
            self.save_global_df()
            self.save_current_to_cache()
    
            # -------------------------
            # SAFE NOTIFY FIRST
            # -------------------------
            self.safe_notify(
                f"Deleted column: {col}",
                "warning"
            )
    
            # -------------------------
            # REFRESH UI
            # -------------------------
            self.safe_refresh()
    
        except Exception as e:
    
            self.safe_notify(
                f"Delete failed: {str(e)}",
                "negative"
            )
                
    def open_fill_dialog(self):

        import pandas as pd
        import numpy as np
    
        if self.current_df is None:
            return
    
        # =====================================================
        # METHODS
        # =====================================================
        methods = {
            "Forward Fill (previous value)": "ffill",
            "Backward Fill": "bfill",
            "Linear Interpolation": "linear",
            "Time Interpolation": "time",
            "Index Interpolation": "index",
            "Nearest": "nearest",
            "Zero": "zero",
            "Quadratic": "quadratic",
            "Cubic": "cubic",
            "Spline": "spline",
            "Polynomial": "polynomial",
        }
    
        # =====================================================
        # SAFE NOTIFY
        # =====================================================
        def safe_notify(msg, t="info"):
    
            try:
                ui.notify(msg, type=t)
            except:
                print(msg)
    
        # =====================================================
        # DIALOG
        # =====================================================
        with ui.dialog() as dialog:
    
            with ui.card().classes("w-[500px]"):
    
                ui.label(
                    "Fill Missing Values"
                ).classes("text-h6")
    
                # =================================================
                # METHOD SELECT
                # =================================================
                selected_method = ui.select(
                    options=list(methods.keys()),
                    value="Forward Fill (previous value)",
                    label="Fill Method"
                ).classes("w-full")
    
                # =================================================
                # ORDER INPUT
                # =================================================
                order_input = ui.number(
                    label="Order (for polynomial/spline)",
                    value=2,
                ).classes("w-full")
    
                order_input.visible = False
    
                # =================================================
                # METHOD CHANGE
                # =================================================
                def on_change():
    
                    method = methods[selected_method.value]
    
                    order_input.visible = (
                        method in [
                            "polynomial",
                            "spline"
                        ]
                    )
    
                selected_method.on(
                    "update:model-value",
                    lambda e: on_change()
                )
    
                # =================================================
                # APPLY FILL
                # =================================================
                def apply_fill():
    
                    try:
    
                        df = self.current_df.copy()
    
                        method = methods[selected_method.value]
    
                        # =============================================
                        # CLEAN EMPTY STRINGS
                        # =============================================
                        df = df.replace("", np.nan)
    
                        # =============================================
                        # SORT DATA
                        # =============================================
                        sort_cols = []
    
                        if "well" in df.columns:
                            sort_cols.append("well")
    
                        if "time [h]" in df.columns:
                            sort_cols.append("time [h]")
    
                        if sort_cols:
                            df = df.sort_values(sort_cols)
    
                        # =============================================
                        # FIX DATETIME
                        # =============================================
                        if "datetime" in df.columns:
    
                            df["datetime"] = pd.to_datetime(
                                df["datetime"],
                                errors="coerce"
                            )
    
                            df["datetime"] = (
                                df["datetime"]
                                .ffill()
                                .bfill()
                            )
    
                        # =============================================
                        # GLOBAL COLUMNS
                        # =============================================
                        global_cols = [
    
                            "Temp [C]",
                            "CO2 [%]",
                            "Shaker [rpm]",
    
                            "TotalWellVolume [uL]",
                            "FedVol_ResA [uL]",
                            "FedVol_ResB [uL]",
                            "FedVol_Robo [uL]"
                        ]
    
                        for col in global_cols:
    
                            if col not in df.columns:
                                continue
    
                            df[col] = pd.to_numeric(
                                df[col],
                                errors="coerce"
                            )
    
                            df[col] = (
                                df[col]
                                .ffill()
                                .bfill()
                            )
    
                        # =============================================
                        # SENSOR COLUMNS
                        # =============================================
                        sensor_cols = [
    
                            "pH calibrated [unit]",
                            "pH raw [unit]",
    
                            "pO2 calibrated [unit]",
                            "pO2 raw [unit]",
    
                            "Biomass_1 calibrated [unit]",
                            "Biomass_1 raw [unit]",
    
                            "Biomass_3 calibrated [unit]",
                            "Biomass_3 raw [unit]",
    
                            "Biomass_6 calibrated [unit]",
                            "Biomass_6 raw [unit]",
    
                            "Fluoresceine_5 calibrated [unit]",
                            "Fluoresceine_5 raw [unit]"
                        ]
    
                        # =============================================
                        # PER-WELL FILL
                        # =============================================
                        if "well" in df.columns:
    
                            for col in sensor_cols:
    
                                if col not in df.columns:
                                    continue
    
                                df[col] = pd.to_numeric(
                                    df[col],
                                    errors="coerce"
                                )
    
                                df[col] = (
                                    df.groupby("well")[col]
                                    .transform(
                                        lambda x:
                                        x.ffill().bfill()
                                    )
                                )
    
                        # =============================================
                        # APPLY USER METHOD
                        # =============================================
                        if method == "ffill":
    
                            df = df.ffill()
    
                        elif method == "bfill":
    
                            df = df.bfill()
    
                        else:
    
                            numeric_cols = df.select_dtypes(
                                include=["number"]
                            ).columns
    
                            # -----------------------------------------
                            # POLYNOMIAL / SPLINE
                            # -----------------------------------------
                            if method in ["polynomial", "spline"]:
    
                                df[numeric_cols] = (
                                    df[numeric_cols]
                                    .interpolate(
                                        method=method,
                                        order=int(order_input.value)
                                    )
                                )
    
                            # -----------------------------------------
                            # TIME INTERPOLATION
                            # -----------------------------------------
                            elif method == "time":
    
                                if "datetime" in df.columns:
    
                                    try:
    
                                        temp_df = df.copy()
    
                                        temp_df = temp_df.set_index(
                                            "datetime"
                                        )
    
                                        temp_df[numeric_cols] = (
                                            temp_df[numeric_cols]
                                            .interpolate(method="time")
                                        )
    
                                        df = temp_df.reset_index()
    
                                    except Exception as e:
    
                                        dialog.close()
    
                                        safe_notify(
                                            f"Time interpolation failed: {str(e)}",
                                            "negative"
                                        )
    
                                        return
    
                                else:
    
                                    dialog.close()
    
                                    safe_notify(
                                        "No datetime column",
                                        "warning"
                                    )
    
                                    return
    
                            # -----------------------------------------
                            # OTHER METHODS
                            # -----------------------------------------
                            else:
    
                                try:
    
                                    df[numeric_cols] = (
                                        df[numeric_cols]
                                        .interpolate(method=method)
                                    )
    
                                except Exception as e:
    
                                    dialog.close()
    
                                    safe_notify(
                                        f"Interpolation failed: {str(e)}",
                                        "negative"
                                    )
    
                                    return
    
                        # =============================================
                        # FINAL CLEAN
                        # =============================================
                        numeric_cols = df.select_dtypes(
                            include=["number"]
                        ).columns
    
                        df[numeric_cols] = (
                            df[numeric_cols]
                            .ffill()
                            .bfill()
                        )
    
                        # Replace remaining NaNs
                        df[numeric_cols] = (
                            df[numeric_cols]
                            .fillna(0)
                        )
    
                        # =============================================
                        # FINAL SORT
                        # =============================================
                        final_sort = []
    
                        if "time [h]" in df.columns:
                            final_sort.append("time [h]")
    
                        if "well" in df.columns:
                            final_sort.append("well")
    
                        if final_sort:
                            df = df.sort_values(final_sort)
    
                        df = df.reset_index(drop=True)
    
                        # =============================================
                        # UPDATE DATA
                        # =============================================
                        self.current_df = df
                        self.df = df.copy()
    
                        # =============================================
                        # DEBUG
                        # =============================================
                        print("\n===== AFTER FILL VALUES =====")
                        print(df.head())
    
                        print("\n===== NaN COUNT =====")
                        print(df.isna().sum())
    
                        # =============================================
                        # CLOSE DIALOG
                        # =============================================
                        dialog.close()
    
                        # =============================================
                        # REFRESH UI
                        # =============================================
                        ui.timer(
                            0.1,
                            lambda: self._post_fill_update(method),
                            once=True
                        )
    
                    except Exception as e:
    
                        dialog.close()
    
                        safe_notify(
                            f"Fill failed: {str(e)}",
                            "negative"
                        )
    
                        print("\n===== FILL ERROR =====")
                        print(str(e))
    
                # =================================================
                # BUTTONS
                # =================================================
                with ui.row().classes(
                    "w-full justify-end"
                ):
    
                    ui.button(
                        "Apply",
                        on_click=apply_fill
                    )
    
                    ui.button(
                        "Cancel",
                        on_click=dialog.close
                    )
    
        dialog.open()
        
    def _post_fill_update(self, method):

        try:
    
            # =====================================================
            # FIX TIMESTAMP JSON ERROR
            # =====================================================
            if self.current_df is not None:
    
                if "datetime" in self.current_df.columns:
    
                    self.current_df["datetime"] = (
                        self.current_df["datetime"]
                        .astype(str)
                    )
    
                self.df = self.current_df.copy()
    
            # =====================================================
            # SAVE
            # =====================================================
            self.save_global_df()
    
            self.save_current_to_cache()
    
            # =====================================================
            # MARK DIRTY
            # =====================================================
            self.mark_dirty()
    
            # =====================================================
            # REFRESH UI
            # =====================================================
            self.refresh_status()
    
            try:
                self.refresh_table()
            except:
                pass
    
            # =====================================================
            # NOTIFY
            # =====================================================
            try:
    
                ui.notify(
                    f"Filled using: {method}",
                    type="info"
                )
    
            except:
    
                print(f"Filled using: {method}")
    
        except Exception as e:
    
            print("\n===== POST FILL UPDATE ERROR =====")
            print(str(e)) 
               
    # ==================================================
    # CLEANING ACTIONS
    # ==================================================
    def remove_empty_rows_ui(self):

        if self.current_df is None:
            return
    
        self.current_df = self.current_df.dropna(how="all")
    
        self.df = self.current_df
    
        self.save_global_df()
        self.save_current_to_cache()
        self.mark_dirty()
        self.refresh_status()
    
    
    def remove_duplicates_ui(self):

        if self.current_df is None:
            return
    
        self.current_df = self.current_df.drop_duplicates()
    
        self.df = self.current_df
    
        self.save_global_df()
        self.save_current_to_cache()
        self.mark_dirty()
        self.refresh_status()
    
    
    def trim_whitespace_ui(self):

        if self.current_df is None:
            return
    
        for c in self.current_df.columns:
            if self.current_df[c].dtype == object:
                self.current_df[c] = self.current_df[c].astype(str).str.strip()
    
        self.df = self.current_df
    
        self.save_global_df()
        self.mark_dirty()
        self.refresh_status()
    
    def reset_original(self):

        try:
            # -------------------------
            # GET ACTIVE FILE
            # -------------------------
            filename = self.storage.get("last_loaded_file")
    
            if not filename:
                ui.notify("No active dataset", type="warning")
                return
    
            # -------------------------
            # CHECK ORIGINAL CACHE
            # -------------------------
            original_cache = self.storage.get("original_cache", {})
    
            if filename not in original_cache:
                ui.notify("Original dataset not found in memory", type="negative")
                return
    
            # -------------------------
            # RESTORE DATAFRAME
            # -------------------------
            df = pd.DataFrame(original_cache[filename])
            df = self.make_json_safe(df)
    
            # -------------------------
            # SET STATE
            # -------------------------
            self.current_df = df.copy()
            self.df = df.copy()
            self.original_df = df.copy()
    
            # -------------------------
            # UPDATE PARSED CACHE (IMPORTANT)
            # -------------------------
            if "parsed_cache" not in self.storage:
                self.storage["parsed_cache"] = {}
    
            self.storage["parsed_cache"][filename] = df.to_dict("records")
    
            # -------------------------
            # SAVE GLOBAL STATE
            # -------------------------
            self.save_global_df()
    
            # -------------------------
            # NOTIFY BEFORE UI REBUILD (CRITICAL FIX)
            # -------------------------
            ui.notify("Dataset restored to original state", type="info")
    
            # -------------------------
            # SAFE UI REFRESH
            # -------------------------
            self.safe_refresh()
    
            # -------------------------
            # BUTTON VISUAL FEEDBACK
            # -------------------------
            if hasattr(self, "reset_btn") and self.reset_btn:
                try:
                    self.reset_btn.props("color=negative")
                except:
                    pass
    
        except Exception as e:
            ui.notify(f"Reset failed: {str(e)}", type="negative")
    
    # ==================================================
    # SHOW MISSING VALUES
    # ==================================================
    def show_missing_values(self):
    
        if self.current_df is None:
    
            ui.notify(
                "No dataset loaded",
                type="warning"
            )
    
            return
    
        df = self.current_df.copy()
    
        # ------------------------------------------------
        # CALCULATE MISSING
        # ------------------------------------------------
        missing = df.isna().sum()
    
        # ALSO COUNT EMPTY STRINGS
        for col in df.columns:
    
            empty_count = (
                df[col]
                .astype(str)
                .str.strip()
                .eq("")
                .sum()
            )
    
            missing[col] += empty_count
    
        missing = missing[missing > 0]
    
        total_missing = int(missing.sum())
    
        # ------------------------------------------------
        # DIALOG
        # ------------------------------------------------
        with ui.dialog() as dialog:
    
            with ui.card().classes("w-[900px]"):
    
                ui.label(
                    "Missing Values Report"
                ).classes(
                    "text-h5 font-bold"
                )
    
                # ----------------------------------------
                # CLEAN DATASET
                # ----------------------------------------
                if total_missing == 0:
    
                    ui.label(
                        "Dataset is clean."
                    ).classes(
                        "text-green text-h6"
                    )
    
                    ui.notify(
                        "No missing values found",
                        type="info"
                    )
    
                # ----------------------------------------
                # MISSING VALUES FOUND
                # ----------------------------------------
                else:
    
                    report_df = pd.DataFrame({
    
                        "Column":
                            missing.index,
    
                        "Missing Values":
                            missing.values,
    
                        "Percentage (%)":
                            (
                                missing.values
                                / len(df)
                                * 100
                            ).round(2)
                    })
    
                    ui.label(
                        f"Total Missing Values: {total_missing}"
                    ).classes(
                        "text-red"
                    )
    
                    ui.table(
    
                        columns=[
    
                            {
                                "name": "Column",
                                "label": "Column",
                                "field": "Column"
                            },
    
                            {
                                "name": "Missing Values",
                                "label": "Missing Values",
                                "field": "Missing Values"
                            },
    
                            {
                                "name": "Percentage (%)",
                                "label": "Percentage (%)",
                                "field": "Percentage (%)"
                            }
                        ],
    
                        rows=report_df.to_dict(
                            "records"
                        ),
    
                        pagination=20
    
                    ).classes(
                        "w-full text-xs"
                    )
    
                    ui.notify(
                        f"{total_missing} missing values found",
                        type="warning"
                    )
    
                # ----------------------------------------
                # CLOSE BUTTON
                # ----------------------------------------
                with ui.row().classes(
                    "w-full justify-end"
                ):
    
                    ui.button(
                        "Close",
                        on_click=dialog.close
                    )
    
        dialog.open()
        
    # ==================================================
    # VALIDATE
    # ==================================================
    def validate_dataset(self):

        if self.current_df is None:
            return
    
        self.validation_label.text = (
            f"{len(self.current_df)} rows loaded.\n"
            f"{len(self.current_df.columns)} columns.\n"
            f"Dataset accepted."
        )

    # ==================================================
    # AUTO FIX
    # ==================================================
    def auto_fix_dataset(self):

        if self.current_df is None:
            return
    
        self.current_df = self.current_df.dropna(how="all")
        self.current_df = self.current_df.drop_duplicates()
    
        for c in self.current_df.columns:
            if self.current_df[c].dtype == object:
                self.current_df[c] = self.current_df[c].astype(str).str.strip()
    
        self.current_df = self.current_df.replace("nan", np.nan)
        self.current_df = self.current_df.fillna("")
    
        self.df = self.current_df
    
        self.save_global_df()
        self.save_current_to_cache()
        self.mark_dirty()
        self.refresh_status()

    # ==================================================
    # EXPORT
    # ==================================================
    def convert_and_download(self):
    
        if self.current_df is None:
            return
    
        df = self.current_df
        fmt = self.output_format.value
    
        export_dir = self.DIRS["exports"]
        filename = f"converted_dataset.{fmt.lower()}"
        path = os.path.join(export_dir, filename)
    
        if fmt == "CSV":
            df.to_csv(path, index=False)
    
        elif fmt == "TSV":
            df.to_csv(path, sep="\t", index=False)
    
        elif fmt == "XLSX":
            df.to_excel(path, index=False)
    
        else:
            df.astype(str).to_json(
                path,
                orient="records",
                indent=2,
            )
    
        ui.download(path)

    # ==================================================
    # PREVIEW
    # ==================================================
    def refresh_preview(self):

        if self.preview_container is None:
            return
    
        self.preview_container.clear()
    
        with self.preview_container:
    
            # ALWAYS USE CURRENT DF (NO FALLBACK TO OLD CACHE)
            if self.current_df is None:
                ui.label("No dataset loaded.")
                return
    
            df = self.current_df
    
            # ---- STATS ----
            ui.label(f"Rows: {len(df)} | Columns: {len(df.columns)}")
    
            # ---- LIMIT PREVIEW ----
            MAX_COLS = 10
            preview_cols = df.columns[:MAX_COLS]
    
            # ---- TABLE ----
            ui.table(
                columns=[
                    {"name": c, "label": c, "field": c}
                    for c in preview_cols
                ],
                rows=df[preview_cols].to_dict("records"),
                pagination=10,
            )
            
    def force_refresh(self):

        try:
            # reload shared storage
            if "shared_data" in app.storage.general:
                self.storage = app.storage.general["shared_data"]
    
            # full UI refresh
            self.show_uploaded_files()
            self.refresh_preview()
    
            ui.notify("Refreshed", type="info")
    
        except Exception as e:
            ui.notify(f"Refresh failed: {str(e)}", type="negative")
    # ==================================================
    # STATUS
    # ==================================================

    def refresh_status(self):

        self.refresh_preview()
        self.show_data_cleaning()
        self.show_column_config()
    
    def safe_refresh(self):
        try:
            self.refresh_status()
        except Exception as e:
            print("SAFE REFRESH ERROR:", e)   
            
    def safe_notify(self, msg, t="info"):
        try:
            ui.notify(msg, type=t)
        except Exception as e:
            print("SAFE NOTIFY ERROR:", e)
            
    # ==================================================
    # CLEAR
    # ==================================================
    def clear_memory(self):

        # -------------------------
        # CLEAR STORAGE
        # -------------------------
        self.storage["files"] = {}
        self.storage["parsed_df_json"] = []
        self.storage["parsed_df_columns"] = []
        self.storage["parsed_filename"] = ""
        self.storage["df_json"] = []
        self.storage["df_columns"] = []
        self.storage["parsed_cache"] = {}
    
        # -------------------------
        # CLEAR LOCAL STATE
        # -------------------------
        self.current_df = None
        self.df = None
        self.original_df = None
        self.file_buffers = {}
    
        # -------------------------
        # DELETE UPLOADED FILES (IMPORTANT)
        # -------------------------
        upload_dir = self.DIRS.get("uploads")
    
        if upload_dir and os.path.exists(upload_dir):
            for f in os.listdir(upload_dir):
                try:
                    os.remove(os.path.join(upload_dir, f))
                except:
                    pass
    
        # -------------------------
        # UI REFRESH
        # -------------------------
        self.show_uploaded_files()
        self.refresh_status()
    
        if self.validation_label:
            self.validation_label.text = "No dataset loaded."
    
        ui.notify("Memory fully cleared", type="info")