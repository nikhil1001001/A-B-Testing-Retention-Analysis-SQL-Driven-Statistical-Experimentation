# Cookie Cats A/B Testing: Mobile Game Gate Placement Analysis

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/pytest-11%20passed-success.svg)](tests/)
[![DuckDB](https://img.shields.io/badge/DuckDB-In--Memory%20SQL-yellow.svg)](https://duckdb.org/)
[![Power BI Ready](https://img.shields.io/badge/Power%20BI-CSV%20Exports-orange.svg)](outputs/)

An end-to-end, production-grade statistical analysis of an A/B test conducted on the popular mobile puzzle game **Cookie Cats** (by Tactile Entertainment). This project evaluates whether relocating a progression gate from **Level 30 (Control)** to **Level 40 (Treatment)** impacts player retention and overall engagement.

> 📚 **Interview Preparation:** If you are reviewing this project for a Data / Product Analyst interview, read [LEARNING_NOTES.md](LEARNING_NOTES.md) first. It provides plain-English explanations, methodological defenses, and direct answers to cross-examination questions for every phase.

---

## 1. Project Overview & Business Problem

In mobile gaming, progression gates force players to wait or make an in-app purchase before unlocking subsequent levels. Relocating a gate represents a core trade-off between giving players unhindered early progression and introducing natural pause points.

- **Control (`gate_30`):** First gate placed at Level 30.
- **Treatment (`gate_40`):** First gate delayed to Level 40.
- **Primary KPI:** 7-Day Player Retention (`retention_7`).
- **Secondary / Guardrail KPIs:** 1-Day Player Retention (`retention_1`), 14-Day Game Rounds (`sum_gamerounds`).

---

## 2. Dataset Information

The analysis is performed on the historical A/B testing dataset:
- **Source:** [Kaggle: Mobile Games A/B Testing (Cookie Cats)](https://www.kaggle.com/datasets/yufengsui/mobile-games-ab-testing)
- **Local Location:** `data/cookie_cats.csv`
- **Total Initial Records:** 90,189 players
- **Validated Clean Sample:** 90,188 players (1 disconnected extreme outlier removed: `userid: 6390605` with 49,854 gamerounds)
- **Schema:**
  - `userid` *(int)*: Unique player identifier.
  - `version` *(str)*: Experimental bucket (`gate_30` vs. `gate_40`).
  - `sum_gamerounds` *(int)*: Total game rounds played during the first 14 days post-install.
  - `retention_1` *(bool)*: Did the player return 1 day after installing?
  - `retention_7` *(bool)*: Did the player return 7 days after installing?

---

## 3. Executive Summary of Findings

| Metric / Test | Control (`gate_30`) | Treatment (`gate_40`) | Absolute Lift | Statistical Test | p-value | Significance ($\alpha=0.05$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **7-Day Retention** | **19.02%** | **18.20%** | **-0.82% pts** (-4.31% rel) | $\chi^2$ Independence / 2-Prop Z | **0.0016** | **Significant** ($p < 0.01$) |
| **1-Day Retention** | **44.82%** | **44.23%** | **-0.59% pts** (-1.32% rel) | $\chi^2$ Independence / 2-Prop Z | **0.0739** | Not Significant |
| **14-Day Game Rounds** | Median: **17.0** (Mean 51.34) | Median: **16.0** (Mean 51.30) | -1.0 round median | Mann-Whitney U Test | **0.0509** | Not Significant |
| **Sample Ratio Mismatch** | 44,699 (49.56%) | 45,489 (50.44%) | +790 users in Gate 40 | $\chi^2$ Goodness-of-Fit | **0.0085** | **SRM Warning** ($p < 0.01$) |
| **Bootstrap 95% CI ($\Delta$ Ret-7)** | — | — | **[-1.33%, -0.30%]** | 10,000 Iterations | — | $P(\text{Gate 30} > \text{Gate 40}) = 99.96\%$ |

### Core Strategic Recommendation:
> **Retain the progression gate at Level 30 (Provisional Recommendation).**  
> Moving the gate to Level 40 statistically significantly degrades 7-day retention by **0.82 percentage points** ($p = 0.0016$) without delivering any statistically significant increase in player rounds played ($p = 0.0509$).  
>  
> *SRM Integrity Caveat:* This recommendation is **provisional pending an engineering audit of the allocation imbalance** ($\chi^2 = 6.92, p = 0.0085$). If the audit confirms the imbalance is unrelated to how retention itself was tracked (e.g. an upstream bot-filtering or traffic-bucketing quirk rather than differential event logging/loss), the Day-7 finding stands as reported.

---

## 4. Repository Structure

```
cookie-cats-ab-test/
├── data/
│   └── cookie_cats.csv            # Raw dataset (90,189 rows)
├── src/
│   ├── __init__.py
│   ├── data_prep.py               # Outlier cleaning, validation, schema standardization
│   ├── sql_layer.py               # In-memory DuckDB queries & Power BI CSV export pipeline
│   ├── stats_tests.py             # Chi-Sq, Two-Prop Z, Mann-Whitney U, SRM & Power suite
│   ├── bootstrap.py               # Vectorized 10,000-iteration percentile bootstrap CI
│   └── peeking_simulation.py      # Sequential testing simulation & Type I error visualization
├── notebooks/
│   └── 01_eda.ipynb               # Exploratory Data Analysis & visual inspections
├── outputs/
│   ├── summary_by_group.csv       # Power BI Import 1 (aggregated summary table)
│   ├── cleaned_data.csv           # Power BI Import 2 (row-level cleaned transactional table)
│   ├── stats_report.md            # Formal statistical & business decision report
│   └── peeking_simulation.png     # Sequential testing / peeking alpha-inflation plot
├── tests/
│   ├── __init__.py
│   ├── test_data_prep.py          # Unit tests on data ingestion & outlier removal
│   ├── test_sql_layer.py          # Unit tests on DuckDB aggregation logic
│   ├── test_stats_tests.py        # Unit tests on statistical testing routines
│   └── test_bootstrap.py          # Unit tests on bootstrap CI calculation
├── LEARNING_NOTES.md              # Interview preparation guide (plain English)
├── README.md                      # Recruiter-facing portfolio documentation
├── requirements.txt               # Locked project dependencies
└── .gitignore                     # Standard Python ignore rules
```

---

## 5. Getting Started & How to Run

### Step 1: Clone Repository & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/your-username/cookie-cats-ab-test.git
cd cookie-cats-ab-test

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Run Unit Tests
```bash
pytest -v tests/
```

### Step 3: Run the End-to-End Pipeline
Execute the modules in logical order:
```bash
# 1. Clean data and inspect distributions
python src/data_prep.py

# 2. Run in-memory DuckDB SQL queries and export Power BI CSVs
python src/sql_layer.py

# 3. Execute core hypothesis tests, SRM check, and power analysis
python src/stats_tests.py

# 4. Compute 10,000-iteration percentile bootstrap confidence intervals
python src/bootstrap.py

# 5. Run sequential peeking risk simulation
python src/peeking_simulation.py
```

---

## 6. Power BI Dashboard Integration

The pipeline exports two pre-formatted CSV files in `outputs/` for direct Power BI consumption:
1. `outputs/summary_by_group.csv`: Aggregated card and KPI metrics (`version`, `n_users`, `retention_1_rate`, `retention_7_rate`, `avg_rounds_played`, `median_rounds_played`).
2. `outputs/cleaned_data.csv`: Granular row-level dataset for slicing by engagement tiers and retention cohorts.

---

## 7. Limitations & Methodological Defenses

1. **Absence of Pre-Treatment Covariates (CUPED Omission):**  
   All features (`sum_gamerounds`, `retention_1`, `retention_7`) were measured *after* variant assignment. Applying CUPED or post-stratification on post-treatment variables induces **collider bias / treatment conditioning**, compromising causal claims. CUPED was deliberately omitted for mathematical validity.
2. **Sample Ratio Mismatch (SRM):**  
   The allocation test flagged a slight imbalance ($\chi^2 = 6.92, p = 0.0085 < 0.01$). In production, this requires an engineering audit of the traffic bucketing hash to confirm no selective user drop-off occurred.
3. **Sequential Peeking Simulation Proxy:**  
   Because the dataset does not include event timestamps, `userid` order was used as an explicit proxy for arrival sequence to demonstrate the hazard of continuous monitoring without alpha-spending.
4. **Empirical Fact vs. Behavioral Hypotheses:**  
   Psychological mechanisms (e.g., player pacing, novelty decay) remain **untested hypotheses**. Validating them requires granular level-by-level drop-off telemetry and monetization logs.
