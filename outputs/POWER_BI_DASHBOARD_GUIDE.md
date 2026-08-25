# Cookie Cats A/B Test: Power BI Executive Dashboard & DAX Modeling Specification

**Author:** Data / Product Analyst Candidate (IIT Kharagpur Portfolio Project)  
**Target Platform:** Power BI Desktop / Power BI Service  
**Dataset Scope:** Historical Cookie Cats A/B Test (90,188 validated records)  
**Primary Metric:** 7-Day Player Retention (`retention_7`)  
**Secondary & Guardrail Metrics:** 1-Day Player Retention (`retention_1`), Total 14-Day Game Rounds (`sum_gamerounds`)  

---

## Executive Overview & Business Problem

Cookie Cats is a classic mobile puzzle game. In this experiment, the product team tested moving the first progression gate from **Level 30 (Control)** to **Level 40 (Treatment)**. Progression gates force players to either wait a specified time or make in-app purchases/request friends to unlock the next level.

This implementation specification provides an end-to-end, production-ready guide to building an enterprise-grade Power BI Executive Dashboard. The dashboard translates statistical rigor (Chi-Square tests, Mann-Whitney U tests, SRM validation, and bootstrap confidence intervals) into intuitive executive visuals, dynamic DAX measures, and action-oriented product recommendations.

---

## 1. Data Model Architecture (Star Schema)

To ensure optimal analytical performance, DAX simplicity, and scalable filtering, the Power BI data model follows a strict **Star Schema** design centered around `Fact_CleanedData`.

```
                  +-----------------------+
                  |      Dim_Variant      |
                  +-----------------------+
                  | version (PK)          |
                  | Variant_Name          |
                  | Gate_Level            |
                  | Target_Allocation_Pct |
                  +-----------+-----------+
                              | 1
                              |
                              | N
+-----------------------------+-----------------------------+
|                      Fact_CleanedData                     |
+-----------------------------------------------------------+
| userid (PK)                                               |
| version (FK)                                              |
| sum_gamerounds                                            |
| retention_1                                               |
| retention_7                                               |
| Engagement Tier (FK)                                      |
| Engagement Tier Sort                                      |
| Retention Cohort (FK)                                     |
+-------------+-------------------------------+-------------+
              | N                             | N
              |                               |
              | 1                             | 1
+-------------+-------------+   +-------------+-------------+
|   Dim_EngagementTier      |   |    Dim_RetentionCohort    |
+---------------------------+   +---------------------------+
| Engagement Tier (PK)      |   | Retention Cohort (PK)     |
| SortOrder                 |   | SortOrder                 |
+---------------------------+   +---------------------------+
```

### Table Specifications & Relationships

1. **`Fact_CleanedData`** (Fact Table):
   - Ingested from `outputs/cleaned_data.csv` (90,188 rows).
   - Contains granular player-level telemetry: `userid`, `version`, `sum_gamerounds`, `retention_1`, `retention_7`.
   - Transformed with added dimension keys: `Engagement Tier`, `Engagement Tier Sort`, `Retention Cohort`.

2. **`Dim_Variant`** (Dimension Table):
   - Inline M table mapping technical versions (`gate_30`, `gate_40`) to executive labels ("Control (Level 30 Gate)", "Treatment (Level 40 Gate)").

3. **`Dim_EngagementTier`** (Dimension Table):
   - Holds standard player lifecycle tiers with an explicit `SortOrder` integer (1 to 5) so visuals sort logically from bounced users to whales.

4. **`Dim_RetentionCohort`** (Dimension Table):
   - Holds retention combinations (D1 & D7, D1 Only, D7 Only, Churned) with `SortOrder` (1 to 4).

5. **`_Measures`** (Disconnected Measure Table):
   - Dedicated container for all calculated DAX measures.

---

## 2. Power Query (M-Code) Transformations & Column Engineering

Follow these steps in Power Query Editor (or paste into the Advanced Editor) to transform raw data and generate required dimension tables.

### 2.1 M-Code for `Fact_CleanedData`

```powerquery
let
    // 1. Load cleaned raw dataset
    Source = Csv.Document(
        File.Contents("c:\Documenten\A_Placement\CV pointers\PROJECT\Cookie Cats AB Test\outputs\cleaned_data.csv"), 
        [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    
    // 2. Enforce explicit column data types
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"userid", Int64.Type},
        {"version", type text},
        {"sum_gamerounds", Int64.Type},
        {"retention_1", type logical},
        {"retention_7", type logical}
    }),

    // 3. Create Engagement Tier column
    AddEngagementTier = Table.AddColumn(TypedTable, "Engagement Tier", each 
        if [sum_gamerounds] = 0 then "0 Rounds (Bounced)"
        else if [sum_gamerounds] <= 10 then "1-10 Rounds (Casual)"
        else if [sum_gamerounds] <= 40 then "11-40 Rounds (Core)"
        else if [sum_gamerounds] <= 100 then "41-100 Rounds (Engaged)"
        else "100+ Rounds (Whales / Power Users)", 
        type text
    ),

    // 4. Create Engagement Tier Sort Order (1 to 5)
    AddEngagementTierSort = Table.AddColumn(AddEngagementTier, "Engagement Tier Sort", each 
        if [sum_gamerounds] = 0 then 1
        else if [sum_gamerounds] <= 10 then 2
        else if [sum_gamerounds] <= 40 then 3
        else if [sum_gamerounds] <= 100 then 4
        else 5, 
        Int64.Type
    ),

    // 5. Create Retention Cohort column
    AddRetentionCohort = Table.AddColumn(AddEngagementTierSort, "Retention Cohort", each 
        if [retention_1] = true and [retention_7] = true then "Retained Both (D1 & D7)"
        else if [retention_1] = true and [retention_7] = false then "Day 1 Only"
        else if [retention_1] = false and [retention_7] = true then "Day 7 Only"
        else "Churned (Neither Day)", 
        type text
    )
in
    AddRetentionCohort
```

### 2.2 M-Code for Dimension Tables

#### `Dim_Variant`
```powerquery
let
    Source = Table.FromRows({
        {"gate_30", "Control (Level 30 Gate)", 30, 0.50},
        {"gate_40", "Treatment (Level 40 Gate)", 40, 0.50}
    }, {"version", "Variant_Name", "Gate_Level", "Target_Allocation_Pct"}),
    Typed = Table.TransformColumnTypes(Source, {
        {"version", type text},
        {"Variant_Name", type text},
        {"Gate_Level", Int64.Type},
        {"Target_Allocation_Pct", Percentage.Type}
    })
in
    Typed
```

#### `Dim_EngagementTier`
```powerquery
let
    Source = Table.FromRows({
        {"0 Rounds (Bounced)", 1},
        {"1-10 Rounds (Casual)", 2},
        {"11-40 Rounds (Core)", 3},
        {"41-100 Rounds (Engaged)", 4},
        {"100+ Rounds (Whales / Power Users)", 5}
    }, {"Engagement Tier", "SortOrder"}),
    Typed = Table.TransformColumnTypes(Source, {
        {"Engagement Tier", type text},
        {"SortOrder", Int64.Type}
    })
in
    Typed
```

#### `Dim_RetentionCohort`
```powerquery
let
    Source = Table.FromRows({
        {"Retained Both (D1 & D7)", 1},
        {"Day 1 Only", 2},
        {"Day 7 Only", 3},
        {"Churned (Neither Day)", 4}
    }, {"Retention Cohort", "SortOrder"}),
    Typed = Table.TransformColumnTypes(Source, {
        {"Retention Cohort", type text},
        {"SortOrder", Int64.Type}
    })
in
    Typed
```

---

## 3. Production DAX Measures Repository

All measures are stored inside the `_Measures` container table.

### 3.1 Base Volumes & SRM Validation

```dax
// 1. Total Players Volume
Total Players = 
COUNTROWS('Fact_CleanedData')

// 2. Control Group Volume (Gate 30)
Gate 30 Players = 
CALCULATE(
    [Total Players], 
    'Fact_CleanedData'[version] = "gate_30"
)

// 3. Treatment Group Volume (Gate 40)
Gate 40 Players = 
CALCULATE(
    [Total Players], 
    'Fact_CleanedData'[version] = "gate_40"
)

// 4. Treatment Allocation Percentage
Gate 40 Allocation % = 
DIVIDE([Gate 40 Players], [Total Players], 0)

// 5. Dynamic SRM Validation Badge (Chi-Square Goodness of Fit Test)
SRM Alert Badge = 
VAR Obs30 = [Gate 30 Players]
VAR Obs40 = [Gate 40 Players]
VAR TotalP = [Total Players]
VAR Exp30 = TotalP * 0.50
VAR Exp40 = TotalP * 0.50
VAR ChiSquare = 
    DIVIDE(POWER(Obs30 - Exp30, 2), Exp30, 0) + 
    DIVIDE(POWER(Obs40 - Exp40, 2), Exp40, 0)
// Critical Chi-Square value for 1 dof at alpha=0.01 is 6.635
VAR IsSRMDetected = ChiSquare > 6.635
VAR AllocPct40 = [Gate 40 Allocation %]
RETURN
    IF(
        IsSRMDetected,
        "⚠️ SRM Warning (" & FORMAT(AllocPct40, "0.00%") & " vs 50.00%, p=0.0085)",
        "✅ SRM Passed (" & FORMAT(AllocPct40, "0.00%") & " vs 50.00%)"
    )
```

### 3.2 Retention Rates (Primary & Secondary Metrics)

```dax
// 6. Overall Day 1 Retention Rate
Day 1 Retention Rate = 
DIVIDE(
    CALCULATE([Total Players], 'Fact_CleanedData'[retention_1] = TRUE()),
    [Total Players],
    0
)

// 7. Overall Day 7 Retention Rate (Primary Outcome Metric)
Day 7 Retention Rate = 
DIVIDE(
    CALCULATE([Total Players], 'Fact_CleanedData'[retention_7] = TRUE()),
    [Total Players],
    0
)

// 8. Day 1 Retention - Gate 30 (Control)
D1 Rate Gate 30 = 
CALCULATE(
    [Day 1 Retention Rate], 
    'Fact_CleanedData'[version] = "gate_30"
)

// 9. Day 1 Retention - Gate 40 (Treatment)
D1 Rate Gate 40 = 
CALCULATE(
    [Day 1 Retention Rate], 
    'Fact_CleanedData'[version] = "gate_40"
)

// 10. Day 7 Retention - Gate 30 (Control)
D7 Rate Gate 30 = 
CALCULATE(
    [Day 7 Retention Rate], 
    'Fact_CleanedData'[version] = "gate_30"
)

// 11. Day 7 Retention - Gate 40 (Treatment)
D7 Rate Gate 40 = 
CALCULATE(
    [Day 7 Retention Rate], 
    'Fact_CleanedData'[version] = "gate_40"
)
```

### 3.3 Statistical A/B Lift Indicators & Executive Callouts

```dax
// 12. Day 7 Absolute Lift (Percentage Points)
Day 7 Retention Lift (pts) = 
[D7 Rate Gate 40] - [D7 Rate Gate 30]

// 13. Day 7 Relative Lift (%)
Day 7 Relative Lift % = 
DIVIDE([Day 7 Retention Lift (pts)], [D7 Rate Gate 30], 0)

// 14. Day 1 Absolute Lift (Percentage Points)
Day 1 Retention Lift (pts) = 
[D1 Rate Gate 40] - [D1 Rate Gate 30]

// 15. Day 1 Relative Lift (%)
Day 1 Relative Lift % = 
DIVIDE([Day 1 Retention Lift (pts)], [D1 Rate Gate 30], 0)

// 16. Dynamic Primary KPI Card Callout Badge (Day 7 Retention)
Day 7 Lift KPI Card Callout = 
VAR LiftPts = [Day 7 Retention Lift (pts)]
VAR LiftFormatted = FORMAT(LiftPts, "+0.00%;-0.00%;0.00%") & " pts"
VAR Arrow = IF(LiftPts < 0, "▼ ", "▲ ")
// Statistical p-value from Chi-Square / 2-Prop Z test = 0.0016
RETURN Arrow & LiftFormatted & " (Statistically Significant, p = 0.0016)"

// 17. Dynamic Secondary KPI Card Callout Badge (Day 1 Retention)
Day 1 Lift KPI Card Callout = 
VAR LiftPts = [Day 1 Retention Lift (pts)]
VAR LiftFormatted = FORMAT(LiftPts, "+0.00%;-0.00%;0.00%") & " pts"
VAR Arrow = IF(LiftPts < 0, "▼ ", "▲ ")
// Statistical p-value from Chi-Square test = 0.0739 (Not Significant at alpha=0.05)
RETURN Arrow & LiftFormatted & " (Not Significant, p = 0.0739)"
```

### 3.4 Engagement & Guardrail Metrics

```dax
// 18. Average Game Rounds Played
Avg Game Rounds = 
AVERAGE('Fact_CleanedData'[sum_gamerounds])

// 19. Median Game Rounds Played (Robust to Right Skew)
Median Game Rounds = 
MEDIAN('Fact_CleanedData'[sum_gamerounds])

// 20. Total Game Rounds Volume
Total Game Rounds = 
SUM('Fact_CleanedData'[sum_gamerounds])

// 21. Median Game Rounds - Gate 30
Median Rounds Gate 30 = 
CALCULATE([Median Game Rounds], 'Fact_CleanedData'[version] = "gate_30")

// 22. Median Game Rounds - Gate 40
Median Rounds Gate 40 = 
CALCULATE([Median Game Rounds], 'Fact_CleanedData'[version] = "gate_40")
```

### 3.5 Executive Recommendation Callout DAX

```dax
// 23. Executive Decision Callout Text Block
Executive Recommendation Callout = 
"PROVISIONAL BUSINESS DECISION: MAINTAIN LEVEL 30 GATE" & UNICHAR(10) &
"--------------------------------------------------------------------------------" & UNICHAR(10) &
"• Primary Outcome (7-Day Retention): Relocating gate to Level 40 caused a statistically significant drop of -0.82% pts (19.02% -> 18.20%, relative -4.31%, Chi-Square = 9.96, p = 0.0016)." & UNICHAR(10) &
"• Secondary Outcome (1-Day Retention): Minor negative delta of -0.59% pts (44.82% -> 44.23%, p = 0.0739) is not statistically significant." & UNICHAR(10) &
"• Guardrail Metric (Gameplay Engagement): Median game rounds show no significant shift (17 vs 16, Mann-Whitney U p = 0.0509)." & UNICHAR(10) &
"• Governance Caveat: Decision is provisional pending Data Engineering audit of SRM Warning (50.44% vs 50.00%, p = 0.0085)."
```

---

## 4. Visual Architecture & 2-Page Wireframe Layouts

### Page 1: Executive Experimentation Overview (A/B Test Scorecard)

Page 1 gives C-suite executives and Product Managers an immediate high-level summary of test outcomes, statistical confidence, and business recommendations.

```
+--------------------------------------------------------------------------------------------------+
| HEADER RIBBON: Cookie Cats A/B Test Scorecard (N=90,188) | [SRM Alert Badge: ⚠️ SRM Warning]      |
+--------------------------------------------------------------------------------------------------+
| [ KPI Card 1 ]       | [ KPI Card 2 ]        | [ KPI Card 3 ]            | [ KPI Card 4 ]       |
| Total Players        | Day-1 Retention       | Day-7 Retention (Primary) | Median Game Rounds   |
| 90,188               | 44.52%                | 18.60%                    | 17.0                 |
| 44,699 Ctrl / 45,489 | ▼ -0.59% pts (p=0.07) | ▼ -0.82% pts (p=0.0016)   | Gate 30: 17 / G40: 16|
+--------------------------------------------------------------------------------------------------+
| Visual Comparison 1 (Left 60% Width)              | Visual Comparison 2 (Right 40% Width)        |
| Clustered Column Chart: Retention by Variant       | Donut Chart: Player Retention Cohort Breakdown|
| - Gate 30 vs Gate 40 for D1 and D7                | - Retained Both (D1 & D7)                     |
| - Explicit 95% Confidence Interval error caps     | - Day 1 Only, Day 7 Only, Churned             |
+--------------------------------------------------------------------------------------------------+
| Bottom Panel 1 (Left 50% Width)                   | Bottom Panel 2 (Right 50% Width)             |
| Statistical Test Summary Table                    | Executive Recommendation Box                 |
| - Metric, Control, Treatment, P-Value, Sig Flag  | - Full DAX Executive Recommendation Callout  |
+--------------------------------------------------------------------------------------------------+
```

#### Detailed Page 1 Visual Specifications

1. **Header Ribbon:**
   - **Title Text:** "Cookie Cats A/B Test: Progression Gate Placement (Level 30 vs Level 40)"
   - **Subtitle / Meta:** "Experiment Scope: 90,188 validated player records | Primary Metric: 7-Day Player Retention"
   - **Card Visual (Top Right):** `[SRM Alert Badge]` (Conditional formatting: Background `#7F1D1D` Dark Red if warning, `#065F46` Dark Green if passed).

2. **Top Row KPI Cards (4 Container Cards):**
   - **Card 1 (Total Players):** Value: `[Total Players]`, Subtext: "Control: 44,699 | Treatment: 45,489".
   - **Card 2 (Day-1 Retention Rate):** Value: `[Day 1 Retention Rate]`, Subtext Callout: `[Day 1 Lift KPI Card Callout]`.
   - **Card 3 (Day-7 Retention Rate - Primary KPI):** Value: `[Day 7 Retention Rate]`, Subtext Callout: `[Day 7 Lift KPI Card Callout]` (Accent Border: Teal `#00A896`).
   - **Card 4 (Median Game Rounds):** Value: `[Median Game Rounds]`, Subtext: "Control: 17.0 | Treatment: 16.0".

3. **Middle Row Visuals:**
   - **Visual 1 (Clustered Column Chart - Retention by Variant):**
     - **X-Axis:** `Dim_Variant[Variant_Name]`
     - **Y-Axis:** `[Day 1 Retention Rate]`, `[Day 7 Retention Rate]`
     - **Colors:** Control Teal `#00A896`, Treatment Rose `#F43F5E`
     - **Data Labels:** Enabled (0.00% format string).
   - **Visual 2 (Donut Chart - Retention Cohort Breakdown):**
     - **Legend:** `Dim_RetentionCohort[Retention Cohort]` (Sorted by `SortOrder`)
     - **Values:** `[Total Players]`
     - **Tooltips:** `% of Total Players`.

4. **Bottom Row Visuals:**
   - **Visual 3 (Statistical Summary Matrix Table):**
     - Columns: Metric Name, Control Value, Treatment Value, Absolute Delta, p-value, Statistical Significance Flag (`p < 0.05`).
   - **Visual 4 (Executive Recommendation Box):**
     - Card / Text Visual displaying `[Executive Recommendation Callout]`.

---

### Page 2: Player Engagement & Segment Deep-Dive

Page 2 enables product managers and game designers to slice data by player engagement tiers and evaluate whether the Level 40 gate disproportionately impacted specific player cohorts (e.g., Casuals vs Core vs Whales).

```
+--------------------------------------------------------------------------------------------------+
| HEADER RIBBON: Player Engagement & Segment Breakdown Deep-Dive                                   |
+--------------------------------------------------------------------------------------------------+
| SLICER 1: Variant Selection                       | SLICER 2: Engagement Tier Selection          |
| [All] | Control (gate_30) | Treatment (gate_40)   | [All] | 0 Rounds | 1-10 | 11-40 | 41-100 | 100+  |
+--------------------------------------------------------------------------------------------------+
| Visual 1 (Top 50% Height)                                                                        |
| 100% Stacked Bar Chart: Day-7 Retention Rate by Engagement Tier & Variant                         |
| - X-Axis: % Retained vs % Churned                                                                |
| - Y-Axis: Engagement Tier (0 Rounds, 1-10, 11-40, 41-100, 100+)                                   |
| - Legend: Retention Cohort (Retained Both, D1 Only, D7 Only, Churned)                            |
+--------------------------------------------------------------------------------------------------+
| Visual 2 (Bottom Left 50% Width)                  | Visual 3 (Bottom Right 50% Width)            |
| Clustered Bar Chart: Player Volume Distribution   | Segment Performance Matrix Table             |
| - Y-Axis: Engagement Tier                         | - Engagement Tier x Variant Breakdown        |
| - X-Axis: [Total Players] by Variant              | - Columns: Players, D1 Rate, D7 Rate, Med Rds|
+--------------------------------------------------------------------------------------------------+
```

#### Detailed Page 2 Visual Specifications

1. **Top Slicer Panel:**
   - **Slicer 1 (Variant Tile Slicer):** Field: `Dim_Variant[Variant_Name]`.
   - **Slicer 2 (Engagement Tier Multi-Select Slicer):** Field: `Dim_EngagementTier[Engagement Tier]` (Sorted by `SortOrder`).

2. **Visual 1 (100% Stacked Bar Chart - D7 Retention by Tier):**
   - **Y-Axis:** `Dim_EngagementTier[Engagement Tier]`
   - **X-Axis:** `[Total Players]`
   - **Legend:** `Dim_RetentionCohort[Retention Cohort]`
   - **Insight:** Highlights that non-zero players in the 11-40 and 41-100 round tiers experience the largest drop in D7 retention under `gate_40`.

3. **Visual 2 (Clustered Bar Chart - Volume Distribution by Tier):**
   - **Y-Axis:** `Dim_EngagementTier[Engagement Tier]`
   - **X-Axis:** `[Total Players]`
   - **Legend:** `Dim_Variant[Variant_Name]`

4. **Visual 3 (Segment Performance Matrix):**
   - **Rows:** `Dim_EngagementTier[Engagement Tier]`
   - **Columns:** `Dim_Variant[Variant_Name]`
   - **Values:** `[Total Players]`, `[Day 1 Retention Rate]`, `[Day 7 Retention Rate]`, `[Median Game Rounds]`
   - **Conditional Formatting:** Color scale on `[Day 7 Retention Rate]` (Teal gradient).

---

## 5. Step-by-Step UI Build Checklist for Power BI Desktop

Follow this exact step-by-step checklist to build the report in Power BI Desktop.

### Step 1: Initialize Project & Import Dataset
1. Open **Power BI Desktop**.
2. Click **Get Data** -> **Text/CSV**.
3. Select `outputs/cleaned_data.csv`.
4. Click **Transform Data** to launch Power Query Editor.

### Step 2: Configure Power Query M Transformations
1. In Power Query Editor, click **Advanced Editor** for `cleaned_data`.
2. Replace the script with the M-code provided in **Section 2.1**. Rename query to `Fact_CleanedData`.
3. Create the three dimension tables:
   - Click **Home** -> **New Source** -> **Blank Query**.
   - Open **Advanced Editor** and paste M-code from **Section 2.2** for `Dim_Variant`. Rename query to `Dim_Variant`.
   - Repeat for `Dim_EngagementTier` and `Dim_RetentionCohort`.
4. Click **Close & Apply**.

### Step 3: Set Data Model Relationships & Sort Columns
1. Navigate to **Model View** (left navigation bar).
2. Ensure the following 1-to-N relationships are active:
   - `Dim_Variant[version]` -> `Fact_CleanedData[version]`
   - `Dim_EngagementTier[Engagement Tier]` -> `Fact_CleanedData[Engagement Tier]`
   - `Dim_RetentionCohort[Retention Cohort]` -> `Fact_CleanedData[Retention Cohort]`
3. Set Sort Order for Dimension Tables:
   - In Data View, select `Dim_EngagementTier`. Click `Engagement Tier` column -> **Column Tools** -> **Sort by Column** -> select `SortOrder`.
   - Select `Dim_RetentionCohort`. Click `Retention Cohort` column -> **Column Tools** -> **Sort by Column** -> select `SortOrder`.

### Step 4: Create Dedicated `_Measures` Container Table
1. Click **Home** -> **Enter Data**.
2. Set Table Name to `_Measures`, click **Load**.
3. Right-click `_Measures` table -> **New Measure**.
4. Paste each DAX measure from **Section 3** one by one.
5. Hide default `Column1` in `_Measures` table so it converts into a measure folder icon.
6. Set Format Strings:
   - `Day 1 Retention Rate`, `Day 7 Retention Rate`, `D1/D7 Gate 30/40 Rates`, `Gate 40 Allocation %` -> Format as **Percentage (`0.00%`)**.
   - `Day 7 Retention Lift (pts)`, `Day 1 Retention Lift (pts)` -> Format as **Percentage (`+0.00%;-0.00%;0.00%`)**.
   - `Total Players`, `Gate 30/40 Players`, `Total Game Rounds` -> Format as **Whole Number (`#,##0`)**.
   - `Avg Game Rounds`, `Median Game Rounds` -> Format as **Decimal (`#,##0.0`)**.

### Step 5: Import Executive Custom Slate Theme
1. Navigate to **View** tab in Power BI top ribbon.
2. Click Themes dropdown arrow -> **Browse for themes**.
3. Select `outputs/cookie_cats_theme.json`.
4. Confirm canvas background shifts to dark slate (`#0F172A`).

### Step 6: Construct Page 1 (Executive Experimentation Overview)
1. Rename Page 1 tab to `Executive Overview`.
2. Add Header Banner Text Box at top `(X: 10, Y: 10, W: 900, H: 60)`.
3. Add Card Visual for `[SRM Alert Badge]` in top right `(X: 920, Y: 10, W: 350, H: 60)`.
4. Add 4 KPI Card Visuals across Y=80:
   - Card 1 (`[Total Players]`), Card 2 (`[Day 1 Retention Rate]`), Card 3 (`[Day 7 Retention Rate]`), Card 4 (`[Median Game Rounds]`).
5. Add Clustered Column Chart for Retention Rates by Variant at `(X: 10, Y: 200, W: 740, H: 320)`.
6. Add Donut Chart for `Dim_RetentionCohort` at `(X: 760, Y: 200, W: 510, H: 320)`.
7. Add Statistical Summary Table at `(X: 10, Y: 530, W: 600, H: 180)`.
8. Add Executive Recommendation Box at `(X: 620, Y: 530, W: 650, H: 180)` using `[Executive Recommendation Callout]`.

### Step 7: Construct Page 2 (Player Engagement Deep-Dive)
1. Add new page, rename tab to `Engagement Deep-Dive`.
2. Add Tile Slicer for `Dim_Variant[Variant_Name]` at top left.
3. Add Dropdown/Tile Slicer for `Dim_EngagementTier[Engagement Tier]` at top right.
4. Add 100% Stacked Bar Chart for Retention by Tier at `(X: 10, Y: 90, W: 1260, H: 300)`.
5. Add Clustered Bar Chart for Volume Distribution at `(X: 10, Y: 400, W: 600, H: 300)`.
6. Add Segment Matrix Table at `(X: 620, Y: 400, W: 650, H: 300)`.

### Step 8: Final Quality Assurance & Publish
1. Test slicer cross-filtering between Page 1 and Page 2.
2. Verify all DAX measure outputs match exact statistical report numbers:
   - Total Users: **90,188**
   - D7 Retention: **19.02% (Gate 30) vs 18.20% (Gate 40)** -> Lift: **-0.82% pts**
   - D1 Retention: **44.82% (Gate 30) vs 44.23% (Gate 40)** -> Lift: **-0.59% pts**
   - SRM Warning Badge: `⚠️ SRM Warning (50.44% vs 50.00%, p=0.0085)`
3. Save file as `Cookie_Cats_AB_Test_Executive_Dashboard.pbix`.

---

## 6. Summary of Deliverable Files in Repository

| File Path | Description |
| :--- | :--- |
| `outputs/cleaned_data.csv` | Granular row-level dataset (90,188 validated player records) |
| `outputs/summary_by_group.csv` | Aggregated variant metric summary |
| `outputs/stats_report.md` | Complete statistical hypothesis testing & experimentation report |
| `outputs/cookie_cats_theme.json` | Power BI custom theme JSON (Slate Dark `#0F172A` & Executive Teal `#00A896`) |
| `outputs/POWER_BI_DASHBOARD_GUIDE.md` | Full Power BI Dashboard & DAX implementation specification (This document) |

---
*End of Power BI Dashboard & DAX Modeling Specification.*
