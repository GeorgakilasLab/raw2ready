"""Parse module.

Provides parser functions for different bioreactor and gas analyzer formats.
"""

# --------------------------------------------------
# PACKAGES
# --------------------------------------------------
import pandas as pd
import numpy as np
import re
import json
import os

# ==========================================================
# GAS ANALYZER (TXT / CSV / TSV)
# ==========================================================
def parse_gas_analyzer(
    file_path: str,
    experiment_start_date: str,
    target_channel: int,
    reference_channel: int,
) -> pd.DataFrame:
    """Parses raw gas analyzer text/CSV/TSV files.

    Args:
        file_path: Path to the raw gas analyzer file.
        experiment_start_date: Start date of the experiment in YYYY-MM-DD format.
        target_channel: Channel ID for the target channel.
        reference_channel: Channel ID for the reference channel.

    Returns:
        A pandas DataFrame containing the parsed and aligned gas analyzer data.

    Raises:
        ValueError: If the file is empty or target/reference channels are not found.
    """

    cleaned_file_rows = []

    with open(file_path, "r") as fh:
        for line in fh:

            line = line.rstrip("\n")

            if line == "" or "Innova" in line:
                continue

            split_line = [x.strip() for x in line.split(",")]
            cleaned_file_rows.append(split_line)

    if not cleaned_file_rows:
        raise ValueError("Empty gas analyzer file")

    # ------------------------------------------------------
    # FIND CHANNELS
    # ------------------------------------------------------
    target_idx = []
    ref_idx = []

    for col_idx in range(len(cleaned_file_rows[0])):

        if str(target_channel) == cleaned_file_rows[0][col_idx]:
            target_idx.append(col_idx)

        elif str(reference_channel) == cleaned_file_rows[0][col_idx]:
            ref_idx.append(col_idx)

    if not target_idx or not ref_idx:
        raise ValueError("Target or reference channel not found")

    # ------------------------------------------------------
    # HEADERS
    # ------------------------------------------------------
    target_header = [
        f"target channel - {x}"
        for x in cleaned_file_rows[1][target_idx[0]:target_idx[-1] + 1]
    ]

    ref_header = [
        f"reference channel - {x}"
        for x in cleaned_file_rows[1][ref_idx[0]:ref_idx[-1] + 1]
    ]

    # ------------------------------------------------------
    # DATA
    # ------------------------------------------------------
    rows = []

    for i in range(2, len(cleaned_file_rows)):
        rows.append(
            [cleaned_file_rows[i][0]]
            + cleaned_file_rows[i][target_idx[0]:target_idx[-1] + 1]
            + cleaned_file_rows[i][ref_idx[0]:ref_idx[-1] + 1]
        )

    df = pd.DataFrame(
        rows,
        columns=["time"] + target_header + ref_header
    )

    data_cols = target_header + ref_header

    df[data_cols] = df[data_cols].replace(
        ["", " ", "NA", "N/A", "nan", "NULL"],
        np.nan
    )

    df = df.dropna(subset=data_cols, how="all")
    df[data_cols] = df[data_cols].apply(pd.to_numeric, errors="coerce")

    # ------------------------------------------------------
    # TIME
    # ------------------------------------------------------
    df["time_dt"] = pd.to_datetime(df["time"], format="%H:%M:%S")

    rollover = df["time_dt"].diff().dt.total_seconds() < 0
    df["day"] = rollover.cumsum()

    base_date = pd.Timestamp(experiment_start_date)

    df["datetime"] = base_date \
        + pd.to_timedelta(df["day"], unit="D") \
        + pd.to_timedelta(
            df["time_dt"].dt.hour * 3600 +
            df["time_dt"].dt.minute * 60 +
            df["time_dt"].dt.second,
            unit="s"
        )

    # ------------------------------------------------------
    # MERGE
    # ------------------------------------------------------
    target_df = df.loc[
        df[target_header].notna().any(axis=1),
        ["datetime"] + target_header
    ].sort_values("datetime")

    ref_df = df.loc[
        df[ref_header].notna().any(axis=1),
        ["datetime"] + ref_header
    ].sort_values("datetime")

    merged_df = pd.merge_asof(
        target_df,
        ref_df,
        on="datetime",
        direction="nearest"
    )

    return merged_df


# ==========================================================
# BIOLECTOR XT (XLS/XLSX)
# ==========================================================
def parse_biolector_xt(raw_path):
    """Parses BioLector XT Excel raw data sheets and builds a long-format DataFrame.

    Args:
        raw_path: Path to the raw Excel spreadsheet.

    Returns:
        A formatted, clean, long-format pandas DataFrame containing aligned data
        across all wells and recorded variables.

    Raises:
        ValueError: If no sheets are found or the table header/time columns
            cannot be located.
    """

    import re
    import pandas as pd
    import numpy as np

    print("DEBUG equipment: BioLectorXT")

    # ==========================================================
    # LOAD XLSX
    # ==========================================================
    xls = pd.ExcelFile(
        raw_path,
        engine="openpyxl"
    )

    # ==========================================================
    # HELPERS
    # ==========================================================
    def normalize(c):

        return (
            str(c)
            .strip()
            .replace("\n", " ")
        )

    def clean_col(c):

        return (
            normalize(c)
            .lower()
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
            .replace("[", "")
            .replace("]", "")
            .replace("(", "")
            .replace(")", "")
        )

    def get_well(col):

        m = re.search(
            r'([A-H][0-9]{2})',
            str(col),
            re.I
        )

        if m:
            return m.group(1).upper()

        return None

    # ==========================================================
    # LOAD METADATA
    # ==========================================================
    metadata_sheet = None

    for s in xls.sheet_names:

        if "meta" in s.lower():

            metadata_sheet = s
            break

    protocol_name = "Unknown_Protocol"
    experiment_start = None

    if metadata_sheet:

        print(f"\n===== METADATA SHEET =====")
        print(metadata_sheet)

        metadata_df = pd.read_excel(
            xls,
            sheet_name=metadata_sheet,
            header=None
        )

        metadata_df = metadata_df.fillna("")

        for r in range(len(metadata_df)):

            row_vals = [
                str(v).strip()
                for v in metadata_df.iloc[r].tolist()
            ]

            # --------------------------------------------------
            # PROTOCOL NAME
            # --------------------------------------------------
            for c_idx, cell in enumerate(row_vals):

                cell_low = cell.lower()

                if cell_low in [
                    "protocol name",
                    "protocolname"
                ]:

                    if c_idx + 1 < len(row_vals):

                        candidate = str(
                            row_vals[c_idx + 1]
                        ).strip()

                        if (
                            candidate
                            and candidate.lower() != "nan"
                        ):

                            protocol_name = candidate

                # --------------------------------------------------
                # REAL DATETIME
                # --------------------------------------------------
                if cell_low == "datetime":

                    if c_idx + 1 < len(row_vals):

                        dt_candidate = str(
                            row_vals[c_idx + 1]
                        ).strip()

                        try:

                            experiment_start = pd.to_datetime(
                                dt_candidate
                            )

                        except Exception:
                            pass

    print("\n===== DETECTED PROTOCOL =====")
    print(protocol_name)

    print("\n===== REAL START DATETIME =====")
    print(experiment_start)

    # ==========================================================
    # FIND REAL HEADER ROW
    # ==========================================================
    def load_real_table(sheet_name):

        raw = pd.read_excel(
            xls,
            sheet_name=sheet_name,
            header=None
        )

        header_row = None

        for i in range(len(raw)):

            vals = (
                raw.iloc[i]
                .astype(str)
                .str.lower()
                .tolist()
            )

            joined = " ".join(vals)

            if (
                "time" in joined
                and (
                    "a01" in joined
                    or "cycle" in joined
                )
            ):

                header_row = i
                break

        if header_row is None:

            raise ValueError(
                f"Could not find table header in sheet: {sheet_name}"
            )

        df = pd.read_excel(
            xls,
            sheet_name=sheet_name,
            header=header_row
        )

        df.columns = [
            normalize(c)
            for c in df.columns
        ]

        return df

    # ==========================================================
    # FIND SHEETS
    # ==========================================================
    volume_sheet = None
    process_sheet = None
    channel_sheets = []

    for s in xls.sheet_names:

        sl = s.lower()

        if "volume" in sl:

            volume_sheet = s

        elif "process" in sl:

            process_sheet = s

        elif "channel" in sl:

            channel_sheets.append(s)

    print("\n===== DETECTED SHEETS =====")
    print("Process :", process_sheet)
    print("Volume  :", volume_sheet)
    print("Channels:", channel_sheets)

    # ==========================================================
    # LOAD SHEETS
    # ==========================================================
    dfs = []

    if process_sheet:

        process_df = load_real_table(process_sheet)
        dfs.append(process_df)

    if volume_sheet:

        volume_df = load_real_table(volume_sheet)
        dfs.append(volume_df)

    for sh in channel_sheets:

        ch_df = load_real_table(sh)
        dfs.append(ch_df)

    if not dfs:

        raise ValueError(
            "No BioLectorXT sheets found."
        )

    # ==========================================================
    # MERGE
    # ==========================================================
    master_df = pd.concat(
        dfs,
        axis=1
    )

    master_df = master_df.loc[
        :,
        ~master_df.columns.duplicated()
    ]

    print("\n===== MASTER DF SHAPE =====")
    print(master_df.shape)

    # ==========================================================
    # TIME COLUMN
    # ==========================================================
    time_col = None

    for c in master_df.columns:

        cl = clean_col(c)

        if (
            cl == "timeh"
            or cl == "time"
            or "timeh" in cl
        ):

            time_col = c
            break

    if time_col is None:

        raise ValueError(
            "Could not find time column."
        )

    print("\n===== TIME COLUMN =====")
    print(time_col)

    master_df["time [h]"] = pd.to_numeric(
        master_df[time_col],
        errors="coerce"
    )

    # ==========================================================
    # REAL DATETIME GENERATION
    # ==========================================================
    if experiment_start is not None:

        master_df["datetime"] = (

            experiment_start +

            pd.to_timedelta(
                master_df["time [h]"],
                unit="h"
            )
        )

    else:

        print(
            "\nWARNING: No real datetime found. Using current timestamp."
        )

        fallback_start = pd.Timestamp.now()

        master_df["datetime"] = (

            fallback_start +

            pd.to_timedelta(
                master_df["time [h]"],
                unit="h"
            )
        )

    # ==========================================================
    # DETECT WELLS
    # ==========================================================
    wells = sorted({

        get_well(c)

        for c in master_df.columns

        if get_well(c)

    })

    print("\n===== DETECTED WELLS =====")
    print(wells)

    # ==========================================================
    # VARIABLE DETECTOR
    # ==========================================================
    def detect_variable(col):

        c = clean_col(col)

        # ------------------------------------------------------
        # IGNORE
        # ------------------------------------------------------
        ignore_patterns = [

            "cycle",
            "comment",
            "user",
            "plate",
            "filename",
            "status",
            "action",
            "creationtime",
            "modifiedtime"
        ]

        for patt in ignore_patterns:

            if patt in c:
                return None

        # ------------------------------------------------------
        # GLOBALS
        # ------------------------------------------------------
        if (
            "temp" in c
            and not c.startswith("ch")
        ):
            return "Temp [C]"

        if (
            "co2" in c
            and not c.startswith("ch")
        ):
            return "CO2 [%]"

        if (
            (
                "rpm" in c
                or "shaker" in c
            )
            and not c.startswith("ch")
        ):
            return "Shaker [rpm]"

        # ------------------------------------------------------
        # VOLUMES
        # ------------------------------------------------------
        if "totalwellvolume" in c:
            return "TotalWellVolume [uL]"

        if "fedvolresa" in c:
            return "FedVol_ResA [uL]"

        if "fedvolresb" in c:
            return "FedVol_ResB [uL]"

        if "fedvolrobo" in c:
            return "FedVol_Robo [uL]"

        # ------------------------------------------------------
        # CHANNELS
        # ------------------------------------------------------
        channel_map = {

            "ch1": "pH",
            "ch2": "pO2",
            "ch3": "Biomass_1",
            "ch4": "Biomass_3",
            "ch5": "Biomass_6",
            "ch6": "Fluoresceine_5"
        }

        for ch, name in channel_map.items():

            if c.startswith(ch):

                if "cal" in c:
                    return f"{name} calibrated [unit]"

                if "raw" in c:
                    return f"{name} raw [unit]"

        return None

    # ==========================================================
    # BUILD LONG FORMAT
    # ==========================================================
    rows = []

    for _, row in master_df.iterrows():

        current_time = row["time [h]"]
        current_datetime = row["datetime"]

        for col in master_df.columns:

            if col in [
                "time [h]",
                "datetime"
            ]:
                continue

            variable = detect_variable(col)

            if variable is None:
                continue

            value = row[col]

            if pd.isna(value):
                continue

            well = get_well(col)

            # --------------------------------------------------
            # GLOBAL VALUES
            # --------------------------------------------------
            if well is None:

                for w in wells:

                    rows.append({

                        "datetime":
                            current_datetime,

                        "time [h]":
                            current_time,

                        "protocol name":
                            protocol_name,

                        "well":
                            w,

                        variable:
                            value
                    })

            # --------------------------------------------------
            # WELL VALUES
            # --------------------------------------------------
            else:

                rows.append({

                    "datetime":
                        current_datetime,

                    "time [h]":
                        current_time,

                    "protocol name":
                        protocol_name,

                    "well":
                        well,

                    variable:
                        value
                })

    if not rows:

        raise ValueError(
            "No BioLectorXT values extracted."
        )

    # ==========================================================
    # CREATE DF
    # ==========================================================
    long_df = pd.DataFrame(rows)

    # ==========================================================
    # GROUP
    # ==========================================================
    final_df = (
        long_df
        .groupby(
            [
                "datetime",
                "time [h]",
                "protocol name",
                "well"
            ],
            dropna=False
        )
        .first()
        .reset_index()
    )

    # ==========================================================
    # ORDER
    # ==========================================================
    ordered_cols = [

        "datetime",
        "time [h]",
        "protocol name",
        "well",

        "Temp [C]",
        "CO2 [%]",
        "Shaker [rpm]",

        "pH calibrated [unit]",
        "pH raw [unit]",

        "pO2 calibrated [unit]",
        "pO2 raw [unit]",

        "Biomass_1 calibrated [unit]",
        "Biomass_1 raw [unit]",

        "Biomass_3 calibrated [unit]",
        "Biomass_3 raw [unit]",

        "Biomass_6 calibrated [unit]",
        "Biomass_6 raw [unit]",

        "Fluoresceine_5 calibrated [unit]",
        "Fluoresceine_5 raw [unit]",

        "TotalWellVolume [uL]",
        "FedVol_ResA [uL]",
        "FedVol_ResB [uL]",
        "FedVol_Robo [uL]"
    ]

    for c in ordered_cols:

        if c not in final_df.columns:
            final_df[c] = np.nan

    final_df = final_df[ordered_cols]

    # ==========================================================
    # NUMERIC CONVERSION
    # ==========================================================
    numeric_cols = [

        c for c in final_df.columns

        if c not in [
            "datetime",
            "protocol name",
            "well"
        ]
    ]

    for col in numeric_cols:

        final_df[col] = pd.to_numeric(
            final_df[col],
            errors="coerce"
        )

    # ==========================================================
    # SMART GLOBAL FILL
    # ==========================================================
    safe_fill_cols = [

        "Temp [C]",
        "Shaker [rpm]",
        "TotalWellVolume [uL]",
        "FedVol_ResA [uL]",
        "FedVol_ResB [uL]",
        "FedVol_Robo [uL]"
    ]

    for col in safe_fill_cols:

        if col in final_df.columns:

            final_df[col] = (

                final_df[col]
                .ffill()
                .bfill()
            )

    # ==========================================================
    # SORT
    # ==========================================================
    final_df = final_df.sort_values(

        by=[
            "datetime",
            "well"
        ]

    ).reset_index(drop=True)

    # ==========================================================
    # DEBUG FINAL
    # ==========================================================
    print("\n===== BIOLECTOR XT FINAL =====")
    print(f"Shape: {final_df.shape}")

    print("\nColumns:")
    print(final_df.columns.tolist())

    print("\nHead:")
    print(final_df.head())

    # ==========================================================
    # RETURN
    # ==========================================================
    return final_df



# ==========================================================
# OTHER (CSV / TSV / SIMPLE FILES)
# ==========================================================
def parse_other(file_path: str, delimiter: str = "Comma") -> pd.DataFrame:
    """Parses simple structured files (e.g., CSV, TSV, TXT, Excel).

    Args:
        file_path: Path to the input data file.
        delimiter: Delimiter description ("Comma", "Tab", or "Space"). Defaults
            to "Comma".

    Returns:
        A cleaned pandas DataFrame of the file contents.

    Raises:
        ValueError: If file format is unsupported or file reading fails.
    """

    delimiter_map = {
        "Comma": ",",
        "Tab": "\t",
        "Space": " "
    }

    sep = delimiter_map.get(delimiter, ",")

    # -----------------------------
    # TRY NORMAL READ
    # -----------------------------
    try:
        if file_path.endswith((".csv", ".txt", ".tsv")):
            df = pd.read_csv(
                file_path,
                sep=sep,
                encoding="latin1",
                engine="python"
            )

        elif file_path.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file_path)

        else:
            raise ValueError("Unsupported file type")

    except Exception as e:
        raise ValueError(f"Failed to read file: {e}")

    # -----------------------------
    # CLEAN
    # -----------------------------
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")

    print("\n===== SIMPLE FILE COLUMNS =====")
    print(df.columns.tolist())

    return df

# --------------------------------------------------
# MAIN PARSE ENTRY (for GUI)
# --------------------------------------------------
def main(config_file: str):
    """Main parsing runner routing based on configuration.

    Args:
        config_file: Path to the JSON configuration file containing parser settings.

    Returns:
        A pandas DataFrame of the parsed data.
    """

    with open(config_file, "r") as f:
        config = json.load(f)

    equipment = config.get("equipment")

    if equipment == "Gas Analyzer":
        params = config["parse parameters"]

        return parse_gas_analyzer(
            file_path=params["gas analyzer input file"],
            experiment_start_date=config.get("experiment start date", "2018-05-16"),
            target_channel=params.get("gas analyzer target channel", 1),
            reference_channel=params.get("gas analyzer reference channel", 2),
        )

    elif equipment == "BioLectorXT":
        params = config["parse parameters"]

        return parse_biolector_xt(
            file_path=params["input file"]
        )

    else:
        # OTHER (CSV / TXT)
        params = config["parse parameters"]

        return parse_other(
            file_path=params["sensor input files"],
            delimiter="Comma"
        )


# --------------------------------------------------
# GUI CALL
# --------------------------------------------------
def run_parse(config_file: str):
    """Wraps main function call to execute the parser.

    Args:
        config_file: Path to the JSON configuration file.

    Returns:
        A pandas DataFrame of the parsed data.
    """
    return main(config_file)