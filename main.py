
from modules.analysis import analyze_datasets
from modules.classification import classify_ml

from modules.precompressing import precompressing
from modules.compression import start_compression
from modules.semantic_compression import semantic_compression_launcher


from modules.decision_engine import start_decision_engine


from utils import load_config
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data','raw')

CONFIG_PATH = os.path.join(BASE_DIR,'config.json')

REAL_FILES = os.path.join(BASE_DIR, 'data', 'real_files')





def main():

    config = load_config(CONFIG_PATH)

    print("analyzing datasets...")
    analyze_datasets(REAL_FILES)

    print("classifying...")
    classify_ml(config, use_saved_model=True)




    # can be applied on diffrent fileSet.

    print("precompressing...")
    precompressing()

    print("compressing...")
    start_compression()

    # optional (experimental)
    print("semantic compressing...")
    semantic_compression_launcher()

    print("decision engine...")
    start_decision_engine(config)


    print("processing finished!")




if __name__ == '__main__':
    main()


    


