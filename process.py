import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import re
from load import load_fit_activity

def to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', str(name))
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def transform_running_activity(activity_df, lt_df, race_df):
    if activity_df.empty or 'timestamp' not in activity_df.columns:
        return pd.DataFrame()

    df = activity_df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    activity_date = df['timestamp'].dt.date.iloc[0]
    df['date_key'] = activity_date
    
    # 1. SET LT BENCHMARKS
    lt_hr, lt_pwr = 170, 350 # Fallbacks
    if not lt_df.empty:
        lt_temp = lt_df.copy()
        lt_temp['date'] = pd.to_datetime(lt_temp['date']).dt.date
        match = lt_temp[lt_temp['date'] <= activity_date].sort_values('date').tail(1)
        if not match.empty:
            lt_hr = match['threshold_heart_rate_bpm'].iloc[0] * 1.04
            lt_pwr = match['threshold_power_watts'].iloc[0] * 1.05

    # Store benchmarks in the DF so the summarizer can find them
    df['benchmark_hr'] = lt_hr
    df['benchmark_power'] = lt_pwr

    # 2. LT BINS (0-200% in 10% steps)
    bins_10 = np.arange(0, 2.1, 0.1)
    if 'heart_rate' in df.columns:
        df['heart_rate_bin'] = pd.cut(df['heart_rate'] / lt_hr, bins=bins_10)
    if 'power' in df.columns:
        df['power_bin'] = pd.cut(df['power'] / lt_pwr, bins=bins_10)

    # 3. RACE PACE BINS (+/- 2.5% Window)
    if 'enhanced_speed' in df.columns and not race_df.empty:
        df['pace_sec_mile'] = 1609.344 / df['enhanced_speed'].replace(0, np.nan)
        
        race_temp = race_df.copy()
        race_temp['date'] = pd.to_datetime(race_temp['calendarDate']).dt.date
        r_match = race_temp[race_temp['date'] <= activity_date].sort_values('date').tail(1)
        
        if not r_match.empty:
            paces = {
                '5K': r_match['raceTime5K'].iloc[0] / 3.10686,
                '10K': r_match['raceTime10K'].iloc[0] / 6.21371,
                'Half': r_match['raceTimeHalf'].iloc[0] / 13.1094,
                'Marathon': r_match['raceTimeMarathon'].iloc[0] / 26.2188
            }
            
            for race_name, target_pace in paces.items():
                lower, upper = target_pace * 0.975, target_pace * 1.025
                
                # Create the bin column
                bin_col = f"race_pace_{race_name.lower()}_bin"
                df[bin_col] = df['pace_sec_mile'].between(lower, upper).map({True: 'HIT', False: 'MISS'})
                
                # Store the specific target pace benchmark
                df[f'benchmark_pace_{race_name.lower()}'] = target_pace

    return df

def summarize_activity_bins(df):
    if df.empty: return pd.DataFrame()

    def format_bin(b):
        if pd.isna(b) or isinstance(b, str): return str(b)
        if hasattr(b, 'left'):
            return f"{int(round(b.left*100))}-{int(round(b.right*100))}%"
        return str(b)

    temp = df.copy()
    bin_cols = [c for c in temp.columns if c.endswith('_bin')]
    if not bin_cols: return pd.DataFrame()

    all_summaries = []
    for bin_col in bin_cols:
        # Determine the correct benchmark column and label
        if 'heart_rate' in bin_col:
            bench_col, label = 'benchmark_hr', "HEART RATE"
        elif 'power' in bin_col:
            bench_col, label = 'benchmark_power', "POWER"
        elif 'race_pace' in bin_col:
            race_type = bin_col.split('_')[2] # e.g., '5k'
            bench_col = f'benchmark_pace_{race_type}'
            label = f"RACE PACE {race_type.upper()}"
        else:
            continue

        if bench_col not in temp.columns: continue

        # Format label and group
        temp[bin_col] = f"{label}: " + temp[bin_col].apply(format_bin).astype(str)

        metric_summary = (
            temp.groupby(['date_key', 'activity_id', bin_col], observed=True)[bench_col]
            .agg(seconds='count', metric_value='mean') # Mean of a constant is the constant
            .reset_index()
        )
        metric_summary = metric_summary.rename(columns={'date_key': 'date', bin_col: 'metric_bin'})
        all_summaries.append(metric_summary)

    return pd.concat(all_summaries, ignore_index=True) if all_summaries else pd.DataFrame()

def _process_single_fit_file(file_path, lt_df, race_df):
    try:
        df = load_fit_activity(file_path)
        if df.empty: return pd.DataFrame()
        
        # Filter: Ignore non-running or stationary files (avg speed < 1.0 m/s)
        if 'enhanced_speed' not in df.columns or df['enhanced_speed'].mean() < 1.0:
            return pd.DataFrame()

        transformed = transform_running_activity(df, lt_df, race_df)
        return summarize_activity_bins(transformed)
    except Exception as e:
        return f"Error in {file_path.name}: {e}"

def process_all_fit_activities(directory_path, lt_df, race_df, max_workers=None):
    path = Path(directory_path)
    fit_files = list(path.glob("*.fit"))
    results, errors = [], []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_single_fit_file, f, lt_df, race_df): f for f in fit_files}
        for future in as_completed(futures):
            res = future.result()
            if isinstance(res, str): errors.append(res)
            elif res is not None and not res.empty: results.append(res)
            
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

def consolidate_garmin_data(race_df, vo2_df, sleep_df):
    """
    Merges daily physiological metrics. 
    Standardizes 'calendarDate' (JSON) and 'date' (CSV) keys.
    """
    processed_dfs = []
    
    # Mapping of source dataframes to their respective date columns
    sources = [
        ('race', race_df),
        ('vo2', vo2_df),
        ('sleep', sleep_df)
    ]
    
    for name, df in sources:
        if df is not None and not df.empty:
            df = df.copy()
            
            # 1. Identify and standardize the date column
            if 'calendarDate' in df.columns:
                df['date'] = pd.to_datetime(df['calendarDate']).dt.date
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date
            else:
                continue
                
            # 2. Handle missing dates (found in your Sleep Data log)
            df = df.dropna(subset=['date'])
            
            # 3. For Race Predictions: Deduplicate (Garmin often exports multiple per day)
            if name == 'race':
                # Keep the latest timestamp for that day
                if 'timestamp' in df.columns:
                    df = df.sort_values('timestamp').drop_duplicates('date', keep='last')
            
            processed_dfs.append(df)

    if not processed_dfs:
        return pd.DataFrame()

    # 4. Perform the Outer Merge
    master = processed_dfs[0]
    for next_df in processed_dfs[1:]:
        master = pd.merge(master, next_df, on='date', how='outer')

    # 5. Clean up column names to snake_case
    master.columns = [to_snake(c) for c in master.columns]
    
    # Ensure the merge key remains named 'date'
    if 'date' in master.columns:
        master = master.sort_values('date').reset_index(drop=True)
        
    return master