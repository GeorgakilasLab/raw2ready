"""Agent Orchestrator.

Orchestrates multiple specialized src.agents to analyze data, search scientific
literature, query databases like BacDive and Crossref, and summarize findings.
"""

import json
import traceback
import re
import os
from datetime import datetime

from src.agents.data_analyst import DataAnalystAgent
from src.agents.bacdive_explorer import BacDiveExplorerAgent
from src.agents.internet_explorer import InternetExplorerAgent
from src.agents.crossref_explorer import CrossrefExplorerAgent
from src.agents.metadata_analyst import MetadataAnalystAgent
from src.agents.master_summarizer import MasterSummarizerAgent
from src.utils.paths import ensure_dirs


class AgentOrchestrator:
    """Orchestrator to run various analytical and explorer src.agents.

    Coordinates the execution of specific src.agents based on user query intent,
    handles logging of agent steps, and compiles results.

    Attributes:
        model_name: The name of the LLM model to use.
        temperature: LLM temperature parameter.
        debug: True if debug prints should be enabled.
        log_dir: Directory path for saving agent execution logs.
    """

    def __init__(
        self,
        model_name="llama3:latest",
        temperature=0.2,
        debug=True,
        log_dir=None
    ):
        """Initializes the AgentOrchestrator and sets up log paths and src.agents.

        Args:
            model_name: The name of the LLM model. Defaults to "llama3:latest".
            temperature: LLM temperature parameter. Defaults to 0.2.
            debug: Whether to print debug information. Defaults to True.
            log_dir: Directory path for saving agent logs. Defaults to
                DIRS["agent_logs"].
        """

        print("\n" + "=" * 100)
        print("[AGENT ORCHESTRATOR] INITIALIZING SYSTEM")
        print("=" * 100)
        print(f"MODEL: {model_name}")
        print(f"TEMPERATURE: {temperature}")

        self.model_name = model_name
        self.temperature = temperature
        self.debug = debug

        self.log_dir = log_dir or str(ensure_dirs()["agent_logs"])
        os.makedirs(self.log_dir, exist_ok=True)

        self.agent_log_paths = {
            "DETECTED_ORGANISMS": os.path.join(self.log_dir, "detected_organisms.log"),
            "DATA_ANALYST": os.path.join(self.log_dir, "data_analyst.log"),
            "INTERNET_EXPLORER": os.path.join(self.log_dir, "internet_explorer.log"),
            "CROSSREF_EXPLORER": os.path.join(self.log_dir, "crossref_explorer.log"),
            "BACDIVE_EXPLORER": os.path.join(self.log_dir, "bacdive_explorer.log"),
            "METADATA_ANALYST": os.path.join(self.log_dir, "metadata_analyst.log"),
            "AGENT_SUMMARIES": os.path.join(self.log_dir, "agent_summaries.log"),
            "MASTER_SUMMARY": os.path.join(self.log_dir, "master_summary.log"),
            "SYSTEM": os.path.join(self.log_dir, "system.log"),
        }

        print("\n[INIT] DATA_ANALYST")
        self.data_agent = DataAnalystAgent(model_name=model_name, temperature=temperature)

        print("[INIT] INTERNET_EXPLORER")
        self.internet_agent = InternetExplorerAgent(model_name=model_name, temperature=temperature)

        print("[INIT] CROSSREF_EXPLORER")
        self.crossref_agent = CrossrefExplorerAgent(model_name=model_name, temperature=temperature)

        print("[INIT] BACDIVE_EXPLORER")
        self.bacdive_agent = BacDiveExplorerAgent(model_name=model_name, temperature=temperature)

        print("[INIT] METADATA_ANALYST")
        self.metadata_agent = MetadataAnalystAgent(model_name=model_name, temperature=temperature)

        print("[INIT] MASTER_SUMMARIZER")
        self.master_agent = MasterSummarizerAgent(model_name=model_name, temperature=temperature)

        print("\n[AGENT ORCHESTRATOR] INITIALIZATION COMPLETE")
        print("=" * 100 + "\n")

    # =====================================================
    # LOGGING
    # =====================================================
    def make_json_safe(self, value):
        try:
            import pandas as pd
            import numpy as np

            if isinstance(value, pd.DataFrame):
                return {
                    "type": "DataFrame",
                    "shape": value.shape,
                    "columns": list(value.columns.astype(str)),
                    "preview": value.head(5).to_dict(orient="records")
                }

            if isinstance(value, pd.Series):
                return value.head(20).to_dict()

            if isinstance(value, np.ndarray):
                return value.tolist()

        except Exception:
            pass

        try:
            json.dumps(value, default=str, ensure_ascii=False)
            return value
        except Exception:
            return str(value)

    def log_agent_step(
        self,
        agent_name,
        step,
        input_data=None,
        output_data=None,
        extra=None
    ):
        try:
            path = self.agent_log_paths.get(
                agent_name,
                os.path.join(self.log_dir, f"{agent_name.lower()}.log")
            )

            os.makedirs(os.path.dirname(path), exist_ok=True)

            record = {
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name,
                "step": step,
                "model": self.model_name,
                "temperature": self.temperature,
                "input": self.make_json_safe(input_data),
                "output": self.make_json_safe(output_data),
                "extra": self.make_json_safe(extra or {})
            }

            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, indent=2, default=str, ensure_ascii=False))
                f.write("\n\n" + "=" * 100 + "\n\n")

        except Exception as ex:
            print(f"[LOGGING ERROR] {agent_name} / {step}: {ex}")

    def log_system_step(self, step, data=None):
        self.log_agent_step(
            agent_name="SYSTEM",
            step=step,
            input_data=None,
            output_data=data
        )

    # =====================================================
    # DEBUG
    # =====================================================
    def debug_print(self, title, data):
        if not self.debug:
            return

        print("\n" + "=" * 100)
        print(f"[AGENT ORCHESTRATOR DEBUG] {title}")
        print("=" * 100)

        try:
            if isinstance(data, str):
                print(data)
            else:
                print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        except Exception as ex:
            print(str(data))
            print(f"[DEBUG PRINT ERROR] {str(ex)}")

        print("=" * 100 + "\n")

    # =====================================================
    # SAFE RUN
    # =====================================================
    def safe_run(self, agent_name, func, *args, **kwargs):
        print("\n" + "=" * 100)
        print(f"[SAFE RUN] STARTING AGENT: {agent_name}")
        print("=" * 100)

        input_payload = {
            "args": args,
            "kwargs": kwargs
        }

        self.debug_print(f"{agent_name} INPUT", input_payload)

        self.log_agent_step(
            agent_name=agent_name,
            step="input",
            input_data=input_payload,
            extra={"status": "starting"}
        )

        try:
            result = func(*args, **kwargs)

            if not isinstance(result, dict):
                result = {"result": result}

            result["agent_status"] = result.get("agent_status", "success")
            result["agent_name"] = result.get("agent_name", agent_name)

            if "agent_summary" not in result:
                result["agent_summary"] = self.build_agent_summary(agent_name, result)

            print(f"[SAFE RUN] {agent_name} COMPLETED SUCCESSFULLY")
            self.debug_print(f"{agent_name} OUTPUT", result)

            self.log_agent_step(
                agent_name=agent_name,
                step="output",
                input_data=input_payload,
                output_data=result,
                extra={"status": "success"}
            )

            return result

        except Exception as ex:
            traceback.print_exc()

            failed = {
                "agent_name": agent_name,
                "agent_status": "failed",
                "error": str(ex),
                "traceback": traceback.format_exc(),
                "agent_summary": f"{agent_name} failed: {str(ex)}"
            }

            self.debug_print(f"{agent_name} FAILED", failed)

            self.log_agent_step(
                agent_name=agent_name,
                step="failed",
                input_data=input_payload,
                output_data=failed,
                extra={"status": "failed"}
            )

            return failed

    # =====================================================
    # SKIPPED AGENT
    # =====================================================
    def skipped_agent(self, agent_name, reason):
        result = {
            "agent_name": agent_name,
            "agent_status": "skipped",
            "reason": reason,
            "agent_summary": reason
        }

        self.log_agent_step(
            agent_name=agent_name,
            step="skipped",
            input_data=None,
            output_data=result,
            extra={"reason": reason}
        )

        return result

    # =====================================================
    # AGENT SUMMARY BUILDER
    # =====================================================
    def build_agent_summary(self, agent_name, result):
        if not isinstance(result, dict):
            return f"{agent_name} returned a non-dictionary result."

        status = result.get("agent_status", "unknown")

        if status == "failed":
            return f"{agent_name} failed: {result.get('error', 'Unknown error')}"

        if status == "skipped":
            return f"{agent_name} was skipped: {result.get('reason', 'No reason provided')}"

        summary = result.get("summary")
        assessment = result.get("assessment")
        answer = result.get("answer")
        final_summary = result.get("final_summary")
        result_text = result.get("result")

        if isinstance(summary, str) and summary.strip():
            return summary.strip()

        if isinstance(assessment, str) and assessment.strip():
            return assessment.strip()

        if isinstance(answer, str) and answer.strip():
            return answer.strip()

        if isinstance(final_summary, str) and final_summary.strip():
            return final_summary.strip()

        if isinstance(result_text, str) and result_text.strip():
            return result_text.strip()

        keys = [
            key for key in result.keys()
            if key not in ["raw_json", "accepted_strains", "results"]
        ]

        return (
            f"{agent_name} completed successfully. "
            f"Available output fields: {', '.join(keys)}."
        )

    # =====================================================
    # NORMALIZATION
    # =====================================================
    def normalize_text(self, text):
        if text is None:
            return ""

        text = str(text)
        text = text.replace("[MULTI-AGENT]", " ")
        text = text.replace("[BACDIVE]", " ")
        text = re.sub(r"[^a-zA-Z0-9\.\-\_\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text.lower()

    def normalize_microorganism_list(self, value):
        if value is None:
            return []

        if isinstance(value, str):
            value = [value]

        if not isinstance(value, list):
            value = [value]

        cleaned = []

        for item in value:
            if item is None:
                continue

            text = str(item).strip()

            if text and text not in cleaned:
                cleaned.append(text)

        return cleaned

    # =====================================================
    # ORGANISM RULES
    # =====================================================
    def organism_alias_rules(self):
        return [
            (["escherichia coli", "e. coli", "e coli", "ecoli", "k12", "k-12", "rr1", "bl21", "dh5a", "mg1655"], "Escherichia coli"),
            (["bacillus subtilis", "b. subtilis", "b subtilis", "subtilis"], "Bacillus subtilis"),
            (["saccharomyces cerevisiae", "s. cerevisiae", "s cerevisiae", "yeast", "baker yeast"], "Saccharomyces cerevisiae"),
            (["komagataella phaffii", "k. phaffii", "k phaffii", "pichia pastoris", "p. pastoris", "p pastoris", "komagataella", "pichia"], "Komagataella phaffii"),
            (["corynebacterium glutamicum", "c. glutamicum", "c glutamicum", "corynebacterium"], "Corynebacterium glutamicum"),
            (["pseudomonas putida", "p. putida", "p putida", "kt2440", "pseudomonas putida kt2440"], "Pseudomonas putida"),
            (["pseudomonas fluorescens", "p. fluorescens", "p fluorescens", "fluorescens"], "Pseudomonas fluorescens"),
            (["pseudomonas aeruginosa", "p. aeruginosa", "p aeruginosa", "aeruginosa"], "Pseudomonas aeruginosa"),
            (["clostridium acetobutylicum", "c. acetobutylicum", "c acetobutylicum", "acetobutylicum"], "Clostridium acetobutylicum"),
            (["clostridium beijerinckii", "c. beijerinckii", "c beijerinckii", "beijerinckii"], "Clostridium beijerinckii"),
            (["lactobacillus plantarum", "l. plantarum", "l plantarum", "plantarum"], "Lactobacillus plantarum"),
            (["lactobacillus casei", "l. casei", "l casei", "casei"], "Lactobacillus casei"),
            (["lactococcus lactis", "l. lactis", "l lactis", "lactis"], "Lactococcus lactis"),
            (["streptomyces coelicolor", "s. coelicolor", "s coelicolor", "coelicolor"], "Streptomyces coelicolor"),
            (["streptomyces griseus", "s. griseus", "s griseus", "griseus"], "Streptomyces griseus"),
            (["aspergillus niger", "a. niger", "a niger", "niger"], "Aspergillus niger"),
            (["aspergillus oryzae", "a. oryzae", "a oryzae", "oryzae"], "Aspergillus oryzae"),
            (["cupriavidus necator", "c. necator", "c necator", "necator"], "Cupriavidus necator"),
            (["zymomonas mobilis", "z. mobilis", "z mobilis", "mobilis"], "Zymomonas mobilis"),
            (["bacillus licheniformis", "b. licheniformis", "b licheniformis", "licheniformis"], "Bacillus licheniformis"),
            (["bacillus megaterium", "b. megaterium", "b megaterium", "megaterium"], "Bacillus megaterium"),
            (["bacillus cereus", "b. cereus", "b cereus", "cereus"], "Bacillus cereus"),
            (["bacillus coagulans", "b. coagulans", "b coagulans", "coagulans"], "Bacillus coagulans"),
            (["bacillus amyloliquefaciens", "b. amyloliquefaciens", "b amyloliquefaciens", "amyloliquefaciens"], "Bacillus amyloliquefaciens"),
            (["yarrowia lipolytica", "y. lipolytica", "y lipolytica", "lipolytica"], "Yarrowia lipolytica"),
            (["schizosaccharomyces pombe", "s. pombe", "s pombe", "pombe"], "Schizosaccharomyces pombe"),
            (["kluyveromyces lactis", "k. lactis", "k lactis"], "Kluyveromyces lactis"),
            (["candida utilis", "c. utilis", "c utilis"], "Candida utilis"),
            (["trichoderma reesei", "t. reesei", "t reesei"], "Trichoderma reesei"),
            (["penicillium chrysogenum", "p. chrysogenum", "p chrysogenum"], "Penicillium chrysogenum"),
            (["arthrospira platensis", "spirulina platensis", "a. platensis"], "Arthrospira platensis"),
            (["chlorella vulgaris", "c. vulgaris"], "Chlorella vulgaris"),
            (["gluconobacter oxydans", "g. oxydans"], "Gluconobacter oxydans"),
            (["acetobacter aceti", "a. aceti"], "Acetobacter aceti")
        ]

    def normalize_organism_name(self, organism):
        if organism is None:
            return None

        text = self.normalize_text(organism)

        if not text:
            return None

        for keywords, canonical in self.organism_alias_rules():
            for keyword in keywords:
                if keyword == text or keyword in text:
                    return canonical

        latin = re.search(r"\b([a-z]+)\s+([a-z]+)\b", text)

        if latin:
            return latin.group(1).capitalize() + " " + latin.group(2).lower()

        return str(organism).strip()

    # =====================================================
    # QUERY INTENT
    # =====================================================
    def query_requests_selected_group(self, query):
        q = self.normalize_text(query)

        phrases = [
            "compare",
            "comparison",
            "rank",
            "ranking",
            "selected microorganisms",
            "selected organisms",
            "these microorganisms",
            "these organisms",
            "all microorganisms",
            "all organisms",
            "all selected",
            "for each microorganism",
            "for each organism",
            "for all microorganisms",
            "for all organisms",
            "among them",
            "between them",
            "final master summary"
        ]

        return any(phrase in q for phrase in phrases)

    def query_is_bacdive_relevant(self, query):
        q = self.normalize_text(query)

        markers = [
            "bacdive",
            "strain",
            "strains",
            "culture",
            "growth",
            "growth condition",
            "growth conditions",
            "morphology",
            "physiology",
            "metabolism",
            "ncbi tax id",
            "taxonomy",
            "interaction",
            "safety",
            "reference strain",
            "type strain",
            "non-reference",
            "non reference",
            "all accepted strains",
            "bacdive url",
            "bacdive link",
            "oxygen",
            "aerobic",
            "anaerobic",
            "facultative",
            "fermentation",
            "temperature",
            "ph",
            "medium",
            "media",
            "substrate"
        ]

        return any(marker in q for marker in markers)

    def query_explicitly_bacdive_only(self, query):
        q = self.normalize_text(query)

        phrases = [
            "bacdive only",
            "only bacdive",
            "use only bacdive",
            "bacdive as the only source",
            "bacdive is the only source",
            "based only on bacdive",
            "from bacdive only"
        ]

        return any(phrase in q for phrase in phrases)

    # =====================================================
    # ORGANISM DETECTION
    # =====================================================
    def detect_organisms(
        self,
        query="",
        protocol=None,
        metadata=None,
        dataframe=None,
        microorganism=None,
        selected_microorganisms=None
    ):
        organisms = []

        selected = self.normalize_microorganism_list(selected_microorganisms)

        if selected and self.query_requests_selected_group(query):
            for item in selected:
                final_name = self.normalize_organism_name(item) or item
                if final_name not in organisms:
                    organisms.append(final_name)

            return organisms

        explicit = self.normalize_microorganism_list(microorganism)

        for item in explicit:
            final_name = self.normalize_organism_name(item) or item
            if final_name not in organisms:
                organisms.append(final_name)

        combined_parts = []

        if query:
            combined_parts.append(str(query))

        if protocol:
            combined_parts.append(str(protocol))

        if metadata:
            combined_parts.append(str(metadata))

        try:
            if dataframe is not None:
                combined_parts.extend([str(c) for c in dataframe.columns])
        except Exception:
            pass

        combined = self.normalize_text(" ".join(combined_parts))

        for keywords, canonical in self.organism_alias_rules():
            for keyword in keywords:
                if keyword in combined:
                    if canonical not in organisms:
                        organisms.append(canonical)
                    break

        if not organisms and combined:
            blocked_first_words = {
                "what", "which", "when", "where", "why", "how",
                "the", "and", "for", "with", "from", "into",
                "based", "using", "given", "under", "over",
                "only", "show", "give", "tell", "find", "compare",
                "optimize", "summary", "final", "master",
                "optimal", "growth", "culture", "oxygen", "fermentation"
            }

            latin_candidates = re.findall(r"\b([a-z]+)\s+([a-z]+)\b", combined)

            for genus, species in latin_candidates:
                if genus in blocked_first_words:
                    continue

                candidate = genus.capitalize() + " " + species.lower()

                if candidate not in organisms:
                    organisms.append(candidate)

        return organisms

    def resolve_bacdive_organisms(
        self,
        query="",
        protocol=None,
        metadata=None,
        dataframe=None,
        microorganism=None,
        selected_microorganisms=None,
        bacdive_microorganisms=None
    ):
        organisms = []

        explicit = self.normalize_microorganism_list(microorganism)
        selected = self.normalize_microorganism_list(selected_microorganisms)
        bacdive_selected = self.normalize_microorganism_list(bacdive_microorganisms)

        if explicit:
            organisms.extend(explicit)

        if bacdive_selected:
            organisms.extend(bacdive_selected)

        if selected:
            if self.query_requests_selected_group(query):
                organisms = list(selected)
            else:
                organisms.extend(selected)

        if not organisms:
            organisms.extend(
                self.detect_organisms(
                    query=query,
                    protocol=protocol,
                    metadata=metadata,
                    dataframe=dataframe,
                    microorganism=None,
                    selected_microorganisms=selected_microorganisms
                )
            )

        normalized = []

        for organism in organisms:
            final_name = self.normalize_organism_name(organism)
            if final_name and final_name not in normalized:
                normalized.append(final_name)

        return normalized

    # =====================================================
    # COLLECT AGENT SUMMARIES
    # =====================================================
    def collect_agent_summaries(self, outputs):
        summaries = {}

        for key, value in outputs.items():
            if not isinstance(value, dict):
                continue

            if key in ["system_summary"]:
                continue

            summaries[key] = {
                "agent_name": value.get("agent_name", key),
                "agent_status": value.get("agent_status", "unknown"),
                "summary": value.get(
                    "agent_summary",
                    self.build_agent_summary(key, value)
                )
            }

        return summaries

    # =====================================================
    # MAIN RUN
    # =====================================================
    def run(
        self,
        query,
        dataframe=None,
        metadata=None,
        protocol=None,
        microorganism=None,
        selected_microorganisms=None,
        bacdive_microorganisms=None,
        run_bacdive=False,
        bacdive_result=None,
        bacdive_max_results=None,
        use_all_agents=True,

        use_dataset=True,
        use_protocol=True,
        use_internet=True,
        use_crossref=True,
        use_literature=True,

        # New multi-context parameters
        datasets=None,
        metadata_files=None
    ):
        """Runs the orchestrated multi-agent workflow sequentially using PydanticAI.

        Args:
            query: The user query string.
            dataframe: Optional single pandas DataFrame (backward compatibility).
            metadata: Optional single experimental metadata dict (backward compatibility).
            protocol: Optional single experimental protocol dict (backward compatibility).
            microorganism: Optional list of target microorganisms.
            selected_microorganisms: Optional list of selected microorganisms.
            bacdive_microorganisms: Optional list of microorganisms for BacDive query.
            run_bacdive: Whether to execute the BacDive agent. Defaults to False.
            bacdive_result: Optional pre-loaded BacDive results dict.
            bacdive_max_results: Optional limit on the number of BacDive search results.
            use_all_agents: Whether to execute all agents regardless of other flags. Defaults to True.
            use_dataset: Whether to include the dataset analyst agent. Defaults to True.
            use_protocol: Whether to include the metadata analyst agent. Defaults to True.
            use_internet: Whether to include the internet explorer agent. Defaults to True.
            use_crossref: Whether to include the Crossref explorer agent. Defaults to True.
            use_literature: Obsolete literature reviewer parameter.
            datasets: Dict of filename -> DataFrame.
            metadata_files: Dict of filename -> Metadata JSON dict.

        Returns:
            A dict containing outputs and final assessment summary.
        """

        print("\n" + "=" * 100)
        print("[AGENT ORCHESTRATOR] RUN STARTED")
        print("=" * 100)

        run_started_at = datetime.now().isoformat()

        # Handle backward compatibility wrappers
        if datasets is None:
            datasets = {}
            if dataframe is not None:
                datasets["default_dataset"] = dataframe

        if metadata_files is None:
            metadata_files = {}
            if metadata is not None:
                metadata_files["default_metadata"] = metadata
            elif protocol is not None:
                metadata_files["default_metadata"] = protocol

        selected_microorganisms = self.normalize_microorganism_list(selected_microorganisms)
        if not selected_microorganisms:
            selected_microorganisms = self.normalize_microorganism_list(microorganism)

        if use_all_agents:
            use_dataset = True
            use_protocol = True
            use_internet = True
            use_crossref = True
            run_bacdive = True

        filter_state = {
            "use_dataset": use_dataset,
            "use_protocol": use_protocol,
            "use_internet": use_internet,
            "use_crossref": use_crossref,
            "run_bacdive": run_bacdive,
            "use_all_agents": use_all_agents
        }

        self.log_system_step(
            "run_started",
            {
                "query": query,
                "filters": filter_state,
                "selected_microorganisms": selected_microorganisms,
                "model": self.model_name,
                "temperature": self.temperature
            }
        )

        outputs = {"query": query}

        # 1. Dataset analysis
        df_to_analyze = None
        if datasets and isinstance(datasets, dict) and len(datasets) > 0:
            df_to_analyze = list(datasets.values())[0]
        elif dataframe is not None:
            df_to_analyze = dataframe

        if use_dataset and df_to_analyze is not None:
            outputs["data_analyst"] = self.safe_run(
                "DATA_ANALYST",
                self.data_agent.run,
                query=query,
                dataframe=df_to_analyze,
                use_llm=True
            )
        else:
            outputs["data_analyst"] = self.skipped_agent("DATA_ANALYST", "Dataset analysis skipped.")

        # 2. Metadata / Protocol analysis
        meta_to_analyze = None
        if metadata_files and isinstance(metadata_files, dict) and len(metadata_files) > 0:
            meta_to_analyze = list(metadata_files.values())[0]
        elif metadata is not None:
            meta_to_analyze = metadata
        elif protocol is not None:
            meta_to_analyze = protocol

        if use_protocol and (meta_to_analyze is not None or protocol is not None):
            outputs["metadata_analyst"] = self.safe_run(
                "METADATA_ANALYST",
                self.metadata_agent.run,
                metadata=meta_to_analyze,
                protocol=protocol,
                use_llm=True
            )
        else:
            outputs["metadata_analyst"] = self.skipped_agent("METADATA_ANALYST", "Metadata analysis skipped.")

        # 3. Organism detection and BacDive search
        resolved_organisms = []
        if run_bacdive or use_all_agents:
            resolved_organisms = self.resolve_bacdive_organisms(
                query=query,
                protocol=meta_to_analyze,
                metadata=meta_to_analyze,
                dataframe=df_to_analyze,
                microorganism=microorganism,
                selected_microorganisms=selected_microorganisms,
                bacdive_microorganisms=bacdive_microorganisms
            )
        
        outputs["detected_organisms"] = {
            "agent_name": "DETECTED_ORGANISMS",
            "agent_status": "success" if resolved_organisms else "skipped",
            "organisms": resolved_organisms
        }

        if run_bacdive and resolved_organisms:
            bacdive_results = {}
            for org in resolved_organisms:
                result = self.safe_run(
                    "BACDIVE_EXPLORER",
                    self.bacdive_agent.run,
                    query=query,
                    microorganism=org,
                    use_llm=False,
                    max_results=bacdive_max_results
                )
                bacdive_results[org] = result
            
            outputs["bacdive_explorer"] = {
                "agent_name": "BACDIVE_EXPLORER",
                "agent_status": "success",
                "results": bacdive_results,
                "agent_summary": f"Executed BacDive search for {', '.join(resolved_organisms)}."
            }
        else:
            outputs["bacdive_explorer"] = self.skipped_agent("BACDIVE_EXPLORER", "BacDive query skipped.")

        # 4. Crossref Explorer
        if use_crossref:
            outputs["crossref_explorer"] = self.safe_run(
                "CROSSREF_EXPLORER",
                self.crossref_agent.run,
                query=query,
                use_llm=True
            )
        else:
            outputs["crossref_explorer"] = self.skipped_agent("CROSSREF_EXPLORER", "Crossref search skipped.")

        # 5. Internet Explorer
        if use_internet:
            outputs["internet_explorer"] = self.safe_run(
                "INTERNET_EXPLORER",
                self.internet_agent.run,
                query=query,
                use_llm=True
            )
        else:
            outputs["internet_explorer"] = self.skipped_agent("INTERNET_EXPLORER", "Internet search skipped.")

        # Build combined agent summaries
        outputs["agent_summaries"] = {
            "agent_name": "AGENT_SUMMARIES",
            "agent_status": "success",
            "summaries": self.collect_agent_summaries(outputs),
            "agent_summary": "Collected summaries from sequential execution."
        }

        # 6. Master Summarizer
        master_result = self.safe_run(
            "MASTER_SUMMARIZER",
            self.master_agent.run,
            agent_outputs=outputs
        )
        outputs["master_summarizer"] = master_result
        outputs["assessment"] = master_result.get("final_summary", "")

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
            "model": self.model_name,
            "temperature": self.temperature,
            "mode": "sequential_multi_agent",
            "run_started_at": run_started_at,
            "run_finished_at": datetime.now().isoformat(),
            "log_directory": self.log_dir
        }

        self.log_system_step("run_completed", outputs["system_summary"])

        print("\n" + "=" * 100)
        print("[AGENT ORCHESTRATOR] RUN COMPLETED")
        print("=" * 100)

        return outputs