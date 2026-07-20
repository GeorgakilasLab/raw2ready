"""Data Analyst Agent.

Analyzes fermentation and bioprocess datasets to identify columns, summarize metrics,
detect oxygen-related trends, and evaluate anomaly levels.
"""
import json
import re
import traceback
import numpy as np
import pandas as pd
import os
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext, ModelSettings
from pydantic_ai.models.ollama import OllamaModel

from pydantic_ai.providers.ollama import OllamaProvider

@dataclass
class DatasetAnalystDeps:
    df: pd.DataFrame

class DataAnalystAgent:
    """Analyzes experimental fermentation datasets.

    Attributes:
        model_name: Name of the LLM.
        temperature: LLM temperature parameter.
        debug: True if debug prints are enabled.
    """
    def __init__(
        self,
        model_name="llama3:latest",
        temperature=0.2,
        debug=True
    ):
        """Initializes the DataAnalystAgent.

        Args:
            model_name: The name of the LLM. Defaults to "llama3:latest".
            temperature: LLM temperature parameter. Defaults to 0.2.
            debug: Whether to print debug information. Defaults to True.
        """
        self.model_name = model_name
        self.temperature = temperature
        self.debug = debug
        print("\n" + "=" * 100)
        print("[DATA ANALYST] INITIALIZING")
        print("=" * 100)
        print(f"MODEL: {model_name}")
        print(f"TEMPERATURE: {temperature}")
        print("[DATA ANALYST] Agent summary enabled")
        
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        provider = OllamaProvider(base_url=base_url)
        model = OllamaModel(model_name=model_name, provider=provider)
        
        self.agent = Agent(
            model=model,
            model_settings=ModelSettings(temperature=temperature)
        )
        
        self.code_agent = Agent(
            model=model,
            deps_type=DatasetAnalystDeps,
            model_settings=ModelSettings(temperature=temperature),
            system_prompt=(
                "You are an expert bioprocess data analyst. Your job is to answer the user's query "
                "by executing Python/pandas expressions or queries on the DataFrame. "
                "You MUST use the `query_dataframe` tool to inspect column metadata, statistics, "
                "or run code on the DataFrame `df`. When asked about summary statistics, correlations, "
                "subsets, or value counts, construct appropriate python expressions and call `query_dataframe`."
            )
        )
        
        # Bind the tool to the code agent
        @self.code_agent.tool
        def query_dataframe(ctx: RunContext[DatasetAnalystDeps], python_expression: str) -> str:
            """Executes a pandas python expression on the dataframe and returns the result as a string.
            
            Args:
                python_expression: A valid Python expression targeting `df`. Example: `df.describe().to_string()`
                                   or `df.corr(numeric_only=True).to_string()` or `df.head().to_string()`.
            """
            df = ctx.deps.df
            try:
                local_vars = {"df": df, "pd": pd, "np": np}
                result = eval(python_expression, {"__builtins__": None, "pd": pd, "np": np}, local_vars)
                return str(result)
            except Exception as e:
                return f"Error executing expression: {e}"
        
        print("[DATA ANALYST] READY")
        print("=" * 100 + "\n")
    def debug_print(self, title, data):
        if not self.debug:
            return
        print("\n" + "=" * 100)
        print(f"[DATA ANALYST DEBUG] {title}")
        print("=" * 100)
        try:
            if isinstance(data, str):
                print(data)
            else:
                print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        except Exception as ex:
            print(str(data))
            print(f"\n[DEBUG PRINT ERROR] {str(ex)}")
        print("=" * 100 + "\n")
    def print_dataframe_preview(self, dataframe, rows=10):
        if not self.debug:
            return
        try:
            print("\n" + "=" * 100)
            print("[DATA ANALYST] DATAFRAME PREVIEW")
            print("=" * 100)
            print(f"ROWS: {len(dataframe)}")
            print(f"COLUMNS: {len(dataframe.columns)}")
            print("\nCOLUMN NAMES:")
            print(list(dataframe.columns))
            print("\nHEAD:")
            print(dataframe.head(rows).to_string())
            print("\nDTYPES:")
            print(dataframe.dtypes.to_string())
            print("=" * 100 + "\n")
        except Exception:
            traceback.print_exc()
    def safe_json(self, data):
        try:
            return json.dumps(data, indent=2, default=str, ensure_ascii=False)
        except Exception:
            return str(data)
    def clean_column_name(self, name):
        return re.sub(r"\s+", " ", str(name)).strip()
    def validate_dataframe(self, dataframe):
        if dataframe is None:
            return False, "No dataframe loaded."
        if not isinstance(dataframe, pd.DataFrame):
            return False, "Input is not a pandas DataFrame."
        if dataframe.empty:
            return False, "Dataframe is empty."
        return True, "Dataframe is valid."
    def detect_process_columns(self, dataframe):
        columns = [self.clean_column_name(c) for c in dataframe.columns]
        detected = {
            "oxygen_columns": [],
            "biomass_columns": [],
            "ph_columns": [],
            "temperature_columns": [],
            "co2_columns": [],
            "fluorescence_columns": [],
            "feed_columns": [],
            "substrate_columns": [],
            "product_columns": [],
            "time_columns": [],
            "well_columns": [],
            "batch_columns": [],
            "condition_columns": []
        }
        for col in columns:
            lower = col.lower()
            compact = re.sub(r"[^a-z0-9]", "", lower)
            oxygen_patterns = [
                "po2",
                "p_o2",
                "do",
                "do%",
                "do %",
                "dissolved oxygen",
                "oxygen",
                "o2",
                "o2 saturation",
                "oxygen saturation"
            ]
            if any(p in lower for p in oxygen_patterns) or compact in ["do", "do2", "po2", "o2"]:
                detected["oxygen_columns"].append(col)
            biomass_patterns = [
                "biomass",
                "od",
                "od600",
                "optical density",
                "cell density",
                "cell count",
                "growth",
                "dry cell weight",
                "dcw"
            ]
            if any(p in lower for p in biomass_patterns):
                detected["biomass_columns"].append(col)
            if lower == "ph" or lower.startswith("ph ") or " ph" in lower:
                detected["ph_columns"].append(col)
            # ASCII-safe temperature detection
            temperature_patterns = [
                "temp",
                "temperature",
                "celsius",
                "degc",
                "degree c",
                "degrees c"
            ]
            if any(p in lower for p in temperature_patterns):
                detected["temperature_columns"].append(col)
            if any(p in lower for p in ["co2", "carbon dioxide", "offgas co"]):
                detected["co2_columns"].append(col)
            if any(p in lower for p in ["fluorescence", "gfp", "rfp", "yfp", "cfp", "luminescence"]):
                detected["fluorescence_columns"].append(col)
            if any(p in lower for p in ["feed", "fedvol", "feed rate", "feeding", "pump"]):
                detected["feed_columns"].append(col)
            if any(p in lower for p in ["glucose", "substrate", "carbon source", "glycerol", "lactose", "sucrose", "acetate"]):
                detected["substrate_columns"].append(col)
            if any(p in lower for p in ["product", "titer", "yield", "protein", "enzyme", "metabolite"]):
                detected["product_columns"].append(col)
            if any(p in lower for p in ["time", "datetime", "timestamp", "hour", "hours", "min", "minute"]):
                detected["time_columns"].append(col)
            if "well" in lower:
                detected["well_columns"].append(col)
            if any(p in lower for p in ["batch", "run", "experiment", "replicate"]):
                detected["batch_columns"].append(col)
            if any(p in lower for p in ["condition", "treatment", "medium", "media", "strain"]):
                detected["condition_columns"].append(col)
        for key in detected:
            detected[key] = list(dict.fromkeys(detected[key]))
        return detected
    def build_numeric_summary(self, dataframe):
        numeric_summary = {}
        numeric_df = dataframe.select_dtypes(include=["number"])
        if numeric_df.empty:
            return numeric_summary
        try:
            desc = numeric_df.describe().to_dict()
            for col, vals in desc.items():
                clean_col = self.clean_column_name(col)
                numeric_summary[clean_col] = {}
                for k, v in vals.items():
                    try:
                        numeric_summary[clean_col][str(k)] = round(float(v), 4)
                    except Exception:
                        numeric_summary[clean_col][str(k)] = str(v)
        except Exception:
            traceback.print_exc()
        return numeric_summary
    def build_missing_summary(self, dataframe):
        try:
            missing_counts = dataframe.isna().sum().to_dict()
            total_rows = len(dataframe)
            return {
                str(k): {
                    "missing_count": int(v),
                    "missing_fraction": round(float(v) / total_rows, 4)
                    if total_rows > 0 else None
                }
                for k, v in missing_counts.items()
            }
        except Exception:
            traceback.print_exc()
            return {}
    def oxygen_analysis(self, dataframe, detected_columns):
        oxygen_results = {}
        for col in detected_columns.get("oxygen_columns", []):
            try:
                series = pd.to_numeric(dataframe[col], errors="coerce").dropna()
                if len(series) == 0:
                    oxygen_results[col] = {
                        "status": "No numeric oxygen data available."
                    }
                    continue
                low_threshold = 20.0
                critical_threshold = 5.0
                low_events = int((series < low_threshold).sum())
                critical_events = int((series < critical_threshold).sum())
                if critical_events > 0:
                    evidence_level = "strong_dataset_signal"
                elif low_events > 0:
                    evidence_level = "possible_dataset_signal"
                else:
                    evidence_level = "no_low_oxygen_signal"
                oxygen_results[col] = {
                    "count": int(len(series)),
                    "mean": round(float(series.mean()), 4),
                    "min": round(float(series.min()), 4),
                    "max": round(float(series.max()), 4),
                    "std": round(float(series.std()), 4),
                    "low_threshold_used": low_threshold,
                    "critical_threshold_used": critical_threshold,
                    "low_oxygen_events": low_events,
                    "critical_oxygen_events": critical_events,
                    "low_oxygen_fraction": round(low_events / len(series), 4),
                    "critical_oxygen_fraction": round(critical_events / len(series), 4),
                    "dataset_signal_for_low_oxygen": evidence_level,
                    "interpretation": (
                        "Dataset contains values below the critical oxygen threshold."
                        if critical_events > 0
                        else (
                            "Dataset contains values below the low oxygen threshold."
                            if low_events > 0
                            else "No values below the configured low oxygen threshold were detected."
                        )
                    )
                }
            except Exception:
                traceback.print_exc()
        return oxygen_results
    def detect_anomalies(self, dataframe):
        anomalies = []
        numeric_df = dataframe.select_dtypes(include=["number"])
        for col in numeric_df.columns:
            try:
                series = pd.to_numeric(numeric_df[col], errors="coerce").dropna()
                if len(series) < 5:
                    continue
                mean = series.mean()
                std = series.std()
                if std == 0 or pd.isna(std):
                    continue
                z_scores = np.abs((series - mean) / std)
                outliers = series[z_scores > 3]
                if len(outliers) > 0:
                    anomalies.append({
                        "column": self.clean_column_name(col),
                        "method": "z_score_greater_than_3",
                        "outlier_count": int(len(outliers)),
                        "outlier_fraction": round(float(len(outliers)) / len(series), 4),
                        "mean": round(float(mean), 4),
                        "std": round(float(std), 4),
                        "max_outlier": round(float(outliers.max()), 4),
                        "min_outlier": round(float(outliers.min()), 4)
                    })
            except Exception:
                traceback.print_exc()
        return anomalies
    def detect_wells(self, dataframe, detected_columns):
        try:
            well_cols = detected_columns.get("well_columns", [])
            if not well_cols:
                return []
            return [
                str(x)
                for x in dataframe[well_cols[0]].dropna().unique().tolist()
            ]
        except Exception:
            traceback.print_exc()
            return []
    def build_confidence(self, summary, oxygen_results, anomalies):
        if not oxygen_results:
            oxygen_confidence = "INSUFFICIENT_DATA"
        elif any(
            x.get("critical_oxygen_events", 0) > 0
            for x in oxygen_results.values()
            if isinstance(x, dict)
        ):
            oxygen_confidence = "MEDIUM_DATASET_SIGNAL"
        elif any(
            x.get("low_oxygen_events", 0) > 0
            for x in oxygen_results.values()
            if isinstance(x, dict)
        ):
            oxygen_confidence = "LOW_DATASET_SIGNAL"
        else:
            oxygen_confidence = "NO_DATASET_SIGNAL"
        total_missing = sum(
            item.get("missing_count", 0)
            for item in summary.get("missing_values", {}).values()
            if isinstance(item, dict)
        )
        if total_missing == 0:
            dataset_quality = "HIGH"
        elif total_missing < summary.get("rows", 0):
            dataset_quality = "MEDIUM"
        else:
            dataset_quality = "LOW"
        sensor_reliability = (
            "LOW"
            if len(anomalies) > 10
            else "MEDIUM"
            if len(anomalies) > 0
            else "NOT_FLAGGED"
        )
        return {
            "oxygen_limitation": oxygen_confidence,
            "sensor_reliability": sensor_reliability,
            "dataset_quality": dataset_quality
        }
    def build_agent_summary(self, structured_data):
        summary = structured_data.get("summary", {})
        detected_columns = structured_data.get("detected_columns", {})
        oxygen_results = structured_data.get("oxygen_analysis", {})
        anomalies = structured_data.get("anomalies", [])
        confidence = structured_data.get("confidence", {})
        text = (
            f"The dataset contains {summary.get('rows', 0)} rows and "
            f"{summary.get('column_count', 0)} columns. "
        )
        oxygen_cols = detected_columns.get("oxygen_columns", [])
        biomass_cols = detected_columns.get("biomass_columns", [])
        time_cols = detected_columns.get("time_columns", [])
        if oxygen_cols:
            text += f"Oxygen-related columns detected: {', '.join(oxygen_cols)}. "
        else:
            text += "No oxygen-related columns were detected. "
        if biomass_cols:
            text += f"Biomass/growth-related columns detected: {', '.join(biomass_cols)}. "
        if time_cols:
            text += f"Time-related columns detected: {', '.join(time_cols)}. "
        for col, result in oxygen_results.items():
            if not isinstance(result, dict):
                continue
            text += (
                f"For oxygen column '{col}', minimum value was {result.get('min')}, "
                f"with {result.get('low_oxygen_events', 0)} low-oxygen events and "
                f"{result.get('critical_oxygen_events', 0)} critical oxygen events. "
            )
        text += (
            f"Detected anomaly groups: {len(anomalies)}. "
            f"Dataset quality confidence: {confidence.get('dataset_quality', 'unknown')}. "
            f"Oxygen limitation confidence from dataset alone: "
            f"{confidence.get('oxygen_limitation', 'unknown')}. "
            "Any oxygen-limitation conclusion should be treated as dataset-level evidence only."
        )
        return text
    def build_prompt(self, query, structured_data):
        return f"""
You are a fermentation data analyst in a collaborative industrial biotechnology multi-agent system.
Your task is to interpret ONLY the dataset-derived evidence below.
USER QUESTION:
{query}
DATASET-DERIVED STRUCTURED ANALYSIS:
{self.safe_json(structured_data)}
STRICT RULES:
1. Use ONLY the provided dataset-derived structured analysis.
2. Do NOT invent measurements.
3. Do NOT invent biological traits.
4. Do NOT infer oxygen limitation unless the oxygen data support a low-oxygen signal.
5. Even if low oxygen values exist, describe them as dataset-level evidence unless supporting process context exists.
6. Do NOT infer industrial scale-up suitability unless explicit scale-up data exist.
7. Do NOT invent fermentation performance claims.
8. Clearly separate measured findings, possible interpretations, missing evidence, and uncertainty.
9. If evidence is insufficient, say "Insufficient evidence available."
10. Keep the answer flexible and directly relevant to the user query.
Do not output raw JSON.
Keep the assessment concise but scientifically useful.
"""
    def run(self, query, dataframe=None, use_llm=True):
        print("\n" + "=" * 100)
        print("[DATA ANALYST] RUN STARTED")
        print("=" * 100)
        print(f"QUERY:\n{query}")
        valid, message = self.validate_dataframe(dataframe)
        if not valid:
            response = {
                "agent_name": "DATA_ANALYST",
                "agent_status": "skipped",
                "reason": message,
                "structured_data": {},
                "summary": {
                    "dataset_available": False,
                    "reason": message
                },
                "agent_summary": (
                    "No dataset analysis was performed because no valid "
                    f"dataframe was available. Reason: {message}"
                ),
                "assessment": "No dataset-derived evidence available."
            }
            self.debug_print("DATA ANALYST SKIPPED", response)
            return response
        dataframe = dataframe.copy()
        self.print_dataframe_preview(dataframe)
        dataframe.columns = [
            self.clean_column_name(c)
            for c in dataframe.columns
        ]
        summary = {
            "rows": int(len(dataframe)),
            "columns": [str(c) for c in dataframe.columns],
            "column_count": int(len(dataframe.columns)),
            "missing_values": self.build_missing_summary(dataframe)
        }
        detected_columns = self.detect_process_columns(dataframe)
        self.debug_print("DETECTED PROCESS COLUMNS", detected_columns)
        numeric_summary = self.build_numeric_summary(dataframe)
        oxygen_results = self.oxygen_analysis(dataframe, detected_columns)
        self.debug_print("OXYGEN ANALYSIS", oxygen_results)
        anomalies = self.detect_anomalies(dataframe)
        self.debug_print("ANOMALIES", anomalies)
        detected_wells = self.detect_wells(dataframe, detected_columns)
        structured_data = {
            "summary": summary,
            "detected_columns": detected_columns,
            "numeric_summary": numeric_summary,
            "oxygen_analysis": oxygen_results,
            "anomalies": anomalies,
            "detected_wells": detected_wells
        }
        structured_data["confidence"] = self.build_confidence(
            summary,
            oxygen_results,
            anomalies
        )
        agent_summary = self.build_agent_summary(structured_data)
        structured_data["agent_summary"] = agent_summary
        self.debug_print("STRUCTURED DATA", structured_data)
        if use_llm:
            try:
                print("[DATA ANALYST] RUNNING CODE AGENT...")
                code_query = (
                    f"The user wants to know: '{query}'.\n"
                    "Please query the dataframe using your query_dataframe tool. "
                    "You can inspect summary statistics, calculate correlations, view column names, "
                    "or isolate rows/columns to answer the user's query. "
                    "Write a clear explanation of what you found."
                )
                code_result = self.code_agent.run_sync(
                    code_query,
                    deps=DatasetAnalystDeps(df=dataframe)
                )
                pandas_analysis = code_result.data
                print("[DATA ANALYST] CODE AGENT SUCCESS")
            except Exception as e:
                print(f"[DATA ANALYST WARNING] Code agent failed: {e}")
                pandas_analysis = "Code execution analysis failed or skipped."

            structured_data["pandas_agent_analysis"] = pandas_analysis
            prompt = self.build_prompt(query, structured_data)
            self.debug_print("DATA ANALYST PROMPT", prompt)
            try:
                print("[DATA ANALYST] INVOKING OLLAMA...")
                result = self.agent.run_sync(prompt)
                assessment = result.data
                status = "success"
                print("[DATA ANALYST] OLLAMA SUCCESS")
            except Exception as ex:
                traceback.print_exc()
                assessment = (
                    "Data Analyst LLM generation failed. "
                    "Using deterministic agent summary.\n\n"
                    + agent_summary
                )
                status = "failed"
                print("[DATA ANALYST ERROR]")
                print(str(ex))
        else:
            assessment = agent_summary
            status = "success"
        response = {
            "agent_name": "DATA_ANALYST",
            "agent_status": status,
            "structured_data": structured_data,
            "summary": {
                "dataset_available": True,
                "rows": summary.get("rows"),
                "columns": summary.get("column_count"),
                "oxygen_columns": detected_columns.get("oxygen_columns", []),
                "biomass_columns": detected_columns.get("biomass_columns", []),
                "time_columns": detected_columns.get("time_columns", []),
                "anomaly_groups": len(anomalies),
                "confidence": structured_data.get("confidence", {})
            },
            "agent_summary": agent_summary,
            "assessment": assessment
        }
        self.debug_print("FINAL DATA ANALYST RESPONSE", response)
        print("\n" + "=" * 100)
        print("[DATA ANALYST] RUN COMPLETE")
        print("=" * 100 + "\n")
        return response