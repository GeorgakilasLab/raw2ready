"""Internet Explorer Agent.

Retrieves scientific literature and metadata from official NCBI/PubMed databases
and optional web search endpoints.
"""

import json
import re
import time
import traceback
import warnings

import requests
from ddgs import DDGS
from Bio import Entrez
import os
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.ollama import OllamaModel


warnings.filterwarnings(
    "ignore",
    message="Email address is not specified.*"
)


class InternetExplorerAgent:
    """Retrieves and validates publication evidence using PubMed and DuckDuckGo.

    Attributes:
        model_name: Name of the LLM.
        temperature: LLM temperature parameter.
        email: User email address for polite Entrez requests.
        api_key: Optional Entrez API key.
        tool: Identifier string for Entrez requests.
        debug: True if debug prints are enabled.
        timeout: Request timeout duration in seconds.
        max_retries: Maximum request retries.
        base_url: Base NCBI API URL.
        esearch_url: ESearch endpoint URL.
        efetch_url: EFetch endpoint URL.
        esummary_url: ESummary endpoint URL.
        elink_url: ELink endpoint URL.
        llm: Language model client.
        session: Active request session.
    """

    def __init__(
        self,
        model_name="llama3:latest",
        temperature=0.1,
        email="local@localhost",
        api_key=None,
        tool="InternetExplorerAgent",
        debug=True,
        timeout=30,
        max_retries=3
    ):
        """Initializes the InternetExplorerAgent.

        Args:
            model_name: The name of the LLM. Defaults to "llama3:latest".
            temperature: LLM temperature parameter. Defaults to 0.1.
            email: Email address for Entrez polite API. Defaults to
                "local@localhost".
            api_key: Optional NCBI Entrez API key.
            tool: Requesting tool name. Defaults to "InternetExplorerAgent".
            debug: Whether to print debug information. Defaults to True.
            timeout: Timeout in seconds for HTTP requests. Defaults to 30.
            max_retries: Maximum request retries. Defaults to 3.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.email = email
        self.api_key = api_key
        self.tool = tool
        self.debug = debug
        self.timeout = timeout
        self.max_retries = max_retries

        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.esearch_url = f"{self.base_url}/esearch.fcgi"
        self.efetch_url = f"{self.base_url}/efetch.fcgi"
        self.esummary_url = f"{self.base_url}/esummary.fcgi"
        self.elink_url = f"{self.base_url}/elink.fcgi"

        Entrez.email = self.email
        Entrez.tool = self.tool

        if self.api_key:
            Entrez.api_key = self.api_key

        from pydantic_ai.providers.ollama import OllamaProvider
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        provider = OllamaProvider(base_url=base_url)
        model = OllamaModel(model_name=model_name, provider=provider)
        self.agent = Agent(
            model=model,
            model_settings=ModelSettings(temperature=temperature)
        )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": f"{self.tool}/1.0 (mailto:{self.email})"
            }
        )

        print("=" * 80)
        print("[INTERNET EXPLORER] INITIALIZED")
        print(f"MODEL: {model_name}")
        print(f"TEMPERATURE: {temperature}")
        print(f"ESEARCH: {self.esearch_url}")
        print(f"EFETCH: {self.efetch_url}")
        print(f"ESUMMARY: {self.esummary_url}")
        print(f"ELINK: {self.elink_url}")
        print("=" * 80)

    # =====================================================
    # BASIC HELPERS
    # =====================================================
    def debug_print(self, title, data):
        if not self.debug:
            return

        print("\n" + "=" * 80)
        print(f"[INTERNET EXPLORER DEBUG] {title}")
        print("=" * 80)

        try:
            if isinstance(data, str):
                print(data)
            else:
                print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        except Exception:
            print(str(data))

        print("=" * 80 + "\n")

    def clean_text(self, text):
        if text is None:
            return ""

        text = str(text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def compact_json(self, data):
        return json.dumps(data, ensure_ascii=False, default=str)

    def clean_query(self, query, max_words=40):
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

        self.debug_print("CLEANED INTERNET QUERY", cleaned)

        return cleaned

    def extract_pmid(self, text):
        if not text:
            return None

        match = re.search(r"(?:PMID[:\s]*)?(\d{6,9})", str(text), flags=re.I)
        return match.group(1) if match else None

    # =====================================================
    # REQUEST HANDLER
    # =====================================================
    def request_get(self, url, params=None):
        params = params or {}

        params.setdefault("tool", self.tool)
        params.setdefault("email", self.email)

        if self.api_key:
            params.setdefault("api_key", self.api_key)

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self.debug_print(
                    f"NCBI REQUEST ATTEMPT {attempt}",
                    {"url": url, "params": params}
                )

                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )

                self.debug_print(
                    "NCBI RESPONSE",
                    {
                        "status_code": response.status_code,
                        "url": response.url
                    }
                )

                if response.status_code == 200:
                    return response

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
                "error": "NCBI request failed after retries",
                "details": last_error
            }
        }

    # =====================================================
    # QUERY BUILDING
    # =====================================================
    def build_pubmed_query(self, query):
        cleaned = self.clean_query(query)

        if not cleaned:
            cleaned = "microbial fermentation biotechnology"

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

        self.debug_print("FINAL PUBMED SEARCH QUERY", cleaned)

        return cleaned

    def build_ddgs_query(self, query):
        cleaned = self.clean_query(query)

        if not cleaned:
            cleaned = "microbial fermentation biotechnology"

        return f"site:pubmed.ncbi.nlm.nih.gov {cleaned}"

    # =====================================================
    # PUBMED SEARCH
    # =====================================================
    def pubmed_esearch(self, query, max_results=10):
        pubmed_query = self.build_pubmed_query(query)

        params = {
            "db": "pubmed",
            "term": pubmed_query,
            "retmax": max_results,
            "sort": "relevance",
            "retmode": "json"
        }

        response = self.request_get(self.esearch_url, params=params)

        if isinstance(response, dict) and response.get("status") == "error":
            return {
                "ids": [],
                "query_used": params,
                "error": response.get("message", {}),
                "source": "PubMed"
            }

        try:
            data = response.json()
            ids = data.get("esearchresult", {}).get("idlist", [])

            return {
                "ids": ids,
                "query_used": params,
                "source": "PubMed"
            }

        except Exception as ex:
            traceback.print_exc()

            return {
                "ids": [],
                "query_used": params,
                "error": str(ex),
                "source": "PubMed"
            }

    def pubmed_efetch(self, pmids):
        if not pmids:
            return []

        if isinstance(pmids, str):
            pmids = [pmids]

        try:
            handle = Entrez.efetch(
                db="pubmed",
                id=",".join(pmids),
                retmode="xml"
            )

            records = Entrez.read(handle)
            handle.close()

            articles = records.get("PubmedArticle", [])
            papers = [self.parse_pubmed_article(article) for article in articles]

            self.debug_print("PARSED PUBMED PAPERS", papers)

            return papers

        except Exception as ex:
            traceback.print_exc()

            return [
                {
                    "error": str(ex),
                    "pmids": pmids,
                    "source": "PubMed"
                }
            ]

    def pubmed_search(self, query, max_results=10):
        pmid = self.extract_pmid(query)

        if pmid:
            papers = self.pubmed_efetch([pmid])

            return {
                "papers": papers,
                "query_used": {
                    "endpoint": self.efetch_url,
                    "pmid": pmid
                },
                "pmids": [pmid],
                "source": "PubMed"
            }

        search_result = self.pubmed_esearch(
            query=query,
            max_results=max_results
        )

        pmids = search_result.get("ids", [])

        if not pmids:
            return {
                "papers": [],
                "query_used": search_result.get("query_used", {}),
                "pmids": [],
                "warning": "No PubMed records found",
                "error": search_result.get("error"),
                "source": "PubMed"
            }

        papers = self.pubmed_efetch(pmids)

        return {
            "papers": papers,
            "query_used": search_result.get("query_used", {}),
            "pmids": pmids,
            "source": "PubMed"
        }

    # =====================================================
    # PARSE PUBMED ARTICLE
    # =====================================================
    def parse_pubmed_article(self, article):
        medline = article.get("MedlineCitation", {})
        article_data = medline.get("Article", {})

        pmid = self.clean_text(medline.get("PMID", ""))
        title = self.clean_text(article_data.get("ArticleTitle", ""))

        abstract = ""

        try:
            abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
            abstract = self.clean_text(" ".join(str(x) for x in abstract_parts))
        except Exception:
            abstract = ""

        journal = self.clean_text(
            article_data.get("Journal", {}).get("Title", "")
        )

        year = self.extract_pubmed_year(article_data)
        authors = self.extract_authors(article_data)
        doi = self.extract_article_doi(article_data)
        publication_types = self.extract_publication_types(article_data)
        mesh_terms = self.extract_mesh_terms(medline)

        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
        doi_url = f"https://doi.org/{doi}" if doi else ""

        return {
            "title": title,
            "abstract": abstract[:5000],
            "journal": journal,
            "year": year,
            "authors": authors,
            "pmid": pmid,
            "pubmed_id": pmid,
            "pubmed_url": pubmed_url,
            "url": pubmed_url,
            "doi": doi,
            "doi_url": doi_url,
            "publication_types": publication_types,
            "mesh_terms": mesh_terms,
            "source": "PubMed"
        }

    def extract_pubmed_year(self, article_data):
        try:
            pub_date = (
                article_data
                .get("Journal", {})
                .get("JournalIssue", {})
                .get("PubDate", {})
            )

            if pub_date.get("Year"):
                return pub_date.get("Year")

            if pub_date.get("MedlineDate"):
                match = re.search(r"\d{4}", pub_date.get("MedlineDate", ""))
                if match:
                    return match.group(0)
        except Exception:
            pass

        return ""

    def extract_authors(self, article_data):
        authors = []

        try:
            for author in article_data.get("AuthorList", []):
                last = self.clean_text(author.get("LastName", ""))
                fore = self.clean_text(author.get("ForeName", ""))
                collective = self.clean_text(author.get("CollectiveName", ""))

                full = f"{fore} {last}".strip()

                if full:
                    authors.append(full)
                elif collective:
                    authors.append(collective)
        except Exception:
            pass

        return authors

    def extract_article_doi(self, article_data):
        try:
            for article_id in article_data.get("ELocationID", []):
                if article_id.attributes.get("EIdType") == "doi":
                    doi = self.clean_text(str(article_id)).lower()
                    if doi and doi not in ["none", "null", "nan"]:
                        return doi
        except Exception:
            pass

        return ""

    def extract_publication_types(self, article_data):
        try:
            return [
                self.clean_text(x)
                for x in article_data.get("PublicationTypeList", [])
            ]
        except Exception:
            return []

    def extract_mesh_terms(self, medline):
        terms = []

        try:
            for mesh in medline.get("MeshHeadingList", []):
                descriptor = mesh.get("DescriptorName", "")
                if descriptor:
                    terms.append(self.clean_text(descriptor))
        except Exception:
            pass

        return terms

    # =====================================================
    # DDGS OPTIONAL SEARCH
    # =====================================================
    def ddgs_search(self, query, max_results=5):
        results_list = []
        search_query = self.build_ddgs_query(query)

        try:
            with DDGS() as ddgs:
                results = list(
                    ddgs.text(
                        search_query,
                        max_results=max_results
                    )
                )

            for r in results:
                if not isinstance(r, dict):
                    continue

                results_list.append(
                    {
                        "title": self.clean_text(r.get("title", "")),
                        "summary": self.clean_text(r.get("body", "")),
                        "url": r.get("href", ""),
                        "source": "DDGS"
                    }
                )

        except Exception as ex:
            traceback.print_exc()

            results_list.append(
                {
                    "error": str(ex),
                    "query": search_query,
                    "source": "DDGS"
                }
            )

        return results_list

    # =====================================================
    # RELEVANCE
    # =====================================================
    def classify_relevance(self, paper, query):
        text = " ".join(
            [
                str(paper.get("title", "")),
                str(paper.get("abstract", "")),
                str(paper.get("journal", "")),
                str(paper.get("mesh_terms", "")),
                str(paper.get("publication_types", ""))
            ]
        ).lower()

        q = self.clean_query(query).lower()

        query_terms = [
            term for term in re.split(r"\s+", q)
            if len(term) > 3
        ]

        matched = [term for term in query_terms if term in text]

        publication_types = " ".join(
            paper.get("publication_types", [])
        ).lower()

        title = str(paper.get("title", "")).lower()

        secondary_markers = [
            "editorial",
            "letter",
            "comment",
            "reply",
            "correction",
            "erratum",
            "retraction",
            "published erratum"
        ]

        if any(marker in publication_types for marker in secondary_markers):
            return "secondary_record"

        if any(marker in title for marker in secondary_markers):
            return "secondary_record"

        if len(matched) >= 4:
            return "directly_relevant"

        if len(matched) >= 2:
            return "partially_relevant"

        if len(matched) >= 1:
            return "indirectly_relevant"

        return "not_relevant"

    # =====================================================
    # DETERMINISTIC SECTIONS
    # =====================================================
    def build_deterministic_pubmed_section(self, papers):
        lines = []

        lines.append("# Deterministic PMID/DOI Evidence")
        lines.append(
            "The PMID/DOI/URL values below are generated directly from parsed "
            "PubMed/NCBI metadata, not by the LLM."
        )

        valid = [
            p for p in papers
            if isinstance(p, dict) and not p.get("error")
        ]

        if not valid:
            lines.append("No valid PubMed records were available.")
            return "\n".join(lines)

        for i, paper in enumerate(valid, start=1):
            lines.append(f"{i}. {paper.get('title', '')}")
            lines.append(f"   PMID: {paper.get('pmid', '')}")
            lines.append(f"   PubMed URL: {paper.get('pubmed_url', '')}")

            if paper.get("doi"):
                lines.append(f"   DOI: {paper.get('doi')}")
                lines.append(f"   DOI URL: {paper.get('doi_url')}")
            else:
                lines.append("   DOI: not available in PubMed metadata")

        lines.append(
            "Interpretation: PubMed registration supports bibliographic "
            "existence in PubMed/NCBI metadata. It does not prove experimental "
            "correctness, biological truth, optimal growth conditions, oxygen "
            "limitation, fermentation performance, process performance, or "
            "industrial feasibility."
        )

        return "\n".join(lines)

    def build_deterministic_ddgs_section(self, ddgs_results):
        valid = [
            x for x in ddgs_results
            if isinstance(x, dict) and not x.get("error")
        ]

        lines = []
        lines.append("# Deterministic Optional Web Evidence")

        if not valid:
            lines.append("No valid optional DDGS web results were retrieved.")
            return "\n".join(lines)

        lines.append(
            f"{len(valid)} optional DDGS web result(s) were retrieved. "
            "These results are supplementary and are not stronger than "
            "PubMed/NCBI metadata."
        )

        for i, item in enumerate(valid, start=1):
            lines.append(f"{i}. {item.get('title', '')}")
            lines.append(f"   URL: {item.get('url', '')}")

        return "\n".join(lines)

    # =====================================================
    # EXTRACTION / SUMMARY
    # =====================================================
    def extract_important_results(self, ddgs_results, pubmed_papers, query):
        extracted = {
            "pubmed_titles": [],
            "pubmed_ids": [],
            "doi_values": [],
            "pubmed_urls": [],
            "doi_urls": [],
            "ddgs_titles": [],
            "web_urls": [],
            "relevance_counts": {},
            "errors": [],
            "warnings": []
        }

        for paper in pubmed_papers:
            if not isinstance(paper, dict):
                continue

            if paper.get("error"):
                extracted["errors"].append(paper.get("error"))
                continue

            if paper.get("title"):
                extracted["pubmed_titles"].append(paper.get("title"))

            if paper.get("pmid"):
                extracted["pubmed_ids"].append(paper.get("pmid"))

            if paper.get("doi"):
                extracted["doi_values"].append(paper.get("doi"))

            if paper.get("pubmed_url"):
                extracted["pubmed_urls"].append(paper.get("pubmed_url"))

            if paper.get("doi_url"):
                extracted["doi_urls"].append(paper.get("doi_url"))

            label = self.classify_relevance(paper, query)

            extracted["relevance_counts"][label] = (
                extracted["relevance_counts"].get(label, 0) + 1
            )

        for item in ddgs_results:
            if not isinstance(item, dict):
                continue

            if item.get("error"):
                extracted["errors"].append(item.get("error"))
                continue

            if item.get("title"):
                extracted["ddgs_titles"].append(item.get("title"))

            if item.get("url"):
                extracted["web_urls"].append(item.get("url"))

        for key in [
            "pubmed_titles",
            "pubmed_ids",
            "doi_values",
            "pubmed_urls",
            "doi_urls",
            "ddgs_titles",
            "web_urls"
        ]:
            extracted[key] = list(dict.fromkeys(extracted[key]))

        return extracted

    def build_agent_summary(self, extracted, pubmed_papers, ddgs_results):
        valid_pubmed = [
            p for p in pubmed_papers
            if isinstance(p, dict) and not p.get("error")
        ]

        valid_ddgs = [
            x for x in ddgs_results
            if isinstance(x, dict) and not x.get("error")
        ]

        relevance_counts = extracted.get("relevance_counts", {})

        text = (
            "# PubMed Validation Summary\n"
            f"Internet Explorer retrieved {len(valid_pubmed)} valid PubMed/NCBI "
            f"record(s) and {len(valid_ddgs)} valid optional DDGS web result(s).\n\n"
        )

        text += "# Relevance to User Query\n"

        if relevance_counts:
            text += f"PubMed relevance counts: {relevance_counts}.\n"

            direct = relevance_counts.get("directly_relevant", 0)
            total = sum(relevance_counts.values())

            if direct == total:
                text += "All classified PubMed records were directly relevant.\n\n"
            else:
                text += (
                    "Not all PubMed records were directly relevant; some were "
                    "partial, indirect, secondary, or not relevant according to "
                    "the deterministic relevance classifier.\n\n"
                )
        else:
            text += "No relevance counts were available.\n\n"

        text += "# What PubMed Supports\n"
        text += (
            "PubMed supports bibliographic existence of the retrieved records "
            "in PubMed/NCBI metadata. Retrieved abstracts may mention reported "
            "experimental parameters such as temperature, pH, oxygen conditions, "
            "media, yields, or growth-related values, but PubMed does not "
            "independently validate those values as scientific truth.\n\n"
        )

        text += "# What PubMed Does Not Support\n"
        text += (
            "PubMed does not automatically prove peer review, publication "
            "quality, experimental correctness, biological truth, industrial "
            "feasibility, optimal growth conditions, oxygen limitation, "
            "fermentation performance, or process performance.\n\n"
        )

        text += "# Scientific Uncertainty\n"
        text += (
            "Any process or biological conclusion must be evaluated from the "
            "actual article content and experimental design, not from PubMed "
            "registration alone."
        )

        return text

    # =====================================================
    # LLM PROMPT
    # =====================================================
    def build_prompt(
        self,
        query,
        pubmed_papers,
        ddgs_results,
        extracted,
        pubmed_query_used,
        deterministic_pubmed_section,
        deterministic_ddgs_section
    ):
        valid_pubmed = [
            p for p in pubmed_papers
            if isinstance(p, dict) and not p.get("error")
        ]

        valid_ddgs = [
            x for x in ddgs_results
            if isinstance(x, dict) and not x.get("error")
        ]

        compact_summary = {
            "usable_pubmed_record_count": len(valid_pubmed),
            "usable_ddgs_result_count": len(valid_ddgs),
            "pmid_count": len(extracted.get("pubmed_ids", [])),
            "doi_count": len(extracted.get("doi_values", [])),
            "relevance_counts": extracted.get("relevance_counts", {}),
            "warnings": extracted.get("warnings", []),
            "errors": extracted.get("errors", [])
        }

        compact_pubmed_records = []

        for paper in valid_pubmed:
            doi = paper.get("doi", "")

            compact_pubmed_records.append(
                {
                    "title": paper.get("title", ""),
                    "year": paper.get("year", ""),
                    "journal": paper.get("journal", ""),
                    "pmid": paper.get("pmid", ""),
                    "doi": doi if doi else "not available in PubMed metadata",
                    "publication_types": paper.get("publication_types", []),
                    "mesh_terms": paper.get("mesh_terms", [])[:12],
                    "abstract_excerpt": paper.get("abstract", "")[:1000],
                    "relevance": self.classify_relevance(paper, query)
                }
            )

        compact_ddgs_records = []

        for item in valid_ddgs:
            compact_ddgs_records.append(
                {
                    "title": item.get("title", ""),
                    "summary_excerpt": item.get("summary", "")[:400],
                    "url": item.get("url", "")
                }
            )

        return f"""
You are a STRICT PubMed/Internet bibliographic evidence validation agent.

USER QUERY:
{query}

DETERMINISTIC COUNTS:
{self.compact_json(compact_summary)}

COMPACT PUBMED RECORDS:
{self.compact_json(compact_pubmed_records)}

COMPACT OPTIONAL DDGS RECORDS:
{self.compact_json(compact_ddgs_records)}

AUTHORITATIVE DETERMINISTIC PMID/DOI SECTION:
{deterministic_pubmed_section}

AUTHORITATIVE DETERMINISTIC DDGS SECTION:
{deterministic_ddgs_section}

==================================================
ABSOLUTE RULES
==================================================
1. PubMed/NCBI metadata proves bibliographic existence only.
2. PubMed may contain reported abstract-level experimental values.
3. PubMed does NOT independently validate reported values as scientific truth.
4. PubMed does NOT automatically prove peer review, publication quality,
   experimental correctness, biological truth, industrial feasibility,
   optimal growth conditions, oxygen limitation, fermentation performance,
   or process performance.
5. NEVER say PubMed supports temperatures, pH, oxygen conditions, media,
   yields, or growth parameters as validated facts.
6. You may say abstracts mention or report such values.
7. NEVER invent citations, DOI values, PMID values, URLs, titles, authors,
   journals, years, temperatures, pH values, oxygen conditions, media,
   yields, or growth parameters.
8. If DOI is missing, write exactly:
   "DOI: not available in PubMed metadata"
9. NEVER write:
   "DOI: none"
   "DOI: None"
   "DOI: https://doi.org/none"
10. The deterministic PMID/DOI section is authoritative.
11. The deterministic DDGS section is authoritative.
12. If usable_ddgs_result_count > 0, include Optional Web Evidence.
13. If usable_ddgs_result_count > 0, do NOT say no optional web evidence was retrieved.
14. Do NOT say all records are directly relevant unless relevance_counts proves every record is directly_relevant.
15. If relevance_counts contains partially_relevant, indirectly_relevant,
    secondary_record, or not_relevant, explicitly say not all records are directly relevant.
16. Be strict, conservative, and concise.

==================================================
OUTPUT REQUIREMENTS
==================================================
Use only these sections when useful:
# PubMed Validation Summary
# Retrieved PubMed Records
# Optional Web Evidence
# Relevance to User Query
# What PubMed Supports
# What PubMed Does Not Support
# Scientific Uncertainty

Do NOT output raw JSON.
Do NOT repeat the full deterministic PMID/DOI section.
Do NOT repeat the full deterministic DDGS section.
Do NOT contradict deterministic counts.
"""

    # =====================================================
    # LLM OUTPUT GUARD
    # =====================================================
    def sanitize_llm_assessment(
        self,
        text,
        valid_ddgs_count,
        relevance_counts=None
    ):
        if not text:
            return ""

        relevance_counts = relevance_counts or {}

        bad_optional_phrases = [
            "No optional web evidence was retrieved.",
            "No optional DDGS web evidence was retrieved.",
            "No optional web evidence retrieved.",
            "No optional web results were retrieved.",
            "No valid optional DDGS web results were retrieved."
        ]

        if valid_ddgs_count > 0:
            for phrase in bad_optional_phrases:
                text = text.replace(
                    phrase,
                    f"{valid_ddgs_count} optional DDGS web result(s) were retrieved."
                )

        doi_bad_patterns = [
            "DOI: https://doi.org/none",
            "DOI: http://doi.org/none",
            "DOI: none",
            "DOI: None",
            "DOI: null",
            "DOI: Null"
        ]

        for pattern in doi_bad_patterns:
            text = text.replace(
                pattern,
                "DOI: not available in PubMed metadata"
            )

        bad_pubmed_support = (
            "PubMed supports the bibliographic existence of the records and "
            "provides metadata such as titles, authors, journals, years, "
            "temperatures, pH values, oxygen conditions, media, yields, and "
            "growth parameters."
        )

        corrected_pubmed_support = (
            "PubMed supports bibliographic existence of the retrieved records "
            "in PubMed/NCBI metadata. Retrieved abstracts may mention reported "
            "experimental parameters such as temperature, pH, oxygen conditions, "
            "media, yields, or growth-related values, but PubMed does not "
            "independently validate those values as scientific truth."
        )

        text = text.replace(bad_pubmed_support, corrected_pubmed_support)

        total = sum(relevance_counts.values())
        direct = relevance_counts.get("directly_relevant", 0)

        if total > 0 and direct < total:
            overclaim_phrases = [
                "The primary records are directly relevant to the user query",
                "The PubMed records are all relevant to the user query",
                "All records are directly relevant",
                "The primary records are directly relevant"
            ]

            for phrase in overclaim_phrases:
                text = text.replace(
                    phrase,
                    "Most records may be relevant, but not all records are directly relevant according to the deterministic relevance counts"
                )

        return text

    # =====================================================
    # RUN
    # =====================================================
    def run(
        self,
        query,
        use_llm=True,
        max_results=10,
        use_ddgs=True
    ):
        self.debug_print("ORIGINAL INTERNET QUERY", query)

        pubmed_result = self.pubmed_search(
            query=query,
            max_results=max_results
        )

        pubmed_papers = pubmed_result.get("papers", [])
        pubmed_query_used = pubmed_result.get("query_used", {})

        if use_ddgs:
            ddgs_results = self.ddgs_search(
                query=query,
                max_results=min(max_results, 5)
            )
        else:
            ddgs_results = []

        extracted = self.extract_important_results(
            ddgs_results=ddgs_results,
            pubmed_papers=pubmed_papers,
            query=query
        )

        deterministic_pubmed_section = self.build_deterministic_pubmed_section(
            pubmed_papers
        )

        deterministic_ddgs_section = self.build_deterministic_ddgs_section(
            ddgs_results
        )

        agent_summary = self.build_agent_summary(
            extracted=extracted,
            pubmed_papers=pubmed_papers,
            ddgs_results=ddgs_results
        )

        valid_pubmed = [
            p for p in pubmed_papers
            if isinstance(p, dict) and not p.get("error")
        ]

        valid_ddgs = [
            x for x in ddgs_results
            if isinstance(x, dict) and not x.get("error")
        ]

        if use_llm:
            prompt = self.build_prompt(
                query=query,
                pubmed_papers=pubmed_papers,
                ddgs_results=ddgs_results,
                extracted=extracted,
                pubmed_query_used=pubmed_query_used,
                deterministic_pubmed_section=deterministic_pubmed_section,
                deterministic_ddgs_section=deterministic_ddgs_section
            )

            self.debug_print("FINAL INTERNET EXPLORER PROMPT", prompt)
            print(f"[INTERNET EXPLORER PROMPT SIZE] {len(prompt)} characters")

            try:
                result = self.agent.run_sync(prompt)
                llm_assessment = result.data
                llm_assessment = self.sanitize_llm_assessment(
                    llm_assessment,
                    valid_ddgs_count=len(valid_ddgs),
                    relevance_counts=extracted.get("relevance_counts", {})
                )
                status = "success"

            except Exception:
                traceback.print_exc()
                llm_assessment = (
                    "Internet Explorer LLM generation failed. "
                    "Using deterministic agent summary.\n\n"
                    + agent_summary
                )
                status = "failed"
        else:
            llm_assessment = agent_summary
            status = "success"

        final_assessment = (
            f"{llm_assessment}\n\n"
            f"{deterministic_pubmed_section}\n\n"
            f"{deterministic_ddgs_section}"
        )

        result = {
            "agent_name": "INTERNET_EXPLORER",
            "agent_status": status,
            "source": "PubMed/NCBI E-utilities + optional DDGS",
            "official_endpoints": {
                "pubmed_website": "https://pubmed.ncbi.nlm.nih.gov/",
                "esearch": self.esearch_url,
                "efetch": self.efetch_url,
                "esummary": self.esummary_url,
                "elink": self.elink_url
            },
            "query": query,
            "pubmed_query_used": pubmed_query_used,
            "results": {
                "pubmed": pubmed_papers,
                "ddgs": ddgs_results
            },
            "summary": {
                "pubmed_results": len(pubmed_papers),
                "usable_pubmed_results": len(valid_pubmed),
                "ddgs_results": len(ddgs_results),
                "usable_ddgs_results": len(valid_ddgs),
                "total_results": len(pubmed_papers) + len(ddgs_results),
                "pmid_count": len([p for p in valid_pubmed if p.get("pmid")]),
                "doi_count": len([p for p in valid_pubmed if p.get("doi")]),
                "relevance_counts": extracted.get("relevance_counts", {}),
                "errors": extracted.get("errors", []),
                "warnings": extracted.get("warnings", [])
            },
            "extracted_results": extracted,
            "deterministic_pubmed_section": deterministic_pubmed_section,
            "deterministic_ddgs_section": deterministic_ddgs_section,
            "agent_summary": agent_summary,
            "assessment": final_assessment
        }

        self.debug_print("FINAL INTERNET EXPLORER OUTPUT", result)

        return result