"""Literature Reviewer Agent.

Synthesizes publication evidence from internet/PubMed search, Crossref registry,
and the BacDive database to create structured literature reviews.
"""

import json
import re
import traceback

from langchain_ollama import OllamaLLM

from src.agents.internet_explorer import InternetExplorerAgent
from src.agents.crossref_explorer import CrossrefExplorerAgent
from src.agents.bacdive_explorer import BacDiveExplorerAgent


class LiteratureReviewerAgent:
    """Synthesizes literary and database evidence for bioreactor experiments.

    Attributes:
        model_name: Name of the LLM.
        temperature: LLM temperature parameter.
        debug: True if debug prints are enabled.
        llm: Language model client.
        internet_agent: InternetExplorerAgent instance.
        crossref_agent: CrossrefExplorerAgent instance.
        bacdive_agent: BacDiveExplorerAgent instance.
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
        """Initializes the LiteratureReviewerAgent and its sub-src.agents.

        Args:
            model_name: The name of the LLM. Defaults to "llama3:latest".
            temperature: LLM temperature parameter. Defaults to 0.2.
            debug: Whether to print debug information. Defaults to True.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.debug = debug

        print("=" * 80)
        print("[LITERATURE REVIEWER] INITIALIZING")
        print(f"MODEL: {model_name}")
        print(f"TEMPERATURE: {temperature}")
        print("[LITERATURE REVIEWER] Agent summary enabled")
        print("=" * 80)

        self.llm = OllamaLLM(
            model=model_name,
            temperature=temperature
        )

        self.internet_agent = InternetExplorerAgent(
            model_name=model_name,
            temperature=temperature
        )

        self.crossref_agent = CrossrefExplorerAgent(
            model_name=model_name,
            temperature=temperature
        )

        self.bacdive_agent = BacDiveExplorerAgent(
            model_name=model_name,
            temperature=temperature
        )

    # =====================================================
    # DEBUG PRINT
    # =====================================================
    def debug_print(self, title, data):

        if not self.debug:
            return

        print("\n" + "=" * 80)
        print(f"[LITERATURE REVIEWER DEBUG] {title}")
        print("=" * 80)

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

        print("=" * 80 + "\n")

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

        if text is None:
            return ""

        text = str(text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # =====================================================
    # ORGANISM DETECTION
    # =====================================================
    def detect_organism(self, query):

        query_lower = str(query).lower()

        organism_map = {
            "e. coli": "Escherichia coli",
            "e coli": "Escherichia coli",
            "ecoli": "Escherichia coli",
            "escherichia coli": "Escherichia coli",

            "bacillus subtilis": "Bacillus subtilis",
            "b. subtilis": "Bacillus subtilis",
            "b subtilis": "Bacillus subtilis",

            "saccharomyces cerevisiae": "Saccharomyces cerevisiae",
            "s. cerevisiae": "Saccharomyces cerevisiae",
            "s cerevisiae": "Saccharomyces cerevisiae",
            "yeast": "Saccharomyces cerevisiae",

            "pichia pastoris": "Komagataella phaffii",
            "p. pastoris": "Komagataella phaffii",
            "p pastoris": "Komagataella phaffii",
            "komagataella": "Komagataella phaffii",
            "k. phaffii": "Komagataella phaffii",
            "k phaffii": "Komagataella phaffii",

            "corynebacterium glutamicum": "Corynebacterium glutamicum",
            "c. glutamicum": "Corynebacterium glutamicum",
            "c glutamicum": "Corynebacterium glutamicum",

            "pseudomonas putida": "Pseudomonas putida",
            "p. putida": "Pseudomonas putida",
            "p putida": "Pseudomonas putida",
            "pseudomonas": "Pseudomonas putida"
        }

        for key, value in organism_map.items():
            if key in query_lower:
                return value

        latin_match = re.search(
            r"\b([A-Z][a-z]+)\s+([a-z][a-z\-]+)\b",
            str(query)
        )

        if latin_match:
            return (
                latin_match.group(1)
                + " "
                + latin_match.group(2)
            )

        return None

    # =====================================================
    # SAFE AGENT RUN
    # =====================================================
    def safe_agent_run(self, agent_name, func, *args, **kwargs):

        try:
            result = func(*args, **kwargs)

            if not isinstance(result, dict):
                result = {
                    "result": result
                }

            result.setdefault("agent_name", agent_name)
            result.setdefault("agent_status", "success")

            return result

        except Exception as ex:
            traceback.print_exc()

            return {
                "agent_name": agent_name,
                "agent_status": "failed",
                "error": str(ex)
            }

    # =====================================================
    # EXTRACT KEY RESULTS
    # =====================================================
    def extract_key_results(
        self,
        internet_results,
        crossref_results,
        bacdive_results
    ):
        extracted = {
            "pubmed_titles": [],
            "ddgs_titles": [],
            "crossref_titles": [],
            "bacdive_organisms": [],
            "bacdive_urls": [],
            "important_urls": [],
            "doi_list": []
        }

        # =================================================
        # INTERNET / DDGS / PUBMED
        # =================================================
        try:
            internet_data = internet_results.get("results", {})

            ddgs_results = internet_data.get("ddgs", [])

            if isinstance(ddgs_results, list):
                for item in ddgs_results:
                    if not isinstance(item, dict) or item.get("error"):
                        continue

                    title = item.get("title", "")
                    url = item.get("url", "")

                    if title:
                        extracted["ddgs_titles"].append(
                            self.clean_text(title)
                        )

                    if url:
                        extracted["important_urls"].append(url)

            pubmed_results = internet_data.get("pubmed", [])

            if isinstance(pubmed_results, list):
                for item in pubmed_results:
                    if not isinstance(item, dict) or item.get("error"):
                        continue

                    title = item.get("title", "")
                    url = item.get("url", "")

                    if title:
                        extracted["pubmed_titles"].append(
                            self.clean_text(title)
                        )

                    if url:
                        extracted["important_urls"].append(url)

        except Exception:
            traceback.print_exc()

        # =================================================
        # CROSSREF
        # =================================================
        try:
            papers = crossref_results.get("papers", [])

            if isinstance(papers, list):
                for item in papers:
                    if not isinstance(item, dict) or item.get("error"):
                        continue

                    title = item.get("title", "")
                    doi = item.get("doi", "")
                    url = item.get("url", "")

                    if title:
                        extracted["crossref_titles"].append(
                            self.clean_text(title)
                        )

                    if doi:
                        extracted["doi_list"].append(doi)

                    if url:
                        extracted["important_urls"].append(url)

        except Exception:
            traceback.print_exc()

        # =================================================
        # BACDIVE
        # Supports both:
        # 1. single BacDiveAgent.run output
        # 2. orchestrator-style {"results": {organism: output}}
        # =================================================
        try:
            if bacdive_results.get("accepted_strains"):
                accepted = bacdive_results.get("accepted_strains", [])
                organism = bacdive_results.get("organism", "")

                for strain in accepted:
                    if not isinstance(strain, dict):
                        continue

                    species = strain.get("species") or organism
                    url = strain.get("bacdive_url", "")
                    designation = strain.get("strain_designation", "")

                    label = species

                    if designation:
                        label += f" ({designation})"

                    if label:
                        extracted["bacdive_organisms"].append(
                            self.clean_text(label)
                        )

                    if url:
                        extracted["bacdive_urls"].append(url)
                        extracted["important_urls"].append(url)

            elif isinstance(bacdive_results.get("results"), dict):
                for organism, result in bacdive_results.get("results", {}).items():
                    if not isinstance(result, dict):
                        continue

                    accepted = result.get("accepted_strains", [])

                    for strain in accepted:
                        if not isinstance(strain, dict):
                            continue

                        species = strain.get("species") or organism
                        url = strain.get("bacdive_url", "")
                        designation = strain.get("strain_designation", "")

                        label = species

                        if designation:
                            label += f" ({designation})"

                        if label:
                            extracted["bacdive_organisms"].append(
                                self.clean_text(label)
                            )

                        if url:
                            extracted["bacdive_urls"].append(url)
                            extracted["important_urls"].append(url)

        except Exception:
            traceback.print_exc()

        for key in extracted:
            extracted[key] = list(dict.fromkeys(extracted[key]))

        return extracted

    # =====================================================
    # AGENT SUMMARY
    # =====================================================
    def build_agent_summary(self, query, extracted_data, statuses):

        text = ""

        text += (
            "The Literature Reviewer combined available literature-oriented "
            "signals from Internet/PubMed, Crossref, and BacDive. "
        )

        text += (
            f"Internet status: {statuses.get('internet_search')}; "
            f"Crossref status: {statuses.get('crossref_search')}; "
            f"BacDive status: {statuses.get('bacdive_search')}. "
        )

        if extracted_data.get("pubmed_titles"):
            text += (
                f"PubMed-like records found: "
                f"{len(extracted_data.get('pubmed_titles', []))}. "
            )

        if extracted_data.get("crossref_titles"):
            text += (
                f"Crossref records found: "
                f"{len(extracted_data.get('crossref_titles', []))}. "
            )

        if extracted_data.get("bacdive_organisms"):
            text += (
                f"BacDive strain/organism records found: "
                f"{len(extracted_data.get('bacdive_organisms', []))}. "
            )

        text += (
            "The reviewer should treat retrieved literature metadata as "
            "supporting context only, unless explicit experimental conclusions "
            "are present in the retrieved records."
        )

        return text

    # =====================================================
    # BUILD PROMPT
    # =====================================================
    def build_prompt(
        self,
        query,
        extracted_data,
        internet_results,
        crossref_results,
        bacdive_results
    ):
        prompt = f"""
You are a senior scientific literature reviewer in a collaborative
industrial biotechnology multi-agent system.

Your task is to review ONLY the evidence provided below and produce a
query-aware literature review that can be used by a master summarizer.

==================================================
USER QUERY
==================================================

{query}

==================================================
EXTRACTED RESULTS
==================================================

{self.safe_json(extracted_data)}

==================================================
INTERNET RESULTS
==================================================

{self.safe_json(internet_results)}

==================================================
CROSSREF RESULTS
==================================================

{self.safe_json(crossref_results)}

==================================================
BACDIVE RESULTS
==================================================

{self.safe_json(bacdive_results)}

==================================================
STRICT RULES
==================================================

1. Use ONLY the provided results.
2. Do NOT invent citations, DOI references, PubMed IDs, URLs, strains, or BacDive data.
3. Do NOT infer oxygen limitation unless explicitly supported.
4. Do NOT infer industrial optimization or scale-up suitability unless explicitly supported.
5. Do NOT invent microbial physiology.
6. Clearly separate evidence from uncertainty.
7. If evidence is weak or absent, say "Insufficient evidence available."
8. BacDive records are descriptive metadata records, not optimization studies.
9. Crossref records are bibliographic metadata unless abstracts explicitly support conclusions.
10. Internet results are contextual unless the retrieved text explicitly supports a claim.

==================================================
FLEXIBLE OUTPUT RULES
==================================================

Do NOT force a fixed template.

Adapt the response to the user's query.

Use only useful sections, for example:
- Literature Reviewer Summary
- Evidence Found
- BacDive Context
- Crossref / DOI Context
- PubMed / Internet Context
- What Is Supported
- What Is Not Supported
- Research Gaps
- Suggested Experiments
- Limitations

Do not include empty sections.
Do not output raw JSON.
Keep the review concise but scientifically useful.
"""

        return prompt

    # =====================================================
    # FORMAT SOURCES
    # =====================================================
    def format_sources(
        self,
        internet_results,
        crossref_results,
        bacdive_results
    ):
        sources = []

        # DDGS
        try:
            ddgs = internet_results.get("results", {}).get("ddgs", [])

            if isinstance(ddgs, list):
                for item in ddgs:
                    if not isinstance(item, dict) or item.get("error"):
                        continue

                    url = item.get("url", "")
                    title = item.get("title", "")

                    if url:
                        sources.append(
                            {
                                "source": "DDGS",
                                "title": self.clean_text(title),
                                "url": url
                            }
                        )

        except Exception:
            traceback.print_exc()

        # PubMed
        try:
            pubmed = internet_results.get("results", {}).get("pubmed", [])

            if isinstance(pubmed, list):
                for item in pubmed:
                    if not isinstance(item, dict) or item.get("error"):
                        continue

                    url = item.get("url", "")
                    title = item.get("title", "PubMed Paper")
                    pubmed_id = item.get("pubmed_id", "")

                    if url:
                        sources.append(
                            {
                                "source": "PubMed",
                                "title": self.clean_text(title),
                                "pubmed_id": pubmed_id,
                                "url": url
                            }
                        )

        except Exception:
            traceback.print_exc()

        # Crossref
        try:
            papers = crossref_results.get("papers", [])

            if isinstance(papers, list):
                for item in papers:
                    if not isinstance(item, dict) or item.get("error"):
                        continue

                    url = item.get("url", "")
                    title = item.get("title", "")
                    doi = item.get("doi", "")

                    if url:
                        sources.append(
                            {
                                "source": "Crossref",
                                "title": self.clean_text(title),
                                "doi": doi,
                                "url": url
                            }
                        )

        except Exception:
            traceback.print_exc()

        # BacDive single result
        try:
            if bacdive_results.get("accepted_strains"):
                accepted = bacdive_results.get("accepted_strains", [])

                for strain in accepted:
                    if not isinstance(strain, dict):
                        continue

                    url = strain.get("bacdive_url", "")
                    species = strain.get("species", "")
                    designation = strain.get("strain_designation", "")

                    if url:
                        sources.append(
                            {
                                "source": "BacDive",
                                "title": self.clean_text(species),
                                "strain": self.clean_text(designation),
                                "url": url
                            }
                        )

            elif isinstance(bacdive_results.get("results"), dict):
                for organism, result in bacdive_results.get("results", {}).items():
                    if not isinstance(result, dict):
                        continue

                    for strain in result.get("accepted_strains", []):
                        if not isinstance(strain, dict):
                            continue

                        url = strain.get("bacdive_url", "")
                        species = strain.get("species") or organism
                        designation = strain.get("strain_designation", "")

                        if url:
                            sources.append(
                                {
                                    "source": "BacDive",
                                    "title": self.clean_text(species),
                                    "strain": self.clean_text(designation),
                                    "url": url
                                }
                            )

        except Exception:
            traceback.print_exc()

        unique = []
        seen = set()

        for item in sources:
            key = (
                item.get("source", ""),
                item.get("url", ""),
                item.get("title", "")
            )

            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique

    # =====================================================
    # COUNT HELPERS
    # =====================================================
    def count_valid_items(self, items):

        if not isinstance(items, list):
            return 0

        return len(
            [
                item for item in items
                if isinstance(item, dict)
                and not item.get("error")
            ]
        )

    def count_bacdive_items(self, bacdive_results):

        try:
            if bacdive_results.get("accepted_strains"):
                return len(
                    [
                        x for x in bacdive_results.get("accepted_strains", [])
                        if isinstance(x, dict)
                    ]
                )

            if isinstance(bacdive_results.get("results"), dict):
                total = 0

                for _, result in bacdive_results.get("results", {}).items():
                    if not isinstance(result, dict):
                        continue

                    total += len(
                        [
                            x for x in result.get("accepted_strains", [])
                            if isinstance(x, dict)
                        ]
                    )

                return total

        except Exception:
            traceback.print_exc()

        return 0

    # =====================================================
    # RUN
    # =====================================================
    def run(
        self,
        query,
        organism=None,
        run_nested_agents=True,
        internet_results=None,
        crossref_results=None,
        bacdive_results=None,
        use_llm=True
    ):
        print("\n" + "=" * 80)
        print("[LITERATURE REVIEWER] RUN STARTED")
        print("=" * 80)

        self.debug_print(
            "ORIGINAL USER QUERY",
            query
        )

        if organism is None:
            organism = self.detect_organism(query)

        self.debug_print(
            "DETECTED ORGANISM",
            organism
        )

        # =================================================
        # RUN OR USE PROVIDED AGENT OUTPUTS
        # =================================================
        if run_nested_agents:
            internet_results = self.safe_agent_run(
                "INTERNET_EXPLORER",
                self.internet_agent.run,
                query=query
            )

            crossref_results = self.safe_agent_run(
                "CROSSREF_EXPLORER",
                self.crossref_agent.run,
                query=query
            )

            if organism:
                bacdive_results = self.safe_agent_run(
                    "BACDIVE_EXPLORER",
                    self.bacdive_agent.run,
                    query=query,
                    microorganism=organism,
                    use_llm=False
                )
            else:
                bacdive_results = {
                    "agent_name": "BACDIVE_EXPLORER",
                    "agent_status": "skipped",
                    "reason": "No organism detected for BacDive search."
                }

        else:
            internet_results = internet_results or {
                "agent_name": "INTERNET_EXPLORER",
                "agent_status": "skipped",
                "reason": "Provided externally or not requested."
            }

            crossref_results = crossref_results or {
                "agent_name": "CROSSREF_EXPLORER",
                "agent_status": "skipped",
                "reason": "Provided externally or not requested."
            }

            bacdive_results = bacdive_results or {
                "agent_name": "BACDIVE_EXPLORER",
                "agent_status": "skipped",
                "reason": "Provided externally or not requested."
            }

        self.debug_print("INTERNET RESULTS", internet_results)
        self.debug_print("CROSSREF RESULTS", crossref_results)
        self.debug_print("BACDIVE RESULTS", bacdive_results)

        extracted_data = self.extract_key_results(
            internet_results,
            crossref_results,
            bacdive_results
        )

        self.debug_print(
            "EXTRACTED RESULTS",
            extracted_data
        )

        sources = self.format_sources(
            internet_results,
            crossref_results,
            bacdive_results
        )

        internet_status = internet_results.get(
            "agent_status",
            "success" if "error" not in internet_results else "failed"
        )

        crossref_status = crossref_results.get(
            "agent_status",
            "success" if "error" not in crossref_results else "failed"
        )

        bacdive_status = bacdive_results.get(
            "agent_status",
            "success" if "error" not in bacdive_results else "failed"
        )

        statuses = {
            "internet_search": internet_status,
            "crossref_search": crossref_status,
            "bacdive_search": bacdive_status
        }

        agent_summary = self.build_agent_summary(
            query=query,
            extracted_data=extracted_data,
            statuses=statuses
        )

        if use_llm:
            prompt = self.build_prompt(
                query,
                extracted_data,
                internet_results,
                crossref_results,
                bacdive_results
            )

            self.debug_print(
                "FINAL PROMPT SENT TO OLLAMA",
                prompt
            )

            print(
                f"[LITERATURE REVIEWER] PROMPT SIZE: "
                f"{len(prompt)} characters"
            )

            try:
                assessment = self.llm.invoke(prompt)
                status = "success"

            except Exception as ex:
                traceback.print_exc()

                assessment = (
                    "Literature Reviewer LLM generation failed. "
                    "Using deterministic agent summary.\n\n"
                    + agent_summary
                )

                status = "failed"

        else:
            assessment = agent_summary
            status = "success"

        self.debug_print(
            "LITERATURE REVIEWER ASSESSMENT",
            assessment
        )

        internet_results_data = internet_results.get("results", {})

        ddgs_count = self.count_valid_items(
            internet_results_data.get("ddgs", [])
        )

        pubmed_count = self.count_valid_items(
            internet_results_data.get("pubmed", [])
        )

        crossref_count = self.count_valid_items(
            crossref_results.get("papers", [])
        )

        bacdive_count = self.count_bacdive_items(
            bacdive_results
        )

        final_response = {
            "agent_name": "LITERATURE_REVIEWER",
            "agent_status": status,
            "query": query,
            "organism": organism,
            "internet_results": internet_results,
            "crossref_results": crossref_results,
            "bacdive_results": bacdive_results,
            "sources": sources,
            "summary": {
                "sources_found": len(sources),
                "ddgs_results": ddgs_count,
                "pubmed_results": pubmed_count,
                "crossref_results": crossref_count,
                "bacdive_results": bacdive_count,
                "internet_search": internet_status,
                "crossref_search": crossref_status,
                "bacdive_search": bacdive_status
            },
            "extracted_results": extracted_data,
            "agent_summary": agent_summary,
            "assessment": assessment
        }

        self.debug_print(
            "FINAL LITERATURE REVIEWER OUTPUT",
            final_response
        )

        return final_response