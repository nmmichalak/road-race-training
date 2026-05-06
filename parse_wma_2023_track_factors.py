import re
import pandas as pd
import json

def extract_wma_factors(html_content):
    # 1. Extract the Age Reference Arrays first
    # These define what age corresponds to which index (e.g., index 1 = age 30)
    m_age_pattern = re.search(r'WMA_M_ages\s*=\s*(\[.*?\]);', html_content, re.DOTALL)
    f_age_pattern = re.search(r'WMA_F_ages\s*=\s*(\[.*?\]);', html_content, re.DOTALL)
    
    # Parse the age strings into Python lists
    # We use index 1+ because index 0 is usually the string "type" or "age"
    m_ages = json.loads(m_age_pattern.group(1)) if m_age_pattern else []
    f_ages = json.loads(f_age_pattern.group(1)) if f_age_pattern else []

    # 2. Regex to capture Gender (M/F), Event Name, and the Array of factors
    pattern = re.compile(r'WMA_([MF])_facs\[["\']([^"\']+)["\']\]\s*=\s*\[(.*?)\s*\];', re.DOTALL)
    
    all_data = []
    matches = pattern.findall(html_content)
    
    if not matches:
        # Fallback for localized scripts
        pattern_fallback = re.compile(r'facs\[["\']([^"\']+)["\']\]\s*=\s*\[(.*?)\s*\];', re.DOTALL)
        matches = [('M', m[0], m[1]) for m in pattern_fallback.findall(html_content)]

    for gender_code, event_name, values_str in matches:
        # Clean and split the factor values
        clean_values = values_str.replace('\n', ' ').replace('\r', ' ')
        parts = [p.strip().strip("'").strip('"') for p in clean_values.split(',')]
        
        if not parts:
            continue
            
        gender = "Male" if gender_code == 'M' else "Female"
        # Select the corresponding age reference list
        current_age_map = m_ages if gender_code == 'M' else f_ages
        
        factor_type = parts[0]  # The identifier (e.g., 'T2')
        factors = parts[1:]     # The actual numeric factors (starting at index 1)
        
        for i, factor_val in enumerate(factors):
            try:
                if not factor_val.strip():
                    continue
                
                # Use the index (+1 to account for skipping factor_type) to get the age
                age_index = i + 1
                if age_index < len(current_age_map):
                    actual_age = current_age_map[age_index]
                else:
                    # Fallback if the age array is shorter than the factor array
                    continue

                val = float(factor_val)
                all_data.append({
                    "gender": gender,
                    "event_name": event_name,
                    "factor_type": factor_type,
                    "age": actual_age, 
                    "factor_value": val
                })
            except ValueError:
                continue
                        
    return pd.DataFrame(all_data)

if __name__ == "__main__":
    file_path = 'data/https___howardgrubb.co.uk_athletics_wmatnf23.html' 
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            df = extract_wma_factors(content)
        
        if df.empty:
            print("DataFrame is empty. Check your HTML source for 'WMA_M_ages' and 'WMA_M_facs'.")
        else:
            print(f"Successfully extracted {len(df)} rows.")
            print("\nFirst 5 rows:")
            print(df.head())
            
            df.to_csv("data/wma_2023_track_factors.csv", index=False)
            print("\nData saved to data/wma_2023_track_factors.csv")
            
    except Exception as e:
        print(f"An error occurred: {e}")