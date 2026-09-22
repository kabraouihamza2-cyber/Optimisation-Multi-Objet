"""
    Moteur de decision multi-objectifs en se basent sur (MCDA)

    - criteria:
        - cost
        - access latency (delay that takes to receive the info)
        - temperatures labels (hot/warm/cold) (importance) 


    
    So this problem is relative it depends on the objectives of the company and the budget

    some companies with low bugdet will priorities cost.
    
    and the ones with high budget will priorities latency and temperature.


    The decision score:
        for low budget:
            for example:
                score = 0.5 * cost + 0.2 * latency + 0.3 * temperature

        for high budget:
            for example:
                score = 0.2 * cost + 0.4 * latency + 0.4 * temperature


        the company can play with the weights depending on the importance of each criteria.



    Problem: when we did  made temperature, tiere dependant:

    chosing hdd with 0.5 always made the decision engini favor the hdd in all cases
    so we will give a slightly lower value.
""" 
import os
import pandas as pd

from modules.storage import simulate_placement, generate_storage_report

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(BASE_DIR, "data", "file_catalog.csv")



def start_decision_engine(config):
    df = pd.read_csv(CATALOG_PATH)

    for _, file_details in df.iterrows():
        best_tier, scores = make_decision(config, file_details)
        simulate_placement(file_details, best_tier, df)

    
    generate_storage_report(df)


def minmax(col):
    denom = col.max() - col.min()

    # if min == max to avoid /0:
    if denom == 0:
        return pd.Series(1.0, index=col.index)

    return (col - col.min()) / denom





def make_decision(config,file_details):

    label = file_details['ml_label'].lower()   # get fie label
    file_size = file_details['size'] # in bytes


    weights = config['weights']
    w_cost, w_latency, w_temp = weights['cost'], weights['latency'], weights['temperature']

    
    pricings = config['pricing']

    # convert file_size to GB:
    file_size = file_size / (1024**3)

    # count cost for each tiere:
    costs = {
        "SSD": file_size * pricings["SSD"],
        "HDD": file_size * pricings["HDD"],
        "ARCHIVE": file_size * pricings["ARCHIVE"]
    }
    
    latencies = config['latencies']

    tieres = ["SSD", "HDD", "ARCHIVE"]


    # make temperature, tiere dependant:
    # this measure how suitable this score for each tiere.

    if label == "hot":
        label_scores = {
            "SSD": 1,
            "HDD": 0,
            "ARCHIVE": 0
        }

    elif label == "warm":
        label_scores = {
            "SSD": 0,
            "HDD": 1,
            "ARCHIVE": 0
        }

    else:
        label_scores = {
            "SSD": 0,
            "HDD": 0,
            "ARCHIVE": 1
        }
   


    
    # normalise costs and latencies
    costs_scores = {k:v for k,v in zip(tieres,minmax(pd.Series(costs.values() )))}
    latencies_scores = {k:v for k,v in zip(tieres,minmax(pd.Series(latencies.values() )))}


    # fonction de decision:
    # en  va calculer ce score pour chaque tiere, ce qui donne la valeur max c'est le choix optimale:

    scores = {}

    for tier in tieres:

        # car quand le prix est bas le score doit etre haut.
        score_cost = 1 - costs_scores[tier]
        score_latency = 1 - latencies_scores[tier]  # same thing lower latency higher score.
        label_score = label_scores[tier]

        score = w_cost*score_cost + w_latency*score_latency + w_temp*label_score 
        scores[tier] = {
            "cost_score": score_cost,
            "latency_score": score_latency,
            "label_score": label_score,
            "score": score
        }

    # get the best tier:
    score_values = [scores[tier]['score'] for tier in tieres]
    index_to_map = score_values.index(max(score_values))
    best_tier = tieres[index_to_map]

    return best_tier, scores

        





