import re
import pandas as pd
from bs4 import BeautifulSoup

def extract_data(html_file):
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Step 1: Find all Factor variable names
    factor_blocks = re.findall(r'var\s+(\w+)\s*=\s*new\s+Factors\(\);', content)
    
    if not factor_blocks:
        print("DEBUG: Could not find any 'var name = new Factors();' patterns.")
        return pd.DataFrame()

    # Mapping logic for your specific naming conventions
    year_map = {"10": 2010, "15": 2015, "20": 2020, "25": 2025} # Per your instruction: 25 is 2015
    org_map = {"WMA": "World Masters Athletics", "MLDR": "Masters Long Distance Running"}
    
    results = []

    for name in factor_blocks:
        print(f"DEBUG: Found Factor group: {name}")
        
        # Parse metadata from the 'name' string (e.g., MLDR_25_M_facs)
        parts = name.split('_')
        if len(parts) >= 3:
            org_code = parts[0]
            year_code = parts[1]
            gender_code = parts[2]
            
            organization = org_map.get(org_code.upper(), org_code)
            factor_year = year_map.get(year_code, year_code)
            gender = "Male" if gender_code.upper() == "M" else "Female"
        else:
            organization, factor_year, gender = "Unknown", "Unknown", "Unknown"

        # Capture the chunk of text between this Factor definition and the next one
        pattern = rf'{name}\.addAges\(new Array\((.*?)\)\);(.*?)(?=var\s+\w+\s*=\s*new\s+Factors|$)'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            continue
            
        # Parse Ages
        age_str = match.group(1)
        ages = [a.strip().strip("'").strip('"') for a in age_str.split(',')]
        
        # Parse Events within this block
        event_block = match.group(2)
        events = re.findall(r'addEvent\s*\(\s*new\s+facrow\s*\(\s*"(.*?)",\s*(.*?)\s*\)\s*\)', event_block, re.DOTALL)
        
        for event_name, data_points in events:
            values = [v.strip() for v in data_points.split(',')]
            
            # Align age factors from the tail of the values list
            factor_values = values[-len(ages):]
            
            for age, val in zip(ages, factor_values):
                results.append({
                    "factor_name": name,
                    "organization": organization,
                    "factor_year": factor_year,
                    "gender": gender,
                    "event": event_name,
                    "age": age,
                    "factor_value": val
                })

    return pd.DataFrame(results)

if __name__ == "__main__":
    target_file = "data/https___howardgrubb.co.uk_athletics_mldrroad25.html" 
    df = extract_data(target_file)
    
    if not df.empty:
        # Reordering columns as requested
        column_order = ["factor_name", "organization", "factor_year", "gender", "age", "factor_value", "event"]
        df = df[column_order]
        
        df.to_csv("data/wma_2010_2025_road_factors.csv", index=False)
        print("\n--- Extraction Complete ---")
        print(f"Total Rows: {len(df)}")
        print(df.head(10))
    else:
        print("\n--- Failed ---")