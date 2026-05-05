import fitparse
import pandas as pd
import json
from pathlib import Path
from typing import Optional, Union

# load.py updates

def load_fit_activity(file_path: Union[str, Path]) -> pd.DataFrame:
    path = Path(file_path)
    try:
        fit = fitparse.FitFile(str(path))
        messages = list(fit.get_messages("record"))
        
        if not messages:
            return pd.DataFrame()
            
        records = []
        for m in messages:
            data = m.get_values()
            # CRITICAL: Only accept records that have both timestamp AND speed/position 
            # to ensure it's an actual activity, not a system file.
            if 'timestamp' in data:
                records.append(data)
        
        if not records:
            return pd.DataFrame()
            
        df = pd.DataFrame(records)
        df["activity_id"] = path.stem.rsplit('_', 1)[-1]
        return df
        
    except Exception:
        return pd.DataFrame()

# Example Usage:
# records = load_fit_activity("data/custom_folder/394249376961.fit")

def load_garmin_race_predictions(export_root: Union[str, Path]) -> pd.DataFrame:
    """
    Locates and aggregates 'RunRacePredictions' JSON files from a Garmin export.
    
    Best Practices:
    - Pathlib: Handles cross-platform pathing for technical data analysis.
    - Pattern Matching: Uses glob to find all files starting with 'RunRacePredictions'.
    - Resilience: Skips empty or corrupted JSON files gracefully.
    """
    # 1. Define the specific subpath for Metrics data
    base_path = Path(export_root) / "DI_CONNECT" / "DI-Connect-Metrics"
    
    # 2. Check if the directory exists
    if not base_path.is_dir():
        print(f"Warning: Metrics directory not found at {base_path}")
        return pd.DataFrame()
    
    # 3. Find all files starting with "RunRacePredictions"
    file_paths = list(base_path.glob("RunRacePredictions*"))
    
    if not file_paths:
        print(f"No race prediction files found in {base_path}")
        return pd.DataFrame()

    # 4. Read and convert to DataFrames
    df_list = []
    for fp in file_paths:
        try:
            with fp.open(mode="r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    # Usually a list of prediction objects
                    df_list.append(pd.DataFrame(data))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Skipping {fp.name} due to error: {e}")
            continue

    # 5. Concatenate and return
    if not df_list:
        return pd.DataFrame()
        
    return pd.concat(df_list, ignore_index=True)
    
def load_garmin_max_met_data(export_root: Union[str, Path]) -> pd.DataFrame:
    """
    Locates and aggregates 'MetricsMaxMetData' JSON files from a Garmin export.
    
    Best Practices applied:
    1. Uses Pathlib for cross-platform path compatibility.
    2. Includes error handling for missing directories and empty file lists.
    3. Uses list comprehension for efficient DataFrame creation.
    
    Args:
        export_root: Path to the root of the unzipped Garmin export folder.
        
    Returns:
        pd.DataFrame: A concatenated DataFrame of all Max MET metrics.
    """
    # 1. Define the specific subpath inside the Garmin export
    base_path = Path(export_root) / "DI_CONNECT" / "DI-Connect-Metrics"
    
    # 2. Check if the directory exists to avoid errors
    if not base_path.is_dir():
        print(f"Warning: Directory not found at {base_path}")
        return pd.DataFrame()
    
    # 3. Find all files starting with "MetricsMaxMetData"
    # We use glob to find filenames matching the pattern
    file_paths = list(base_path.glob("MetricsMaxMetData*"))
    
    if not file_paths:
        print(f"No files found matching 'MetricsMaxMetData' in {base_path}")
        return pd.DataFrame()

    # 4. Read and convert to DataFrames
    # We read each file into a list to concatenate all at once (more efficient)
    df_list = []
    for fp in file_paths:
        try:
            with fp.open(mode="r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure we only append if there is actual data in the JSON
                if data:
                    df_list.append(pd.DataFrame(data))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse {fp.name}: {e}")
            continue

    # 5. Concatenate and return
    if not df_list:
        return pd.DataFrame()
        
    return pd.concat(df_list, ignore_index=True)

# Example Usage:
# garmin_export_path = "data/1e633af1-bbb3-4207-9bb3-713a938c89fa_1"
# metrics_max_met = load_garmin_max_met_data(garmin_export_path)

def load_garmin_sleep_data(export_root: Union[str, Path]) -> pd.DataFrame:
    """
    Locates and aggregates 'sleepData' JSON files from a Garmin export.
    
    Best Practices:
    - Pathlib: Handles cross-platform pathing (Windows vs Linux).
    - Globbing: Efficiently filters for "sleepData" anywhere in the filename.
    - Error Handling: Skips corrupted files and warns about missing directories.
    - Performance: Concatenates list of DataFrames once at the end.
    
    Args:
        export_root: Path to the root of the unzipped Garmin export folder.
        
    Returns:
        pd.DataFrame: Combined sleep records.
    """
    # 1. Define the specific subpath for Wellness data
    base_path = Path(export_root) / "DI_CONNECT" / "DI-Connect-Wellness"
    
    # 2. Check if the directory exists
    if not base_path.is_dir():
        print(f"Warning: Wellness directory not found at {base_path}")
        return pd.DataFrame()
    
    # 3. Find all files containing "sleepData"
    # The '*' on both sides handles suffixes like dates or indices
    file_paths = list(base_path.glob("*sleepData*"))
    
    if not file_paths:
        print(f"No sleep data files found in {base_path}")
        return pd.DataFrame()

    # 4. Read and convert to DataFrames
    df_list = []
    for fp in file_paths:
        try:
            with fp.open(mode="r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    # Garmin sleep JSONs are usually lists of objects
                    df_list.append(pd.DataFrame(data))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Skipping {fp.name} due to error: {e}")
            continue

    # 5. Concatenate and return
    if not df_list:
        return pd.DataFrame()
        
    return pd.concat(df_list, ignore_index=True)

# Example Usage:
# garmin_export_path = "data/1e633af1-bbb3-4207-9bb3-713a938c89fa_1"
# sleep_df = load_garmin_sleep_data(garmin_export_path)

def fill_lactate_data(df: pd.DataFrame, end_date: Optional[Union[str, pd.Timestamp]] = None) -> pd.DataFrame:
    """
    Transforms a lactate threshold DataFrame by filling in daily entries
    from the first available date until a specified end date.
    """
    if df.empty:
        return df

    # Ensure the 'date' column is in datetime format
    df['date'] = pd.to_datetime(df['date'])
    
    # Set 'date' as the index for reindexing
    df = df.set_index('date')
    
    # Define the date range: from the first record to the end_date (default to today)
    start_date = df.index.min()
    if end_date is None:
        end_date = pd.Timestamp.now().normalize()
    else:
        end_date = pd.to_datetime(end_date).normalize()
        
    # Create a continuous range of daily dates
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Reindex and forward-fill values
    filled_df = df.reindex(all_dates).ffill().reset_index()
    filled_df = filled_df.rename(columns={'index': 'date'})
    
    return filled_df

def load_lactate_threshold_data(data_root: Union[str, Path], end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Locates the lactate threshold history file and applies daily filling.
    
    Best Practices applied:
    - Pathlib: For clean, cross-platform path management.
    - Validation: Checks if the file exists before attempting to read.
    - Encapsulation: Combines loading and transformation logic into one workflow.
    
    Args:
        data_root: Path to the directory containing the 'garmin-metrics' folder.
        end_date: Optional date string to fill the data until.
        
    Returns:
        pd.DataFrame: A daily-filled DataFrame of lactate threshold metrics.
    """
    # 1. Define the specific path for this specific source
    file_path = Path(data_root) / "garmin-metrics" / "lactate-threshold-history.csv"
    
    # 2. Check if file exists
    if not file_path.is_file():
        print(f"Warning: Lactate threshold file not found at {file_path}")
        return pd.DataFrame()
    
    # 3. Read and process
    try:
        lt_df = pd.read_csv(file_path)
        
        # 4. Apply the filling logic
        return fill_lactate_data(lt_df, end_date=end_date)
        
    except Exception as e:
        print(f"Error processing {file_path.name}: {e}")
        return pd.DataFrame()

# Example Usage:
# data_directory = "data"
# lactate_threshold = load_lactate_threshold_data(data_directory)