# Cookie Cats A/B Testing — Learning Notes & Interview Preparation Guide

> **Core Context & Experimental Framing**  
> This project analyzes historical data from an A/B test already conducted on the mobile game *Cookie Cats* by Tactile Entertainment (randomized assignment and data collection were completed upfront). We are conducting the **rigorous analysis half of A/B testing** — verifying experiment integrity, hypothesis testing, non-parametric evaluation, guardrail analysis, bootstrapping, and sequential peeking simulations.  
>  
> **Empirical Reporting Discipline**  
> We report strictly what the data empirically supports (differences, effect directions, confidence intervals, p-values). We never assert unverified causal mechanisms (such as "burnout" or "forced rest") as established facts. Where behavioral theories are discussed, they are explicitly labeled as *untested hypotheses*, accompanied by the exact telemetry data needed to test them.

---

## Phase 1: Setup, Exploratory Data Analysis & Outlier Cleaning

### 1. What we did in this phase
We loaded the raw dataset (90,189 player records), validated column schema and missingness, identified a disconnected single extreme outlier in game rounds played (`userid: 6390605` with 49,854 rounds), removed it to yield a clean dataset of 90,188 rows, and analyzed the distribution of game rounds and retention rates across both test variants (`gate_30` and `gate_40`).

### 2. Why this method and not an obvious alternative?
- **Why inspect the distribution tail and drop only a disconnected outlier rather than blindly applying standard $Z$-score or IQR filtering?**  
  Standard IQR/Z-score clipping on engagement data would truncate thousands of legitimate, highly engaged "power users" (whales) whose behavior is valid signal. However, `userid: 6390605` logged 49,854 rounds in 14 days (~3,561 rounds/day, or ~2.5 rounds per minute continuously for two full weeks with no sleep), whereas the second highest player played 2,961 rounds. This value is mathematically and physically disconnected from the data generating process (indicating a bot, test account, or telemetry bug). Dropping this single observation preserves all genuine player variance while preventing an extreme skew of the group mean.
- **Why inspect skewness explicitly during EDA?**  
  Engagement metrics in mobile gaming are almost universally right-skewed with long tails. Confirming extreme positive skewness (mean ~51.9 vs median 16) during EDA provides the empirical justification for selecting a non-parametric test (Mann-Whitney U) instead of a standard Student's t-test in Phase 3.

### 3. What the actual result was, and what it means in plain terms
- **Initial Dataset:** 90,189 rows, 0 nulls across all fields.
- **Outlier Dropped:** UserID `6390605` (`sum_gamerounds = 49,854` in `gate_30`).
- **Cleaned Dataset:** 90,188 rows (`gate_30`: 44,699 users; `gate_40`: 45,489 users).
- **First-Look Baseline Metrics:**
  - Day-1 Retention: `gate_30` = 44.82% vs `gate_40` = 44.23% (Δ = -0.59 percentage points)
  - Day-7 Retention: `gate_30` = 19.02% vs `gate_40` = 18.20% (Δ = -0.82 percentage points)
  - Engagement (`sum_gamerounds`): Median is 16 rounds for both groups; mean is 51.34 (`gate_30`) vs 51.30 (`gate_40`).

### 4. If asked "Why does this matter?" in an interview, what is the one-sentence answer?
> *"Checking data integrity and distributional assumptions before running hypothesis tests prevents automated statistical tools from drawing false conclusions driven by anomalous data entry artifacts or unfulfilled normality assumptions."*

---

## Phase 2: In-Memory SQL Layer (DuckDB) & BI Exports

### 1. What we did in this phase
We registered the cleaned dataset as an in-memory SQL table `cookie_cats` inside DuckDB, wrote standalone, commented SQL aggregation queries to compute group sizes and variant-level retention and engagement metrics, and exported the results to `outputs/summary_by_group.csv` and `outputs/cleaned_data.csv` for Power BI consumption.

### 2. Why this method and not an obvious alternative?
- **Why write explicit SQL via DuckDB rather than just chaining `df.groupby().agg()` in pandas?**  
  In production analytics environments, data resides in data warehouses (Snowflake, BigQuery, Redshift, Databricks), not in-memory pandas dataframes. Demonstrating that you can translate business definitions into clean, portable, and performant SQL queries (`COUNT(*)`, `AVG(CASE WHEN ... THEN 1.0 ELSE 0.0 END)`, `MEDIAN()`) proves that you are warehouse-native and capable of extracting production metrics directly at scale without relying on client-side Python for foundational aggregations.
- **Why export structured CSVs for Power BI?**  
  Enterprise decision-makers consume dashboards, not Python terminal logs or Jupyter notebooks. Producing decoupled, pre-aggregated and clean transactional data feeds ensures seamless BI ingestion, proper star-schema modeling, and rapid dashboard rendering.

### 3. What the actual result was, and what it means in plain terms
- **Query 1 (Group Counts):** `gate_30` = 44,699 users (49.56%); `gate_40` = 45,489 users (50.44%).
- **Query 2 (Aggregations):**
  - **Day-1 Retention:** `gate_30` = 44.82% vs `gate_40` = 44.23% (-0.59 percentage points for Level 40 gate).
  - **Day-7 Retention:** `gate_30` = 19.02% vs `gate_40` = 18.20% (-0.82 percentage points for Level 40 gate).
  - **Mean Game Rounds:** `gate_30` = 51.34 rounds vs `gate_40` = 51.30 rounds.
  - **Median Game Rounds:** `gate_30` = 17.0 rounds vs `gate_40` = 16.0 rounds.

### 4. If asked "Why does this matter?" in an interview, what is the one-sentence answer?
> *"Demonstrating SQL proficiency via DuckDB shows that I can write warehouse-native, production-grade analytical queries that scale across massive distributed datasets, bridging data engineering and business intelligence."*

---

## Phase 3: Core Statistical Hypothesis Testing

### 1. What we did in this phase
We executed Chi-Square tests of independence and Two-Proportion Z-tests on Day-1 and Day-7 retention rates, conducted a non-parametric Mann-Whitney U test on game rounds played, and evaluated retrospective statistical power and Minimum Detectable Effects (MDE).

### 2. Why this method and not an obvious alternative?
- **Why run formal hypothesis tests rather than just comparing percentage rates directly?**  
  Random sampling variation naturally produces observed differences even when no true underlying effect exists. A hypothesis test quantifies the probability ($p$-value) of observing a difference at least as large as the empirical result under the null hypothesis of equal performance, guarding against costly business decisions driven by sample noise.
- **Why Chi-Square and Two-Proportion Z-Test together?**  
  For a $2 \times 2$ contingency table with independent binomial samples, the Chi-Square statistic equals the square of the standard normal two-proportion $Z$-statistic ($\chi^2 = Z^2$) asymptotically. Running both serves as a rigorous mathematical cross-check confirming that asymptotic approximations hold cleanly on our sample ($N > 90,000$).
- **Why the Mann-Whitney U test rather than a Student's t-test for game rounds?**  
  Student's t-test assumes normality (or relies on the Central Limit Theorem for sample means). However, `sum_gamerounds` exhibits extreme right-skewness (skewness $> 4.7$), high kurtosis, and heavy clustering at low values ($>50\%$ of players play $<20$ rounds). The non-parametric Mann-Whitney U test evaluates stochastic dominance by comparing rank sums rather than means, making it robust against extreme skewness and heavy tails.
- **Why calculate retrospective power and Minimum Detectable Effect (MDE)?**  
  A non-significant result ($p > 0.05$, as observed for Day-1 retention) does **not** prove the null hypothesis ("absence of evidence is not evidence of absence"). Calculating achieved power and MDE reveals whether the test failed to achieve significance because there was genuinely no effect, or because the sample size lacked the sensitivity (power) to detect a subtle difference.

### 3. What question each test is actually answering & What the actual result was:
1. **Day-7 Retention Test (Chi-Square & Z-Test):**
   - *Question Answered:* "Is the observed drop in 7-day retention between Level 30 and Level 40 statistically significant or likely due to random chance?"
   - *Result:* `gate_30` = 19.02% vs `gate_40` = 18.20% ($\Delta = -0.82\%$ pts, relative lift = $-4.31\%$). $\chi^2 = 9.96, p = 0.0016; Z = -3.16, p = 0.0016$.
   - *Meaning:* Significant at $\alpha = 0.01$. Placing the gate at Level 40 leads to lower 7-day retention.
2. **Day-1 Retention Test (Chi-Square & Z-Test):**
   - *Question Answered:* "Does gate placement immediately impact whether a new player returns the very next day?"
   - *Result:* `gate_30` = 44.82% vs `gate_40` = 44.23% ($\Delta = -0.59\%$ pts). $\chi^2 = 3.19, p = 0.0739; Z = -1.79, p = 0.0739$.
   - *Meaning:* Inconclusive / not statistically significant at $\alpha = 0.05$.
3. **Engagement Test (Mann-Whitney U):**
   - *Question Answered:* "Do players in one variant systematically play more game rounds overall than players in the other variant?"
   - *Result:* $U = 1,024,285,762, p = 0.0509$. Median rounds = 17 (`gate_30`) vs 16 (`gate_40`).
   - *Meaning:* No statistically significant difference in engagement volume across 14 days.
4. **Retrospective Power Analysis:**
   - *Question Answered:* "Did this experiment have enough statistical sensitivity to detect meaningful changes in retention?"
   - *Result:* Day-7 power was **88.17%** (adequate, MDE = 0.74% pts). Day-1 power was **42.86%** (MDE = 0.94% pts).
   - *Meaning:* The test was adequately powered to detect the Day-7 effect, but underpowered to detect the smaller 0.59% point Day-1 difference.

### 4. If asked "Why does this matter?" in an interview, what is the one-sentence answer?
> *"Selecting the correct test based on distributional properties and cross-checking asymptotic statistics ensures that executive product decisions are grounded in sound probabilistic evidence rather than statistical artifacts."*

---

## Phase 4: Sample Ratio Mismatch (SRM) Check

### 1. What we did in this phase
We performed a Chi-Square goodness-of-fit test comparing the observed user allocations (44,699 in `gate_30` vs 45,489 in `gate_40`) against the expected 50/50 randomized split.

### 2. Why this method and not an obvious alternative?
- **Why perform an SRM check as a prerequisite before trusting metric p-values?**  
  An SRM test is an essential experimental validity check. If the randomization mechanism or tracking pipeline systematically dropped users from one group or assigned them unequally, the fundamental assumption of A/B testing (exchangeability / ceteris paribus) is violated. Downstream metrics can exhibit severe selection bias, rendering all subsequent $p$-values invalid regardless of how "significant" they appear.
- **Why use a strict threshold ($\alpha = 0.01$) for SRM?**  
  With massive sample sizes ($N > 90,000$), tiny incidental fluctuations can trigger statistical tests. Using $\alpha = 0.01$ prevents excessive false alarms while flagging genuine infrastructure or tracking issues.

### 3. What the actual result was, and what it means in plain terms
- **Observed Allocation:** `gate_30` = 44,699 (49.56%) vs `gate_40` = 45,489 (50.44%).
- **Goodness-of-Fit Statistic:** $\chi^2 = 6.9200, p = 0.0085$.
- **Verdict:** Because $p = 0.0085 < 0.01$, this triggers an **SRM Warning**.
- **Practical Meaning:** There is a slight over-representation of users in `gate_40` (+790 users, or ~0.88% delta) that is unlikely to occur under pure 50/50 binomial sampling. In an enterprise setting, an analyst must report this finding to data engineering to audit the hash bucketing and event ingestion pipelines before rolling out decisions.

### 4. If asked "Why does this matter?" in an interview, what is the one-sentence answer?
> *"Checking for Sample Ratio Mismatch verifies the integrity of the randomization mechanism itself; if the split is broken, downstream statistical tests are compromised by selection bias."*

---

## Phase 5: Guardrail Metric Analysis & Empirical Discipline

### 1. What we did in this phase
We synthesized the primary retention results alongside engagement guardrails, applying strict empirical discipline to separate observed statistical facts from speculative causal narratives.

### 2. Why this method and not an obvious alternative?
- **Why monitor guardrail metrics alongside the primary metric?**  
  Evaluating only a single metric creates blind spots. An intervention might increase retention while cratering gameplay volume or monetization. Monitoring guardrail metrics ensures the business does not optimize one KPI at the expense of the broader ecosystem.
- **Why strictly separate empirical observations from speculative causal claims (e.g., 'burnout' or 'forced rest')?**  
  Disciplined analysts never mistake a plausible psychological story for an established empirical fact. The dataset contains only aggregate rounds and return flags. Asserting that "players felt burnout" or "experienced the hedonic treadmill" without session-level telemetry or survey data oversteps what the data proves. Clearly defining what data *would* be required to test these hypotheses demonstrates senior analytical maturity.

### 3. What the actual result was, and what it means in plain terms
- **Empirical Synthesis:** Moving the gate to Level 40 significantly degraded 7-day retention (-0.82% pts, $p = 0.0016$) without generating any compensatory increase in player engagement ($p = 0.0509$, median rounds 17 vs 16).
- **Untested Behavioral Hypotheses (Explicitly Labeled):**
  - *Hypothesis A:* Gating at level 30 forces an early pause that sustains interest, whereas delaying to level 40 exhausts player novelty.
  - *Hypothesis B:* Level 40 is harder to reach, causing players who drop off before level 40 to churn without encountering a gating motivation.
  - *Required Validation Data:* To test these hypotheses, the team would need level-by-level drop-off funnels, session duration distributions, time spent blocked at gates, and in-app purchase logs.

### 4. If asked "Why does this matter?" in an interview, what is the one-sentence answer?
> *"Tracking guardrails prevents optimizing retention at the expense of engagement, but any product recommendation must remain provisional pending an SRM audit — because if the sample imbalance stems from differential logging rather than benign bucketing quirks, even highly significant headline metrics cannot be trusted."*

---

## Phase 6: Advanced Experimentation (Bootstrap, Peeking & CUPED Defense)

### 1. What we did in this phase
We computed empirical 95% percentile bootstrap confidence intervals (10,000 iterations), conducted a sequential peeking simulation to demonstrate Type I error inflation, and documented the methodological justification for intentionally omitting CUPED.

### 2. Why these methods and not obvious alternatives?
- **Why use Bootstrap Percentile Confidence Intervals alongside asymptotic tests?**  
  Asymptotic tests rely on theoretical sampling distributions that assume large sample normal approximations. Non-parametric bootstrap resampling estimates the empirical sampling distribution directly from the observed data by drawing repeated resamples with replacement, providing an assumption-free validation of effect sizes and confidence intervals.
- **Why simulate sequential peeking?**  
  In live product teams, stakeholders frequently monitor live dashboards and stop tests the moment $p < 0.05$. Simulating running tests across sample increments visually demonstrates how "peeking" without alpha-spending corrections dramatically inflates false positive rates.
- **Why was CUPED deliberately NOT implemented?**  
  CUPED (Controlled-experiment Using Pre-Experiment Data) requires a **pre-treatment covariate** (a baseline metric measured *before* the user was assigned to a variant) that correlates with the outcome. In this dataset, all variables (`sum_gamerounds`, `retention_1`, `retention_7`) are measured **post-treatment** (during the 14 days after assignment). Using post-treatment engagement as a covariate would condition on a variable affected by the treatment itself, introducing **collider bias / treatment bias** and invalidating causal inference. Omitting CUPED is a deliberate, mathematically rigorous choice.

### 3. What the actual result was, and what it means in plain terms
- **Bootstrap 95% Percentile Confidence Intervals (10,000 resamples):**
  - **Day-1 Retention Difference (`gate_40` - `gate_30`):** Mean = -0.59% pts, 95% CI = `[-1.25%, +0.06%]`, $P(\text{gate\_30} > \text{gate\_40}) = 96.56\%$.
  - **Day-7 Retention Difference (`gate_40` - `gate_30`):** Mean = -0.82% pts, 95% CI = `[-1.33%, -0.30%]`, $P(\text{gate\_30} > \text{gate\_40}) = 99.96\%$.
  - *Meaning:* The bootstrap interval for Day-7 retention is entirely negative and bounded away from zero, confirming that `gate_30` provides higher 7-day retention with 99.96% empirical confidence.
- **Peeking Simulation Findings:**
  - Evaluated across 60 sequential checkpoints, the unadjusted running $p$-value dropped below $\alpha = 0.05$ in **38 of 60 checkpoints**, illustrating severe alpha-spending vulnerability if early stopping rules are applied naively.

### 4. If asked "Why does this matter?" in an interview, what is the one-sentence answer?
> *"Applying bootstrap resampling validates effect robustness without distribution assumptions, understanding peeking risks prevents false-positive product rollouts, and avoiding post-treatment conditioning preserves true causal inference."*

---
