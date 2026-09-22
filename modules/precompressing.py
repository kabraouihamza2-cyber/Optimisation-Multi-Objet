"""
cleaning files based on files type and classe:

categories:
    - csv/json
    - text/md/log

csv/json/text/md/log:
    - Hot
        - deduplication (2 version selon categorie)

    - warm:
        - deduplication (2 version selon categorie)
        - whitespace cleanup (supprimer espaces inutiles) (2 version selon categorie)

    - cold:
        - deduplication (2 version selon categorie)
        - whitespace cleanup (2 version selon categorie)
        - suppression des ligne vides.  (selement pour text/md/log)

    avec fonctions utiles comme: load/save (2 versions selon categorie)

"""

import os
import hashlib
import pandas as pd
import time 

import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(BASE_DIR, "data", "file_catalog.csv")

PRECOMPRESSING_REPORT_PATH = os.path.join(BASE_DIR, 'data','results','precompressing_report.json')


def precompressing():
    """
        Apply precompressing to all files in the cataloge
    """

    all_stats = []

    df = pd.read_csv(CATALOG_PATH)

    for _,file in df.iterrows():

        start = time.perf_counter()

        file_path = file['path']
        classe = file['ml_label'].lower()
        taille_initiale = os.path.getsize(file_path)

        try:
            ext  = file['type'].lower()

            if ext in ['.csv', '.json']:
                clean_csv_json(file_path, classe)

            elif ext in ['.txt', '.md', '.log']:
                clean_txt_md_log(file_path, classe)

            else:
                continue

        except Exception as e:
            print(f"Error processing: {e}")

            statistiques = {
                "method": 'failed precompressing',
                "original_size_bytes": taille_initiale,
                "new_size_bytes": taille_initiale,
                "compression_ratio": 0.0,
                "space_saving_pct": 0.0,
                "precompressing_time_sec": time.perf_counter() - start,
            }

            all_stats.append(statistiques)
            continue

        

        end = time.perf_counter()
        temps_comp = end - start

        new_size = os.path.getsize(file_path)

        gain_pct = (taille_initiale - new_size) / taille_initiale * 100
        ratio = (taille_initiale / new_size) if new_size > 0 else 1.0

        statistiques = {
        "method": 'precompressing',
        "original_size_bytes": taille_initiale,
        "new_size_bytes": new_size,
        "compression_ratio": round(ratio, 3),
        "space_saving_pct": round(gain_pct, 2),
        "precompressing_time_sec": temps_comp,
        }

        all_stats.append(statistiques)

    generate_precompressing_report(all_stats)



def generate_precompressing_report(all_stats):

    stats_df = pd.DataFrame(all_stats)

    results = stats_df.agg({
        "original_size_bytes": 'sum',
        "new_size_bytes": 'sum',
        "compression_ratio": 'mean',
        "space_saving_pct": 'mean',
        "precompressing_time_sec": 'mean'
    }).round(5)



    # to convert the series to a dataframe: we used to_frame + transpose:
    results.to_frame().T.to_json(PRECOMPRESSING_REPORT_PATH, orient='records', indent=4)





def clean_csv_json(file_path, classe):

    if classe == 'hot':
        drop_duplicates_csv_json(file_path)

    elif classe == 'warm':
        drop_duplicates_csv_json(file_path)
        whitespace_cleanup_csv_json(file_path)

    elif classe == 'cold':
        drop_duplicates_csv_json(file_path)
        whitespace_cleanup_csv_json(file_path)
    


def clean_txt_md_log(file_path, classe):

    if classe == 'hot':
        drop_duplicates_text(file_path)

    elif classe == 'warm':
        drop_duplicates_text(file_path)
        whitespace_cleanup_text(file_path)

    elif classe == 'cold':
        drop_duplicates_text(file_path)
        whitespace_cleanup_text(file_path)
        remove_empty_lines(file_path)   




# text deduplication: --------------


def load_text_lines(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:  # ignore invalid chars during reading.
        lines = f.readlines()

    return lines




def save_text_lines(file_path, lines):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)





def drop_duplicates_text(file_path):
    """
        md5 was used for text files for performance.
    """

    distinct_hashes = set()
    distinct_lines = []

    lines = load_text_lines(file_path)

    if not lines:
        return

    for line in lines:
        line_hashed = hashlib.md5(line.encode('utf-8')).hexdigest()   # hash the lines

        if line_hashed not in distinct_hashes:
            distinct_hashes.add(line_hashed)
            distinct_lines.append(line)


    save_text_lines(file_path, distinct_lines)
    
        

# csv json deduplication: ----------------


def load_csv_json(file_path):
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)

    elif file_path.endswith('.json'):
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            data = [data]

        return pd.DataFrame(data)


def save_csv_json(file_path, df):
    if file_path.endswith('.csv'):
        df.to_csv(file_path, index=False)

    elif file_path.endswith('.json'):
        df.to_json(file_path, orient='records', indent = 2)



def drop_duplicates_csv_json(file_path):
    """
        we will use drop_duplicates because it's heavily optimized in C.
    """

    df = load_csv_json(file_path)
    
    if df.empty:
        return

    df = df.drop_duplicates().reset_index(drop=True) # drop=True to do not save the index as a column
    # and reset_index so the index can be continuous from 0 to n-1.  not having holes.

    save_csv_json(file_path, df)




# whitespace cleanup: ------------

def whitespace_cleanup_text(file_path):

    lines = load_text_lines(file_path)

    if not lines:
        return 

    clean_lines = []

    for line in lines:
        line = " ".join(line.split())   # split auto removes \n \t \r and multiple spaces.
        clean_lines.append(line + "\n") # \n to keep that return to the line.


    save_text_lines(file_path, clean_lines)



def whitespace_cleanup_csv_json(file_path):
    
    df = load_csv_json(file_path)

    if df.empty:
        return 

    for column in df.select_dtypes(include=['object', 'string']):
        
        df[column] = df[column].astype(str, errors='ignore').str.split().str.join(' ')



    save_csv_json(file_path, df)    



# empty text lines:
def remove_empty_lines(file_path):

    lines = load_text_lines(file_path)
    
    
    if not lines:
        return

    lines_to_keep = []

    for line in lines:
        if not (line.strip() == ''):
            lines_to_keep.append(line)

    
    save_text_lines(file_path, lines_to_keep)
    



        









