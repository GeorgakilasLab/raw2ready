# -*- coding: utf-8 -*-
# src.agents/bacdive_explorer.py

import re
import json
import traceback
import requests

from urllib.parse import quote
from langchain_ollama import OllamaLLM


class BacDiveExplorerAgent:
    """
    Deterministic BacDive Scientific Explorer

    Responsibilities:
    - Retrieve BacDive strain-level evidence.
    - Use BacDive as descriptive strain metadata.
    - Avoid unsupported biological inference.
    - Exact species matching required.
    - Return both detailed assessment and compact agent_summary.
    - LLM is optional and used only for formatting/summarization.
    """

    def __init__(
        self,
        model_name="llama3:latest",
        temperature=0.0,
        debug=True
    ):
        self.base_url = "https://api.bacdive.dsmz.de/v2"
        self.debug = debug

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "BacDiveExplorerAgent/14.0"
            }
        )

        self.model_name = model_name
        self.temperature = temperature

        self.llm = OllamaLLM(
            model=model_name,
            temperature=temperature
        )

        self.organism_aliases = {
            "e. coli": "Escherichia coli",
            "e coli": "Escherichia coli",
            "ecoli": "Escherichia coli",

            "b. subtilis": "Bacillus subtilis",
            "b subtilis": "Bacillus subtilis",

            "s. cerevisiae": "Saccharomyces cerevisiae",
            "s cerevisiae": "Saccharomyces cerevisiae",

            "pichia pastoris": "Komagataella phaffii",
            "p. pastoris": "Komagataella phaffii",
            "p pastoris": "Komagataella phaffii",

            "k. phaffii": "Komagataella phaffii",
            "k phaffii": "Komagataella phaffii",

            "spirulina platensis": "Arthrospira platensis"
        }

        self.valid_microorganisms = sorted({
            "Acetobacter aceti",
            "Arthrospira platensis",
            "Aspergillus niger",
            "Aspergillus oryzae",
            "Bacillus amyloliquefaciens",
            "Bacillus cereus",
            "Bacillus coagulans",
            "Bacillus licheniformis",
            "Bacillus megaterium",
            "Bacillus subtilis",
            "Candida utilis",
            "Chlorella vulgaris",
            "Clostridium acetobutylicum",
            "Clostridium beijerinckii",
            "Corynebacterium glutamicum",
            "Cupriavidus necator",
            "Escherichia coli",
            "Gluconobacter oxydans",
            "Kluyveromyces lactis",
            "Komagataella phaffii",
            "Lactobacillus casei",
            "Lactobacillus plantarum",
            "Lactococcus lactis",
            "Penicillium chrysogenum",
            "Pseudomonas aeruginosa",
            "Pseudomonas fluorescens",
            "Pseudomonas putida",
            "Saccharomyces cerevisiae",
            "Schizosaccharomyces pombe",
            "Streptomyces coelicolor",
            "Streptomyces griseus",
            "Trichoderma reesei",
            "Yarrowia lipolytica",
            "Zymomonas mobilis"
        })

        print("[BACDIVE] Deterministic BacDive Explorer initialized")
        print("[BACDIVE] Evidence-safe mode enabled")
        print("[BACDIVE] Exact species validation enabled")
        print("[BACDIVE] Agent summary enabled")
        print("[BACDIVE] LLM used ONLY for optional UI summarization")

    # =====================================================
    # BASIC HELPERS
    # =====================================================

    def debug_print(self, title, data):
        if not self.debug:
            return

        print("\n" + "=" * 80)
        print(f"[BACDIVE DEBUG] {title}")
        print("=" * 80)

        try:
            print(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False,
                    default=str
                )
            )
        except Exception:
            print(str(data))

        print("=" * 80 + "\n")

    def normalize_text(self, text):
        if text is None:
            return ""

        text = str(text).replace("\n", " ")
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def strip_html_tags(self, text):
        if text is None:
            return ""

        return re.sub(r"<[^>]+>", "", str(text)).strip()

    def clean_organism(self, query=None, microorganism=None):
        source = microorganism if microorganism else query

        if not source:
            return None

        source = self.normalize_text(source)
        lower = source.lower()

        for alias, canonical in self.organism_aliases.items():
            if re.search(rf"\b{re.escape(alias)}\b", lower):
                return canonical

        for organism in self.valid_microorganisms:
            if lower == organism.lower():
                return organism

        for organism in self.valid_microorganisms:
            if lower in organism.lower():
                return organism

        latin_match = re.search(
            r"\b([A-Z][a-z]+)\s+([a-z][a-z\-]+)\b",
            source
        )

        if latin_match:
            return f"{latin_match.group(1)} {latin_match.group(2)}"

        latin_match_lower = re.search(
            r"\b([a-z]{3,})\s+([a-z]{3,})\b",
            lower
        )

        if latin_match_lower:
            genus = latin_match_lower.group(1).capitalize()
            species = latin_match_lower.group(2).lower()
            return f"{genus} {species}"

        return None

    def canonical_species(self, organism):
        organism = self.clean_organism(query=organism)

        if not organism:
            return None

        parts = organism.split()

        if len(parts) < 2:
            return organism

        return f"{parts[0]} {parts[1]}"

    # =====================================================
    # BACDIVE API
    # =====================================================

    def api_get(self, endpoint):
        url = f"{self.base_url}{endpoint}"

        response = self.session.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    def get_taxon_records(self, organism):
        canonical = self.canonical_species(organism)

        if not canonical:
            return {
                "count": 0,
                "results": []
            }

        parts = canonical.split()

        if len(parts) != 2:
            return {
                "count": 0,
                "results": []
            }

        genus = quote(parts[0])
        species = quote(parts[1])

        endpoint = f"/taxon/{genus}/{species}"

        try:
            data = self.api_get(endpoint)

            self.debug_print(
                "BACDIVE RAW TAXON RESULT",
                data
            )

            return data

        except Exception as ex:
            self.debug_print(
                "BACDIVE TAXON ERROR",
                str(ex)
            )

            return {
                "count": 0,
                "results": []
            }

    def extract_bacdive_ids(self, taxon_data):
        if not taxon_data:
            return []

        results = taxon_data.get("results", [])
        ids = []

        for item in results:
            if isinstance(item, int):
                ids.append(str(item))

            elif isinstance(item, str):
                ids.append(item)

            elif isinstance(item, dict):
                for key in [
                    "id",
                    "bacdive_id",
                    "BacDive-ID"
                ]:
                    if key in item:
                        ids.append(str(item[key]))
                        break

        return list(dict.fromkeys(ids))

    def fetch_strain(self, bacdive_id):
        endpoint = f"/fetch/{bacdive_id}"

        data = self.api_get(endpoint)

        self.debug_print(
            f"FETCH STRAIN {bacdive_id}",
            data
        )

        results = data.get("results", {})

        if isinstance(results, dict):
            if str(bacdive_id) in results:
                return results[str(bacdive_id)]

            values = list(results.values())

            if values:
                return values[0]

        return data

    # =====================================================
    # JSON HELPERS
    # =====================================================

    def flatten_json(self, data, parent_key=""):
        rows = []

        if isinstance(data, dict):
            for key, value in data.items():
                new_key = (
                    f"{parent_key}.{key}"
                    if parent_key
                    else str(key)
                )

                rows.extend(
                    self.flatten_json(
                        value,
                        new_key
                    )
                )

        elif isinstance(data, list):
            for index, value in enumerate(data):
                new_key = f"{parent_key}[{index}]"

                rows.extend(
                    self.flatten_json(
                        value,
                        new_key
                    )
                )

        else:
            rows.append(
                {
                    "field": parent_key,
                    "value": self.strip_html_tags(str(data))
                }
            )

        return rows

    def get_record_species_name(self, strain):
        flat = self.flatten_json(strain)

        for row in flat:
            field = row["field"].lower()
            value = row["value"]

            if (
                "full scientific name" in field
                or "species" in field
                or "organism" in field
            ):
                match = re.search(
                    r"\b([A-Z][a-z]+)\s+([a-z][a-z\-]+)\b",
                    value
                )

                if match:
                    return f"{match.group(1)} {match.group(2)}"

        return ""

    def species_matches(self, requested, strain):
        requested_species = self.canonical_species(requested)
        record_species = self.get_record_species_name(strain)

        if not requested_species or not record_species:
            return False

        return requested_species.lower() == record_species.lower()

    # =====================================================
    # STRAIN METADATA HELPERS
    # =====================================================

    def get_taxonomy_value(self, strain, key_name):
        taxonomy = strain.get(
            "Name and taxonomic classification",
            {}
        )

        if isinstance(taxonomy, dict):
            for key, value in taxonomy.items():
                if key.lower() == key_name.lower():
                    return self.strip_html_tags(value)

            for value in taxonomy.values():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_key.lower() == key_name.lower():
                            return self.strip_html_tags(sub_value)

        return ""

    def get_description(self, strain):
        full_name = self.get_taxonomy_value(
            strain,
            "full scientific name"
        )

        if full_name:
            return full_name

        flat = self.flatten_json(strain)

        for row in flat:
            field = row["field"].lower()
            value = row["value"]

            if "description" in field and value:
                return value

        return "No BacDive description available."

    def get_ncbi_tax_id(self, strain):
        flat = self.flatten_json(strain)

        for row in flat:
            field = row["field"].lower()

            if "ncbi tax id" in field:
                return row["value"]

        return "Not available in BacDive record."

    def get_strain_designation(self, strain):
        flat = self.flatten_json(strain)
        values = []

        wanted_fields = [
            "strain designation",
            "designation",
            "strain number",
            "culture collection no",
            "culture collection number"
        ]

        for row in flat:
            field = row["field"].lower()
            value = self.normalize_text(row["value"])

            if not value:
                continue

            for wanted in wanted_fields:
                if wanted in field:
                    if value not in values:
                        values.append(value)

        return ", ".join(values)

    def is_reference_strain(self, strain):
        flat = self.flatten_json(strain)

        for row in flat:
            field = row["field"].lower()
            value = str(row["value"]).lower().strip()

            if "type strain" in field and value == "yes":
                return True

        return False

    # =====================================================
    # READABLE SECTION FORMATTER
    # =====================================================

    def clean_field_name(self, field):
        field = field.split(".")[-1]
        field = re.sub(r"\[\d+\]", "", field)
        field = field.replace("_", " ")
        field = field.strip()

        if not field:
            return "Value"

        return field[:1].upper() + field[1:]

    def should_skip_output_field(self, field, value):
        field_lower = field.lower()
        value = str(value).strip()

        if not value or value.lower() in [
            "none",
            "null",
            "nan"
        ]:
            return True

        skip_tokens = [
            "@ref",
            "url",
            "link",
            "file name",
            "score",
            "accession",
            "database",
            "sequence identity",
            "total samples",
            "soil counts",
            "aquatic counts",
            "animal counts",
            "plant counts",
            "pubmed",
            "doi",
            "reference"
        ]

        return any(
            token in field_lower
            for token in skip_tokens
        )

    def format_readable_section(self, title, section_data):
        text = f"### {title}\n\n"

        if not section_data:
            text += "No BacDive evidence retrieved for this section.\n\n"
            return text

        flat = self.flatten_json(section_data)
        rows = []

        for row in flat:
            field = row["field"]
            value = self.normalize_text(row["value"])

            if self.should_skip_output_field(field, value):
                continue

            clean_field = self.clean_field_name(field)
            line = f"- {clean_field}: {value}"

            if line not in rows:
                rows.append(line)

        if not rows:
            text += "No important BacDive evidence retrieved for this section.\n\n"
        else:
            text += "\n".join(rows) + "\n\n"

        return text

    # =====================================================
    # EXTRACT STRAIN DATA
    # =====================================================

    def extract_strain_data(self, strain, bacdive_id):
        species_name = self.get_record_species_name(strain)

        return {
            "bacdive_id": bacdive_id,
            "bacdive_url": f"https://bacdive.dsmz.de/strain/{bacdive_id}",
            "species": species_name,
            "is_reference": self.is_reference_strain(strain),
            "strain_designation": self.get_strain_designation(strain),
            "raw_json": strain
        }

    # =====================================================
    # VALID MICROORGANISMS
    # =====================================================

    def get_valid_microorganisms(self):
        return sorted(list(set(self.valid_microorganisms)))

    def print_valid_microorganisms(self):
        print("\n" + "=" * 80)
        print("VALID BACDIVE MICROORGANISMS")
        print("=" * 80)

        for index, organism in enumerate(
            self.get_valid_microorganisms(),
            start=1
        ):
            print(f"{index}. {organism}")

        print("=" * 80 + "\n")

    def validate_microorganism(self, organism):
        canonical = self.canonical_species(organism)

        if not canonical:
            return False

        try:
            data = self.search(
                organism=canonical,
                max_results=1
            )

            return data.get("supported", False)

        except Exception:
            return False

    def add_valid_microorganism(self, organism):
        canonical = self.canonical_species(organism)

        if not canonical:
            return False

        try:
            if not self.validate_microorganism(canonical):
                return False

            if canonical not in self.valid_microorganisms:
                self.valid_microorganisms.append(canonical)
                self.valid_microorganisms = sorted(
                    list(set(self.valid_microorganisms))
                )

            print(f"[BACDIVE] Added valid microorganism: {canonical}")

            return True

        except Exception as ex:
            print(
                f"[BACDIVE] Failed adding microorganism "
                f"{organism}: {str(ex)}"
            )

            return False

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        organism=None,
        max_results=None
    ):
        organism = self.clean_organism(query=organism)

        if not organism:
            return {
                "supported": False,
                "message": "No valid microorganism provided."
            }

        try:
            taxon_data = self.get_taxon_records(organism)
            count = taxon_data.get("count", 0)
            raw_ids = self.extract_bacdive_ids(taxon_data)

            if count == 0 or not raw_ids:
                return {
                    "supported": False,
                    "organism": organism,
                    "message": "This microorganism is not currently supported by BacDive.",
                    "summary": {
                        "raw_count": count,
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "fetched_count": 0
                    }
                }

            accepted = []
            rejected = []

            ids_to_fetch = (
                raw_ids
                if max_results is None
                else raw_ids[:max_results]
            )

            for bacdive_id in ids_to_fetch:
                try:
                    strain = self.fetch_strain(bacdive_id)

                    if not self.species_matches(organism, strain):
                        rejected.append(
                            {
                                "bacdive_id": bacdive_id,
                                "reason": "Species mismatch"
                            }
                        )
                        continue

                    accepted.append(
                        self.extract_strain_data(
                            strain,
                            bacdive_id
                        )
                    )

                except Exception as ex:
                    rejected.append(
                        {
                            "bacdive_id": bacdive_id,
                            "reason": str(ex)
                        }
                    )

            return {
                "supported": len(accepted) > 0,
                "organism": organism,
                "summary": {
                    "raw_count": count,
                    "accepted_count": len(accepted),
                    "rejected_count": len(rejected),
                    "fetched_count": len(ids_to_fetch)
                },
                "raw_taxon_result": taxon_data,
                "accepted_strains": accepted,
                "rejected_strains": rejected
            }

        except Exception as ex:
            traceback.print_exc()

            return {
                "supported": False,
                "organism": organism,
                "error": str(ex)
            }

    # =====================================================
    # AGENT SUMMARY
    # =====================================================

    def build_agent_summary(
        self,
        organism,
        accepted_strains,
        rejected_strains,
        summary
    ):
        accepted_count = summary.get("accepted_count", 0)
        rejected_count = summary.get("rejected_count", 0)
        raw_count = summary.get("raw_count", 0)
        fetched_count = summary.get("fetched_count", 0)

        reference_count = len(
            [
                strain for strain in accepted_strains
                if strain.get("is_reference")
            ]
        )

        non_reference_count = accepted_count - reference_count

        urls = [
            strain.get("bacdive_url")
            for strain in accepted_strains
            if strain.get("bacdive_url")
        ]

        text = ""

        text += f"BacDive retrieved descriptive strain-level evidence for {organism}. "
        text += (
            f"{raw_count} raw BacDive records were found, "
            f"{fetched_count} records were fetched, "
            f"and {accepted_count} exact-species records were accepted. "
        )

        if rejected_count:
            text += (
                f"{rejected_count} records were rejected, mainly because of "
                "species mismatch or fetch/parsing issues. "
            )

        text += (
            f"Among accepted records, {reference_count} were identified as "
            f"reference/type strains and {non_reference_count} as non-reference strains. "
        )

        if urls:
            text += "BacDive strain URLs are available in the detailed output. "

        text += (
            "These BacDive records should be treated as descriptive metadata, "
            "not as proof of industrial optimization, oxygen-limited feasibility, "
            "scale-up suitability, or optimized growth conditions."
        )

        return text

    # =====================================================
    # BUILD SAFE READABLE ASSESSMENT
    # =====================================================

    def build_non_llm_assessment(
        self,
        organism,
        accepted_strains,
        rejected_strains,
        summary
    ):
        text = ""

        text += f"# BacDive Evidence for {organism}\n\n"

        text += (
            "IMPORTANT:\n"
            "The retrieved BacDive records are descriptive strain records. "
            "They do not constitute experimentally validated industrial "
            "bioprocess optimization studies. Missing evidence should be "
            "treated as unknown.\n\n"
        )

        text += "# Executive Summary\n\n"
        text += f"Raw BacDive records found: {summary.get('raw_count', 0)}\n\n"
        text += f"Fetched BacDive records: {summary.get('fetched_count', 0)}\n\n"
        text += f"Accepted exact-species strains: {summary.get('accepted_count', 0)}\n\n"
        text += f"Rejected strains: {summary.get('rejected_count', 0)}\n\n"

        reference_strains = [
            strain for strain in accepted_strains
            if strain.get("is_reference")
        ]

        non_reference_strains = [
            strain for strain in accepted_strains
            if not strain.get("is_reference")
        ]

        text += f"Reference/type strains in fetched results: {len(reference_strains)}\n\n"
        text += f"Non-reference strains in fetched results: {len(non_reference_strains)}\n\n"

        text += "# Central BacDive Information\n\n"

        if accepted_strains:
            strain_data = accepted_strains[0]

            strain = strain_data.get("raw_json", {})
            bacdive_id = strain_data.get("bacdive_id")
            bacdive_url = strain_data.get("bacdive_url")
            species = strain_data.get("species") or organism
            strain_designation = strain_data.get("strain_designation")
            label = "Reference" if strain_data.get("is_reference") else "Non-reference"

            text += f"## First Accepted Strain ({label})\n\n"
            text += f"Species: {species}\n\n"

            if strain_designation:
                text += f"Strain designation: {strain_designation}\n\n"

            text += f"BacDive ID: {bacdive_id}\n\n"
            text += f"BacDive URL: {bacdive_url}\n\n"

            text += "### Description\n\n"
            text += f"{self.get_description(strain)}\n\n"

            text += "### NCBI Tax ID\n\n"
            text += f"{self.get_ncbi_tax_id(strain)}\n\n"

            text += self.format_readable_section(
                "Morphology",
                strain.get("Morphology", {})
            )

            text += self.format_readable_section(
                "Culture and Growth Conditions",
                strain.get("Culture and growth conditions", {})
            )

            text += self.format_readable_section(
                "Physiology and Metabolism",
                strain.get("Physiology and metabolism", {})
            )

            text += self.format_readable_section(
                "Interaction and Safety",
                strain.get("Application and interaction", {})
            )

        else:
            text += "No accepted BacDive strains were available.\n\n"

        text += "# All Accepted Strains\n\n"

        if accepted_strains:
            for strain_data in accepted_strains:
                species = strain_data.get("species") or organism
                bacdive_url = strain_data.get("bacdive_url")
                strain_designation = strain_data.get("strain_designation")

                if strain_data.get("is_reference"):
                    text += f"Reference --> {species} - {bacdive_url}\n"
                else:
                    if strain_designation:
                        text += (
                            f"Non-reference --> {species} - strain "
                            f"{strain_designation} - {bacdive_url}\n"
                        )
                    else:
                        text += f"Non-reference --> {species} - {bacdive_url}\n"
        else:
            text += "No accepted BacDive strain URLs available.\n"

        if rejected_strains:
            text += "\n# Rejected Strains\n\n"

            for item in rejected_strains:
                bacdive_id = item.get("bacdive_id", "Unknown")
                reason = item.get("reason", "Unknown reason")
                text += f"- BacDive ID {bacdive_id}: {reason}\n"

        text += "\n# Scientific Limitations\n\n"

        text += (
            "- BacDive records are descriptive metadata records.\n"
            "- Missing evidence should be treated as unknown.\n"
            "- Recorded growth conditions are not necessarily optimized industrial conditions.\n"
            "- No inferred oxygen limitation conclusions should be made.\n"
            "- No inferred industrial optimization conclusions should be made.\n"
            "- No inferred scale-up conclusions should be made.\n"
            "- No inferred metabolic behavior should be made beyond explicit evidence.\n"
        )

        return text

    # =====================================================
    # RUN
    # =====================================================

    def run(
        self,
        query=None,
        microorganism=None,
        use_llm=False,
        max_results=None
    ):
        organism = self.clean_organism(
            query=query,
            microorganism=microorganism
        )

        self.debug_print(
            "BACDIVE CLEANED ORGANISM",
            organism
        )

        data = self.search(
            organism=organism,
            max_results=max_results
        )

        if not data.get("supported"):
            message = data.get(
                "message",
                "Microorganism not supported or no exact-species BacDive records accepted."
            )

            return {
                "agent_name": "BACDIVE_EXPLORER",
                "agent_status": "success",
                "source": "BacDive",
                "supported": False,
                "organism": organism,
                "summary": data.get("summary", {}),
                "agent_summary": (
                    f"BacDive did not provide accepted exact-species evidence "
                    f"for {organism}. {message}"
                ),
                "assessment": (
                    f"# BacDive Evidence for {organism}\n\n"
                    f"{message}\n\n"
                    "No BacDive-supported strain-level conclusion can be made."
                ),
                "message": message
            }

        accepted = data.get("accepted_strains", [])
        rejected = data.get("rejected_strains", [])
        summary = data.get("summary", {})

        assessment = self.build_non_llm_assessment(
            organism,
            accepted,
            rejected,
            summary
        )

        agent_summary = self.build_agent_summary(
            organism,
            accepted,
            rejected,
            summary
        )

        if use_llm:
            prompt = f"""
You are a scientific UI summarizer.

STRICT RULES:
- ONLY summarize the BacDive evidence below.
- DO NOT infer biology.
- DO NOT invent strain traits.
- DO NOT invent oxygen limitation.
- DO NOT invent industrial optimization.
- DO NOT invent scale-up conclusions.
- DO NOT add unsupported scientific claims.
- Preserve BacDive URLs if present.
- Keep the summary flexible and query-relevant.

USER QUERY:
{query}

BACDIVE DATA:
{assessment}
"""

            try:
                assessment = self.llm.invoke(prompt)

            except Exception as ex:
                assessment = (
                    f"LLM summarization failed: {str(ex)}\n\n"
                    + assessment
                )

        self.debug_print(
            "BACDIVE AGENT SUMMARY",
            agent_summary
        )

        self.debug_print(
            "BACDIVE FINAL ASSESSMENT",
            assessment
        )

        return {
            "agent_name": "BACDIVE_EXPLORER",
            "agent_status": "success",
            "source": "BacDive",
            "supported": True,
            "organism": organism,
            "summary": summary,
            "agent_summary": agent_summary,
            "accepted_strains": accepted,
            "rejected_strains": rejected,
            "assessment": assessment
        }


# =====================================================
# OPTIONAL TEST
# =====================================================

if __name__ == "__main__":

    agent = BacDiveExplorerAgent(
        debug=True
    )

    agent.print_valid_microorganisms()

    result = agent.run(
        microorganism="Bacillus subtilis",
        use_llm=False,
        max_results=None
    )

    print("\n")
    print(result["agent_summary"])
    print("\n")
    print(result["assessment"])