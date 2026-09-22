from modules.classification import classify_with_scoring
import os
import json
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import uuid



SYNTHETIC_DIR = r"C:\Users\achra\OneDrive\Desktop\UIT_master\Uit Master projects\Concepts big data\synthetic_files"
DATA_PATH = r"C:\Users\achra\OneDrive\Desktop\UIT_master\Uit Master projects\Concepts big data\Approche Hybride d'Optimisation Multi-Objectifs pour le Stockage et le Traitement Adaptatif dans les Architectures BIG DATA\data"
CSV_ENTRAINEMENT = os.path.join(DATA_PATH, "ml_train_metadata.csv")


def load_config(config_path):

    with open(config_path, 'r') as f:
        return json.load(f)    



def update_last_access(target_dir):
    # updates the last_access of files to simulate old files:
    for file in os.listdir(target_dir):
        f_path = os.path.join(target_dir,file)

        new_access_time = datetime.now() - timedelta(days=random.randint(0,365))

        modified_time = os.path.getmtime(f_path)

        os.utime(f_path, (new_access_time.timestamp(), modified_time))





def generate_files():
    # generate 3000 raw files: between 1 and 500KB.

    # the synthetic files need to be outside the working dir because there is an issue:
    # when updating the last_accessed metadata, the IDE updates the last_accessed again
    # raw now is just a link to the outer file: mklink /J data\raw C:\...\synthetic_files

    ext = ['.pdf', '.docx', '.txt', '.csv', '.json']

    sizes = np.random.lognormal(mean=4.2, sigma=0.8,size=3000)  # <=>  exp(Normal(4.5, 2))
    # lognormal to get many small values, some medium and few large values.

    sizes = sizes.clip(1,500).astype(int)  # in KB.
    sizes = sizes * 1024 # converts KB to bytes

    for i, size in zip(range(3000),sizes):
        
        f_ext = random.choice(ext)
        full_f_name = f"{uuid.uuid4().hex}_file_{i:04d}{f_ext}"
        # emebeded uuid so when scaning the files to know the uuid of the file .
        

        f_path = os.path.join(SYNTHETIC_DIR, full_f_name)

        with open(f_path,"wb") as f:
            f.write(os.urandom(size))


    # updates the last_accesed metadata
    update_last_access(SYNTHETIC_DIR)

        





def generate_ml_train_csv(df):
    # use classification module to rule based classification to train the model


    # inner import to resolve circular imports
    from modules.classification import classify_with_scoring


    df_result = classify_with_scoring(df)

    df_result = df_result[["file_id", "access_freq", "last_access_days_ago", "size", "temperature", "label"]]

    df_result.to_csv(CSV_ENTRAINEMENT, index=False)








def generate_file_catalog():
    rows = []

    for file in os.listdir(SYNTHETIC_DIR):
        f_path = os.path.join(SYNTHETIC_DIR,file)

        last_accesed = datetime.fromtimestamp(os.path.getatime(f_path))
        f_size = os.path.getsize(f_path)  # in bytes.
        f_type = os.path.splitext(file)[1].lower()

        # this can be implemented in the user side: increment the counter in each access.
        random_file_access_freq = np.random.randint(1,500)

        # Id for files:       
        file_id, display_name = file.split("_", 1)


        row  = {
            "file_id":file_id,
            "name":display_name,
            "type":f_type,
            "size":f_size,  # in bytes.
            "access_freq":random_file_access_freq,
            "last_access_date":last_accesed,
            "path":f_path
        }
        
        rows.append(row)

    
    df = pd.DataFrame(rows)

    catalog_path = os.path.join(DATA_PATH,"file_catalog.csv")

    df.to_csv(catalog_path, index=False)

    return df



def rename_all_real_files(data_dir):
    """
    change the real files into the following formats:
        <uuid>_file_<counter><.ext>
    """

    for i, file in enumerate(os.listdir(data_dir)):
        old_path  = os.path.join(data_dir,file)

        file_name, ext = os.path.splitext(file)

        new_name = f"{uuid.uuid4().hex}_{file_name}_{i:04d}{ext}"

        new_path = os.path.join(data_dir,new_name)

        os.rename(old_path,new_path)


    
        

