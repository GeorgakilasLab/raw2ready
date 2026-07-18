"""GUI Config Tools module.

Provides basic helper functions to read text documents and load YAML configurations.
"""

#-----------------------
# PACKAGES
#-----------------------
import yaml
import os
import json
import logging
from typing import List, Dict, Any, Optional
from src.utils.logging_config import get_logger

logger = get_logger('tools')


#-----------------------
# FUNCTIONS
#-----------------------
def read_in_text(text_to_read):
    """Reads in text documents, replacing backslash-n sequences with newlines.

    Args:
        text_to_read: File path of the text document to read.

    Returns:
        The read text string with normalized newlines.
    """
    #------------------------------------------
    # read in funding text  
    logger.debug('Reading text: %s', text_to_read)
    with open(text_to_read, 'r') as file:
                
        tmp_text = file.read().replace("\\n", "\n")
            
    return tmp_text



def load_config(configuration_file, dump_indentation = 4):
    """Loads a YAML configuration file.

    Args:
        configuration_file: Filepath of the configuration file.
        dump_indentation: Number of indentation spaces to use for the YAML dump.
            Defaults to 4.

    Returns:
        A tuple containing:
            - Dict: The parsed configuration content.
            - Str: The dumped YAML string.
    """
    #-----------------
    # normalise the filepath to file system
    configuration_file = os.path.normpath(configuration_file)

    #-----------------
    # Use pyyaml to open and load configuration file
    with open(configuration_file) as f:

        try:
            content = yaml.safe_load(f)
            content_dump = yaml.dump(content, indent=dump_indentation)

        except yaml.YAMLError as e:

            logger.error('Error loading config: %s', e)

    return content, content_dump



#-----------------------
# CLASSES
#-----------------------

import pandas as pd

def restore_dataframe(cached_data: list, cached_dtypes: dict) -> pd.DataFrame:
    """Restores a pandas DataFrame from a list of records and a dictionary of dtypes."""
    df = pd.DataFrame(cached_data)
    if not cached_dtypes:
        return df
        
    for col, dtype_name in cached_dtypes.items():
        if col in df.columns:
            if "datetime" in dtype_name:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            elif "timedelta" in dtype_name:
                df[col] = pd.to_timedelta(df[col], errors="coerce")
            else:
                try:
                    df[col] = df[col].astype(dtype_name)
                except Exception:
                    pass
    return df
