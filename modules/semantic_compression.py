"""
implementer par achraf (version experimental)

l'idee c'est d'utiliser olama pour une compression sematic des cold fichier txt
.txt  .md   .log

refrence: https://arxiv.org/abs/2304.12512 



gemma3:4b 
    To make things faster 
    the context max is: 131072

    So because of my computer performance i will fix it at: 40000

    and because always token <=> word, so some cases where there is letters with space
    it counts as a token or more, so i will leave a safe margin for it.

    so max_char_per_chunk i choose: 60000 double with a 10000 margin. 





    
"""

import ollama

import time
from langchain_text_splitters import RecursiveCharacterTextSplitter

import os
import pandas as pd
MAX_CHARS_PER_CHUNK = 60000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(BASE_DIR, "data", "file_catalog.csv")
SEMANTIC_COMPRESSED = os.path.join(BASE_DIR, "data","semantic_compressed")

SEMANTIC_COMPRESSION_REPORT_PATH = os.path.join(BASE_DIR, "data", 'results', "semantic_compression_report.json")

def semantic_compression(text):

    prompt = f"""
    You are a semantic compression engine.

    TASK:
    Extract only the main topics from the document.

    OUTPUT FORMAT:

    TOPIC: <topic name>
    SUMMARY: <maximum 1 sentence>
    KEYWORDS: keyword1, keyword2, keyword3

    RULES:

    - Output ONLY the format above.
    - Do NOT explain your work.
    - Do NOT write introductions.
    - Do NOT write conclusions.
    - Do NOT ask questions.
    - Do NOT say "Here is an analysis".
    - Do NOT number topics.
    - Maximum 10 topics.
    - Maximum 1 sentence per summary.
    - Maximum 5 keywords.
    - Ignore boilerplate text such as:
    Project Gutenberg,
    copyright notices,
    table of contents,
    publication information,
    license information.

    Document:

{text}
    """

    response = ollama.chat(
        model="gemma3:4b",
        messages=[
            {
                "role": "system",
                "content": """
                You are a semantic compression engine.
                Output only:

                TOPIC:
                SUMMARY:
                KEYWORDS:

                No introductions.
                No explanations.
                No markdown.
                No questions.
                """
            },
            {
                "role": "user",
                "content": prompt
            }
            
        ],
        options={
        "num_ctx": 40000
        }
    )


    response = response["message"]["content"]

    response = response.replace("```json", "")
    response = response.replace("```", "")
    response = response.strip()


    print(response)

    return response
 

# json dont work because AI returns duplicates because of low context.


def start_semantic_compression(text):

    start = time.perf_counter()

    # split txt into chunks:
    """
        first i started to split chunks based on size then i realised i need smth
        that splits based on paragraph words and then final solution is chars
        but i found a library that do that:

        Paragraphs -> Lines -> Sentences -> Words -> Characters

        pip install langchain-text-splitters
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHARS_PER_CHUNK,
        chunk_overlap=500  # to give context to the next chunk
    )

    """
    Why chunk overlap is important:

    Chunk 1:
    TCP is connection-oriented.
    It uses acknowledgements.

    Chunk 2:
    TCP is connection-oriented.
    It uses acknowledgements.
    This improves reliability.
    """

    chunks = splitter.split_text(text)
    

    # combine all chunks results:
    processed_chunks = 0
    compressed_data = ""
    for chunk in chunks:

        # attemp 3 times
        for i in range(3):
            try:
                results = semantic_compression(chunk)
                compressed_data += "\n\n" + results

                if results: 
                    processed_chunks += 1
                    break


            except Exception as e:
                print(f"(SKIPPED), Error : {e}")
                continue
            



    duree = time.perf_counter() - start
           

    taille_initale = len(text.encode("utf-8"))  # pour compter les char francais arabic etc

    # ensure_ascii=False to do not remove arabic and french chars from json.
    # converts json to str and count bytes.
    taille_compressee = len(compressed_data.encode("utf-8"))  
    
    ratio = taille_initale / taille_compressee if taille_compressee > 0 else 1.0
    gain_pct = (1.0 - (taille_compressee / taille_initale)) * 100 if taille_initale > 0 else 0.0

    statistics = {
        "algorithm": "gemma3:4b",
        "original_size_bytes": taille_initale,
        "semantic_compressed_size_bytes": taille_compressee,
        "semantic_compression_ratio": round(ratio, 3),
        "space_saving_pct": round(gain_pct, 2),
        "semantic_compression_time_sec": duree,
        "processed_chunks": processed_chunks,
        "total_chunks": len(chunks)
    }


    return compressed_data, statistics




def semantic_compression_launcher():
    df = pd.read_csv(CATALOG_PATH)

    all_stats = []
    for indx, row in df.iterrows():

        # compress only cold txt files:
        if (row['ml_label'].lower() not in ['cold']) or (row['type'].lower() not in ['.txt','.md']):
            continue 

        print(f'starting -> file:{row['file_id']}')  
        with open(row['path'],'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()

        
        compressed_data , stats = start_semantic_compression(text)
        stats['file_name'] = row['name']
        all_stats.append(stats)
        
        out_path = os.path.join(SEMANTIC_COMPRESSED, f"{os.path.basename(row['path'])}.txt")

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(compressed_data)

        # update cataloge:
        df.loc[indx, 'semantic_compression_path'] = out_path
        print(f'file:{indx} compressed!')  

    # save the cataqloge:
    df.to_csv(CATALOG_PATH, index=False)


    # generate_semantic_compression_report
    generate_semantic_compression_report(all_stats)





def generate_semantic_compression_report(all_stats):
    stats_df = pd.DataFrame(all_stats)

    stats_df.to_json(SEMANTIC_COMPRESSION_REPORT_PATH, orient='records', indent=4)
    

        
        

        
        