# Approche Hybride d'Optimisation Multi-Objectifs pour le Stockage et le Traitement Adaptatif dans les Architectures Big Data

> Prototype académique — Master Big Data & Intelligence Artificielle (2025–2026)

---

## Table des matières

1. [Présentation du projet](#présentation-du-projet)
2. [Architecture du pipeline](#architecture-du-pipeline)
3. [Description des modules](#description-des-modules)
4. [Technologies utilisées](#technologies-utilisées)
5. [Structure du projet](#structure-du-projet)
6. [Installation et lancement](#installation-et-lancement)
7. [Résultats obtenus](#résultats-obtenus)
8. [Références scientifiques](#références-scientifiques)

---

## Présentation du projet

Les systèmes Big Data modernes font face à des défis critiques : saturation des espaces de stockage, coûts d'infrastructure élevés, dégradation des performances d'accès, et présence massive de données redondantes ou de faible qualité.

Ce projet propose une **architecture intelligente en pipeline** capable d'optimiser simultanément le traitement et le stockage de données massives, en s'appuyant sur :

- la **classification automatique** des données selon leur fréquence d'usage (Hot / Warm / Cold)
- le **traitement adaptatif** (déduplication, normalisation, filtrage) calibré par classe
- la **compression adaptative** via trois algorithmes sélectionnés dynamiquement
- un **moteur de décision multi-objectifs** minimisant coût, latence et redondance
- un **stockage hiérarchique intelligent** (SSD / HDD / Archive)

---

## Architecture du pipeline

```
Fichiers bruts (réels ou synthétiques)
            │
            ▼
  ┌─────────────────────┐
  │   utils.py          │  Génération des fichiers synthétiques + file_catalog.csv
  └─────────────────────┘
            │
            ▼
  ┌─────────────────────┐
  │   analysis.py       │  Mise à jour du catalogue + Feature Engineering
  └─────────────────────┘
            │
            ▼
  ┌─────────────────────┐
  │  classification.py  │  Règles MCDA + Random Forest → labels Hot/Warm/Cold
  └─────────────────────┘
            │
            ▼
  ┌─────────────────────┐
  │  precompressing.py  │  Déduplication MD5 + Normalisation + Filtrage
  └─────────────────────┘
            │
            ▼
  ┌──────────────────────────────────────────┐
  │  compression.py + semantic_compression.py │  Snappy / ZSTD / GZIP + LLM sémantique
  └──────────────────────────────────────────┘
            │
            ▼
  ┌─────────────────────┐
  │  cost_evaluation.py │  Coût mensuel, gain de stockage, pénalité d'accès
  └─────────────────────┘
            │
            ▼
  ┌─────────────────────┐
  │  decision_engine.py │  Score multi-objectifs → décision optimale
  └─────────────────────┘
            │
            ▼
  ┌─────────────────────┐
  │  tiered_storage.py  │  Placement SSD / HDD / Archive
  └─────────────────────┘
```

---

## Description des modules

### `utils.py` — Génération et initialisation

Génère **3 000 fichiers synthétiques** simulant un environnement Big Data réel :

- **Distribution logarithmique des tailles** (1 Ko – 500 Ko) : nombreux petits fichiers, peu de grands fichiers, comme en production
- **Nommage par UUID** : `<uuid>_<nom>_<numéro>.<ext>` — identifiant unique résistant aux renommages, utilisé pour la déduplication et la mise à jour du catalogue
- **Métadonnées aléatoires** : `last_accessed` = date courante − random(0, 365 jours)
- **Génération de `file_catalog.csv`** : colonnes `file_id`, `name`, `type`, `size`, `access_freq`, `last_access_date`, `path`
- **Génération de `ml_train_metadata.csv`** : données d'entraînement pour le classificateur ML

> **Problème résolu** : les IDEs modifient `last_accessed` à l'ouverture d'un dossier. Solution : les fichiers synthétiques sont placés dans un dossier **externe** au projet, référencé par un lien symbolique interne.

---

### `analysis.py` — Analyse et Feature Engineering

Met à jour `file_catalog.csv` et prépare les features pour la classification :

- **Mise à jour optimisée du catalogue** : détecte les fichiers renommés, supprimés ou modifiés via leur UUID. L'approche v2 régénère le catalogue complet en < 30 secondes (vs > 10 minutes pour l'approche v1 par diff ligne à ligne)
- **Feature engineering** : création de `last_access_days_ago` (nombre de jours depuis le dernier accès)
- Lance la génération de `ml_train_metadata.csv` pour l'entraînement

---

### `classification.py` — Classification Hot / Warm / Cold

Deux méthodes combinées pour une classification robuste :

#### 1. Règles MCDA (Multi-Criteria Decision Analysis)

Basé sur trois critères pondérés selon leur importance métier :

| Critère  | Poids | Logique |
|----------|-------|---------|
| Récence  | 60%   | Fichier récemment accédé → température haute |
| Fréquence | 30%  | Fichier souvent consulté → température haute |
| Taille   | 10%   | Fichier volumineux → température basse (coût de stockage premium) |

**Formule de température** (après normalisation Min-Max et inversion de récence et taille) :

```
Temp = 0.6 × recency + 0.3 × freq + 0.1 × (1 - size)
```

**Labels attribués** :
- `Temp ≥ 0.75` → **HOT**
- `Temp ≤ 0.25` → **COLD**
- `0.25 < Temp < 0.75` → **WARM**

Un **bruit aléatoire** est ajouté aux valeurs proches des seuils (zones grises) pour éviter que le modèle ML apprenne mécaniquement la formule — technique de régularisation standard.

#### 2. Random Forest (ML)

Hyperparamètre tuning appliqué. Le modèle capture les zones grises que les règles strictes ne gèrent pas correctement. Sauvegardé au format `.pkl`. Produit `label_rule` et `label_ml` dans le catalogue.

---

### `precompressing.py` — Traitement Adaptatif

Prétraitement intelligent avant compression, calibré selon la classe :

| Classe | Traitement appliqué |
|--------|---------------------|
| **Hot** | Minimal (priorité vitesse) |
| **Warm** | Standard |
| **Cold** | Complet (priorité optimisation stockage) |

Opérations : **déduplication MD5**, **normalisation** (dates, nombres, formats texte), **filtrage** des valeurs manquantes ou invalides.

---

### `compression.py` — Compression Adaptative

Trois algorithmes **lossless** (compression réversible sans perte) sélectionnés selon la température du fichier :

| Classe | Algorithme | Caractéristique |
|--------|-----------|-----------------|
| **Hot** | **Snappy** | Compression rapide, priorité vitesse |
| **Warm** | **ZSTD** | Meilleur ratio vitesse / taux de compression |
| **Cold** | **GZIP** | Taux de compression maximal |

Chaque compression passe un **test loopback** (compression → décompression) pour garantir l'intégrité des données.

---

### `semantic_compression.py` — Compression Sémantique (LLM)

Pour les fichiers texte classés **Cold**, une compression sémantique est appliquée via un LLM local (Ollama) :

- **Modèle** : `qwen2.5:0.5b` (faible consommation CPU/RAM/GPU, contexte 32 768 tokens ≈ 80–120k caractères)
- **Découpage intelligent** via `RecursiveCharacterTextSplitter` (LangChain) :
  - `chunk_size = 30 000` caractères
  - `chunk_overlap = 500` caractères (contexte transmis au bloc suivant)
  - Découpage hiérarchique : paragraphes → phrases → mots → caractères
- Maximum **3 tentatives** par bloc ; bloc ignoré si dépassé
- Résultats observés : jusqu'à **95% de réduction** sur fichiers `.md`

---

### `cost_evaluation.py` — Évaluation des Coûts (Module 5)

Calcule trois métriques économiques pour chaque fichier :

**1. Coût mensuel de stockage** (USD / Go / mois) :
```
coût = taille_compressée (Go) × prix_tier
```

| Tier    | Prix (USD/Go/mois) | Latence |
|---------|--------------------|---------|
| SSD     | $0.10              | 5 ms    |
| HDD     | $0.03              | 20 ms   |
| Archive | $0.005             | 500 ms  |

**2. Gain de stockage** :
```
gain (%) = (taille_originale - taille_compressée) / taille_originale × 100
```

**3. Pénalité d'accès** :
```
pénalité = température × latence_tier
```
Capture le coût "caché" d'une donnée chaude placée sur un tier lent.

**Résultats clés** (dataset de démonstration, 155 fichiers) :
- Gain moyen de compression : **49.13%**
- Réduction de coût vs tout-SSD : **36%**
- Pénalité d'accès du tiering vs tout-Archive : **25× plus faible**

---

### `decision_engine.py` + `tiered_storage.py` — Décision et Stockage Hiérarchique

**Score multi-objectifs** (à minimiser) :
```
score = 0.4 × coût_normalisé + 0.3 × latence_normalisée + 0.3 × température
```

Placement final selon la décision optimale :

| Classe | Tier    | Justification |
|--------|---------|---------------|
| Hot    | SSD     | Accès rapide prioritaire |
| Warm   | HDD     | Compromis coût / performance |
| Cold   | Archive | Coût minimal, accès rare |

---

## Technologies utilisées

| Domaine | Technologie |
|---------|------------|
| Langage | Python 3.x |
| Analyse de données | Pandas, NumPy |
| Machine Learning | Scikit-Learn (Random Forest) |
| Compression | `zstandard`, `python-snappy`, `gzip` |
| Compression sémantique | Ollama (`qwen2.5:0.5b`), LangChain |
| Visualisation | Matplotlib |
| Déduplication | `hashlib` (MD5) |
| Identification | `uuid` |

---

## Structure du projet

```
Approche Hybride d'Optimisation Multi-Objectifs/
│
├── config.json                  # Paramètres : prix tiers, latences, poids du score
├── main.py                      # Point d'entrée — orchestre tout le pipeline
├── initialize_project.py        # Initialisation des dossiers et liens symboliques
├── utils.py                     # Génération fichiers synthétiques + catalogues
├── update_new_file_names.py     # Mise à jour des noms dans le catalogue
│
├── modules/
│   ├── analysis.py              # Feature engineering + mise à jour catalogue
│   ├── classification.py        # Classification MCDA + Random Forest
│   ├── precompressing.py        # Déduplication + normalisation + filtrage
│   ├── compression.py           # Compression adaptative (Snappy/ZSTD/GZIP)
│   ├── semantic_compression.py  # Compression sémantique LLM (Cold uniquement)
│   ├── cost_evaluation.py       # Calcul coût / gain / pénalité
│   ├── decision_engine.py       # Moteur de décision multi-objectifs
│   └── tiered_storage.py        # Placement SSD / HDD / Archive
│
├── data/
│   ├── file_catalog.csv         # Catalogue principal des fichiers
│   ├── ml_train_metadata.csv    # Données d'entraînement ML
│   ├── storage_report.json      # Rapport final de placement (Module 7)
│   ├── compression_report.json  # Statistiques de compression
│   └── ...
│
├── real_test_files/             # Fichiers réels pour tests
├── synthetic_files/             # Fichiers synthétiques générés (lien symbolique)
│
├── README.md                    # Ce fichier
├── .gitignore
├── plan.md
└── rapport.docx
```

---

## Installation et lancement

### Prérequis

```bash
Python >= 3.9
Ollama installé localement (pour la compression sémantique)
```

### Installation des dépendances

```bash
pip install pandas numpy scikit-learn zstandard python-snappy matplotlib langchain-text-splitters
```

### Lancer Ollama (compression sémantique)

```bash
ollama pull qwen2.5:0.5b
ollama serve
```

### Lancer le pipeline complet

```bash
python main.py
```

### Initialisation (première utilisation uniquement)

```bash
python initialize_project.py
```

---

## Résultats obtenus

| Métrique | Valeur |
|----------|--------|
| Gain moyen de compression | **49.13%** |
| Gain compression sémantique (fichiers `.md`) | **jusqu'à 95.43%** |
| Réduction de coût vs stockage tout-SSD | **36%** |
| Pénalité d'accès tiering vs tout-Archive | **25× plus faible** |
| Précision classificateur Random Forest | Voir `classification_report` dans les logs |
| Fichiers traités (démo) | **155 fichiers** |

---

## Références scientifiques

- **DITIS (2025)** — Stockage hiérarchique intelligent, optimisation SSD/HDD
- **xCache (2024)** — Compression adaptative et sélection dynamique d'algorithmes
- **Dynamic Multi-Objective Big Data Optimization Framework (2024)** — Optimisation multi-objectifs, minimisation des coûts
- **Adaptive Metaheuristic Framework (2024)** — Adaptation dynamique et prise de décision intelligente
- Machine Learning-Based Caching and Tiering in Modern Data Storage Systems — [ACM DL](https://dl.acm.org/doi/epdf/10.1145/3803857)
- MCDA Reference — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S266618882600016X)
- Semantic Compression — [arXiv:2304.12512](https://arxiv.org/abs/2304.12512)
- Compression Algorithms — [apxml.com](https://apxml.com/courses/intro-data-lake-architectures/chapter-2-file-formats-and-optimization/compression-algorithms)

---

> **Note** : Ce projet est un prototype académique développé dans le cadre d'un Master Big Data & IA. Le dataset de démonstration est synthétique (~7 Mo). L'architecture est conçue pour passer à l'échelle sur des volumes réels (To+).