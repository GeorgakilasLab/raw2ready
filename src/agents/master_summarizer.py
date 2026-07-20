"""Master Summarizer Agent.

Aggregates scientific and database evidence from other src.agents to formulate a cohesive,
accurate final master summary.
"""

import json
import traceback

import os
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.ollama import OllamaModel


class MasterSummarizerAgent:
    """Aggregates all agent outputs to produce a final consensus summary.

    Attributes:
        model_name: Name of the LLM.
        temperature: LLM temperature parameter.
        debug: True if debug prints are enabled.
        llm: Language model client.
    """

    def __init__(
        self,
        model_name="llama3:latest",
        temperature=0.2,
        debug=True
    ):
        """Initializes the MasterSummarizerAgent.

        Args:
            model_name: The name of the LLM. Defaults to "llama3:latest".
            temperature: LLM temperature parameter. Defaults to 0.2.
            debug: Whether to print debug information. Defaults to True.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.debug = debug

        print("\n" + "=" * 100)
        print("[MASTER SUMMARIZER] INITIALIZING")
        print("=" * 100)
        print(f"MODEL: {model_name}")
        print(f"TEMPERATURE: {temperature}")

        from pydantic_ai.providers.ollama import OllamaProvider
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        provider = OllamaProvider(base_url=base_url)
        model = OllamaModel(model_name=model_name, provider=provider)
        self.agent = Agent(
            model=model,
            model_settings=ModelSettings(temperature=temperature)
        )

        print("[MASTER SUMMARIZER] READY")
        print("=" * 100 + "\n")

    # =====================================================
    # DEBUG
    # =====================================================
    def debug_print(self, title, data):

        if not self.debug:
            return

        print("\n" + "=" * 100)
        print(f"[MASTER SUMMARIZER DEBUG] {title}")
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
    # AGENT STATUS
    # =====================================================
    def extract_agent_status(self, agent_outputs):

        status = {}

        try:
            for key, value in agent_outputs.items():
                if isinstance(value, dict):
                    status[key] = value.get("agent_status", "unknown")
        except Exception:
            traceback.print_exc()

        return status

    # =====================================================
    # QUERY TYPE / FLAGS
    # =====================================================
    def get_query_type(self, agent_outputs):

        return agent_outputs.get(
            "query_type",
            "collaborative_multi_agent"
        )

    def is_bacdive_only(self, agent_outputs):

        return bool(agent_outputs.get("bacdive_only", False))

    def is_bacdive_relevant(self, agent_outputs):

        return bool(agent_outputs.get("bacdive_relevant", False))

    def is_collaborative_mode(self, agent_outputs):

        return bool(agent_outputs.get("collaborative_mode", True))

    # =====================================================
    # AGENT SUMMARIES
    # =====================================================
    def extract_agent_summaries(self, agent_outputs):

        summaries = {}

        try:
            wrapper = agent_outputs.get("agent_summaries", {})

            if isinstance(wrapper, dict):
                raw = wrapper.get("summaries", {})

                if isinstance(raw, dict):
                    return raw

            for key, value in agent_outputs.items():

                if not isinstance(value, dict):
                    continue

                if key in [
                    "agent_summaries",
                    "system_summary"
                ]:
                    continue

                summaries[key] = {
                    "agent_name": value.get("agent_name", key),
                    "agent_status": value.get("agent_status", "unknown"),
                    "summary": value.get(
                        "agent_summary",
                        value.get(
                            "summary",
                            value.get(
                                "assessment",
                                value.get(
                                    "answer",
                                    value.get(
                                        "final_summary",
                                        ""
                                    )
                                )
                            )
                        )
                    )
                }

        except Exception:
            traceback.print_exc()

        return summaries

    # =====================================================
    # BACDIVE EXTRACTION
    # =====================================================
    def extract_bacdive_assessments(self, agent_outputs):

        bacdive = agent_outputs.get("bacdive_explorer", {})
        assessments = {}

        try:
            results = bacdive.get("results", {})

            if isinstance(results, dict):
                for organism, result in results.items():

                    if not isinstance(result, dict):
                        continue

                    assessment = result.get("assessment", "")

                    if assessment:
                        assessments[organism] = assessment

            elif isinstance(results, list):
                for item in results:

                    if not isinstance(item, dict):
                        continue

                    organism = item.get("organism", "Unknown organism")
                    assessment = item.get("assessment", "")

                    if assessment:
                        assessments[organism] = assessment

        except Exception:
            traceback.print_exc()

        return assessments

    # =====================================================
    # KEY FINDINGS
    # =====================================================
    def extract_key_findings(self, agent_outputs):

        findings = {
            "successful_agents": [],
            "failed_agents": [],
            "skipped_agents": [],
            "bacdive_available": False,
            "bacdive_organisms": [],
            "bacdive_urls": [],
            "doi_references": [],
            "pubmed_titles": [],
            "important_urls": []
        }

        try:
            statuses = self.extract_agent_status(agent_outputs)

            for agent, status in statuses.items():

                if status == "success":
                    findings["successful_agents"].append(agent)

                elif status == "failed":
                    findings["failed_agents"].append(agent)

                elif status == "skipped":
                    findings["skipped_agents"].append(agent)

            bacdive = agent_outputs.get("bacdive_explorer", {})

            if bacdive.get("agent_status") == "success":
                findings["bacdive_available"] = True

            results = bacdive.get("results", {})

            if isinstance(results, dict):
                for organism, result in results.items():

                    findings["bacdive_organisms"].append(organism)

                    if not isinstance(result, dict):
                        continue

                    accepted = result.get("accepted_strains", [])

                    for strain in accepted:

                        if not isinstance(strain, dict):
                            continue

                        url = strain.get("bacdive_url", "")

                        if url:
                            findings["bacdive_urls"].append(url)
                            findings["important_urls"].append(url)

            crossref = agent_outputs.get("crossref_explorer", {})
            papers = crossref.get("papers", [])

            if isinstance(papers, list):
                for paper in papers:

                    if not isinstance(paper, dict):
                        continue

                    doi = paper.get("doi", "")
                    url = paper.get("url", "")

                    if doi:
                        findings["doi_references"].append(doi)

                    if url:
                        findings["important_urls"].append(url)

            internet = agent_outputs.get("internet_explorer", {})
            internet_results = internet.get("results", {})

            if isinstance(internet_results, dict):
                pubmed = internet_results.get("pubmed", [])

                if isinstance(pubmed, list):
                    for paper in pubmed:

                        if not isinstance(paper, dict):
                            continue

                        title = paper.get("title", "")
                        url = paper.get("url", "")

                        if title:
                            findings["pubmed_titles"].append(title)

                        if url:
                            findings["important_urls"].append(url)

        except Exception:
            traceback.print_exc()

        for key in [
            "important_urls",
            "bacdive_urls",
            "doi_references",
            "pubmed_titles",
            "bacdive_organisms"
        ]:
            findings[key] = list(dict.fromkeys(findings[key]))

        return findings

    # =====================================================
    # BUILD PROMPT
    # =====================================================
    def build_prompt(self, agent_outputs):

        query = agent_outputs.get("query", "")
        query_type = self.get_query_type(agent_outputs)
        bacdive_only = self.is_bacdive_only(agent_outputs)
        bacdive_relevant = self.is_bacdive_relevant(agent_outputs)
        collaborative_mode = self.is_collaborative_mode(agent_outputs)

        agent_status = self.safe_json(
            self.extract_agent_status(agent_outputs)
        )

        agent_summaries = self.safe_json(
            self.extract_agent_summaries(agent_outputs)
        )

        key_findings = self.safe_json(
            self.extract_key_findings(agent_outputs)
        )

        bacdive_assessments = self.safe_json(
            self.extract_bacdive_assessments(agent_outputs)
        )

        serialized_outputs = self.safe_json(agent_outputs)

        prompt = f"""
You are the MASTER scientific coordinator of a collaborative multi-agent
industrial biotechnology system.

Your task is to produce ONE final answer for the user by integrating the
outputs from all available src.agents.

==================================================
USER QUERY
==================================================

{query}

==================================================
QUERY MODE
==================================================

Query type: {query_type}
Collaborative mode: {collaborative_mode}
BacDive relevant: {bacdive_relevant}
BacDive only: {bacdive_only}

==================================================
MAIN INSTRUCTION
==================================================

Answer the user's query directly and flexibly.

Do NOT use a fixed template every time.

Use only the sections that are useful for this specific query.

The final answer must be based on:
1. The user's query.
2. The individual agent summaries.
3. The detailed agent outputs when needed.

Do not simply dump all agent outputs.

Do not ignore successful src.agents.

Do not use BacDive alone unless BacDive-only mode is true.

==================================================
AGENT-SUMMARY POLICY
==================================================

Each agent may provide an agent_summary.

Use these summaries as the first-level evidence map:

- DATA_ANALYST summary:
  dataset-derived evidence.

- BACDIVE_EXPLORER summary:
  strain-level BacDive evidence.

- INTERNET_EXPLORER summary:
  web/PubMed/contextual evidence.

- CROSSREF_EXPLORER summary:
  DOI/literature metadata evidence.



- METADATA_ANALYST summary:
  protocol, metadata, missing fields, and quality issues.

If an agent summary is vague, inspect the full agent output.

==================================================
STRICT SCIENTIFIC RULES
==================================================

- Use ONLY evidence present in the agent outputs.
- Do NOT hallucinate scientific findings.
- Do NOT invent citations, DOIs, PubMed papers, URLs, or BacDive records.
- Do NOT invent growth optima.
- Do NOT infer oxygen limitation unless explicitly supported.
- Do NOT infer industrial optimization unless explicitly supported.
- Do NOT infer scale-up suitability unless explicitly supported.
- Do NOT infer metabolic behavior beyond the provided evidence.
- If evidence is missing, say that evidence is insufficient or unavailable.
- Clearly separate evidence from assumptions.
- Mention contradictions between src.agents if they exist.
- Mention failed/skipped src.agents only if this affects confidence.

==================================================
BACDIVE HANDLING RULES
==================================================

If BacDive evidence is available:
- Use it as strain-level/descriptive evidence.
- Preserve BacDive URLs when relevant.
- Preserve reference/type strain vs non-reference strain distinction when relevant.
- If the user asks for all strains, include all relevant strain URLs.
- If the user asks for optimal growth conditions, explain that BacDive may contain
  recorded growth conditions, but these are not necessarily optimized industrial
  conditions.
- BacDive records are descriptive metadata records, not proof of industrial
  feasibility.

If BacDive-only mode is true:
- Use only BacDive evidence.
- Ignore external literature, internet, Crossref, and dataset claims.
- Still answer flexibly based on the query.

==================================================
FLEXIBLE OUTPUT STYLE
==================================================

Choose the best structure for the query.

Possible sections, only when useful:
- Direct Answer
- Integrated Summary
- Agent-by-Agent Evidence Summary
- Evidence From BacDive
- Evidence From Dataset
- Evidence From Literature
- Metadata / Protocol Gaps
- Missing Evidence
- Limitations
- Final Recommendation

Do not include empty sections.

Do not output raw JSON.

Keep the answer readable, concise, and scientifically conservative.

==================================================
AGENT EXECUTION STATUS
==================================================

{agent_status}

==================================================
AGENT SUMMARIES
==================================================

{agent_summaries}

==================================================
EXTRACTED KEY FINDINGS
==================================================

{key_findings}

==================================================
BACDIVE ASSESSMENTS
==================================================

{bacdive_assessments}

==================================================
FULL AGENT OUTPUTS
==================================================

{serialized_outputs}
"""

        return prompt

    # =====================================================
    # FALLBACK SUMMARY WITHOUT LLM
    # =====================================================
    def fallback_summary(self, agent_outputs):

        query = agent_outputs.get("query", "")
        findings = self.extract_key_findings(agent_outputs)
        summaries = self.extract_agent_summaries(agent_outputs)
        bacdive_assessments = self.extract_bacdive_assessments(agent_outputs)

        text = "# Final Summary\n\n"
        text += f"User query: {query}\n\n"

        if summaries:
            text += "## Agent-by-Agent Evidence Summary\n\n"

            for key, item in summaries.items():
                if not isinstance(item, dict):
                    continue

                status = item.get("agent_status", "unknown")
                summary = item.get("summary", "")

                text += f"### {key}\n\n"
                text += f"Status: {status}\n\n"

                if summary:
                    text += f"{summary}\n\n"
                else:
                    text += "No summary available.\n\n"

        if bacdive_assessments:
            text += "## BacDive Evidence\n\n"

            for organism, assessment in bacdive_assessments.items():
                text += f"### {organism}\n\n"
                text += assessment + "\n\n"

        if findings.get("doi_references"):
            text += "## DOI References Found\n\n"

            for doi in findings["doi_references"]:
                text += f"- {doi}\n"

            text += "\n"

        if findings.get("important_urls"):
            text += "## Relevant URLs\n\n"

            for url in findings["important_urls"]:
                text += f"- {url}\n"

            text += "\n"

        text += "## Limitations\n\n"
        text += (
            "- This fallback summary only reports extracted evidence.\n"
            "- Missing evidence should be treated as unknown.\n"
            "- No unsupported biological or industrial conclusions are made.\n"
        )

        return text

    # =====================================================
    # RUN
    # =====================================================
    def run(self, agent_outputs):

        print("\n" + "=" * 100)
        print("[MASTER SUMMARIZER] RUN STARTED")
        print("=" * 100)

        self.debug_print(
            "RAW AGENT OUTPUTS INPUT",
            agent_outputs
        )

        prompt = self.build_prompt(agent_outputs)

        self.debug_print(
            "MASTER SUMMARIZER PROMPT",
            prompt
        )

        try:
            print("[MASTER SUMMARIZER] INVOKING OLLAMA...")

            final_summary = self.agent.run_sync(prompt).data

            status = "success"
            llm_used = True

            print("[MASTER SUMMARIZER] OLLAMA SUCCESS")

        except Exception as ex:
            traceback.print_exc()

            final_summary = (
                "Master summarization with LLM failed. "
                "Using deterministic fallback summary.\n\n"
                + self.fallback_summary(agent_outputs)
            )

            status = "failed"
            llm_used = False

            print("[MASTER SUMMARIZER ERROR]")
            print(str(ex))

        agent_status = self.extract_agent_status(agent_outputs)

        response = {
            "agent_name": "MASTER_SUMMARIZER",
            "agent_status": status,
            "model": self.model_name,
            "temperature": self.temperature,
            "agent_count": len(agent_status),
            "successful_agents": len(
                [x for x in agent_status.values() if x == "success"]
            ),
            "failed_agents": len(
                [x for x in agent_status.values() if x == "failed"]
            ),
            "skipped_agents": len(
                [x for x in agent_status.values() if x == "skipped"]
            ),
            "agent_execution_status": agent_status,
            "query_type": self.get_query_type(agent_outputs),
            "collaborative_mode": self.is_collaborative_mode(agent_outputs),
            "bacdive_relevant": self.is_bacdive_relevant(agent_outputs),
            "bacdive_only": self.is_bacdive_only(agent_outputs),
            "final_summary": final_summary,
            "answer": final_summary,
            "llm_used": llm_used
        }

        self.debug_print(
            "MASTER SUMMARIZER RESPONSE",
            response
        )

        print("\n" + "=" * 100)
        print("[MASTER SUMMARIZER] RUN COMPLETE")
        print("=" * 100 + "\n")

        return response