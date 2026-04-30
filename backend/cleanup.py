import os

def clean_file(filepath, start_marker):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_index = -1
    for i, line in enumerate(lines):
        if line.strip() == start_marker:
            start_index = i
            # To be absolutely sure, check if the next line also matches expected structure roughly
            # if we wanted to...
            break
            
    if start_index != -1:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines[start_index:])
        print(f"Cleaned {os.path.basename(filepath)} - removed {start_index} lines of commented out code.")
    else:
        print(f"Start marker not found in {os.path.basename(filepath)}")

def clean_fe_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    start_index = -1
    for i, line in enumerate(lines):
        if line.strip() == 'import pandas as pd':
            if i + 1 < len(lines) and lines[i+1].strip() == 'import pandas_ta as ta':
                 start_index = i
                 break # Take the first match of the clean block

    if start_index != -1:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines[start_index:])
        print(f"Cleaned {os.path.basename(filepath)} - removed {start_index} lines of commented out code.")
    else:
        print(f"Start marker not found in {os.path.basename(filepath)}")

base_dir = r"c:\Users\Lenovo\Documents\VS CODE codes(files)\helloworld\Project sem-6\backend"
clean_file(os.path.join(base_dir, 'IntegratedPostGreSQL.py'), 'import yfinance as yf')
clean_fe_file(os.path.join(base_dir, 'FeatureEngineering.py'))
