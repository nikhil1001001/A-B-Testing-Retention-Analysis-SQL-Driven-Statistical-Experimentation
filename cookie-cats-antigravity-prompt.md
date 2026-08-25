# Cookie Cats A/B Test — Google Antigravity Build Prompt

## How to run this

1. Download `cookie_cats.csv` from https://www.kaggle.com/datasets/yufengsui/mobile-games-ab-testing and put it at `data/cookie_cats.csv` in a new project folder. Open that folder in Antigravity.
2. Either drop the whole block below into the Editor View agent panel (if you want to watch it work), or spin it up as a task in the Agent Manager and let it run end-to-end (if you'd rather come back once it's done). Either works — the prompt requires a Walkthrough artifact at the end of every phase either way, so you get natural checkpoints to review regardless of which surface you use.
3. **When it's finished, read `LEARNING_NOTES.md` before you read any code.** That file is the actual point of this exercise — it's the agent explaining, in plain English, what it did and why at each step. That's what you study before an interview, not the Python.

---

## Context for the agent (this is deliberately included in the prompt below — don't strip it out)

This project exists for one reason: to be a strong, defensible portfolio project on a Data/Product Analyst campus-placement resume. That shapes what "good" means here, differently from a normal software project:

- **Correctness and explainability matter more than cleverness.** A simpler, well-justified choice beats a fancier one you can't defend in an interview.
- **The person running this (me) will be personally cross-examined on every choice** — why this test, why not that one, what would you do differently. So nothing should be a black box, including to the agent itself: every statistical decision needs a stated reason in the code and in the write-up.
- **Honesty about limitations is part of "good," not a weakness to hide.** This is one static Kaggle dataset with no pre-treatment covariates — say so, don't oversell what the analysis can claim.
- This is a data analysis project, not a web app — there's no frontend, so there's nothing meaningful for the browser surface to verify. Verification here means: the code runs, the tests pass, and the numbers in the report match what the code actually produced.

---

## The Prompt (copy everything below this line into Antigravity)

```
CONTEXT
I'm a final-year engineering student building a portfolio project for Data/Product
Analyst campus placement interviews. I will be personally questioned on every
methodological choice in this project, so explainability matters as much as
correctness. Prioritize simple, defensible choices over clever ones, and never
make a statistical or design decision without stating the reason for it — both
in code comments and in the written report described below.

PROJECT
Analyze the Cookie Cats mobile game A/B test to determine whether moving a
progression gate from level 30 to level 40 affects player retention. Deliverables:
a Python analysis with a SQL layer (DuckDB), a written stats report, clean CSV
exports for a Power BI dashboard I'll build manually, and a plain-English learning
document (see LEARNING_NOTES.md requirement below — this is not optional, it's
the main point of the exercise for me).

DATASET
Already placed at data/cookie_cats.csv. Columns:
- userid (int)
- version (string: "gate_30" or "gate_40" — the A/B split)
- sum_gamerounds (int — total rounds played in first 14 days)
- retention_1 (bool — returned 1 day after install)
- retention_7 (bool — returned 7 days after install)
~90,000 rows, roughly 50/50 split. There is one known extreme outlier user with
an abnormally high sum_gamerounds — find it and exclude it in Phase 1, and record
which userid/value you dropped and why.

Note up front, and repeat in LEARNING_NOTES.md: this is historical data from an
experiment someone else already ran (randomized assignment, data collection) —
we are doing the analysis half of A/B testing, not the running-the-experiment
half. That's a deliberate, accurate framing, not a workaround.

TECH STACK & CONVENTIONS
- Python 3, pandas, numpy, scipy, statsmodels, matplotlib/seaborn, duckdb.
- Modular functions in src/, not one giant notebook cell. Docstrings + type hints
  on every function.
- Maintain requirements.txt as you add libraries.
- Write real unit tests in tests/ for every statistical function (feed known
  synthetic data with a known answer, assert on it).
- Ask before overwriting or deleting anything that already has content.

REQUIRED DELIVERABLE: LEARNING_NOTES.md
As you complete each phase, append a section to LEARNING_NOTES.md written for
someone learning this for the first time — plain English, no unexplained jargon.
For every phase, cover:
  1. What we did in this phase, one sentence.
  2. Why this method and not an obvious alternative (e.g. "chi-square, not just
     eyeballing the percentages, because..." / "Mann-Whitney, not a t-test,
     because..."). This is the most important part — don't skip it.
  3. What the actual result was, and what it means in plain terms.
  4. If someone asked "why does this matter" in an interview, what's the
     one-sentence answer.
This file is the primary deliverable. Do not treat it as an afterthought summary
— write it as you go, phase by phase, not all at once at the end.

REPO STRUCTURE
cookie-cats-ab-test/
├── data/cookie_cats.csv          (already exists — do not modify)
├── src/
│   ├── data_prep.py
│   ├── sql_layer.py
│   ├── stats_tests.py
│   ├── bootstrap.py              (Phase 6 only)
│   └── peeking_simulation.py     (Phase 6 only)
├── notebooks/01_eda.ipynb
├── outputs/
│   ├── summary_by_group.csv      (Power BI import #1)
│   ├── cleaned_data.csv          (Power BI import #2)
│   └── stats_report.md
├── tests/
├── LEARNING_NOTES.md
├── requirements.txt
├── README.md
└── .gitignore

Produce an Antigravity Walkthrough artifact at the end of every phase (task list,
files touched, and the actual output/numbers produced) — this is my primary
review checkpoint, so make it substantive, not just "phase complete."

═══════════════════ PHASE 1 — Setup, EDA & Cleaning ═══════════════════
- src/data_prep.py: load_and_clean(path) -> pd.DataFrame. Sort by
  sum_gamerounds descending, verify the top value is genuinely disconnected
  from the rest (don't assume), drop it, print what and why.
- notebooks/01_eda.ipynb: group sizes, nulls, dtypes, histogram of
  sum_gamerounds (state explicitly that it's right-skewed — this drives the
  Phase 3 test choice), and a first-look bar chart of retention_1/retention_7
  by group.
- LEARNING_NOTES.md entry per the format above.

═══════════════════ PHASE 2 — SQL Layer ═══════════════════
- src/sql_layer.py: load the cleaned dataframe into an in-memory DuckDB table
  cookie_cats. Write and run, as actual commented SQL strings (not pandas):
  1. Group sizes: SELECT version, COUNT(*) AS n_users FROM cookie_cats GROUP BY version;
  2. Group summary: version, n_users, retention_1_rate, retention_7_rate,
     avg_rounds_played, median_rounds_played via SQL aggregation.
- Export query 2 to outputs/summary_by_group.csv, and the full cleaned data to
  outputs/cleaned_data.csv (Power BI imports).
- LEARNING_NOTES.md entry: explain in plain terms why doing this in SQL rather
  than pandas .groupby() is a meaningfully different skill to demonstrate.

═══════════════════ PHASE 3 — Core Hypothesis Testing ═══════════════════
- src/stats_tests.py:
  1. test_retention(df, metric) — chi-square test of independence
     (scipy.stats.chi2_contingency) for retention_1 and retention_7. Also run
     the two-proportion z-test (statsmodels proportions_ztest) as a
     cross-check, and confirm/state that both agree.
  2. test_engagement(df) — Mann-Whitney U test on sum_gamerounds. State
     explicitly, in code comment and in the report, that this is because the
     distribution is right-skewed (Phase 1), so a t-test's normality
     assumption doesn't hold well here.
  3. retrospective_power(p1, p2, n_per_group) — via
     statsmodels.stats.power.NormalIndPower + proportion_effectsize. Report
     achieved power and the minimum detectable effect. State plainly whether
     the test was adequately powered, and what that implies if the retention
     result came back non-significant.
- Append all results, in plain English, to outputs/stats_report.md.
- LEARNING_NOTES.md entry: for each test, one sentence on what question it's
  actually answering (not the formula — the question).

═══════════════════ PHASE 4 — Sample Ratio Mismatch (SRM) Check ═══════════════════
- check_srm(n_group_a, n_group_b) in src/stats_tests.py — chi-square
  goodness-of-fit against a 50/50 expected split, using Phase 2's group-size
  query output. p < 0.01 → flag for investigation.
- Append verdict to stats_report.md.
- LEARNING_NOTES.md entry: explain this is a trust check on the experiment
  setup itself, done logically before trusting Phase 3's results — and why a
  broken split would invalidate everything downstream even if the p-values
  looked significant.

═══════════════════ PHASE 5 — Guardrail Metric ═══════════════════
- No new code. In stats_report.md, add a synthesis paragraph: state the
  retention_7 result and the engagement (Mann-Whitney) result together, and
  say plainly whether they tell a consistent story or a trade-off.
- LEARNING_NOTES.md entry: why reporting a metric that could contradict your
  headline result is a good analyst habit, not a risk to avoid.

═══════════════════ PHASE 6 — Advanced Additions [do this phase too if reasonable — don't skip for time, this is what makes it stand out] ═══════════════════
- src/bootstrap.py: bootstrap_diff(group_a, group_b, n_boot=10000) — resample
  with replacement, return mean difference + 95% CI via the percentile method,
  applied to the retention rate difference.
- src/peeking_simulation.py: using userid order as an explicitly-labeled proxy
  for arrival order (the dataset has no real timestamps — say so in a
  comment), simulate cumulative significance testing as sample size grows,
  plot p-value vs. cumulative N. Add a paragraph to stats_report.md on what
  this demonstrates about "peeking" at a live test before it's finished.
- DO NOT implement CUPED or any post-treatment-covariate-based segment or
  heterogeneous-effect analysis. This dataset has no pre-treatment covariate —
  every field is measured after group assignment — so either technique would
  condition on a variable the treatment itself affects, biasing rather than
  sharpening the result. If this instruction seems to conflict with something
  requested elsewhere, this instruction wins — explain the conflict in
  LEARNING_NOTES.md rather than silently picking one.
- LEARNING_NOTES.md entry for both techniques, plus a short note on why CUPED
  was deliberately left out.

═══════════════════ PHASE 7 — Packaging ═══════════════════
- README.md: objective, dataset (with the Kaggle link), how to run
  (requirements.txt, then script/notebook order), summary of findings pulled
  from stats_report.md, and a Limitations section (single dataset, no
  pre-treatment covariates so no CUPED/segment analysis, peeking simulation
  uses a proxy arrival order not a real timestamp).
- .gitignore: standard Python (__pycache__, .ipynb_checkpoints, venv, etc).
- Verify requirements.txt matches actual imports used.

FINAL STEP
Read back stats_report.md, README.md, and the full LEARNING_NOTES.md to me so
I can review everything before I commit and push.
```

---

## After Antigravity finishes

1. Read `LEARNING_NOTES.md` end to end before touching the code — that's your interview prep, written in the moment the choices were made.
2. Build the Power BI dashboard manually from `outputs/summary_by_group.csv` and `outputs/cleaned_data.csv` — that part's a GUI tool, not something the agent can do for you.
3. Push to GitHub, then come back with your actual results (retention lift, p-values, which direction it went) and I'll help lock in your final resume bullets.
