"""AI Chat Engine module.

Implements the AI chat panel backing logic. Interfaces with local Ollama Llama3 model
instances, formats dataset contexts, intercepts query shortcuts, and manages error states.
"""

import json
import requests
import traceback
import pandas as pd

from src.utils.logging_config import get_logger

from src.core.ai_analytics import (
    summarize_df,
    detect_anomalies,
)

from src.core.auto_visualizer import AutoVisualizer


logger = get_logger("ai_chat_engine")


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"
TIMEOUT_SECONDS = 180


def storage_to_df(storage: dict) -> pd.DataFrame:
    """Converts the session storage representation into a pandas DataFrame.

    Args:
        storage: Session state storage dictionary.

    Returns:
        Reconstructed DataFrame matching stored metadata.
    """

    rows = storage.get("df_json", [])
    cols = storage.get("df_columns", [])

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    if cols:
        safe_cols = [c for c in cols if c in df.columns]
        if safe_cols:
            df = df[safe_cols]

    return df


def numeric_columns(df: pd.DataFrame):
    """Identifies all numeric column headers in a DataFrame.

    Args:
        df: Pandas DataFrame.

    Returns:
        List of numeric column header name strings.
    """

    if df.empty:
        return []

    return list(
        df.select_dtypes(
            include="number"
        ).columns
    )


def dataframe_context(df: pd.DataFrame) -> str:
    """Generates a text summary detailing columns, row counts, and sample metrics for prompt injection.

    Args:
        df: Target pandas DataFrame.

    Returns:
        Compact summary description block string.
    """

    if df.empty:
        return "No dataset loaded."

    rows = len(df)
    cols = len(df.columns)

    nums = numeric_columns(df)
    txt = [
        c for c in df.columns
        if c not in nums
    ]

    missing = int(
        df.isna().sum().sum()
    )

    duplicate = int(
        df.duplicated().sum()
    )

    lines = []

    lines.append(
        f"Rows: {rows}"
    )

    lines.append(
        f"Columns: {cols}"
    )

    lines.append(
        f"Numeric Columns ({len(nums)}): "
        + ", ".join(nums[:15])
    )

    lines.append(
        f"Text Columns ({len(txt)}): "
        + ", ".join(txt[:15])
    )

    lines.append(
        f"Missing Values: {missing}"
    )

    lines.append(
        f"Duplicate Rows: {duplicate}"
    )

    # numeric stats
    if nums:

        lines.append(
            "Numeric Insights:"
        )

        for col in nums[:8]:

            try:
                s = pd.to_numeric(
                    df[col],
                    errors="coerce"
                ).dropna()

                if len(s) == 0:
                    continue

                lines.append(
                    f"{col}: "
                    f"min={round(float(s.min()),3)}, "
                    f"max={round(float(s.max()),3)}, "
                    f"mean={round(float(s.mean()),3)}"
                )

            except Exception:
                pass

    return "\n".join(lines)


def split_lines(text: str):
    """Splits raw answer block into lists of stripped non-empty lines.

    Args:
        text: Raw answer string.

    Returns:
        List of non-empty line strings.
    """

    text = text.replace("\r", "")

    raw = text.split("\n")

    lines = []

    for line in raw:

        line = line.strip()

        if line != "":
            lines.append(line)

    if not lines:
        lines = ["No response generated."]

    return lines


def local_tool_router(
    prompt: str,
    storage: dict,
):
    """Intercepts simple queries and runs instant local routines instead of LLM inference.

    Args:
        prompt: Raw user query text.
        storage: State storage container mapping.

    Returns:
        Result dictionary if query was intercepted, otherwise None.
    """

    p = prompt.lower()

    df = storage_to_df(storage)

    # charts
    if any(
        x in p
        for x in [
            "chart",
            "charts",
            "plot",
            "graph",
            "visualize",
            "dashboard graph",
        ]
    ):
        try:
            AutoVisualizer(
                storage
            ).render()

            return {
                "title": "Charts Generated",
                "lines": [
                    "Charts generated successfully.",
                    "Open Visualize tab.",
                ],
            }

        except Exception as e:
            return {
                "title": "Charts Error",
                "lines": [str(e)],
            }

    # instant summary
    if any(
        x in p
        for x in [
            "quick summary",
            "fast summary",
        ]
    ):
        return {
            "title": "Dataset Summary",
            "lines": summarize_df(df),
        }

    # anomalies
    if any(
        x in p
        for x in [
            "quick anomalies",
            "fast anomalies",
        ]
    ):
        return {
            "title": "Anomaly Detection",
            "lines": detect_anomalies(df),
        }

    return None


def build_system_prompt(df: pd.DataFrame):
    """Composes the system prompt incorporating the dataset context.

    Args:
        df: Pandas DataFrame.

    Returns:
        Formulated system prompt string.
    """

    context = dataframe_context(df)

    system = f"""
You are Raw2Ready Industrial AI Copilot.

You are an elite expert in:

- Data Science
- Industrial Analytics
- Bioprocess Engineering
- Fermentation
- Manufacturing
- Mathematics
- Statistics
- Machine Learning
- Process Optimization
- Chemical Engineering
- Automation

Your tasks:

1. Answer any technical question.
2. Explain equations clearly.
3. Generate formulas when asked.
4. Explain symbols/variables.
5. Suggest improvements.
6. Use dataframe context when relevant.
7. If user asks about trends/correlations,
   reason using the dataset.
8. Be practical and professional.
9. Give detailed useful answers.
10. If no dataset relevance, still answer normally.

Current Dataset Context:
{context}
"""

    return system


def ask_ollama(
    user_prompt: str,
    system_prompt: str,
):
    """Executes a chat completion query against Ollama.

    Args:
        user_prompt: Raw user query text.
        system_prompt: Formulated system context string.

    Returns:
        Ollama raw text response.
    """

    payload = {
        "model": OLLAMA_MODEL,
        "prompt":
            system_prompt
            + "\n\nUser Question:\n"
            + user_prompt
            + "\n\nAnswer:",
        "stream": False,
    }

    logger.info(
        "Sending prompt to Ollama..."
    )

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    data = response.json()

    answer = data.get(
        "response",
        ""
    ).strip()

    return answer


def ask_ai(
    prompt: str,
    storage: dict,
):
    """Processes user chat request using local shortcut routing or remote LLM completions.

    Args:
        prompt: Raw user query text.
        storage: Web app session state dictionary.

    Returns:
        Result dictionary containing report title and list of line strings.
    """

    try:

        prompt = str(prompt).strip()

        logger.info(
            "=" * 60
        )
        logger.info(
            f"USER QUESTION: {prompt}"
        )

        # ------------------------------
        # local tool shortcuts
        # ------------------------------
        tool_result = local_tool_router(
            prompt,
            storage,
        )

        if tool_result is not None:

            logger.info(
                "Answered by local tool router."
            )

            return tool_result

        # ------------------------------
        # dataframe
        # ------------------------------
        df = storage_to_df(storage)

        logger.info(
            f"Dataset shape: "
            f"{df.shape}"
        )

        # ------------------------------
        # build prompt
        # ------------------------------
        system_prompt = build_system_prompt(
            df
        )

        logger.info(
            "System prompt built."
        )

        # ------------------------------
        # LLM answer
        # ------------------------------
        answer = ask_ollama(
            prompt,
            system_prompt,
        )

        logger.info(
            "Ollama response received."
        )

        logger.info(
            f"ANSWER:\n{answer}"
        )

        return {
            "title": "AI Copilot",
            "lines": split_lines(answer),
        }

    except requests.exceptions.ConnectionError:

        logger.error(
            "Cannot connect to Ollama."
        )

        return {
            "title": "AI Copilot Error",
            "lines": [
                "Cannot connect to Ollama.",
                "Run: ollama serve",
            ],
        }

    except requests.exceptions.Timeout:

        logger.error(
            "Ollama timeout."
        )

        return {
            "title": "AI Copilot Timeout",
            "lines": [
                "Model took too long to respond."
            ],
        }

    except Exception as e:

        logger.error(
            traceback.format_exc()
        )

        return {
            "title": "AI Copilot Error",
            "lines": [
                str(e)
            ],
        }