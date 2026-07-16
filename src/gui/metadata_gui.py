"""Metadata GUI module.

Provides a user interface to view, edit, validate, and manage metadata
schemas and protocols following the ISA/MIM structure for fermentation experiments.
"""

from nicegui import ui
import pandas as pd
import json
import os

from copy import deepcopy
from datetime import datetime

import src.utils.theme as theme
from src.utils.paths import ensure_dirs


class NewProtocol:
    """Manages the metadata builder and protocol schema editing interface.

    Attributes:
        storage: Data storage container dict.
        dynamic_inputs: Dictionary mapping fields to their input widgets.
        section_memory: Cache of metadata sections in the form interface.
        current_selected_objects: Dictionary mapping section names to selected object IDs.
        is_loading_object: Flag indicating if an object is currently being loaded.
        is_refreshing_selectors: Flag indicating if selectors are being refreshed.
        dataset_info: UI label displaying the active JSON filename.
        score_label: UI label displaying status information.
        loaded_json: Nested dictionary of all protocol sections and objects.
        current_json_name: The filename of the currently active JSON file.
        json_dirty: Flag indicating if the active JSON has unsaved changes.
        json_created: Flag indicating if a new JSON was initialized.
        data_: Internal memory representation of the metadata.
        field_descriptions: Help text tooltips for specific metadata terms.
        protocol_schema: Defined field terms and their validation rules.
    """

    # =====================================================
    # INIT
    # =====================================================
    def __init__(self, storage_container=None):
        """Initializes the NewProtocol.

        Args:
            storage_container: Optional primary data storage dictionary.
        """

        self.storage = storage_container or {}
    
        # =================================================
        # SESSION JSON CACHE
        # =================================================
        if "loaded_json_cache" not in self.storage:
    
            self.storage["loaded_json_cache"] = {}
    
        self.dynamic_inputs = {}
    
        self.section_memory = {}
    
        self.current_selected_objects = {}
        
        self.is_loading_object = False
        self.is_refreshing_selectors = False
        
        self.dataset_info = None
        self.score_label = None

        # =================================================
        # NEW JSON STORAGE
        # =================================================
        self.loaded_json = {
            "Investigations": {},
            
                "Studies": {},
            
                "observationUnits": {},
            
                "Samples": {},
            
                "Assays": {}
        }
        

                
        self.current_json_name = None
        self.json_dirty = False
        self.json_created = False

        self.data_ = {

            "File name": "",
            "Updated": "",
            "Investigations": {}
        }

        # =================================================
        # FIELD DESCRIPTIONS
        # =================================================
        self.field_descriptions = {

            "Target Metabolite":
                "Desired metabolite or product produced.",

            "Temperature":
                "Fermentation process temperature.",

            "pH":
                "Acidity or alkalinity of the cultivation medium.",

            "pO2":
                "Partial oxygen pressure inside the reactor.",

            "Feed Flow Rate":
                "Rate of substrate feed addition.",

            "Agitation Rate":
                "Impeller or shaker agitation speed.",

            "Aeration Rate":
                "Gas or air supply flow rate.",

            "Sample Storage Temperature":
                "Temperature used for sample preservation.",

            "Protocol URL":
                "Link to the protocol documentation."
        }

        # =================================================
        # ISA / MIM STRUCTURE
        # =================================================
        self.protocol_schema = {

            "Investigation": [

                ("Title", "{text}"),
                ("Description", "{text}"),
                ("Start Date", "{date}"),
                ("End Date", "{date}"),
                ("References", "{text}")
            ],

            "Study": [

                ("Title", "{text}"),
                ("Description", "{text}"),
                ("Start Date", "{date}"),
                ("End Date", "{date}"),
                ("Target Metabolite", "{text}")
            ],

            "observationUnit": [
            
                ("Title", "{text}"),
                ("Description", "{text}"),
            
                ("Start Date", "{date}"),
                ("End Date", "{date}"),
            
                ("Internal ID", "{id}"),
                ("Protocol", "{URL}"),
            
                ("Culture Collection ID", "(DSM|ATCC|CBS) \\+?(?:[1-9]\\d*|0(?!(?:\\.0+)?$))?(?:\\.\\d+)?+"),
            
                ("Designations", "{text}"),
                ("Source", "{text}"),
            
                ("Organism", "{text}"),
                ("Species", "{text}"),
            
                ("Taxonomy ID", "{NCBI taxid}"),
            
                ("Local ID", "{id}"),
                ("BacDive ID", "{positive number}"),
            
                ("Sequence Accession Number", "{id}"),
            
                ("Biosafety Level", "(1|2|3|4|unknown)"),
            
                ("Pathogenicity", "(human|animal|plant|none|unknown)"),
            
                ("GMO", "{boolean}"),
            
                ("Modifications", "{text}"),
            
                ("Resistance", "{text}"),
                ("Resistance MIC", "{number}"),
            
                ("Oxygen Dependence", "{text}"),
            
                ("Morphology",
                 "(rod-shaped|coccus-shaped|ring-shaped|ovoid-shaped|spiral-shaped|filament-shaped|helical-shaped|vibrio-shaped|surrounded by sheath-like structure|sphere-shaped|curved-shaped|pleomorphic-shaped|oval-shaped|crescent-shaped|disc-shaped|flask-shaped|square-shaped|star-shaped|spore-shaped|spindel-shaped|bean-shaped|dumbbell-shaped|ellipsoidal|bent-rod shaped|cylindrical-shaped|other)"
                ),
            
                ("Sporulation", "{boolean}"),
            
                ("Feed Type", "(liquid|solid|gas)"),
            
                ("Feed Weight", "{positive number}"),
            
                ("Compound Name", "{text}"),
                ("Concentration", "{positive number}"),
            
                ("Feed Flow Rate", "{positive number}"),
            
                ("Control Scheme", "{text}"),
                ("Input Localisation", "{text}"),
            
                ("Phase", "(lag phase|log phase|stationary phase)"),
            
                ("Phase Purpose", "{text}"),
            
                ("Phase Start Time", "{timestamp}"),
                ("Phase End Time", "{timestamp}"),
            
                ("Phase Duration", "{positive number}"),
            
                ("Temperature", "{number}"),
            
                ("pH", "{positive number}"),
            
                ("pO2", "{positive number}"),
            
                ("pCO2", "{positive number}"),
            
                ("pRedox", "{positive number}"),
            
                ("Volume", "{integer}"),
            
                ("Pressure", "{number}"),
            
                ("Weight", "{number}"),
            
                ("Substrate Flow Rate", "{number}"),
            
                ("Acid Type", "{text}"),
                ("Base Type", "{text}"),
                ("Antifoam Type", "{text}"),
            
                ("Acid Weight", "{positive number}"),
                ("Base Weight", "{positive number}"),
                ("Antifoam Weight", "{positive number}"),
            
                ("Harvest Weight", "{positive number}"),
            
                ("Acid Flow Rate", "{number}"),
                ("Base Flow Rate", "{number}"),
            
                ("Aeration Rate", "{number}"),
            
                ("Water Flow Rate", "{number}"),
            
                ("Harvest Flow Rate", "{number}"),
            
                ("Agitation Rate", "{number}"),
            
                ("Gas Flow Rate", "{number}"),
            
                ("Gas Input Composition", "{text}"),
            
                ("Relative Pressure", "{number}"),
            
                ("Fedbatch Type", "{text}"),
                ("Fedbatch Rate", "{number}"),
                ("Fedbatch Trigger", "{text}"),
            
                ("Induction Type", "{text}"),
                ("Induction Trigger", "{text}"),
            
                ("Induction Trigger Duration", "{positive number}"),
            
                ("Induction Rate", "{positive number}"),
            
                ("Cultivation Type", "(batch|fed-batch|continuous)"),
            
                ("Inoculum Type", "{text}"),
            
                ("Preculture Medium", "{text}"),
            
                ("Inoculum Composition", "{text}"),
            
                ("Harvesting Conditions", "{text}"),
            
                ("Concentration Method", "{text}"),
            
                ("Purification Method", "{text}"),
            
                ("Preculture Description", "{text}"),
            
                ("Inoculum Duration", "{positive number}"),
            
                ("Temperature Of Inoculum", "{number}"),
            
                ("Amount Of Inoculum", "{text}"),
            
                ("Initial Working Volume", "{number}"),
            
                ("Dilution Rate", "{number}"),
            
                ("Inoculation Source", "{text}"),
            
                ("Target Metabolite", "{text}"),
            
                ("Replicate ID", "{text}"),
            
                ("Replicate Type", "{text}")
            ],

            "Sample": [

                ("Sample Name", "{text}"),
            
                ("Sample Description", "{text}"),
            
                ("Sampling Time Point", "{timestamp}"),
            
                ("Volume", "{positive number}"),
            
                ("Recipe URL", "{URL}"),
            
                ("Phase", "{text}"),
            
                ("Phase Purpose", "{text}"),
            
                ("Phase Duration", "{positive number}"),
            
                ("Replicate", "{text}"),
            
                ("Sample Material", "{text}"),
            
                ("Sample Material Processing", "{text}"),
            
                ("Sample Collection Device", "{text}"),
            
                ("Sample Collection Method", "{text}"),
            
                ("Sample Storage Buffer", "{text}"),
            
                ("Sample Storage Conditions", "{text}"),
            
                ("Sample Storage Container", "{text}"),
            
                ("Sample Storage Duration", "{positive number}"),
            
                ("Sample Storage Location", "{text}"),
            
                ("Sample Storage Temperature", "{number}"),
            
                ("Sample Treatment", "{text}"),
            
                ("Sample Wet Mass", "{positive number}"),
            
                ("Sample Dry Mass", "{positive number}")
            ],

            "Assay": [

                ("Title", "{text}"),
                ("Description", "{text}"),
                ("Start Date", "{date}"),
                ("End Date", "{date}"),
                ("Assay Type", "{text}"),
                ("Technology Type", "{text}"),
                ("Protocol URL", "{URL}")
            ]
        }

        self.load_memory()
        
    # =====================================================
    # MEMORY
    # =====================================================
    def save_memory(self):
        """Saves current state of data_ in session memory cache."""

        self.pull_ui()

        self.data_["Updated"] = str(
            datetime.now()
        )

        self.storage[
            "protocol_memory"
        ] = deepcopy(self.data_)

        ui.notify(
            "Protocol saved in memory",
            type="info"
        )

    def load_memory(self):
        """Loads data_ state from session memory cache if present."""

        if "protocol_memory" in self.storage:

            self.data_ = deepcopy(
                self.storage[
                    "protocol_memory"
                ]
            )
    # =====================================================
    # LOAD JSON
    # =====================================================
    async def load_json(self, e):
        """Loads metadata protocol dictionary from an uploaded JSON file.

        Args:
            e: Event dictionary containing the uploaded file reference.
        """

        try:
    
            # =============================================
            # READ FILE CONTENT
            # =============================================
            content = await e.file.read()
    
            # =============================================
            # CONVERT TO STRING
            # =============================================
            text_data = content.decode(
                "utf-8"
            )
    
            # =============================================
            # LOAD JSON
            # =============================================
            data = json.loads(
                text_data
            )
    
            # =============================================
            # FILE NAME
            # =============================================
            filename = getattr(
                e.file,
                "name",
                "loaded_protocol.json"
            )
    
            # =============================================
            # SAVE CURRENT JSON BEFORE UPLOADING NEW ONE
            # IMPORTANT:
            # silent=True prevents the dropdown from jumping
            # back to the previous JSON.
            # =============================================
            if (
                self.current_json_name
                and
                self.current_json_name != filename
            ):
    
                self.temp_save_current_json(
                    silent=True
                )
    
            # =============================================
            # SET LOADED JSON
            # =============================================
            self.loaded_json = deepcopy(
                data
            )
    
            # =============================================
            # UPDATE CURRENT JSON STATE
            # =============================================
            self.current_json_name = filename
    
            self.json_created = True
    
            self.json_dirty = False
    
            # =============================================
            # ENSURE CACHE EXISTS
            # =============================================
            if "loaded_json_cache" not in self.storage:
    
                self.storage[
                    "loaded_json_cache"
                ] = {}
    
            # =============================================
            # CACHE UPLOADED JSON
            # =============================================
            self.storage[
                "loaded_json_cache"
            ][filename] = deepcopy(
                data
            )
    
            # =============================================
            # CLEAR CURRENT UI BEFORE APPLYING NEW JSON
            # =============================================
            self.clear_dynamic_fields()
    
            # =============================================
            # UPDATE JSON DROPDOWN
            # =============================================
            if hasattr(
                self,
                "dataset_select"
            ):
    
                self.refresh_json_dropdown()
    
                self.dataset_select.value = filename
    
                self.dataset_select.update()
    
            # =============================================
            # REFRESH SECTION SELECTORS
            # This also loads the first object of each section.
            # =============================================
            if hasattr(
                self,
                "section_memory"
            ):
    
                self.refresh_section_selectors()
    
            # =============================================
            # LABELS
            # =============================================
            if self.dataset_info is not None:
    
                self.dataset_info.text = (
                    f"Loaded JSON: {filename}"
                )
    
            if self.score_label is not None:
    
                self.score_label.text = (
                    "JSON successfully loaded"
                )
    
            # =============================================
            # FORCE UI UPDATE
            # =============================================
            ui.update()
    
            # =============================================
            # SUCCESS
            # =============================================
            ui.notify(
                f"{filename} loaded successfully",
                type="info"
            )
    
            print("\n===== LOADED JSON =====")
    
            print(filename)
    
            print(
                json.dumps(
                    self.loaded_json,
                    indent=4,
                    ensure_ascii=False
                )
            )
    
        except Exception as ex:
    
            print(
                f"\nJSON LOAD ERROR:\n{ex}"
            )
    
            ui.notify(
                f"Failed to load JSON: {ex}",
                type="negative"
            )

    # =====================================================
    # EXPORT
    # =====================================================
    def export_protocol(self):
        """Exports the active metadata dictionary as a downloadable JSON file."""

        # =============================================
        # SAVE CURRENT UI STATE
        # =============================================
        self.pull_ui()
    
        # =============================================
        # SAVE ALL CURRENTLY OPEN OBJECTS
        # =============================================
        for section_name in [
    
            "Investigation",
            "Study",
            "observationUnit",
            "Sample",
            "Assay"
        ]:
    
            self.save_current_section_object(
                section_name
            )
    
        # =============================================
        # EXPORT DIRECTORY
        # =============================================
        export_dir = str(ensure_dirs()["exports"])
    
        # =============================================
        # FILE NAME
        # =============================================
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
    
        filename = (
            f"protocol_export_{timestamp}.json"
        )
    
        path = os.path.join(
            export_dir,
            filename
        )
    
        # =============================================
        # ROOT EXPORT STRUCTURE
        # =============================================
        export_data = {
    
            "File name": filename,
    
            "Updated": str(
                datetime.now()
            ),
    
            "Investigations": {},
    
            "Studies": {},
    
            "observationUnits": {},
    
            "Samples": {},
    
            "Assays": {}
        }
    
        # =============================================
        # ENSURE LOADED JSON EXISTS
        # =============================================
        if not isinstance(
            self.loaded_json,
            dict
        ):
    
            self.loaded_json = {}
    
        # =============================================
        # EXPORT COMPLETE MEMORY
        # =============================================
        export_data[
            "Investigations"
        ] = deepcopy(
    
            self.loaded_json.get(
                "Investigations",
                {}
            )
        )
    
        export_data[
            "Studies"
        ] = deepcopy(
    
            self.loaded_json.get(
                "Studies",
                {}
            )
        )
    
        export_data[
            "observationUnits"
        ] = deepcopy(
    
            self.loaded_json.get(
                "observationUnits",
                {}
            )
        )
    
        export_data[
            "Samples"
        ] = deepcopy(
    
            self.loaded_json.get(
                "Samples",
                {}
            )
        )
    
        export_data[
            "Assays"
        ] = deepcopy(
    
            self.loaded_json.get(
                "Assays",
                {}
            )
        )
    
        # =============================================
        # SAVE JSON FILE
        # =============================================
        with open(
    
            path,
    
            "w",
    
            encoding="utf-8"
    
        ) as fp:
    
            json.dump(
    
                export_data,
    
                fp,
    
                indent=4,
    
                ensure_ascii=False
            )
    
        # =============================================
        # AUTO REGISTER JSON INTO CACHE
        # =============================================
        if "loaded_json_cache" not in self.storage:
    
            self.storage[
                "loaded_json_cache"
            ] = {}
    
        self.storage[
            "loaded_json_cache"
        ][filename] = deepcopy(
            export_data
        )
    
        # =============================================
        # REFRESH DROPDOWN
        # =============================================
        self.refresh_json_dropdown()
    
        self.dataset_select.value = filename
    
        self.dataset_select.update()
    
        # =============================================
        # LABELS
        # =============================================
        if self.dataset_info is not None:

            self.dataset_info.text = (
                f"Exported JSON: {filename}"
            )
        
        if self.score_label is not None:
        
            self.score_label.text = (
                "Protocol exported successfully"
            )
    
        # =============================================
        # SUCCESS
        # =============================================
        ui.notify(
            "Full protocol exported",
            type="positive"
        )
    
        # =============================================
        # DEBUG PRINT
        # =============================================
        print("\n===== EXPORTED JSON =====")
    
        print(
            json.dumps(
                export_data,
                indent=4,
                ensure_ascii=False
            )
        )
    
        # =============================================
        # DOWNLOAD FILE
        # =============================================
        ui.download(path)
        
    # =====================================================
    # CLEAR EVERYTHING
    # =====================================================
    def clear_all(self):
        """Clears all form fields to default/empty values."""

        # =============================================
        # CLEAR UI INPUTS
        # =============================================
        for key, widgets in self.dynamic_inputs.items():
    
            try:
    
                value_widget = widgets[
                    "value_input"
                ]
    
                widget_class = value_widget.__class__.__name__.lower()
    
                if "number" in widget_class:
    
                    value_widget.value = None
    
                elif isinstance(
                    getattr(value_widget, "value", None),
                    bool
                ):
    
                    value_widget.value = False
    
                else:
    
                    value_widget.value = ""
    
                value_widget.update()
    
            except Exception as ex:
    
                print(
                    f"CLEAR ALL FIELD ERROR: {ex}"
                )
    
        # =============================================
        # CLEAR JSON MEMORY
        # =============================================
        self.loaded_json = {
    
            "Investigations": {},
    
            "Studies": {},
    
            "observationUnits": {},
    
            "Samples": {},
    
            "Assays": {}
        }
    
        self.data_ = {
    
            "File name": "",
            "Updated": "",
            "Investigations": {}
        }
    
        # =============================================
        # CLEAR SESSION JSON CACHE
        # IMPORTANT:
        # This is what clears the Loaded JSON dropdown
        # permanently for the current session.
        # =============================================
        if "loaded_json_cache" in self.storage:
    
            self.storage[
                "loaded_json_cache"
            ] = {}
    
        else:
    
            self.storage[
                "loaded_json_cache"
            ] = {}
    
        # =============================================
        # RESET CURRENT JSON STATE
        # =============================================
        self.current_json_name = None
    
        self.json_dirty = False
    
        self.json_created = False
    
        self.current_selected_objects = {}
    
        # =============================================
        # RESET DATASET SELECT
        # =============================================
        try:
    
            self.dataset_select.options = []
    
            self.dataset_select.value = None
    
            self.dataset_select.update()
    
        except Exception as ex:
    
            print(
                f"CLEAR DATASET SELECT ERROR: {ex}"
            )
    
        # =============================================
        # RESET SECTION SELECTORS
        # =============================================
        for selector in self.section_memory.values():
    
            try:
    
                selector.options = []
    
                selector.value = None
    
                selector.update()
    
            except Exception as ex:
    
                print(
                    f"CLEAR SECTION SELECTOR ERROR: {ex}"
                )
    
        # =============================================
        # RESET LABELS
        # =============================================
        try:
    
            if self.dataset_info is not None:
    
                self.dataset_info.text = (
                    "No JSON loaded."
                )
    
            if self.score_label is not None:
    
                self.score_label.text = (
                    "Waiting for JSON..."
                )
    
        except Exception as ex:
    
            print(
                f"CLEAR LABEL ERROR: {ex}"
            )
    
        # =============================================
        # FORCE JSON DROPDOWN REFRESH
        # =============================================
        try:
    
            self.refresh_json_dropdown()
    
        except Exception as ex:
    
            print(
                f"REFRESH AFTER CLEAR ERROR: {ex}"
            )
    
        # =============================================
        # NOTIFY USER
        # =============================================
        ui.notify(
            "Everything cleared",
            type="warning"
        )
    
        ui.update()
    
    
    # =====================================================
    # RESET JSON FORM
    # =====================================================
    def reset_json_form(self):
    
        try:
    
            # clear all input fields
            for key, widgets in self.dynamic_inputs.items():
    
                try:

                    value_widget = widgets[
                        "value_input"
                    ]
                
                    widget_class = value_widget.__class__.__name__.lower()
                
                    if "number" in widget_class:
                
                        value_widget.value = None
                
                    elif isinstance(
                        getattr(value_widget, "value", None),
                        bool
                    ):
                
                        value_widget.value = False
                
                    else:
                
                        value_widget.value = ""
                
                    value_widget.update()
                
                except:
                    pass
    
            # clear loaded json memory
            self.loaded_json = {

                "Investigations": {},
            
                "Studies": {},
            
                "observationUnits": {},
            
                "Samples": {},
            
                "Assays": {}
            }
        
    
            # reset labels
            if self.dataset_info is not None:
            
               self.dataset_info.text = (
                   "New JSON form"
               )
            
            if self.score_label is not None:
            
               self.score_label.text = (
                   "JSON form reset"
               )
    
            ui.notify(
                "JSON form reset",
                type="warning"
            )
    
            ui.update()
    
        except Exception as ex:
    
            ui.notify(
                f"Reset failed: {ex}",
                type="negative"
            )
           
    # =====================================================
    # CLEAR
    # =====================================================
    def clear_section(
        self,
        tab_name
    ):
    
        for key, widgets in self.dynamic_inputs.items():
    
            if not key.startswith(
                f"{tab_name}::"
            ):
                continue
    
            try:
    
                value_widget = widgets[
                    "value_input"
                ]
    
                widget_class = value_widget.__class__.__name__.lower()
    
                if "number" in widget_class:
    
                    value_widget.value = None
    
                elif isinstance(
                    getattr(value_widget, "value", None),
                    bool
                ):
    
                    value_widget.value = False
    
                else:
    
                    value_widget.value = ""
    
                value_widget.update()
    
            except Exception as ex:
    
                print(
                    f"CLEAR SECTION FIELD ERROR: {ex}"
                )
    
        ui.notify(
            f"{tab_name} cleared",
            type="warning"
        )

    # =====================================================
    # JSON FILES
    # =====================================================
    def get_available_json(self):

        return list(
            self.storage.get(
                "loaded_json_cache",
                {}
            ).keys()
        )

    # =====================================================
    # SCORE
    # =====================================================
    def compatibility_score(self, df):

        if (
            df is None
            or
            not isinstance(df, pd.DataFrame)
        ):
            return 0

        cols = [
            str(c).lower()
            for c in df.columns
        ]

        tokens = {

            "time": 15,
            "ph": 15,
            "temp": 15,
            "temperature": 15,
            "rpm": 15,
            "oxygen": 20,
            "po2": 20,
            "co2": 15,
            "feed": 20,
            "volume": 10,
            "od": 20,
            "biomass": 20,
        }

        score = 0

        for c in cols:

            for t, val in tokens.items():

                if t in c:
                    score += val

        return min(score, 100)

    # =====================================================
    # ICONS
    # =====================================================
    def syntax_icon(self, syntax):

        s = str(syntax).lower()

        if "date" in s:
            return "calendar_month"

        if "timestamp" in s:
            return "schedule"

        if "url" in s:
            return "link"

        if "id" in s:
            return "fingerprint"

        if "boolean" in s:
            return "toggle_on"

        if "number" in s:
            return "functions"

        return "text_fields"

    # =====================================================
    # SYNTAX OPTIONS
    # =====================================================
    def syntax_options(self, syntax):

        s = str(syntax).lower()

        if "boolean" in s:

            return [
                "{boolean}",
                "true",
                "false"
            ]

        if "{id}" in s:

            return [
                "{id}",
                "uuid",
                "string"
            ]

        if "url" in s:

            return [
                "{URL}",
                "https://"
            ]

        if (
            "{date}" in s
            and "timestamp" not in s
        ):

            return [
                "{date}",
                "YYYY-MM-DD"
            ]

        if "timestamp" in s:

            return [
                "{timestamp}",
                "ISO-8601"
            ]

        if "positive number" in s:

            return [
                "{positive number}",
                "float",
                "integer"
            ]

        return [
            "{text}",
            "string",
            "varchar"
        ]

    # =====================================================
    # FIELD FACTORY
    # =====================================================
    def create_dynamic_field(

        self,
        tab_name,
        term,
        syntax
    ):

        key = f"{tab_name}::{term}"

        syntax_low = str(syntax).lower()

        with ui.card().classes(
            "w-full border border-slate-200 shadow-sm p-3"
        ):

            with ui.row().classes(
                "w-full items-center gap-6"
            ):

                with ui.column().classes(
                    "w-80"
                ):

                    ui.label(
                        term
                    ).classes(
                        "font-bold text-base"
                    )

                    ui.label(
                        f"Expected Syntax: {syntax}"
                    ).classes(
                        "text-xs text-slate-500"
                    )

                if "boolean" in syntax_low:

                    widget = ui.switch()
                    
                    widget.on(
                        "update:model-value",
                        self.handle_field_change
                    )

                elif (
                    "{date}" in syntax_low
                    and "timestamp" not in syntax_low
                ):

                    widget = ui.input().props(
                        "type=date"
                    ).classes(
                        "w-72"
                    )
                    
                    widget.on(
                        "update:model-value",
                        self.handle_field_change
                    )

                elif "timestamp" in syntax_low:

                    widget = ui.input().props(
                        "type=datetime-local"
                    ).classes(
                        "w-72"
                    )
                    
                    widget.on(
                        "update:model-value",
                        self.handle_field_change
                    )

                elif "positive number" in syntax_low:

                    widget = ui.number().classes(
                        "w-72"
                    )
                    
                    widget.on(
                        "update:model-value",
                        self.handle_field_change
                    )

                else:

                    widget = ui.input().classes(
                        "w-72"
                    )
                    
                    widget.on(
                        "update:model-value",
                        self.handle_field_change
                    )

                syntax_select = ui.select(

                    self.syntax_options(syntax),

                    value=self.syntax_options(syntax)[0],

                    label="Value Syntax"

                ).classes(
                    "w-64"
                )

                self.dynamic_inputs[key] = {

                    "value_input": widget,

                    "syntax_input": syntax_select
                }   
            
    
    # =====================================================
    # SAVE UI
    # =====================================================
    def pull_ui(self):

        protocol_data = {}

        for key, widgets in self.dynamic_inputs.items():

            try:

                protocol_data[key] = {

                    "value":
                        widgets[
                            "value_input"
                        ].value,

                    "syntax":
                        widgets[
                            "syntax_input"
                        ].value
                }

            except:
                pass

        self.data_[
            "protocol_data"
        ] = protocol_data

    # =====================================================
    # LOAD UI
    # =====================================================
    def push_ui(self):

        protocol_data = self.data_.get(
            "protocol_data",
            {}
        )

        for key, widgets in self.dynamic_inputs.items():

            if key not in protocol_data:
                continue

            try:

                widgets[
                    "value_input"
                ].value = protocol_data[
                    key
                ].get(
                    "value",
                    ""
                )

                widgets[
                    "syntax_input"
                ].value = protocol_data[
                    key
                ].get(
                    "syntax",
                    ""
                )

            except:
                pass
    
    # =====================================================
    # REFRESH JSON LIST
    # =====================================================
    def refresh_json_dropdown(self):

        try:
    
            # =============================================
            # ENSURE SESSION CACHE EXISTS
            # =============================================
            if "loaded_json_cache" not in self.storage:
    
                self.storage[
                    "loaded_json_cache"
                ] = {}
    
            # =============================================
            # SESSION CACHE FILES ONLY
            # =============================================
            files = list(
    
                self.storage.get(
                    "loaded_json_cache",
                    {}
                ).keys()
            )
    
            # =============================================
            # SORT NEWEST FIRST
            # =============================================
            files = sorted(
                files,
                reverse=True
            )
    
            # =============================================
            # UPDATE DROPDOWN
            # =============================================
            self.dataset_select.options = files
    
            # =============================================
            # RESET INVALID SELECTION
            # =============================================
            current = self.dataset_select.value
    
            if current not in files:
    
                self.dataset_select.value = None
    
            # =============================================
            # UPDATE UI
            # =============================================
            self.dataset_select.update()
    
            print("\n===== JSON DROPDOWN REFRESH =====")
    
            print(files)
    
        except Exception as ex:
    
            print(
                f"\nREFRESH JSON DROPDOWN ERROR:\n{ex}"
            )
    
            ui.notify(
                f"Dropdown refresh failed: {ex}",
                type="negative"
            )
    
    # =====================================================
    # LOAD SELECTED JSON
    # =====================================================
    def load_selected_json(
        self,
        filename
    ):
    
        try:
    
            # =============================================
            # VALIDATE
            # =============================================
            if not filename:
                return
    
            # =============================================
            # DO NOT RELOAD SAME JSON
            # =============================================
            if (
                self.current_json_name
                and
                filename == self.current_json_name
            ):
    
                return
    
            # =============================================
            # SAVE CURRENT JSON BEFORE SWITCHING
            # IMPORTANT:
            # silent=True prevents temp_save_current_json()
            # from forcing the dropdown back to the old JSON.
            # =============================================
            if self.current_json_name:
    
                self.temp_save_current_json(
                    silent=True
                )
    
            # =============================================
            # GET SESSION CACHE
            # =============================================
            cache = self.storage.get(
                "loaded_json_cache",
                {}
            )
    
            # =============================================
            # CHECK JSON EXISTS IN CACHE
            # =============================================
            if filename not in cache:
    
                ui.notify(
                    "JSON not found in session",
                    type="negative"
                )
    
                return
    
            # =============================================
            # LOAD JSON FROM CACHE
            # =============================================
            self.loaded_json = deepcopy(
                cache[filename]
            )
    
            # =============================================
            # UPDATE CURRENT JSON STATE
            # =============================================
            self.current_json_name = filename
    
            self.json_created = True
    
            self.json_dirty = False
    
            # =============================================
            # CLEAR CURRENT UI FIELDS
            # =============================================
            self.clear_dynamic_fields()
    
            # =============================================
            # REFRESH SECTION SELECTORS
            # NOTE:
            # Your refresh_section_selectors() already loads
            # the first object of each section after refresh.
            # So we do NOT manually load each section again here.
            # =============================================
            self.refresh_section_selectors()
    
            # =============================================
            # UPDATE DATASET DROPDOWN
            # =============================================
            self.dataset_select.value = filename
    
            self.dataset_select.update()
    
            # =============================================
            # LABELS
            # =============================================
            if self.dataset_info is not None:
    
                self.dataset_info.text = (
                    f"Loaded JSON: {filename}"
                )
    
            if self.score_label is not None:
    
                self.score_label.text = (
                    "JSON loaded successfully"
                )
    
            # =============================================
            # FORCE FULL UI UPDATE
            # =============================================
            ui.update()
    
            # =============================================
            # SUCCESS
            # =============================================
            ui.notify(
                f"{filename} loaded",
                type="info"
            )
    
            print("\n===== JSON LOADED =====")
    
            print(filename)
    
            print(
                json.dumps(
                    self.loaded_json,
                    indent=4,
                    ensure_ascii=False
                )
            )
    
        except Exception as ex:
    
            print(
                f"\nLOAD JSON ERROR:\n{ex}"
            )
    
            ui.notify(
                f"Failed to load JSON: {ex}",
                type="negative"
            )
    
    # =====================================================
    # CLEAR ALL UI INPUTS
    # =====================================================
    def clear_dynamic_fields(self):

        for key, widgets in self.dynamic_inputs.items():
    
            try:
    
                value_widget = widgets.get(
                    "value_input"
                )
    
                if not value_widget:
                    continue
    
                # =====================================
                # SWITCH / BOOLEAN
                # =====================================
                if isinstance(value_widget.value, bool):
    
                    value_widget.value = False
    
                # =====================================
                # NUMBER INPUTS
                # =====================================
                elif value_widget.__class__.__name__.lower() == "number":
    
                    value_widget.value = None
    
                # =====================================
                # EVERYTHING ELSE
                # =====================================
                else:
    
                    value_widget.value = ""
    
                value_widget.update()
    
            except Exception as ex:
    
                print(
                    f"CLEAR FIELD ERROR: {ex}"
                ) 

    # =====================================================
    # NEW JSON SESSION
    # =====================================================
    def start_new_json(self):

        try:
            # =============================================
            # AUTO TEMP SAVE CURRENT JSON BEFORE SWITCHING
            # =============================================
            if self.current_json_name:
                
                self.temp_save_current_json()
    
            # =============================================
            # ENSURE SESSION CACHE EXISTS
            # =============================================
            if "loaded_json_cache" not in self.storage:
    
                self.storage[
                    "loaded_json_cache"
                ] = {}
    
            # =============================================
            # CLEAR ONLY UI FIELDS
            # =============================================
            for key, widgets in self.dynamic_inputs.items():
    
                try:
    
                    widgets[
                        "value_input"
                    ].value = ""
    
                except:
                    pass
    
            # =============================================
            # RESET JSON MEMORY
            # =============================================
            self.loaded_json = {
    
                "Investigations": {
                    "Investigation 1": {}
                },
    
                "Studies": {
                    "Study 1": {}
                },
    
                "observationUnits": {
                    "observationUnit 1": {}
                },
    
                "Samples": {
                    "Sample 1": {}
                },
    
                "Assays": {
                    "Assay 1": {}
                }
            }
    
            # =============================================
            # RESET FLAGS
            # =============================================
            self.json_dirty = False
    
            self.json_created = True
    
            # =============================================
            # CREATE SESSION FILE NAME
            # =============================================
            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
    
            filename = (
                f"metadata_{timestamp}.json"
            )
    
            self.current_json_name = filename
    
            # =============================================
            # REGISTER JSON IN SESSION CACHE
            # =============================================
            self.storage[
                "loaded_json_cache"
            ][filename] = deepcopy(
                self.loaded_json
            )
    
            # =============================================
            # REFRESH DROPDOWN
            # =============================================
            self.refresh_json_dropdown()
    
            self.dataset_select.value = filename
    
            self.dataset_select.update()
    
            # =============================================
            # RELOAD SECTION SELECTORS
            # =============================================
            self.refresh_section_selectors()
    
            # =============================================
            # LABELS
            # =============================================
            if self.dataset_info is not None:
            
               self.dataset_info.text = (
                   f"New JSON created: {filename}"
               )
               
            if self.score_label is not None:
            
               self.score_label.text = (
                   "JSON initialized successfully"
               )
    
            # =============================================
            # SUCCESS
            # =============================================
            ui.notify(
                f"{filename} created",
                type="info"
            )
    
            print("\n===== NEW JSON SESSION =====")
    
            print(filename)
    
            ui.update()
    
        except Exception as ex:
    
            ui.notify(
                f"Failed to create JSON: {ex}",
                type="negative"
            )
    
            print(
                f"\nNEW JSON ERROR:\n{ex}"
            )
    
    
    # =====================================================
    # CREATE JSON ON FIRST EDIT
    # =====================================================
    def ensure_json_created(self):

        if self.json_created:
            return
    
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
    
        filename = f"metadata_{timestamp}.json"
    
        # =============================================
        # SESSION ONLY
        # =============================================
        self.current_json_name = filename
    
        self.json_created = True
    
        # =============================================
        # ENSURE CACHE EXISTS
        # =============================================
        if "loaded_json_cache" not in self.storage:
    
            self.storage[
                "loaded_json_cache"
            ] = {}
    
        # =============================================
        # CREATE EMPTY SESSION JSON
        # =============================================
        self.storage[
            "loaded_json_cache"
        ][filename] = deepcopy(
            self.loaded_json
        )
    
        # =============================================
        # REFRESH UI
        # =============================================
        self.refresh_json_dropdown()
    
        self.dataset_select.value = filename
    
        self.dataset_select.update()
    
        self.dataset_info.text = (
            f"New JSON created: {filename}"
        )
    
        ui.notify(
            f"Created {filename}",
            type="info"
        )
    
    
    # =====================================================
    # HANDLE FIELD CHANGE
    # =====================================================
    def handle_field_change(self, e):

        if self.is_loading_object:
            return
    
        if self.is_refreshing_selectors:
            return
    
        self.json_dirty = True
    
        if not self.current_json_name:
    
            self.ensure_json_created()
    
        self.autosave_json()
    
    # =====================================================
    # TEMP SAVE CURRENT JSON
    # =====================================================
    def temp_save_current_json(
        self,
        silent=False
    ):
    
        try:
    
            # =============================================
            # DO NOT SAVE WHILE OBJECT IS BEING LOADED
            # This prevents overwriting a newly loaded JSON
            # with values from the previous screen.
            # =============================================
            if self.is_loading_object:
                return
    
            # =============================================
            # ENSURE JSON NAME EXISTS
            # =============================================
            if not self.current_json_name:
    
                selected = getattr(
                    self.dataset_select,
                    "value",
                    None
                )
    
                if selected:
    
                    self.current_json_name = selected
    
            if not self.current_json_name:
    
                if not silent:
    
                    ui.notify(
                        "No JSON selected to save",
                        type="warning"
                    )
    
                return
    
            # =============================================
            # SAVE ALL CURRENT SECTION OBJECTS FROM UI
            # =============================================
            for section_name in [
    
                "Investigation",
                "Study",
                "observationUnit",
                "Sample",
                "Assay"
    
            ]:
    
                self.save_current_section_object(
                    section_name
                )
    
            # =============================================
            # ENSURE CACHE EXISTS
            # =============================================
            if "loaded_json_cache" not in self.storage:
    
                self.storage[
                    "loaded_json_cache"
                ] = {}
    
            # =============================================
            # SAVE FULL JSON INTO SESSION CACHE
            # =============================================
            self.storage[
                "loaded_json_cache"
            ][self.current_json_name] = deepcopy(
                self.loaded_json
            )
    
            # =============================================
            # JSON IS NOW CLEAN
            # =============================================
            self.json_dirty = False
    
            # =============================================
            # ONLY UPDATE UI WHEN USER PRESSES SAVE JSON IN MEMORY BUTTON
            # DO NOT UPDATE DROPDOWN WHEN SWITCHING / LOADING JSON
            # =============================================
            if not silent:
    
                self.refresh_json_dropdown()
    
                self.dataset_select.value = self.current_json_name
    
                self.dataset_select.update()
    
                if self.dataset_info is not None:
    
                    self.dataset_info.text = (
                        f"Temporary saved JSON: {self.current_json_name}"
                    )
    
                if self.score_label is not None:
    
                    self.score_label.text = (
                        "Temporary JSON saved successfully"
                    )
    
                ui.notify(
                    f"{self.current_json_name} temporarily saved",
                    type="info"
                )
    
                ui.update()
    
            # =============================================
            # DEBUG PRINT
            # =============================================
            print("\n===== SAVE JSON IN MEMORY =====")
    
            print(
                self.current_json_name
            )
    
            print(
                json.dumps(
                    self.loaded_json,
                    indent=4,
                    ensure_ascii=False
                )
            )
    
        except Exception as ex:
    
            print(
                f"\nSAVE JSON IN MEMORY:\n{ex}"
            )
    
            if not silent:
    
                ui.notify(
                    f"Temporary save failed: {ex}",
                    type="negative"
                )
            
    # =====================================================
    # AUTOSAVE
    # =====================================================
    def autosave_json(self):

        try:
    
            if self.is_loading_object:
                return
    
            if not self.current_json_name:
                return
    
            current_tab = None
    
            for section_name, selector in self.section_memory.items():
    
                if selector and selector.value:
    
                    self.save_current_section_object(
                        section_name
                    )
    
            if "loaded_json_cache" not in self.storage:
    
                self.storage[
                    "loaded_json_cache"
                ] = {}
    
            self.storage[
                "loaded_json_cache"
            ][self.current_json_name] = deepcopy(
                self.loaded_json
            )
    
            print(
                f"AUTOSAVED JSON: {self.current_json_name}"
            )
    
        except Exception as ex:
    
            print(
                f"\nAUTOSAVE ERROR:\n{ex}"
            )
    # =====================================================
    # DYNAMIC JSON -> UI
    # =====================================================
    def apply_json_to_ui_dynamic(
        self,
        data
    ):
    
        try:
    
            # =============================================
            # FLATTEN JSON
            # =============================================
            def flatten_json(
                obj,
                parent=""
            ):
    
                items = {}
    
                if isinstance(obj, dict):
    
                    for k, v in obj.items():
    
                        new_key = (
                            f"{parent}::{k}"
                            if parent
                            else k
                        )
    
                        items.update(
    
                            flatten_json(
                                v,
                                new_key
                            )
                        )
    
                elif isinstance(obj, list):
    
                    for i, v in enumerate(obj):
    
                        new_key = (
                            f"{parent}::{i}"
                        )
    
                        items.update(
    
                            flatten_json(
                                v,
                                new_key
                            )
                        )
    
                else:
    
                    items[parent] = obj
    
                return items
    
            # =============================================
            # FLATTENED JSON
            # =============================================
            flat_json = flatten_json(
                data
            )
    
            print("\n===== FLAT JSON =====")
    
            for k, v in flat_json.items():
    
                print(k, "=", v)
    
            # =============================================
            # MATCH UI FIELDS
            # =============================================
            for ui_key, widgets in self.dynamic_inputs.items():
    
                ui_field = ui_key.split(
                    "::"
                )[-1].lower().replace(
                    " ",
                    ""
                ).replace(
                    "-",
                    ""
                )
    
                for json_key, value in flat_json.items():
    
                    json_field = json_key.split(
                        "::"
                    )[-1].lower().replace(
                        " ",
                        ""
                    ).replace(
                        "-",
                        ""
                    )
    
                    # =====================================
                    # MATCH FIELD NAMES
                    # =====================================
                    if ui_field == json_field:
    
                        try:
    
                            widgets[
                                "value_input"
                            ].value = value
    
                            print(
                                f"MATCHED: {ui_key} -> {value}"
                            )
    
                        except Exception as ex:
    
                            print(
                                f"UI SET ERROR: {ex}"
                            )
    
            ui.update()
    
        except Exception as ex:
    
            print(
                f"\nDYNAMIC APPLY ERROR:\n{ex}"
            )
    
    # =====================================================
    # REFRESH SECTION SELECTORS
    # =====================================================
    def refresh_section_selectors(self):

        try:
    
            self.is_refreshing_selectors = True
    
            mapping = {
    
                "Investigation": "Investigations",
                "Study": "Studies",
                "observationUnit": "observationUnits",
                "Sample": "Samples",
                "Assay": "Assays"
            }
    
            for ui_name, json_name in mapping.items():
    
                selector = self.section_memory.get(
                    ui_name
                )
    
                if not selector:
                    continue
    
                section_data = self.loaded_json.get(
                    json_name,
                    {}
                )
    
                options = list(
                    section_data.keys()
                )
    
                print(
                    f"REFRESH {ui_name}: {options}"
                )
    
                selector.options = options
    
                if options:
    
                    first_object = options[0]
    
                    selector.value = first_object
    
                    self.current_selected_objects[
                        ui_name
                    ] = first_object
    
                else:
    
                    selector.value = None
    
                    self.current_selected_objects[
                        ui_name
                    ] = None
    
                selector.update()
    
            ui.update()
    
        except Exception as ex:
    
            print(
                f"\nSECTION REFRESH ERROR:\n{ex}"
            )
    
            ui.notify(
                f"Section refresh failed: {ex}",
                type="negative"
            )
    
        finally:
    
            self.is_refreshing_selectors = False
    
        # =============================================
        # LOAD FIRST OBJECTS AFTER REFRESH IS FINISHED
        # =============================================
        for ui_name in [
    
            "Investigation",
            "Study",
            "observationUnit",
            "Sample",
            "Assay"
    
        ]:
    
            selected = self.current_selected_objects.get(
                ui_name
            )
    
            if selected:
    
                self.load_selected_object(
                    ui_name,
                    selected
                )
    
    # =====================================================
    # LOAD SELECTED OBJECT
    # =====================================================
    def load_selected_object(

        self,
    
        section_name,
    
        object_name
    ):
    
        if self.is_refreshing_selectors:
            return
    
        if self.is_loading_object:
            return
    
        if not object_name:
            return
    
        try:
    
            self.is_loading_object = True
    
            # ============================================
            # SAVE PREVIOUS OBJECT ONLY IF DIFFERENT
            # ============================================
            previous_object = self.current_selected_objects.get(
                section_name
            )
    
            if (
                previous_object
                and
                previous_object != object_name
            ):
    
                self.save_current_section_object(
                    section_name
                )
    
            self.current_selected_objects[
                section_name
            ] = object_name
    
            # ============================================
            # SECTION MAPPING
            # ============================================
            mapping = {
    
                "Investigation": "Investigations",
    
                "Study": "Studies",
    
                "observationUnit": "observationUnits",
    
                "Sample": "Samples",
    
                "Assay": "Assays"
            }
    
            json_section = mapping.get(
                section_name
            )
    
            if not json_section:
                return
    
            section_data = self.loaded_json.get(
                json_section,
                {}
            )
    
            selected_object = section_data.get(
                object_name,
                {}
            )
    
            print(
                f"\nLOADING {section_name}: {object_name}"
            )
    
            # ============================================
            # CLEAR ONLY CURRENT SECTION FIELDS
            # ============================================
            for key, widgets in self.dynamic_inputs.items():
            
                if not key.startswith(
                    f"{section_name}::"
                ):
                    continue
            
                try:
            
                    value_widget = widgets.get(
                        "value_input"
                    )
            
                    if not value_widget:
                        continue
            
                    # NiceGUI ui.number has validation/format props
                    # safest check: class name contains "Number"
                    widget_class = value_widget.__class__.__name__.lower()
            
                    if "number" in widget_class:
            
                        value_widget.value = None
            
                    elif isinstance(
                        getattr(value_widget, "value", None),
                        bool
                    ):
            
                        value_widget.value = False
            
                    else:
            
                        value_widget.value = ""
            
                    value_widget.update()
            
                except Exception as ex:
            
                    print(
                        f"CLEAR FIELD ERROR: {ex}"
                    )
    
            # ============================================
            # LOAD VALUES INTO UI
            # ============================================
            for field_name, value in selected_object.items():
    
                normalized_json_field = (
                    field_name
                    .lower()
                    .replace("-", " ")
                    .replace("_", " ")
                    .strip()
                )
    
                for ui_key, widgets in self.dynamic_inputs.items():
    
                    if not ui_key.startswith(
                        f"{section_name}::"
                    ):
                        continue
    
                    ui_field = (
                        ui_key.split(
                            "::"
                        )[-1]
                        .lower()
                        .strip()
                    )
    
                    if ui_field == normalized_json_field:
    
                        try:
    
                            widgets[
                                "value_input"
                            ].value = value
    
                            widgets[
                                "value_input"
                            ].update()
    
                            print(
                                f"SET {ui_key} -> {value}"
                            )
    
                        except Exception as ex:
    
                            print(
                                f"SET ERROR: {ex}"
                            )
    
            ui.update()
    
        except Exception as ex:
    
            print(
                f"\nOBJECT LOAD ERROR:\n{ex}"
            )
    
            ui.notify(
    
                f"Object load failed: {ex}",
    
                type="negative"
            )
    
        finally:
    
            self.is_loading_object = False 
            
    # =====================================================
    # SAVE CURRENT SECTION OBJECT
    # =====================================================
    def save_current_section_object(
        self,
        section_name
    ):
    
        if self.is_loading_object:
            return
    
        try:
    
            selector = self.section_memory.get(
                section_name
            )
    
            if not selector:
                return
    
            object_name = selector.value
    
            if not object_name:
                return
    
            mapping = {
    
                "Investigation": "Investigations",
                "Study": "Studies",
                "observationUnit": "observationUnits",
                "Sample": "Samples",
                "Assay": "Assays"
            }
    
            json_section = mapping.get(
                section_name
            )
    
            if not json_section:
                return
    
            if json_section not in self.loaded_json:
    
                self.loaded_json[
                    json_section
                ] = {}
    
            if (
                object_name
                not in
                self.loaded_json[json_section]
            ):
    
                self.loaded_json[
                    json_section
                ][object_name] = {}
    
            object_data = {}
    
            for key, widgets in self.dynamic_inputs.items():
    
                if not key.startswith(
                    f"{section_name}::"
                ):
                    continue
    
                field_name = key.split(
                    "::"
                )[-1]
    
                try:
    
                    value = widgets[
                        "value_input"
                    ].value
    
                    if value not in [
                        None,
                        "",
                        []
                    ]:
    
                        json_field = (
                            field_name
                            .lower()
                            .replace(" ", "-")
                        )
    
                        object_data[
                            json_field
                        ] = value
    
                except Exception as ex:
    
                    print(
                        f"READ FIELD ERROR: {ex}"
                    )
    
            self.loaded_json[
                json_section
            ][object_name] = object_data
    
            selected_json = self.current_json_name
    
            if not selected_json:
    
                selected_json = getattr(
                    self.dataset_select,
                    "value",
                    None
                )
    
            if selected_json:
    
                if "loaded_json_cache" not in self.storage:
    
                    self.storage[
                        "loaded_json_cache"
                    ] = {}
    
                self.storage[
                    "loaded_json_cache"
                ][selected_json] = deepcopy(
                    self.loaded_json
                )
    
            print(
                f"SAVED {section_name}: {object_name}"
            )
    
        except Exception as ex:
    
            print(
                f"SAVE OBJECT ERROR: {ex}"
            )
                   
    # =====================================================
    # PAGE
    # =====================================================
    def add_page(

        self,
        page_url="/metadata",
        frame_name="MetaData Window"
    ):
        """Adds this page as a distinct route in the application.

        Args:
            page_url: URL path for the page. Defaults to "/metadata".
            frame_name: Display name of the page frame. Defaults to "MetaData Window".
        """

        @ui.page(page_url)
        def page():

            with theme.frame(frame_name):

                self.content_()
    
    # =====================================================
    # CREATE NEW SECTION OBJECT
    # =====================================================
    def create_new_section_object(
        self,
        section_name
    ):
    
        try:
    
            mapping = {
    
                "Investigation": "Investigations",
                "Study": "Studies",
                "observationUnit": "observationUnits",
                "Sample": "Samples",
                "Assay": "Assays"
            }
    
            json_section = mapping.get(
                section_name
            )
    
            if not json_section:
                return
    
            # =============================================
            # ENSURE SECTION EXISTS
            # =============================================
            if json_section not in self.loaded_json:
    
                self.loaded_json[
                    json_section
                ] = {}
    
            section_data = self.loaded_json[
                json_section
            ]
    
            # =============================================
            # FIND NEXT INDEX
            # =============================================
            existing = list(
                section_data.keys()
            )
    
            next_id = 1
    
            while (
                f"{section_name} {next_id}"
                in existing
            ):
    
                next_id += 1
    
            new_object_name = (
                f"{section_name} {next_id}"
            )
    
            # =============================================
            # CREATE EMPTY OBJECT
            # =============================================
            section_data[
                new_object_name
            ] = {}
    
            # =============================================
            # UPDATE SELECTOR
            # =============================================
            selector = self.section_memory.get(
                section_name
            )
    
            if selector:
    
                selector.options = list(
                    section_data.keys()
                )
    
                selector.value = new_object_name
    
                selector.update()
    
            # =============================================
            # CLEAR SECTION UI
            # =============================================
            self.clear_section(
                section_name
            )
    
            # =============================================
            # UPDATE MAIN CACHE
            # =============================================
            selected_json = (
                self.dataset_select.value
            )
    
            if (
                selected_json
                and
                "loaded_json_cache"
                in self.storage
            ):
    
                self.storage[
                    "loaded_json_cache"
                ][selected_json] = self.loaded_json
    
            ui.notify(
                f"{new_object_name} created",
                type="info"
            )
    
            ui.update()
    
        except Exception as ex:
    
            ui.notify(
                f"Creation failed: {ex}",
                type="negative"
            )
            
    # =====================================================
    # UI
    # =====================================================
    def content_(self):
        """Renders the HTML/CSS contents of the metadata builder page."""

        with ui.column().classes(
            "w-full p-4 gap-6"
        ):
    
            # =================================================
            # HEADER CARD
            # =================================================
            with ui.card().classes(
                "w-full p-6 shadow-sm"
            ):
    
                ui.label(
                    "Industrial MetaData Builder"
                ).classes(
                    "text-h4 font-bold"
                )
    
                ui.label(
                    "Fermentation experiment metadata system"
                ).classes(
                    "text-slate-500"
                )
    
                ui.separator()
    
                # =============================================
                # JSON TOOLBAR
                # =============================================
                with ui.column().classes(
                    "w-full gap-4"
                ):
                
                    # =========================================
                    # ROW 1: JSON SELECT + JSON UPLOAD
                    # =========================================
                    with ui.row().classes(
                        "w-full items-end gap-4"
                    ):
                
                        # =====================================
                        # LOADED JSON DROPDOWN
                        # =====================================
                        self.dataset_select = ui.select(
                
                            [],
                
                            label="Loaded JSON",
                
                            on_change=lambda e:
                            self.load_selected_json(
                                e.value
                            )
                
                        ).classes(
                            "w-72"
                        )
                
                        # =====================================
                        # JSON UPLOAD
                        # =====================================
                        ui.upload(
                            label="Load JSON",
                            auto_upload=True,
                            on_upload=self.load_json
                        ).props(
                            'accept=".json"'
                        ).classes(
                            "w-96"
                        )
                
                    # =========================================
                    # ROW 2: ACTION BUTTONS
                    # =========================================
                    with ui.row().classes(
                        "w-full items-center gap-3"
                    ):
                
                        ui.button(
                            "NEW JSON",
                            icon="add",
                            color="info",
                            on_click=self.start_new_json
                        ).classes(
                            "w-44"
                        )
                
                        ui.button(
                            "SAVE JSON IN MEMORY",
                            icon="save",
                            color="info",
                            on_click=self.temp_save_current_json
                        ).classes(
                            "w-52"
                        )
                
                        ui.button(
                            "EXPORT JSON",
                            icon="download",
                            color="info",
                            on_click=self.export_protocol
                        ).classes(
                            "w-48"
                        )
                
                        ui.button(
                            "CLEAR WINDOW",
                            icon="delete",
                            color="negative",
                            on_click=self.clear_all
                        ).classes(
                            "w-48"
                        )
                
                    # =========================================
                    # ROW 3: STATUS LABELS
                    # =========================================
                    with ui.column().classes(
                        "gap-1"
                    ):
                    
                        self.dataset_info = ui.label(
                            "No JSON loaded."
                        ).classes(
                            "text-sm text-slate-600"
                        )
                    
                        self.score_label = ui.label(
                            "Waiting for JSON..."
                        ).classes(
                            "text-sm text-slate-500"
                        )
    
            # =================================================
            # TABS
            # =================================================
            with ui.tabs().classes(
                "w-full bg-white rounded shadow px-2 py-1"
            ).props(
                'active-color="primary" indicator-color="primary"'
            ) as tabs:
    
                tab_objects = {}
    
                for tab_name in self.protocol_schema.keys():
    
                    tab_objects[
                        tab_name
                    ] = ui.tab(
                        tab_name.upper()
                    ).classes(
                        "font-bold text-sm"
                    )
    
            # =================================================
            # TAB PANELS
            # =================================================
            with ui.tab_panels(
                tabs,
                value=tab_objects["Investigation"]
            ).classes(
                "w-full"
            ):
    
                for tab_name, fields in self.protocol_schema.items():
    
                    with ui.tab_panel(
                        tab_objects[tab_name]
                    ):
    
                        with ui.card().classes(
                            "w-full p-6 shadow-sm"
                        ):
    
                            # =====================================
                            # TOP BAR
                            # =====================================
                            with ui.row().classes(
                                "w-full justify-between items-center"
                            ):
    
                                # =================================
                                # SECTION TITLE
                                # =================================
                                ui.label(
                                    tab_name
                                ).classes(
                                    "text-h5 font-bold"
                                )
    
                                # =================================
                                # RIGHT SIDE CONTROLS
                                # =================================
                                with ui.row().classes(
                                    "items-center gap-2"
                                ):
                                
                                    selector = ui.select(
                                        [],
                                        label=f"{tab_name} Objects",
                                        on_change=lambda e,
                                        t=tab_name:
                                        self.load_selected_object(
                                            t,
                                            e.value
                                        )
                                    ).classes(
                                        "w-72"
                                    )
                                
                                    ui.button(
                                        icon="add",
                                        color="info",
                                        on_click=lambda t=tab_name:
                                        self.create_new_section_object(t)
                                    ).props(
                                        "round dense"
                                    )
                                
                                    self.section_memory[
                                        tab_name
                                    ] = selector
    
                            ui.separator()
    
                            # =====================================
                            # FIELDS
                            # =====================================
                            with ui.column().classes(
                                "w-full gap-4"
                            ):
    
                                for term, syntax in fields:
    
                                    self.create_dynamic_field(
                                        tab_name=tab_name,
                                        term=term,
                                        syntax=syntax
                                    )
    
        # =====================================================
        # INITIALIZE UI STATE
        # =====================================================
        self.push_ui()
    
        self.refresh_json_dropdown()