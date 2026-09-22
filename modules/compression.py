"""
Hot : snappy -> tres rapide
Warm: zstd -> Bon balance entre la vitesse et la compression.
Cold: gzip -> compression max mais lent

Refrence: 
https://apxml.com/courses/intro-data-lake-architectures/chapter-2-file-formats-and-optimization/compression-algorithms

there 3 are lossless compression

"""

import time
import gzip
import snappy
import zstandard as zstd
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPRESSED_DIR = os.path.join(BASE_DIR, "data", "compressed")
CATALOG_PATH = os.path.join(BASE_DIR, "data", "file_catalog.csv")


COMPRESSION_REPORT_PATH = os.path.join(BASE_DIR, 'data', 'results', 'compression_report.json')

def speed_test(func):
    def wrapper(*args, **kwarg):
        start = time.perf_counter()
        res = func(*args, **kwarg)
        duree = time.perf_counter() - start
        return res, duree
    return wrapper
    

@speed_test
def compress_data(data_bytes, algorithm):
    
    if algorithm == "snappy":
        res = snappy.compress(data_bytes)

    elif algorithm == "zstd":
        # valeur par default = 3
        compressorObj = zstd.ZstdCompressor(level=3)
        res = compressorObj.compress(data_bytes)

    elif algorithm == "gzip":
        # valeur par default = 6
        res = gzip.compress(data_bytes, compresslevel=6)

    elif algorithm == "none" or not algorithm:
        res = data_bytes
    else:
        raise ValueError(f"Algorithme inconnu: {algorithm}")
        
    return res


@speed_test
def decompress_data(compressed_bytes, algorithm):
    """
    utiliser pour verifier les donnees sont corrompues ou non.
    """
    
    if algorithm == "snappy":
        res = snappy.decompress(compressed_bytes)

    elif algorithm == "zstd":
        decompressorObj = zstd.ZstdDecompressor()
        res = decompressorObj.decompress(compressed_bytes)

    elif algorithm == "gzip":
        res = gzip.decompress(compressed_bytes)

    elif algorithm == "none" or not algorithm:
        res = compressed_bytes
    else:
        raise ValueError(f"Algorithme inconnu: {algorithm}")
        
    return res




def run_adaptive_compression(data_bytes, classification):
    """
    Choisit l'algorithme de compression selon la temperature du fichier.
    Fait aussi un test loopback (compression/decompression) pour verifier la coherence.

    choix selon temperature:
    avec test loopback (compression/decompression) -> verifier si les donner sont corrumpu
    """

    choix_algo = {
        "Hot": "snappy",
        "Warm": "zstd",
        "Cold": "gzip"
    }
    
    algo = choix_algo.get(classification, "none")
    
    
    # compression
    donnees_compressees, temps_comp = compress_data(data_bytes, algo)
    

    # test loopback:
    donnees_decompressees, temps_decomp = decompress_data(donnees_compressees, algo)
    
    if donnees_decompressees != data_bytes:
        raise ValueError("Erreur de corruption de donnees détectée !")
        

    # stats:
    taille_compressee = len(donnees_compressees)
    taille_initiale = len(data_bytes)

    # how much smaller the compressed file: e.g ratio = 2; means compressed file = 1/2 original size.
    ratio = taille_initiale / taille_compressee if taille_compressee > 0 else 1.0
    gain_pct = (1.0 - (taille_compressee / taille_initiale)) * 100 if taille_initiale > 0 else 0.0
    
    statistiques = {
        "algorithm": algo,
        "original_size_bytes": taille_initiale,
        "compressed_size_bytes": taille_compressee,
        "compression_ratio": round(ratio, 3),
        "space_saving_pct": round(gain_pct, 2),
        "compression_time_sec": temps_comp,
        "decompression_time_sec": temps_decomp
    }
    
    return donnees_compressees, statistiques






def start_compression():
    """
        store the compressed files in compressed dir
        same exextencion as the original file but with .snappy, .zstd or .gzip
    """


    df = pd.read_csv(CATALOG_PATH)
    all_stats = []

    for indx, row in df.iterrows():

        file_path = row['path']
        label = row['ml_label']

        try:
            
            with open(file_path, 'rb') as f:
                data_bytes = f.read()

            compressed_bytes, stats = run_adaptive_compression(data_bytes, label)

            # map compression_type to extension
            mapper = {
                "snappy": ".snappy",
                "zstd": ".zstd",
                "gzip": ".gzip",
            }
            
            algo = stats['algorithm'].lower()

            compressed_path = os.path.join(COMPRESSED_DIR, os.path.basename(file_path) + mapper[algo])

            with open(compressed_path, "wb") as f:
                f.write(compressed_bytes)

            all_stats.append(stats)

            # upadate cataloge:
            df.loc[indx, 'compression_algo'] = stats['algorithm']
            df.loc[indx, 'compressed_path'] = compressed_path
            df.loc[indx, 'compressed_size_bytes'] = stats['compressed_size_bytes']



        
        except Exception as e:
            print('compression failed!', e) 

    df.to_csv(CATALOG_PATH, index=False)

    generate_compression_report(all_stats)





def generate_compression_report(all_stats):
    """
        Aggregate statistics from all_stats
    """

    stats_df = pd.DataFrame(all_stats)

    results = stats_df.groupby('algorithm').agg({
        'original_size_bytes': 'sum',
        'compressed_size_bytes': 'sum',
        'compression_time_sec': 'mean',
        'space_saving_pct': 'mean',
    }).round(5)


    # ratio: compressed sgher b ch7al mn mera.
    results['algorithm_ratio'] = (results['original_size_bytes'] / results['compressed_size_bytes']).round(5)

    # Count:
    results['files_count'] = stats_df.groupby('algorithm').size()

    # reset_index to include algorithm name!
    results = results.reset_index()

    results.to_json(COMPRESSION_REPORT_PATH, orient='records', indent=4)
