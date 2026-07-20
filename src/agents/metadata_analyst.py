"""Metadata Analyst Agent.

Analyzes experimental metadata and protocols for completeness, ISA-tab compliance,
and alignment with FAIR data sharing principles.
"""

import json
import re
import traceback

import os
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.ollama import OllamaModel


from pydantic_ai.providers.ollama import OllamaProvider


class MetadataAnalystAgent:
    """Evaluates experimental metadata quality and protocol completeness.

    Attributes:
        model_name: Name of the LLM.
        temperature: LLM temperature parameter.
        debug: True if debug prints are enabled.
    """
    # =====================================================
    # INIT
    # =====================================================
    def __init__(
        self,
        model_name="llama3:latest",
        temperature=0.2,
        debug=True
    ):
        """Initializes the MetadataAnalystAgent.

        Args:
            model_name: The name of the LLM. Defaults to "llama3:latest".
            temperature: LLM temperature parameter. Defaults to 0.2.
            debug: Whether to print debug information. Defaults to True.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.debug = debug
        print("\n" + "=" * 100)
        print("[METADATA ANALYST] INITIALIZING")
        print("=" * 100)
        print(f"MODEL: {model_name}")
        print(f"TEMPERATURE: {temperature}")
        print("[METADATA ANALYST] Agent summary enabled")
        
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        provider = OllamaProvider(base_url=base_url)
        model = OllamaModel(model_name=model_name, provider=provider)
        self.agent = Agent(
            model=model,
            model_settings=ModelSettings(temperature=temperature)
        )
        print("[METADATA ANALYST] READY")
        print("=" * 100 + "\n")
    # =====================================================
    # DEBUG PRINT
    # =====================================================
    def debug_print(self, title, data):
        if not self.debug:
            return
        print("\n" + "=" * 100)
        print(f"[METADATA ANALYST DEBUG] {title}")
        print("=" * 100)
        try:
            if isinstance(data, str):
                print(data)
            else:
                print(
                    json.dumps(
                        data,
                        indent=2,
                        default=str,
                        ensure_ascii=False
                    )
                )
        except Exception as ex:
            print(str(data))
            print(f"\n[DEBUG PRINT ERROR] {str(ex)}")
        print("=" * 100 + "\n")
    # =====================================================
    # SAFE JSON
    # =====================================================
    def safe_json(self, data):
        try:
            return json.dumps(
                data,
                indent=2,
                default=str,
                ensure_ascii=False
            )
        except Exception:
            return str(data)
    # =====================================================
    # CLEAN TEXT
    # =====================================================
    def clean_text(self, text):
        text = str(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    # =====================================================
    # EMPTY VALUE CHECK
    # =====================================================
    def is_empty_value(self, value):
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False
    # =====================================================
    # NORMALIZE KEYS
    # =====================================================
    def normalize_keys(self, data):
        if not isinstance(data, dict):
            return {}
        return {
            str(k).strip().lower(): v
            for k, v in data.items()
        }
    # =====================================================
    # DETECT MISSING FIELDS
    # =====================================================
    def detect_missing_metadata(self, metadata, protocol):
        required_metadata = [
            "title",
            "description",
            "organism",
            "strain",
            "investigator",
            "institution",
            "date",
            "project",
            "keywords",
            "funding",
            "license"
        ]
        required_protocol = [
            "protocol_title",
            "protocol_description",
            "temperature",
            "ph",
            "medium",
            "sampling",
            "replicates",
            "instrument",
            "calibration",
            "analysis_method"
        ]
        metadata_lower = self.normalize_keys(metadata)
        protocol_lower = self.normalize_keys(protocol)
        missing = {
            "metadata_missing": [],
            "protocol_missing": [],
            "metadata_present": [],
            "protocol_present": []
        }
        for field in required_metadata:
            value = metadata_lower.get(field)
            if self.is_empty_value(value):
                missing["metadata_missing"].append(field)
            else:
                missing["metadata_present"].append(field)
        for field in required_protocol:
            value = protocol_lower.get(field)
            if self.is_empty_value(value):
                missing["protocol_missing"].append(field)
            else:
                missing["protocol_present"].append(field)
        return missing
    # =====================================================
    # ISA COMPLIANCE CHECK
    # =====================================================
    def isa_compliance_check(self, metadata, protocol):
        total = 10
        checks = {
            "investigation_present": False,
            "study_description_present": False,
            "protocol_present": False,
            "organism_or_material_present": False,
            "instrument_present": False,
            "experimental_factors_present": False,
            "replicates_present": False,
            "sampling_present": False,
            "metadata_keywords_present": False,
            "license_present": False
        }
        metadata_text = json.dumps(
            metadata,
            default=str,
            ensure_ascii=False
        ).lower()
        protocol_text = json.dumps(
            protocol,
            default=str,
            ensure_ascii=False
        ).lower()
        combined_text = metadata_text + " " + protocol_text
        if any(
            x in metadata_text
            for x in ["investigator", "author", "researcher", "contact"]
        ):
            checks["investigation_present"] = True
        if any(
            x in metadata_text
            for x in ["description", "study", "objective", "aim", "title"]
        ):
            checks["study_description_present"] = True
        if isinstance(protocol, dict) and len(protocol) > 0:
            checks["protocol_present"] = True
        if any(
            x in combined_text
            for x in ["organism", "strain", "species", "sample", "material"]
        ):
            checks["organism_or_material_present"] = True
        if any(
            x in protocol_text
            for x in ["instrument", "bioreactor", "biolector", "sensor", "plate reader"]
        ):
            checks["instrument_present"] = True
        if any(
            x in protocol_text
            for x in ["temperature", "ph", "oxygen", "rpm", "medium", "feed"]
        ):
            checks["experimental_factors_present"] = True
        if any(
            x in protocol_text
            for x in ["replicate", "replicates", "biological replicate", "technical replicate"]
        ):
            checks["replicates_present"] = True
        if any(
            x in protocol_text
            for x in ["sampling", "sample", "timepoint", "interval", "measurement"]
        ):
            checks["sampling_present"] = True
        if any(
            x in metadata_text
            for x in ["keyword", "keywords", "tag", "tags"]
        ):
            checks["metadata_keywords_present"] = True
        if any(
            x in metadata_text
            for x in ["license", "cc by", "creativecommons", "reuse"]
        ):
            checks["license_present"] = True
        score = sum(1 for v in checks.values() if v)
        return {
            "score": score,
            "max_score": total,
            "percentage": round((score / total) * 100, 2),
            "checks": checks
        }
    # =====================================================
    # FAIR SUPPORT CHECK
    # =====================================================
    def fair_support_check(self, metadata, protocol):
        metadata_text = json.dumps(
            metadata,
            default=str,
            ensure_ascii=False
        ).lower()
        protocol_text = json.dumps(
            protocol,
            default=str,
            ensure_ascii=False
        ).lower()
        combined_text = metadata_text + " " + protocol_text
        checks = {
            "findable": any(
                x in metadata_text
                for x in ["title", "keywords", "identifier", "doi", "accession"]
            ),
            "accessible": any(
                x in metadata_text
                for x in ["license", "repository", "url", "access"]
            ),
            "interoperable": any(
                x in combined_text
                for x in ["ontology", "isa", "unit", "standard", "controlled vocabulary"]
            ),
            "reusable": any(
                x in combined_text
                for x in ["license", "protocol", "method", "calibration", "replicate"]
            )
        }
        score = sum(1 for v in checks.values() if v)
        return {
            "score": score,
            "max_score": 4,
            "percentage": round((score / 4) * 100, 2),
            "checks": checks
        }
    # =====================================================
    # BUILD STRUCTURED DATA
    # =====================================================
    def build_structured_analysis(self, metadata, protocol):
        if not isinstance(metadata, dict):
            metadata = {}
        if not isinstance(protocol, dict):
            protocol = {}
        missing_fields = self.detect_missing_metadata(
            metadata,
            protocol
        )
        isa_analysis = self.isa_compliance_check(
            metadata,
            protocol
        )
        fair_analysis = self.fair_support_check(
            metadata,
            protocol
        )
        structured = {
            "metadata": metadata,
            "protocol": protocol,
            "missing_analysis": missing_fields,
            "isa_compliance": isa_analysis,
            "fair_support": fair_analysis,
            "metadata_field_count": int(len(metadata)),
            "protocol_field_count": int(len(protocol))
        }
        structured["agent_summary"] = self.build_agent_summary(
            structured
        )
        return structured
    # =====================================================
    # AGENT SUMMARY
    # =====================================================
    def build_agent_summary(self, structured):
        metadata_count = structured.get("metadata_field_count", 0)
        protocol_count = structured.get("protocol_field_count", 0)
        missing = structured.get("missing_analysis", {})
        isa = structured.get("isa_compliance", {})
        fair = structured.get("fair_support", {})
        metadata_missing = missing.get("metadata_missing", [])
        protocol_missing = missing.get("protocol_missing", [])
        text = ""
        text += (
            f"Metadata contains {metadata_count} fields and protocol contains "
            f"{protocol_count} fields. "
        )
        text += (
            f"Missing metadata fields: "
            f"{', '.join(metadata_missing) if metadata_missing else 'none detected'}. "
        )
        text += (
            f"Missing protocol fields: "
            f"{', '.join(protocol_missing) if protocol_missing else 'none detected'}. "
        )
        text += (
            f"ISA-style completeness score: "
            f"{isa.get('score', 0)}/{isa.get('max_score', 10)} "
            f"({isa.get('percentage', 0)}%). "
        )
        text += (
            f"FAIR-support score: "
            f"{fair.get('score', 0)}/{fair.get('max_score', 4)} "
            f"({fair.get('percentage', 0)}%). "
        )
        if metadata_missing or protocol_missing:
            text += (
                "The missing fields may reduce reproducibility, protocol "
                "interpretability, and reuse of the experiment."
            )
        else:
            text += (
                "No required metadata/protocol fields were flagged as missing "
                "by the configured checklist."
            )
        return text
    # =====================================================
    # BUILD PROMPT
    # =====================================================
    def build_prompt(self, structured):
        return f"""
You are a scientific metadata analyst in a collaborative industrial
biotechnology multi-agent system.
Your task is to interpret ONLY the metadata/protocol evidence below.
==================================================
STRUCTURED METADATA ANALYSIS
==================================================
{self.safe_json(structured)}
==================================================
STRICT RULES
==================================================
1. Use ONLY the provided metadata and protocol information.
2. Do NOT invent missing metadata.
3. Do NOT infer experimental conditions unless explicitly present.
4. Do NOT infer biological or industrial conclusions.
5. Clearly separate:
   - observed metadata
   - missing metadata
   - reproducibility risks
   - uncertainty
6. If evidence is insufficient, say "Insufficient evidence available."
7. Keep the answer concise and useful for the MasterSummarizer.
==================================================
OUTPUT STYLE
==================================================
Do NOT force a fixed template.
Use only useful sections, for example:
- Metadata Completeness
- Protocol Completeness
- ISA-Style Assessment
- FAIR Support
- Reproducibility Risks
- Recommended Metadata Improvements
Do not include empty sections.
Do not output raw JSON.
"""
    # =====================================================
    # RUN
    # =====================================================
    def run(
        self,
        metadata=None,
        protocol=None,
        use_llm=True
    ):
        print("\n" + "=" * 100)
        print("[METADATA ANALYST] RUN STARTED")
        print("=" * 100)
        metadata = metadata or {}
        protocol = protocol or {}
        self.debug_print(
            "RAW METADATA INPUT",
            metadata
        )
        self.debug_print(
            "RAW PROTOCOL INPUT",
            protocol
        )
        structured = self.build_structured_analysis(
            metadata,
            protocol
        )
        self.debug_print(
            "STRUCTURED ANALYSIS",
            structured
        )
        agent_summary = structured.get(
            "agent_summary",
            ""
        )
        if use_llm:
            prompt = self.build_prompt(structured)
            self.debug_print(
                "METADATA ANALYST PROMPT",
                prompt
            )
            try:
                print("[METADATA ANALYST] INVOKING OLLAMA...")
                result = self.agent.run_sync(prompt)
                assessment = result.data
                status = "success"
                print("[METADATA ANALYST] OLLAMA SUCCESS")
            except Exception as ex:
                traceback.print_exc()
                assessment = (
                    "Metadata Analyst LLM generation failed. "
                    "Using deterministic agent summary.\n\n"
                    + agent_summary
                )
                status = "failed"
                print("[METADATA ANALYST ERROR]")
                print(str(ex))
        else:
            assessment = agent_summary
            status = "success"
        self.debug_print(
            "FINAL METADATA ASSESSMENT",
            assessment
        )
        response = {
            "agent_name": "METADATA_ANALYST",
            "agent_status": status,
            "structured": structured,
            "summary": {
                "metadata_fields": structured.get("metadata_field_count", 0),
                "protocol_fields": structured.get("protocol_field_count", 0),
                "missing_metadata_count": len(
                    structured.get("missing_analysis", {}).get(
                        "metadata_missing",
                        []
                    )
                ),
                "missing_protocol_count": len(
                    structured.get("missing_analysis", {}).get(
                        "protocol_missing",
                        []
                    )
                ),
                "isa_percentage": structured.get(
                    "isa_compliance",
                    {}
                ).get("percentage", 0),
                "fair_percentage": structured.get(
                    "fair_support",
                    {}
                ).get("percentage", 0)
            },
            "agent_summary": agent_summary,
            "assessment": assessment
        }
        self.debug_print(
            "FINAL METADATA RESPONSE",
            response
        )
        print("\n" + "=" * 100)
        print("[METADATA ANALYST] RUN COMPLETE")
        print("=" * 100 + "\n")
        return response