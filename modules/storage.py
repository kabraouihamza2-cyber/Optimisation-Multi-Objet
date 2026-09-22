
"""
Simuler placement,
generer le fichier storage_report.json

"""

import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SSD_DIR =  os.path.join(BASE_DIR, "data", "storage", "ssd")
HDD_DIR =  os.path.join(BASE_DIR, "data", "storage", "hdd")
ARCHIVE_DIR = os.path.join(BASE_DIR, "data", "storage", "archive")

CATALOG_PATH = os.path.join(BASE_DIR, "data", "file_catalog.csv")

COMPRESSED_DIR = os.path.join(BASE_DIR, "data", "compressed")

def simulate_placement(file_details, tier, df):
    
    # get path:
    if tier.lower() == 'ssd':
        path = SSD_DIR 

    elif tier.lower() == 'hdd':
        path = HDD_DIR

    else:
        path = ARCHIVE_DIR


    file_id = file_details['file_id']


    # compressed vers SSD/HDD/ARCHIVE :
    source = df.loc[df['file_id'] == file_id, 'compressed_path'].iloc[0]

    compressed_name = os.path.basename(source)

    destination = os.path.join(path, compressed_name)
    
    shutil.copy2(source, destination)


    # save tier for report generation: (in memory no need to save it in the file)
    # dataframes are passed by refrence
    df.loc[df['file_id'] == file_id, 'tier'] = tier

    



def generate_storage_report(df):

    """
    make a report in the following format:

        {
        "summary": {
            "total_files": 150,

            "ssd_tier": {
            "count": 25,
            "size_mb": 8240
            },

            "hdd_tier": {
            "count": 75,
            "size_mb": 24310
            },

            "archive_tier": {
            "count": 50,
            "size_mb": 10030
            }
        },

        "files": [
            {
            "file_id": "001",
            "filename": "sales_q1.pdf",
            "size_mb": 12.5,
            "tier": "SSD",
            "compressing_algo": "gzip"
            }
        ]
        }
    """


    report = {
        "summary" : {},
        "files" : []
    }


    report['summary']['total_files'] = len(df)

    # general stats:
    for  tier in ['SSD', 'HDD', 'ARCHIVE']:
        df_filtered = df[df['tier'].str.lower() == tier.lower()]
        report['summary'][tier] = {

            "count":len(df_filtered),
            "size_mb":df_filtered['compressed_size_bytes'].sum() / (1024 ** 2)

        }


    # files stats:
    for _, file in df.iterrows():
        report['files'].append({
            "file_id": file['file_id'],
            "filename": file['name'],
            "size_mb": file['compressed_size_bytes'] / (1024 ** 2),
            "tier": file['tier'],
            "compressing_algo": file['compression_algo']
        })
        


    # save report:
    STORAGE_REPORT_PATH = os.path.join(BASE_DIR, "data", "storage", "storage_report.json")
    with open(STORAGE_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=4)
        

    



