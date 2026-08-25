# Statistical Analysis & Experimentation Report: Cookie Cats A/B Test

**Experiment:** Cookie Cats Progression Gate Placement (`gate_30` vs. `gate_40`)  
**Dataset Scope:** Historical A/B Test Data (90,188 validated player records)  
**Primary Metric:** 7-Day Player Retention (`retention_7`)  
**Secondary / Guardrail Metrics:** 1-Day Player Retention (`retention_1`), 14-Day Game Rounds (`sum_gamerounds`)  

---

## 1. Executive Summary

This report evaluates the randomized A/B test conducted on the mobile game *Cookie Cats* to determine whether relocating the initial progression gate from **Level 30 (Control)** to **Level 40 (Treatment)** impacts player retention and gameplay engagement.

### Key Empirical Findings:
1. **Primary Metric (7-Day Retention):** Moving the gate to Level 40 resulted in a statistically significant **0.82 percentage point decrease** in 7-day retention (Control: **19.02%** vs. Treatment: **18.20%**, $\chi^2 = 9.96$, $p = 0.0016$, Two-Proportion $Z = -3.16$, $p = 0.0016$).
2. **Secondary Metric (1-Day Retention):** Day-1 retention showed a minor negative difference of **-0.59 percentage points** (Control: **44.82%** vs. Treatment: **44.23%**), but this difference was **not statistically significant** at the $\alpha = 0.05$ level ($\chi^2 = 3.19, p = 0.0739$).
3. **Guardrail Metric (14-Day Engagement):** A non-parametric Mann-Whitney U test revealed no statistically significant difference in rounds played between groups ($U = 1,024,285,762, p = 0.0509$). The median rounds played were 17 in `gate_30` vs. 16 in `gate_40`.
4. **Sample Ratio Mismatch (SRM):** A Chi-Square goodness-of-fit test on sample allocations (44,699 vs. 45,489) yielded $\chi^2 = 6.92, p = 0.0085$, crossing the standard $p < 0.01$ threshold. This indicates a minor sample allocation imbalance that must be investigated in the logging/randomization pipeline.
5. **Business Recommendation:** **Do not roll out `gate_40`.** Keep the progression gate at **Level 30**, as `gate_30` yields superior long-term player retention without harming gameplay volume.

---

## 2. Experimental Hygiene & Pre-Analysis Checks

### 2.1 Outlier Detection & Data Cleaning
- **Initial Sample:** 90,189 player records.
- **Outlier Identified:** User ID `6390605` recorded **49,854 game rounds** within 14 days (~3,561 rounds/day). The next highest player recorded **2,961 rounds**.
- **Action Taken:** Excluded User ID `6390605` as an unphysical outlier / telemetry artifact.
- **Cleaned Sample:** **90,188 validated records** (`gate_30`: 44,699; `gate_40`: 45,489).

### 2.2 Sample Ratio Mismatch (SRM) Validation
Before drawing causal inferences from test metrics, we test whether user allocation adheres to the intended 50/50 randomized split.

| Variant | Observed Count | Expected Count (50/50) | Allocation % |
| :--- | :--- | :--- | :--- |
| **Control (`gate_30`)** | 44,699 | 45,094.0 | 49.56% |
| **Treatment (`gate_40`)** | 45,489 | 45,094.0 | 50.44% |
| **Total** | **90,188** | **90,188.0** | **100.00%** |

- **Test Statistic ($\chi^2$):** $6.9200$
- **p-value:** $0.0085$
- **Decision Rule:** $p < 0.01 \implies$ **SRM Detected (Flag for Pipeline Audit)**
- **Methodological Context:** In industry experimentation, an SRM check flags potential assignment bias, bot-filtering discrepancies, or tracking dropped events. While the magnitude of imbalance is modest (0.88% delta), mature data teams flag this for data engineering review before taking critical product bets.

---

## 3. Core Statistical Hypothesis Testing

### 3.1 Primary Metric: 7-Day Retention (`retention_7`)
- **Hypothesis:**  
  - $H_0: p_{\text{gate\_40}} = p_{\text{gate\_30}}$ (Moving gate to level 40 has no effect on Day-7 retention)  
  - $H_1: p_{\text{gate\_40}} \neq p_{\text{gate\_30}}$ (Day-7 retention differs between versions)

| Metric | Control (`gate_30`) | Treatment (`gate_40`) | Absolute Difference | Relative Lift |
| :--- | :--- | :--- | :--- | :--- |
| **Retained Users** | 8,501 / 44,699 | 8,279 / 45,489 | — | — |
| **Retention Rate** | **19.02%** | **18.20%** | **-0.82% pts** | **-4.31%** |

- **Chi-Square Test of Independence:** $\chi^2 = 9.9590, \text{dof} = 1, p = 0.0016$
- **Two-Proportion Z-Test:** $Z = -3.1558, p = 0.0016$
- **Cross-Check Agreement:** Confirmed asymptotic consistency ($Z^2 \approx \chi^2$).
- **Conclusion:** **Reject $H_0$ at $\alpha = 0.01$.** Day-7 retention is significantly lower when the gate is moved to Level 40.

---

### 3.2 Secondary Metric: 1-Day Retention (`retention_1`)
- **Hypothesis:**  
  - $H_0: p_{\text{gate\_40}} = p_{\text{gate\_30}}$  
  - $H_1: p_{\text{gate\_40}} \neq p_{\text{gate\_30}}$

| Metric | Control (`gate_30`) | Treatment (`gate_40`) | Absolute Difference | Relative Lift |
| :--- | :--- | :--- | :--- | :--- |
| **Retained Users** | 20,034 / 44,699 | 20,119 / 45,489 | — | — |
| **Retention Rate** | **44.82%** | **44.23%** | **-0.59% pts** | **-1.32%** |

- **Chi-Square Test of Independence:** $\chi^2 = 3.1930, p = 0.0739$
- **Two-Proportion Z-Test:** $Z = -1.7869, p = 0.0739$
- **Conclusion:** **Fail to reject $H_0$ at $\alpha = 0.05$.** Day-1 retention difference is not statistically distinguishable from random noise.

---

### 3.3 Guardrail / Engagement Metric: Total Game Rounds (`sum_gamerounds`)
- **Distributional Property:** Skewness = $4.71$, confirming extreme positive skew and heavy right tail.
- **Test Choice:** **Mann-Whitney U Test** (Non-parametric rank-sum test). A Student's t-test's normality assumption is violated.

| Variant | Mean Rounds | Median Rounds | IQR (25th - 75th) | Mann-Whitney U | p-value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `gate_30` | 51.34 | **17.0** | 5.0 - 50.0 | \multirow{2}{*}{$1,024,285,762$} | \multirow{2}{*}{**0.0509**} |
| `gate_40` | 51.30 | **16.0** | 5.0 - 52.0 | | |

- **Conclusion:** **Fail to reject $H_0$ at $\alpha = 0.05$.** The distribution of game rounds played does not exhibit a statistically significant shift between gate levels.

---

### 3.4 Retrospective Statistical Power & Minimum Detectable Effect (MDE)
Evaluated using `statsmodels.stats.power.NormalIndPower` at $\alpha = 0.05$ (two-sided) with $N \approx 44,699$ per group:

| Metric | Baseline ($p_1$) | Observed ($p_2$) | Effect Size ($h$) | Achieved Power | MDE (at 80% Power) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Day-7 Retention** | 19.02% | 18.20% | -0.0210 | **88.17%** | **0.74% pts** |
| **Day-1 Retention** | 44.82% | 44.23% | -0.0119 | **42.86%** | **0.94% pts** |

- **Power Interpretation:**
  - **Day-7 Retention:** With 88.17% power, the sample size was fully adequate to detect the observed -0.82% point effect.
  - **Day-1 Retention:** The Minimum Detectable Effect at 80% power was 0.94 percentage points. Because the observed difference was only 0.59 percentage points, the experiment had only 42.86% power to detect a delta of that scale. This explains why the Day-1 test yielded an inconclusive p-value ($p = 0.0739$).

---

## 4. Guardrail Metric Synthesis & Empirical Discipline

### 4.1 Metric Synthesis
When synthesizing the primary metric (`retention_7`) and the engagement metric (`sum_gamerounds`):
- Moving the gate to Level 40 produced a **clear negative impact on 7-day retention (-0.82% pts, $p = 0.0016$)**.
- Total game rounds played remained **statistically unchanged ($p = 0.0509$)**, with median rounds virtually identical (17 vs. 16).
- There is **no positive engagement trade-off** offsetting the drop in player retention.

### 4.2 Distinguishing Empirical Facts from Untested Hypotheses
As a core analytical discipline, we report only what the observed data empirically substantiates:
- **Empirical Facts:** Day-7 retention is lower in `gate_40`. Engagement across 14 days shows no significant increase.
- **Untested Behavioral Hypotheses:** Explanations such as "player burnout," "the hedonic treadmill," "forced rest pauses renewing interest," or "frustration at higher difficulty gates" are **plausible behavioral hypotheses, NOT established empirical facts**.
- **Data Required to Test These Hypotheses:**
  To validate *why* players churned between level 30 and level 40, the product team would need additional granular telemetry:
  1. *Level-by-level progression timestamps:* Measuring exact drop-off rates at levels 30, 31, ..., 40.
  2. *Session duration and inter-session intervals:* Checking if gate encounters cause users to take beneficial rest breaks vs. abandon the app.
  3. *In-app purchase & monetization logs:* Measuring whether gate placement influences monetization conversion or paywall frustration.
  4. *Churn survey telemetry:* In-app feedback on reasons for stopping play.

---

## 5. Advanced Experimentation Techniques

### 5.1 Non-Parametric Bootstrap Resampling (10,000 Iterations)
To estimate the difference in retention rates without asymptotic normality assumptions, we performed a 10,000-iteration empirical percentile bootstrap:

| Metric Difference (`gate_40` - `gate_30`) | Bootstrap Mean Diff | Bootstrap Std Error | 95% Percentile CI | $P(\text{Gate 30} > \text{Gate 40})$ |
| :--- | :--- | :--- | :--- | :--- |
| **Day-1 Retention Difference** | -0.5938% pts | 0.334% pts | `[-1.2532%, +0.0596%]` | **96.56%** |
| **Day-7 Retention Difference** | -0.8195% pts | 0.264% pts | `[-1.3320%, -0.2976%]` | **99.96%** |

- **Bootstrap Insight:** The 95% confidence interval for Day-7 retention strictly excludes zero (`[-1.33%, -0.30%]`), providing non-parametric confirmation that `gate_30` outperforms `gate_40` with 99.96% empirical posterior certainty.

---

### 5.2 Sequential Testing & Peeking Simulation
In live experimentation, stakeholders frequently "peek" at dashboards daily and stop tests early when $p < 0.05$. We simulated cumulative sequential testing across 60 checkpoints (using `userid` order as an explicit proxy for user arrival order):

![Peeking Simulation](outputs/peeking_simulation.png)

- **Simulation Findings:**
  - The running p-value fluctuated substantially across sample sizes, crossing the $\alpha = 0.05$ threshold in **38 out of 60 checkpoints**.
  - **The Peeking Problem:** Repeatedly evaluating significance without adjusting the critical threshold (e.g. via alpha-spending functions like Pocock or O'Brien-Fleming) dramatically inflates the true Type I error rate well above 5% (often exceeding 20-30%).
  - **Best Practice:** Tests must run to their pre-determined sample size unless a formalized group sequential design or sequential probability ratio test (SPRT) is established upfront.

---

### 5.3 Methodological Note: Deliberate Omission of CUPED
- **What is CUPED?** Controlled-experiment Using Pre-Experiment Data (CUPED) is a variance reduction technique that uses pre-treatment covariates to subtract explainable variance from the outcome metric.
- **Why CUPED is Inapplicable Here:** All available variables in this dataset (`sum_gamerounds`, `retention_1`, `retention_7`) were recorded **post-treatment** (during the 14 days following assignment).
- **Risk of Post-Treatment Conditioning:** Adjusting or segmenting on a variable affected by the treatment itself introduces **collider bias / post-treatment selection bias**, destroying the causal guarantees of randomization. Therefore, omitting CUPED is a deliberate, mathematically sound decision.

---

## 6. Strategic Business Recommendations

1. **Retain Gate at Level 30 (Provisional Recommendation):** Do not deploy `gate_40` to production. Placing the gate at Level 30 preserves higher 7-day player retention (19.02% vs. 18.20%, a relative +4.5% retention advantage).
2. **SRM Caveat & Allocation Audit:** This headline recommendation is **provisional pending an audit of the sample ratio allocation imbalance** ($\chi^2 = 6.92, p = 0.0085$). If the data engineering audit confirms that the slight imbalance (+790 users in `gate_40`) is unrelated to how retention itself was tracked (e.g., an upstream traffic bucketing or bot-filtering quirk rather than differential event logging or user drop-off during tracking), the Day-7 finding stands as reported.
3. **Instrument Pre-Treatment Telemetry:** For future experimentation, capture pre-experiment baseline features (e.g., historical rounds played, device tier) to unlock valid CUPED variance reduction.
