"""Crossref Explorer Agent.

Retrieves and validates bibliographic metadata from the official Crossref API.
"""
import json
import re
import time
import traceback
from urllib.parse import quote
import requests
from langchain_ollama import OllamaLLM

class CrossrefExplorerAgent:
    """Bibliographic metadata explorer using the Crossref REST API.

    Attributes:
        model_name: Name of the LLM.
        temperature: LLM temperature parameter.
        mailto: User email address for polite API identification.
        debug: True if debug prints are enabled.
        timeout: HTTP request timeout duration in seconds.
        max_retries: Maximum number of HTTP request retries.
        base_url: Base URL of the Crossref API.
        works_url: URL for works endpoint.
        llm: Language model client.
        session: Active request session.
    """
    def __init__(
        self,
        model_name="llama3:latest",
        temperature=0.2,
        mailto="local@localhost",
        debug=True,
        timeout=30,
        max_retries=3
    ):
        """Initializes the CrossrefExplorerAgent.

        Args:
            model_name: The name of the LLM. Defaults to "llama3:latest".
            temperature: LLM temperature parameter. Defaults to 0.2.
            mailto: Email address used for the polite API header. Defaults to
                "local@localhost".
            debug: Whether to print debug messages. Defaults to True.
            timeout: Timeout in seconds for HTTP requests. Defaults to 30.
            max_retries: Number of request retry attempts. Defaults to 3.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.mailto = mailto
        self.debug = debug
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = "https://api.crossref.org"
        self.works_url = f"{self.base_url}/works"
        self.llm = OllamaLLM(
            model=model_name,
            temperature=temperature
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": (
                    "CrossrefExplorerAgent/6.0 "
                    f"(mailto:{self.mailto})"
                )
            }
        )
        print("=" * 80)
        print("[CROSSREF EXPLORER] INITIALIZED")
        print(f"MODEL: {model_name}")
        print(f"TEMPERATURE: {temperature}")
        print(f"WORKS ENDPOINT: {self.works_url}")
        print(f"MAILTO: {mailto}")
        print("=" * 80)
    def debug_print(self, title, data):
        if not self.debug:
            return
        print("\n" + "=" * 80)
        print(f"[CROSSREF DEBUG] {title}")
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
            print(f"[DEBUG PRINT ERROR] {str(ex)}")
        print("=" * 80 + "\n")
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
    def strip_html_tags(self, text):
        if text is None:
            return ""
        text = re.sub(r"<[^>]+>", " ", str(text))
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    def clean_query(self, query, max_words=35):
        cleaned = str(query or "").lower()
        blocked_phrases = [
            "tell me about",
            "tell me",
            "give me",
            "explain",
            "what are",
            "what is",
            "show me",
            "find",
            "search",
            "please",
            "i want",
            "i need",
            "can you",
            "could you",
            "perform",
            "[multi-agent]",
            "[bacdive]",
            "complete scientific assessment",
            "optimization strategies",
            "final master summary",
            "use all src.agents",
            "collaborative",
            "multi-agent"
        ]
        for phrase in blocked_phrases:
            cleaned = cleaned.replace(phrase, " ")
        cleaned = re.sub(r"[?!.:,;]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            cleaned = str(query or "").strip()
        cleaned = " ".join(cleaned.split()[:max_words])
        self.debug_print("CLEANED CROSSREF QUERY", cleaned)
        return cleaned
    def extract_doi(self, text):
        if not text:
            return None
        match = re.search(
            r"10\.\d{4,9}/[-._;()/:A-Z0-9]+",
            str(text),
            flags=re.I
        )
        if match:
            return match.group(0).rstrip(".,; )]").lower()
        return None
    def first_list_value(self, value):
        if isinstance(value, list) and value:
            return self.strip_html_tags(value[0])
        if isinstance(value, str):
            return self.strip_html_tags(value)
        return ""
    def request_get(self, url, params=None):
        params = params or {}
        if self.mailto:
            params.setdefault("mailto", self.mailto)
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self.debug_print(
                    f"CROSSREF REQUEST ATTEMPT {attempt}",
                    {
                        "url": url,
                        "params": params
                    }
                )
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )
                self.debug_print(
                    "CROSSREF RESPONSE",
                    {
                        "status_code": response.status_code,
                        "url": response.url
                    }
                )
                if response.status_code == 200:
                    return response.json()
                if response.status_code in [429, 500, 502, 503, 504]:
                    last_error = response.text[:1000]
                    time.sleep(1.5 * attempt)
                    continue
                return {
                    "status": "error",
                    "message": {
                        "status_code": response.status_code,
                        "details": response.text[:1000],
                        "url": response.url
                    }
                }
            except Exception as ex:
                traceback.print_exc()
                last_error = str(ex)
                time.sleep(1.5 * attempt)
        return {
            "status": "error",
            "message": {
                "error": "Crossref request failed after retries",
                "details": last_error
            }
        }
    def build_query(self, query):
        cleaned = self.clean_query(query)
        q = cleaned.lower()
        organism_terms = [
            "escherichia coli",
            "e coli",
            "e. coli",
            "bacillus subtilis",
            "saccharomyces cerevisiae",
            "pichia pastoris",
            "komagataella phaffii"
        ]
        process_terms = [
            "fermentation",
            "growth",
            "growth conditions",
            "temperature",
            "ph",
            "medium",
            "oxygen",
            "dissolved oxygen",
            "bioreactor",
            "culture",
            "cultivation",
            "substrate",
            "scale-up",
            "bioprocess"
        ]
        has_organism = any(term in q for term in organism_terms)
        has_process = any(term in q for term in process_terms)
        if has_organism and not has_process:
            cleaned = f"{cleaned} growth conditions temperature pH medium"
        self.debug_print("FINAL CROSSREF SEARCH QUERY", cleaned)
        return cleaned
    def validate_doi_agency(self, doi):
        if not doi:
            return {
                "doi": doi,
                "valid": False,
                "agency": None,
                "source": "Crossref"
            }
        encoded_doi = quote(doi, safe="")
        url = f"{self.works_url}/{encoded_doi}/agency"
        data = self.request_get(url)
        if data.get("status") != "ok":
            return {
                "doi": doi,
                "valid": False,
                "agency": None,
                "details": data.get("message", {}),
                "source": "Crossref"
            }
        agency = data.get("message", {}).get("agency", {})
        return {
            "doi": doi,
            "valid": True,
            "agency": agency.get("id", ""),
            "agency_label": agency.get("label", ""),
            "source": "Crossref"
        }
    def get_work_by_doi(self, doi):
        encoded_doi = quote(doi, safe="")
        url = f"{self.works_url}/{encoded_doi}"
        data = self.request_get(url)
        if data.get("status") != "ok":
            return {
                "error": "DOI lookup failed",
                "doi": doi,
                "details": data.get("message", {}),
                "source": "Crossref"
            }
        paper = self.parse_work(data.get("message", {}))
        paper["doi_validation"] = self.validate_doi_agency(doi)
        return paper
    def search(
        self,
        query,
        rows=10,
        filters=None,
        reference_mode="any",
        sort="relevance",
        order="desc",
        select=None,
        field_queries=None
    ):
        cleaned_query = self.build_query(query)
        rows = max(1, min(int(rows), 1000))
        params = {
            "query": cleaned_query,
            "rows": rows,
            "sort": sort,
            "order": order
        }
        filter_parts = []
        if filters:
            if isinstance(filters, dict):
                for key, value in filters.items():
                    if value is not None and str(value).strip():
                        filter_parts.append(f"{key}:{value}")
            elif isinstance(filters, str):
                filter_parts.append(filters)
        if reference_mode == "with_references":
            filter_parts.append("has-references:true")
        elif reference_mode == "without_references":
            filter_parts.append("has-references:false")
        if filter_parts:
            params["filter"] = ",".join(filter_parts)
        if select:
            if isinstance(select, list):
                params["select"] = ",".join(select)
            else:
                params["select"] = str(select)
        if field_queries and isinstance(field_queries, dict):
            for key, value in field_queries.items():
                if value:
                    params[f"query.{key}"] = value
        self.debug_print("CROSSREF API PAYLOAD", params)
        data = self.request_get(
            self.works_url,
            params=params
        )
        if data.get("status") != "ok":
            return {
                "items": [],
                "query_used": params,
                "error": data.get("message", {}),
                "source": "Crossref"
            }
        message = data.get("message", {})
        items = message.get("items", [])
        papers = [self.parse_work(item) for item in items]
        return {
            "items": papers,
            "query_used": params,
            "total_results": message.get("total-results", 0),
            "items_per_page": message.get("items-per-page", rows),
            "source": "Crossref"
        }
    def parse_work(self, item):
        doi = item.get("DOI", "")
        crossref_url = item.get("URL", "")
        doi_url = f"https://doi.org/{doi}" if doi else crossref_url
        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            full_name = f"{given} {family}".strip()
            if full_name:
                authors.append(full_name)
        references = item.get("reference", [])
        reference_count = item.get(
            "reference-count",
            len(references) if isinstance(references, list) else 0
        )
        return {
            "title": self.first_list_value(item.get("title")),
            "subtitle": self.first_list_value(item.get("subtitle")),
            "authors": authors,
            "year": self.extract_year(item),
            "journal": self.first_list_value(item.get("container-title")),
            "publisher": item.get("publisher", ""),
            "type": item.get("type", ""),
            "doi": doi,
            "url": doi_url,
            "crossref_url": crossref_url,
            "abstract": self.strip_html_tags(item.get("abstract", "")),
            "score": item.get("score", 0),
            "is_referenced_by_count": item.get("is-referenced-by-count", 0),
            "reference_count": reference_count,
            "has_references": bool(reference_count and reference_count > 0),
            "subjects": item.get("subject", []),
            "published": item.get("published", {}),
            "issued": item.get("issued", {}),
            "source": "Crossref"
        }
    def extract_year(self, item):
        for key in [
            "published",
            "published-print",
            "published-online",
            "issued",
            "created"
        ]:
            try:
                date_parts = item.get(key, {}).get("date-parts", [])
                if date_parts and date_parts[0]:
                    return date_parts[0][0]
            except Exception:
                continue
        return ""
    def classify_relevance(self, paper, query):
        text = " ".join(
            [
                str(paper.get("title", "")),
                str(paper.get("abstract", "")),
                str(paper.get("journal", "")),
                str(paper.get("subjects", ""))
            ]
        ).lower()
        q = self.clean_query(query).lower()
        query_terms = [
            term
            for term in re.split(r"\s+", q)
            if len(term) > 3
        ]
        matched = [
            term
            for term in query_terms
            if term in text
        ]
        paper_type = str(paper.get("type", "")).lower()
        title = str(paper.get("title", "")).lower()
        secondary_markers = [
            "editor",
            "decision letter",
            "evaluation",
            "comment",
            "reply",
            "correction",
            "erratum"
        ]
        if any(marker in title for marker in secondary_markers):
            return "secondary_record"
        if paper_type in [
            "peer-review",
            "posted-content",
            "proceedings-article",
            "book-chapter"
        ]:
            if len(matched) >= 2:
                return "partially_relevant"
            return "indirectly_relevant"
        if len(matched) >= 4:
            return "directly_relevant"
        if len(matched) >= 2:
            return "partially_relevant"
        if len(matched) >= 1:
            return "indirectly_relevant"
        return "not_relevant"
    # =====================================================
    # DETERMINISTIC DOI SECTION
    # =====================================================
    def build_deterministic_doi_section(self, papers):
        valid_papers = [
            p for p in papers
            if isinstance(p, dict) and not p.get("error")
        ]
        lines = []
        lines.append("# Deterministic DOI Evidence")
        lines.append(
            "The DOI values below are generated directly from the parsed "
            "Crossref API response, not by the LLM."
        )
        doi_index = 1
        for paper in valid_papers:
            doi = paper.get("doi", "")
            title = paper.get("title", "")
            url = paper.get("url", "")
            if not doi:
                continue
            lines.append(
                f"{doi_index}. {title}\n"
                f"   DOI: {doi}\n"
                f"   DOI URL: {url}"
            )
            doi_index += 1
        if doi_index == 1:
            lines.append("No DOI values were available in the retrieved Crossref records.")
        lines.append(
            "Interpretation: DOI registration supports bibliographic existence "
            "and resolvability. It does not prove experimental correctness, "
            "biological truth, optimal growth conditions, fermentation "
            "performance, oxygen limitation, or industrial feasibility."
        )
        return "\n".join(lines)
    def format_papers(self, papers, query=None):
        formatted = ""
        for i, paper in enumerate(papers, start=1):
            if paper.get("error"):
                formatted += f"""
==================================================
PAPER {i} ERROR
==================================================
ERROR:
{paper.get("error", "")}
DETAILS:
{paper.get("details", "")}
"""
                continue
            relevance = (
                self.classify_relevance(paper, query)
                if query
                else "not_classified"
            )
            formatted += f"""
==================================================
PAPER {i}
==================================================
TITLE:
{paper.get("title", "")}
RELEVANCE CLASSIFICATION:
{relevance}
AUTHORS:
{", ".join(paper.get("authors", []))}
YEAR:
{paper.get("year", "")}
JOURNAL:
{paper.get("journal", "")}
PUBLISHER:
{paper.get("publisher", "")}
TYPE:
{paper.get("type", "")}
DOI:
{paper.get("doi", "")}
URL:
{paper.get("url", "")}
REFERENCE COUNT:
{paper.get("reference_count", 0)}
CITED BY COUNT:
{paper.get("is_referenced_by_count", 0)}
ABSTRACT:
{paper.get("abstract", "")[:2500]}
"""
        return formatted
    def build_agent_summary(
        self,
        query,
        papers,
        query_used=None,
        doi_validation=None
    ):
        valid_papers = [
            p for p in papers
            if isinstance(p, dict) and not p.get("error")
        ]
        doi_count = len([p for p in valid_papers if p.get("doi")])
        works_with_references = len(
            [p for p in valid_papers if p.get("has_references")]
        )
        classifications = {}
        for paper in valid_papers:
            label = self.classify_relevance(paper, query)
            classifications[label] = classifications.get(label, 0) + 1
        titles = [
            p.get("title")
            for p in valid_papers
            if p.get("title")
        ]
        years = [
            p.get("year")
            for p in valid_papers
            if p.get("year")
        ]
        text = (
            "Crossref searched official bibliographic metadata. "
            f"{len(valid_papers)} usable records were retrieved, including "
            f"{doi_count} DOI-linked records and {works_with_references} "
            "records with deposited reference metadata. "
        )
        if classifications:
            text += f"Relevance classification counts: {classifications}. "
        if years:
            text += (
                f"Retrieved record years span "
                f"{min(years)} to {max(years)}. "
            )
        if titles:
            text += "Representative retrieved titles include: "
            text += "; ".join(titles[:3]) + ". "
        if doi_validation:
            text += f"DOI agency validation result: {doi_validation}. "
        text += (
            "Crossref validates bibliographic existence and DOI metadata only. "
            "It does not validate biological truth, experimental correctness, "
            "peer-review quality, fermentation performance, oxygen limitation, "
            "or industrial feasibility unless such claims are explicitly "
            "supported by retrieved title or abstract metadata."
        )
        return text
    def build_prompt(
        self,
        query,
        papers,
        query_used=None,
        doi_validation=None,
        deterministic_doi_section=None
    ):
        formatted_papers = self.format_papers(
            papers=papers,
            query=query
        )
        return f"""
You are a STRICT Crossref bibliographic metadata validation agent.
You use ONLY official Crossref metadata retrieved from:
- https://api.crossref.org/works
- https://api.crossref.org/works/{{doi}}
- https://api.crossref.org/works/{{doi}}/agency
USER QUERY:
{query}
CROSSREF QUERY USED:
{self.safe_json(query_used)}
DOI VALIDATION:
{self.safe_json(doi_validation)}
DETERMINISTIC DOI SECTION:
{deterministic_doi_section}
RETRIEVED CROSSREF RESULTS:
{formatted_papers}
==================================================
ABSOLUTE RULES
==================================================
1. Crossref metadata proves bibliographic registration only.
2. Crossref metadata does NOT automatically prove:
   - peer review
   - publication quality
   - experimental correctness
   - biological truth
   - industrial feasibility
   - optimal growth conditions
   - oxygen limitation
   - process performance
3. NEVER say "all papers are published and indexed".
4. Instead say:
   "The retrieved records are registered in Crossref metadata."
5. NEVER say "all papers are relevant".
6. Instead classify records as:
   - directly relevant
   - partially relevant
   - indirectly relevant
   - secondary_record
   - not relevant
7. Treat preprints, SSRN records, editor evaluations, decision letters,
   reviews, comments, corrections, book chapters, and protocols as limited
   or secondary evidence unless the abstract explicitly supports the claim.
8. NEVER claim that retrieved papers support biological conclusions unless
   the title or abstract explicitly states the claim.
9. If abstracts are missing, say:
   "Insufficient abstract-level evidence available."
10. If only title/metadata is available, say:
   "Only bibliographic/topic relevance can be assessed."
11. NEVER invent citations, DOI references, authors, journals, years, URLs,
    experimental values, temperatures, pH values, media, oxygen conditions,
    or growth parameters.
12. DOI existence means the DOI is registered/resolvable, not that the
    scientific claim is proven.
13. Clearly separate:
    - bibliographic validation
    - topic relevance
    - scientific evidence
    - unsupported conclusions
    - uncertainty
14. Do NOT create your own DOI list.
15. If DOI evidence is needed, refer only to the deterministic DOI section.
Do not output raw JSON.
Be concise, strict, and conservative.
"""
    def run(
        self,
        query,
        rows=10,
        use_llm=True,
        filters=None,
        reference_mode="any",
        select=None,
        field_queries=None
    ):
        self.debug_print("ORIGINAL CROSSREF QUERY", query)
        doi = self.extract_doi(query)
        doi_validation = None
        if doi:
            self.debug_print("DOI DETECTED", doi)
            paper = self.get_work_by_doi(doi)
            papers = [paper]
            if not paper.get("error"):
                doi_validation = paper.get("doi_validation")
            query_used = {
                "endpoint": f"{self.works_url}/{doi}",
                "doi": doi
            }
        else:
            search_result = self.search(
                query=query,
                rows=rows,
                filters=filters,
                reference_mode=reference_mode,
                select=select,
                field_queries=field_queries
            )
            papers = search_result.get("items", [])
            if search_result.get("error"):
                papers.append(
                    {
                        "error": "Crossref search failed",
                        "details": search_result.get("error"),
                        "source": "Crossref"
                    }
                )
            query_used = search_result.get("query_used", {})
        deterministic_doi_section = self.build_deterministic_doi_section(
            papers
        )
        agent_summary = self.build_agent_summary(
            query=query,
            papers=papers,
            query_used=query_used,
            doi_validation=doi_validation
        )
        if use_llm:
            prompt = self.build_prompt(
                query=query,
                papers=papers,
                query_used=query_used,
                doi_validation=doi_validation,
                deterministic_doi_section=deterministic_doi_section
            )
            self.debug_print("FINAL CROSSREF PROMPT TO OLLAMA", prompt)
            print(f"[CROSSREF PROMPT SIZE] {len(prompt)} characters")
            try:
                llm_assessment = self.llm.invoke(prompt)
                status = "success"
            except Exception as ex:
                traceback.print_exc()
                llm_assessment = (
                    "Crossref LLM assessment failed. "
                    "Using deterministic Crossref summary.\n\n"
                    + agent_summary
                )
                status = "failed"
        else:
            llm_assessment = agent_summary
            status = "success"
        assessment = (
            f"{llm_assessment}\n\n"
            f"{deterministic_doi_section}"
        )
        valid_papers = [
            p for p in papers
            if isinstance(p, dict) and not p.get("error")
        ]
        result = {
            "agent_name": "CROSSREF_EXPLORER",
            "agent_status": status,
            "source": "Crossref",
            "official_endpoints": {
                "works": self.works_url,
                "work_by_doi": f"{self.works_url}/{{doi}}",
                "doi_agency": f"{self.works_url}/{{doi}}/agency"
            },
            "query": query,
            "query_used": query_used,
            "doi_detected": doi,
            "doi_validation": doi_validation,
            "papers": papers,
            "deterministic_doi_section": deterministic_doi_section,
            "summary": {
                "papers_found": len(papers),
                "usable_papers": len(valid_papers),
                "doi_count": len(
                    [p for p in valid_papers if p.get("doi")]
                ),
                "works_with_references": len(
                    [p for p in valid_papers if p.get("has_references")]
                ),
                "contains_errors": any(
                    isinstance(p, dict) and p.get("error")
                    for p in papers
                )
            },
            "agent_summary": agent_summary,
            "llm_assessment": llm_assessment,
            "assessment": assessment
        }
        self.debug_print("FINAL CROSSREF OUTPUT", result)
        return result