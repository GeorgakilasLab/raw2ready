"""Microorganism Router.

Classifies incoming natural language queries to determine if query details correspond to
selected microorganisms and require looking up databases like BacDive.
"""

import json
import re

import os
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.ollama import OllamaModel


class MicroorganismRouter:
    """Ollama-based router to determine if queries require BacDive data exploration.

    Attributes:
        model_name: Name of the LLM.
        temperature: LLM temperature parameter.
        llm: Language model client.
    """

    def __init__(
        self,
        model_name="llama3:latest",
        temperature=0.0
    ):
        """Initializes the MicroorganismRouter.

        Args:
            model_name: The name of the LLM. Defaults to "llama3:latest".
            temperature: LLM temperature parameter. Defaults to 0.0.
        """
        self.model_name = model_name
        self.temperature = temperature

        from pydantic_ai.providers.ollama import OllamaProvider
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        provider = OllamaProvider(base_url=base_url)
        model = OllamaModel(model_name=self.model_name, provider=provider)
        self.agent = Agent(
            model=model,
            model_settings=ModelSettings(temperature=self.temperature)
        )

    # =====================================================
    # UPDATE MODEL
    # =====================================================
    def update_model(
        self,
        model_name=None,
        temperature=None
    ):
        if model_name is not None:
            self.model_name = model_name

        if temperature is not None:
            self.temperature = temperature

        from pydantic_ai.providers.ollama import OllamaProvider
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        provider = OllamaProvider(base_url=base_url)
        model = OllamaModel(model_name=self.model_name, provider=provider)
        self.agent = Agent(
            model=model,
            model_settings=ModelSettings(temperature=self.temperature)
        )

    # =====================================================
    # ALIASES
    # =====================================================
    def microorganism_keywords(
        self,
        microorganism
    ):
        m = str(microorganism).lower().strip()

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
            [m]
        )

    # =====================================================
    # KEYWORD FALLBACK
    # =====================================================
    def keyword_match(
        self,
        query,
        selected_microorganisms
    ):
        q = str(query).lower()

        matched = []

        for microorganism in selected_microorganisms:

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

    # =====================================================
    # GENERAL SELECTED PHRASES
    # =====================================================
    def asks_about_all_selected(
        self,
        query
    ):
        q = str(query).lower()

        phrases = [
            "selected microorganisms",
            "these microorganisms",
            "those microorganisms",
            "all microorganisms",
            "all selected microorganisms",
            "compare them",
            "compare these",
            "compare selected",
            "for each microorganism",
            "for all microorganisms",
            "for all",
            "them"
        ]

        return any(
            phrase in q
            for phrase in phrases
        )

    # =====================================================
    # ROUTE
    # =====================================================
    def route(
        self,
        query,
        selected_microorganisms
    ):

        try:

            # =============================================
            # NORMALIZE SELECTED MICROORGANISMS
            # =============================================
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

            if not selected_microorganisms:

                return {
                    "use_bacdive": False,
                    "matched_microorganisms": [],
                    "reason": "No microorganisms selected."
                }

            # =============================================
            # DIRECT GENERAL PHRASE MATCH
            # =============================================
            if self.asks_about_all_selected(
                query
            ):

                return {
                    "use_bacdive": True,
                    "matched_microorganisms": selected_microorganisms,
                    "reason": "Question refers to all selected microorganisms."
                }

            # =============================================
            # DIRECT KEYWORD MATCH FIRST
            # =============================================
            keyword_matches = self.keyword_match(
                query,
                selected_microorganisms
            )

            # Do not return yet. We still let Ollama validate relevance.
            # But if Ollama fails, keyword_matches will be used safely.

            selected_text = "\n".join(
                [
                    f"- {m}"
                    for m in selected_microorganisms
                ]
            )

            router_prompt = f"""
You are a strict routing classifier for a BacDive microorganism agent.

The user selected these microorganisms:

{selected_text}

User question:
{query}

Your job:
Decide whether the question is specifically about one or more selected microorganisms
or about their fermentation, physiology, oxygen metabolism, growth, culture conditions,
strain behavior, morphology, taxonomy, biosafety, industrial use, or BacDive evidence.

Return ONLY valid JSON.

Schema:
{{
  "use_bacdive": true or false,
  "matched_microorganisms": ["exact selected microorganism name"],
  "reason": "short reason"
}}

Rules:
- If the question is unrelated to microorganisms, return false.
- If the question asks about a microorganism but it is not selected, return false.
- If the question is about selected microorganisms generally, return true.
- If the question says "selected microorganisms", "these microorganisms", or "compare them", match all selected microorganisms.
- If the question mentions aliases like E. coli, yeast, P. putida, map them to the exact selected microorganism name.
- If uncertain, return false.
- Return JSON only.
"""

            result = self.agent.run_sync(
                router_prompt
            )
            response = result.data

            print(
                "\n========== MICROORGANISM ROUTER RAW =========="
            )
            print(response)

            cleaned = str(response).strip()

            json_match = re.search(
                r"\{.*\}",
                cleaned,
                re.DOTALL
            )

            if json_match:

                cleaned = json_match.group(
                    0
                )

            parsed = json.loads(
                cleaned
            )

            use_bacdive = bool(
                parsed.get(
                    "use_bacdive",
                    False
                )
            )

            matched = parsed.get(
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

            # =============================================
            # VALIDATE MATCHES AGAINST SELECTED ONLY
            # =============================================
            valid_selected = []

            for candidate in matched:

                for selected in selected_microorganisms:

                    if str(candidate).lower().strip() == str(selected).lower().strip():

                        if selected not in valid_selected:

                            valid_selected.append(
                                selected
                            )

            # =============================================
            # IF OLLAMA APPROVES BUT RETURNS NO MATCHES
            # USE GENERAL OR KEYWORD FALLBACK
            # =============================================
            if use_bacdive and not valid_selected:

                if self.asks_about_all_selected(
                    query
                ):

                    valid_selected = list(
                        selected_microorganisms
                    )

                elif keyword_matches:

                    valid_selected = keyword_matches

            # =============================================
            # IF KEYWORD MATCH EXISTS BUT OLLAMA SAYS FALSE,
            # STILL ALLOW ONLY IF QUESTION HAS BIO/FERMENTATION TERMS
            # =============================================
            if (
                not use_bacdive
                and keyword_matches
                and self.is_biological_question(
                    query
                )
            ):

                return {
                    "use_bacdive": True,
                    "matched_microorganisms": keyword_matches,
                    "reason": "Keyword match with biological/fermentation relevance."
                }

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
                "reason": parsed.get(
                    "reason",
                    ""
                )
            }

        except Exception as ex:

            print(
                f"[MICROORGANISM ROUTER ERROR] {ex}"
            )

            keyword_matches = self.keyword_match(
                query,
                selected_microorganisms
            )

            if (
                keyword_matches
                and self.is_biological_question(
                    query
                )
            ):

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

    # =====================================================
    # BIOLOGICAL / BACDIVE RELEVANCE CHECK
    # =====================================================
    def is_biological_question(
        self,
        query
    ):
        q = str(query).lower()

        terms = [
            "fermentation",
            "ferment",
            "oxygen",
            "aerobic",
            "anaerobic",
            "microaerobic",
            "facultative",
            "growth",
            "grow",
            "culture",
            "medium",
            "media",
            "temperature",
            "ph",
            "strain",
            "taxonomy",
            "morphology",
            "metabolism",
            "metabolic",
            "physiology",
            "biosafety",
            "pathogenic",
            "industrial",
            "bioprocess",
            "substrate",
            "product",
            "yield",
            "bacdive",
            "evidence",
            "condition",
            "conditions",
            "gram",
            "motility",
            "sporulation",
            "enzyme",
            "carbon source",
            "nitrogen source"
        ]

        return any(
            term in q
            for term in terms
        )