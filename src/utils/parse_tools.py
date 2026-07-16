"""Data Parsing Utilities module.

Provides functions to parse diverse data formats (CSV, TSV, YAML, JSON, Excel, ODS)
locally or via file buffers uploaded from the GUI, along with data cleaning helpers.
"""

import io
import json
import yaml
import pandas as pd
from pathlib import Path
from src.utils.logging_config import get_logger


logger = get_logger('parse')


#-----------------------
# FUNCTIONS
#-----------------------
def parse_file(file_to_parse, 
               sep_ =None,
               header_idx_ = 0, encoding_fmt = "utf-8", 
               sheetname = None, xls_engine_ = None
               ):
    """Parses a local file based on its file extension.

    Args:
        file_to_parse: Path of the file to parse.
        sep_: Column delimiter character. Defaults to None.
        header_idx_: Row index to use as columns. Defaults to 0.
        encoding_fmt: Text encoding format. Defaults to "utf-8".
        sheetname: Active Excel sheet identifier. Defaults to None.
        xls_engine_: Engine choice for reading spreadsheet format. Defaults to None.

    Returns:
        Dict representation for YAML/JSON, or pandas DataFrame for table files.
    """
    #---------------------
    # GET FILE EXTENSION from file
    file_ext = Path(file_to_parse).suffix.lower()


    #---------------------
    # Match file_ext to parser
    if file_ext == '.json':
        
        parsed_file = parse_json(file_to_parse)


    elif file_ext == '.yaml':
        
        parsed_file = parse_yaml(file_to_parse)

    
    elif file_ext == '.csv':

        if sep_ is None:
            print('User has not defined separator. Using default separator: comma ')
            sep_ = ','
            
        parsed_file = parse_csv(file_to_parse, sep_= sep_, header_idx=header_idx_, encoding_fmt = encoding_fmt)


    elif file_ext == '.tsv':

        if sep_ is None:
            print('User has not defined separator. Using default separator: tab ')
            sep_ = '\t'

        parsed_file = parse_tsv(file_to_parse, sep_= sep_, header_idx=header_idx_, encoding_fmt = encoding_fmt)         


    elif file_ext in ['.xlsx', '.xls']:
        
        if sheetname is None:
            sheetname = 0
            print('User has not defined sheet. Using default sheetname: 0 ')

        if xls_engine_ is None:
            xls_engine_ = "calamine"
            print('User has not defined xls_engine. Using default xls engine: calamine ')

        parsed_file = parse_xls(file_to_parse, sheet_name=sheetname, header_idx=header_idx_, xls_engine_=xls_engine_)


    elif file_ext in ['.ods', '.odf', '.odt']:
        
        if sheetname is None:
            sheetname = 0
            print('User has not defined sheet. Using default sheetname: 0 ')

        if xls_engine_ is None:
            xls_engine_ = "calamine"
            print('User has not defined xls_engine. Using default xls engine: calamine ')

        parsed_file = parse_ods(file_to_parse, sheet_name_=sheetname, header_idx=header_idx_, xls_engine_=xls_engine_)


    else:

        raise ValueError(f"Unsupported file format: {file_ext}")
    

    return parsed_file



def parse_file_gui(filepath,
                    file_to_parse,     
                    sep_ =None,
                    header_idx_ = 0, 
                    skip_rows = None,
                    encoding_fmt = "utf-8", 
                    sheetname = None, xls_engine_ = None
                    ):
    """Parses a file payload uploaded in-memory from the web GUI.

    Args:
        filepath: Original name/path of the uploaded file.
        file_to_parse: In-memory file content bytes.
        sep_: Column delimiter character. Defaults to None.
        header_idx_: Row index to use as columns. Defaults to 0.
        skip_rows: Number of lines to skip. Defaults to None.
        encoding_fmt: Text encoding format. Defaults to "utf-8".
        sheetname: Active Excel sheet identifier. Defaults to None.
        xls_engine_: Engine choice for reading spreadsheet format. Defaults to None.

    Returns:
        Dict representation for YAML/JSON, or pandas DataFrame for table files.
    """
    #---------------------
    # GET FILE EXTENSION from file
    file_ext = Path(filepath).suffix.lower()


    #---------------------
    # Match file_ext to parser
    if file_ext == '.json':
        
        parsed_file = parse_json(io.BytesIO(file_to_parse))


    elif file_ext == '.yaml':
        
        parsed_file = parse_yaml(io.BytesIO(file_to_parse))

    
    elif file_ext == '.csv':

        if sep_ is None:
            print('User has not defined separator. Using default separator: comma ')
            sep_ = ','
            
        parsed_file = parse_csv(io.BytesIO(file_to_parse), sep_= sep_, header_idx=header_idx_, encoding_fmt = encoding_fmt)


    elif file_ext == '.tsv':

        if sep_ is None:
            print('User has not defined separator. Using default separator: tab ')
            sep_ = '\t'

        parsed_file = parse_tsv(io.BytesIO(file_to_parse), sep_= sep_, header_idx=header_idx_, encoding_fmt = encoding_fmt)         


    elif file_ext in ['.xlsx', '.xls']:
        
        if sheetname is None:
            sheetname = 0
            print('User has not defined sheet. Using default sheetname: 0 ')

        if xls_engine_ is None:
            xls_engine_ = "openpyxl"#"calamine"
            print('User has not defined xls_engine. Using openpyxl ')

        parsed_file = parse_xls(io.BytesIO(file_to_parse), sheet_name_=sheetname, header_idx=header_idx_, 
                                xls_engine_=xls_engine_
                                )


    elif file_ext in ['.ods', '.odf', '.odt']:
        
        if sheetname is None:
            sheetname = 0
            print('User has not defined sheet. Using default sheetname: 0 ')

        #if xls_engine_ is None:
        #    xls_engine_ = "calamine"
        #    print('User has not defined xls_engine. Using default xls engine: calamine ')

        parsed_file = parse_ods(io.BytesIO(file_to_parse), sheet_name_=sheetname, header_idx=header_idx_, 
                                #xls_engine_=xls_engine_
                                )


    else:

        raise ValueError(f"Unsupported file format: {file_ext}")
    

    return parsed_file


#------------------------
# PARSE file types
def parse_json(json_file):
    """Loads a JSON-formatted file or stream buffer.

    Args:
        json_file: Path string or byte buffer pointing to a JSON file.

    Returns:
        Dictionary/list containing parsed JSON data structure.
    """
    if isinstance(json_file, (str, Path)):
        with open(json_file, "r") as fh:
            json_data = json.load(fh)
    else:
        json_data = json.load(json_file)

    return json_data



def parse_yaml(yaml_file):
    """Loads a YAML-formatted file or stream buffer.

    Args:
        yaml_file: Path string or byte buffer pointing to a YAML file.

    Returns:
        Dictionary containing parsed YAML data structure.
    """
    if isinstance(yaml_file, (str, Path)):
        with open(yaml_file, "r") as fh:
            yaml_data = yaml.safe_load(fh)
    else:
        yaml_data = yaml.safe_load(yaml_file)

    return yaml_data



def parse_csv(csv_file, sep_ = ',', header_idx = 0, encoding_fmt ="utf-8"):
    """Parses a CSV file into a pandas DataFrame.

    Args:
        csv_file: Path string or byte buffer pointing to a CSV file.
        sep_: Delimiter character. Defaults to ','.
        header_idx: Row index to use as columns. Defaults to 0.
        encoding_fmt: Character encoding standard. Defaults to "utf-8".

    Returns:
        DataFrame containing parsed CSV data.
    """
    df = pd.read_csv(csv_file, sep=sep_,header=header_idx, encoding= encoding_fmt)
    
    return df



def parse_tsv(tsv_file, sep_ = '\t', header_idx = 0, encoding_fmt ="utf-8"):
    """Parses a TSV file into a pandas DataFrame.

    Args:
        tsv_file: Path string or byte buffer pointing to a TSV file.
        sep_: Delimiter character. Defaults to '\\t'.
        header_idx: Row index to use as columns. Defaults to 0.
        encoding_fmt: Character encoding standard. Defaults to "utf-8".

    Returns:
        DataFrame containing parsed TSV data.
    """
    
    return parse_csv(tsv_file, sep_ = sep_, header_idx=header_idx, encoding_fmt=encoding_fmt)



def parse_xls(xls_file, sheet_name_ = 0, header_idx = 0, xls_engine_ ="calamine"):
    """Parses an Excel spreadsheet (XLS/XLSX) file into a pandas DataFrame.

    Args:
        xls_file: Path string or byte buffer pointing to an Excel file.
        sheet_name_: Target worksheet index or name. Defaults to 0.
        header_idx: Row index to use as columns. Defaults to 0.
        xls_engine_: Library engine to read Excel. Defaults to "calamine".

    Returns:
        DataFrame containing spreadsheet contents.
    """
    df = pd.read_excel(xls_file,sheet_name=sheet_name_,engine=xls_engine_,header=header_idx, )

    return df



def parse_ods(ods_file, sheet_name_ = 0, header_idx = 0, xls_engine_ ="calamine"):
    """Parses an OpenDocument spreadsheet (ODS) file into a pandas DataFrame.

    Args:
        ods_file: Path string or byte buffer pointing to an ODS file.
        sheet_name_: Target worksheet index or name. Defaults to 0.
        header_idx: Row index to use as columns. Defaults to 0.
        xls_engine_: Library engine to read ODS. Defaults to "calamine".

    Returns:
        DataFrame containing spreadsheet contents.
    """
    df = pd.read_excel(ods_file,sheet_name=sheet_name_,engine=xls_engine_,header=header_idx, )

    return df


#--------------------------
# EXCEL Tools
def get_sheet_names(xls_file, filename, xls_engine = 'openpyxl'):
    """Extracts the list of sheet names from an Excel payload.

    Args:
        xls_file: Byte buffer representing the Excel file contents.
        filename: Original file name string.
        xls_engine: Library engine choice. Defaults to 'openpyxl'.

    Returns:
        List of sheet name strings.
    """
    try:
        
        #excel_file = pd.ExcelFile(xls_file, xls_engine)
        excel_file = pd.ExcelFile( io.BytesIO(xls_file), engine = xls_engine  )
        
        
        return excel_file.sheet_names
        
    except Exception as e:

        print(f"Error reading sheet names: {str(e)}")
        return []




#--------------------------
# CLEAN file
def remove_empty_rows(df):
    """Drops DataFrame rows that consist entirely of null/blank values.

    Args:
        df: Pandas DataFrame to clean.

    Returns:
        A tuple containing:
            - DataFrame: Cleaned DataFrame.
            - Int: Count of removed rows.
            - Int: Count of rows before cleaning.
            - Int: Count of rows after cleaning.
    """
    before = len(df)

    df = df.dropna(how='all')

    after = len(df)

    removed = before - after
    
    return df, removed, before, after



def remove_duplicates(df):
    """Drops duplicate rows from a pandas DataFrame.

    Args:
        df: Pandas DataFrame to clean.

    Returns:
        A tuple containing:
            - DataFrame: Cleaned DataFrame.
            - Int: Count of duplicate rows removed.
            - Int: Count of rows before cleaning.
            - Int: Count of rows after cleaning.
    """
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    removed = before - after

    return df, removed, before, after



def trim_whitespace(df):
    """Trims whitespace padding from all text-containing columns.

    Args:
        df: Pandas DataFrame to clean.

    Returns:
        DataFrame with stripped string values.
    """
    for col in df.columns:

        if df[col].dtype == 'object':

            df[col] = df[col].str.strip() if hasattr(df[col], 'str') else df[col]

    return df



def fill_values(df):
    """Fills empty cell spaces by performing a forward-fill.

    Args:
        df: Pandas DataFrame to clean.

    Returns:
        DataFrame with filled cell values.
    """

    # Replace empty strings / whitespace-only strings with NaN
    df = df.replace(r'^\s*$', pd.NA, regex=True)

    # Forward fill values from previous rows
    df = df.ffill()

    return df




#-----------------------
# CLASSES
#-----------------------
