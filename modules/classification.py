"""
Classification des fichiers en Hot, Warm, Cold.
avec 2 approches: par regles simples 
               et  Machine Learning avec scikit-learn.
"""


import joblib
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_ENTRAINEMENT = os.path.join(BASE_DIR, "data", "ml_train_metadata.csv")
CATALOG_PATH = os.path.join(BASE_DIR, "data", "file_catalog.csv")

MODEL_PATH = os.path.join(BASE_DIR,"data" ,"models", "hot_warm_cold_rf.pkl")


CLASS_REPORT_PATH = os.path.join(BASE_DIR, "data", "results", "classification_report.txt")

def minmax(col):
    denom = col.max() - col.min()

    # if min == max to avoid /0:
    if denom == 0:
        return pd.Series(1.0, index=col.index)

    return (col - col.min()) / denom




def classify_with_scoring(df):
    """
    This will be used to give labels to our synthetic files (to train ML model)
    Instead of using simple method like classifying based on frequency 
    i will use a method that considers 3 factors : file size , frequency and recency 
    based on a reference paper titled: "Machine Learning-Based Caching and Tiering in ModernData Storage Systems: A Survey"
    https://dl.acm.org/doi/epdf/10.1145/3803857


    So to make a scoring function i will use the MCDA (Multi-Criteria Decision Analysis) 
    https://www.sciencedirect.com/science/article/pii/S266618882600016X#sec0005
    idea to rank each criteria based on their importance to a total of 100:
    "Recency" 60% (0.6)
    "Frequency" 30% (0.3)
    "Size" 10% (0.1)

    to make a function: temp = 0.6 *recency + 0.3*freq + 0.1*size . 

    So these 3 columns need to be feature engineered before.
    where all features are normalised.

    Because the rule based method is very strict. we will need to use a machine learning
    model to catch all borderline cases because it's more flexible.

    because size stored in hot tieres is related to cost the more size the more the cost. 
    this is why "size" is the least important criteria. 

    so we will need to inverse it when creating our scoring function: 
    size = 1 - normlized_size 

    same thing for recency because the more days the less the recency.
    recency = 1 - normalized_recency.

    Ajout de noise pour que model classify gray areas and not just search for 
    the formula.
    """

    df_result = df.copy()

    # min max normalization:
    freq = minmax(df_result["access_freq"])
    size = 1 - minmax(df_result["size"])
    recency = 1 - minmax(df_result["last_access_days_ago"])

    # calculate temperature:
    df_result['temperature'] = 0.6*recency + 0.3*freq + 0.1*size  # entre [0,1]

    # cree des ecart entre -0.06 et 0.06:  car ~95% des valeur entre -2*std et +2*std.
    # loc=0 pour centraliser les valeurs autour de 0.
    noise = np.random.normal(loc=0, scale=0.03, size=len(df_result))
    
    score_with_noise = np.clip(df_result['temperature'] + noise, 0, 1)

    # we can use quartiles of [0,1] 
    # 0,  Q1(25%) = 0.25, Q2(50%)= 0.5, Q3(75%)= 0.75, Q4(100%)= 1
    
    conditions = [
         (score_with_noise >= 0.75),
         (score_with_noise <= 0.25)
    ]

    choices = ["Hot", "Cold"]

    df_result["label"] = np.select(conditions, choices, default="Warm")



    return df_result






def predict_using_model():
    """
        use saved model from previous training.
    """
    clf = joblib.load(MODEL_PATH)

    df = pd.read_csv(CSV_ENTRAINEMENT)
    
    X = df[["size", "access_freq", "last_access_days_ago"]]
    y = clf.predict(X)
    

    code_labels= {0: "Hot", 1: "Warm", 2: "Cold"}



    predictions_labels = []
    for val in y:
        predictions_labels.append(code_labels[val])

    df['ml_label'] = predictions_labels

    df.to_csv(CSV_ENTRAINEMENT, index=False)

    update_cataloge_with_classes(df)
    




def classify_ml(config, use_saved_model=False):
    """
    Utiliser pour etre un alternative flexible qui peut capturer les zones 
    grises (borderline cases).
    """


    if use_saved_model:
        return predict_using_model()
        

    # synthetic training data currently we need to generate it using utils.py.
    # but in the future we will use real data from our files.
    df = pd.read_csv(CSV_ENTRAINEMENT)
    
    # temperature not given to the model so the model can learn it from the features.
    # file_id is not given so the model dont learn a pattern from it.
    X = df[["size", "access_freq", "last_access_days_ago"]]
    y = df["label"]
    

    # encoder les labels
    y_num = y.replace({"Hot": 0, "Warm": 1, "Cold": 2}).astype(int)
    

    # train test split
    r_state = config.get("random_seed", 42)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_num, test_size=0.25, random_state=r_state, stratify=y_num
    )
    


    # model training:
    rf = RandomForestClassifier(random_state=r_state)
    
    param_grid = {
    "n_estimators": [50, 100, 200],
    "max_depth": [None, 5, 10, 20],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4]
    }


    grid = GridSearchCV(
    estimator=rf,
    param_grid=param_grid,
    cv=5,
    scoring="accuracy",
    n_jobs=-1
    )

    grid.fit(X_train, y_train)

    clf = grid.best_estimator_


        
    
    # Evaluation
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    

    # Rapport detaille
    rapport = classification_report(y_test, y_pred, target_names=["Hot", "Warm", "Cold"], zero_division=0)
    print(f"\nReport details:\n{rapport}")
    

    # ---------- fin de training




    # ---------- Prediction de nos fichiers avec format dans format txt a la place de numero de classe.
    X_fichiers = df[["size", "access_freq", "last_access_days_ago"]]

    preds_fichiers = clf.predict(X_fichiers)
    

    # reconstruire les labels texte
    code_labels= {0: "Hot", 1: "Warm", 2: "Cold"}



    predictions_labels = []
    for val in preds_fichiers:
        predictions_labels.append(code_labels[val])
         


    df_out = df.copy()
    df_out["ml_label"] = predictions_labels


    joblib.dump(clf,MODEL_PATH)
        

    update_cataloge_with_classes(df_out)

    generate_classification_report(accuracy, rapport)





def update_cataloge_with_classes(df_out):
    catalog = pd.read_csv(CATALOG_PATH)

    catalog = catalog.merge(
        df_out[["file_id", "ml_label"]],
        on='file_id'
    )

    catalog.to_csv(CATALOG_PATH, index=False)






def generate_classification_report(accuracy, report):

    with open(CLASS_REPORT_PATH, "w") as f:
        f.write(f"Accuracy: {accuracy}\n\n")
        f.write("Classification Report:\n")
        f.write(report)
    