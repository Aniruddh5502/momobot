---
name: quant_analysis
description: Identify, validate, and trade based on Alternative Data and OSINT. Use this skill whenever the user wants to perform quantitative analysis, signal hunting, correlation testing, or financial modeling using non-traditional data sources.
---

# QUANT_ANALYSIS_ULTRA_MANUAL

## Purpose
This is a high-granularity execution manual designed for autonomous agents to identify, validate, and trade based on Alternative Data and OSINT.

---

## ⚠️ SUBAGENT COGNITIVE ALIGNMENT (CRITICAL)
This section overrides the general "Completion Mindset" in `sub_soul.md`.
- **Redefining Success**: In Quant Analysis, finding that a signal is "Noise" is a SUCCESS. It prevents the loss of capital. Do NOT force a correlation to satisfy a "completion" requirement.
- **Linearity Over Scale**: For current operations, ignore "Swarm" or "Parallel" logic. Operate in a strict **Linear Sequence**.
- **Verification**: Verify the *logic* and the *sample* of data. Do not attempt to read every single data point into the context.

---

## 🌍 CONTEXT-AWARE STRATEGY (THE "REAL WORLD" FILTER)
Before executing any trade, the agent must apply the **Market Reality Filter** to avoid "Academic Failure."

### 1. The "Analog Gap" Analysis
Recognize that in many markets (especially emerging ones like BD), the most valuable data is not digital.
- **Action**: Identify "Information Choke Points" (e.g., brokers, local middlemen, port authorities).
- **Requirement**: If the signal depends on "Digital-Only" data, flag it as "Low Confidence" and prompt the user for a "Local Ground-Truth" verification.

### 2. The "Syndicate/Manipulation" Check
Distinguish between **Organic Supply/Demand** and **Artificial Manipulation**.
- **Organic**: Volume $\downarrow$ $\rightarrow$ Price $\uparrow$
- **Manipulated**: Volume $\uparrow$ (but hidden/hoarded) $\rightarrow$ Price $\uparrow$
- **Action**: Compare the "Physical Proxy" (Trucks/Ships) with the "Market Price." If they diverge logically, flag the move as "Manipulated."

### 3. The "Perishability/Decay" Variable
For physical commodities, time is a liability, not an asset.
- **Action**: Calculate the "Value Decay Curve."
- **Rule**: If the predicted "Price Peak" occurs after the "Maximum Shelf Life" of the product, the trade is a **FAIL**.

---

## PHASE 1: SIGNAL IDENTIFICATION (THE HUNT)
**Goal**: Find a physical-world "leak" that correlates with a financial outcome.

### Step 1.1: Define the Target
- **1.1.1**: Select a specific company or commodity.
- **1.1.2**: Identify the "Critical Success Factor."

### Step 1.2: Map the Physical Proxy
- **1.2.1**: Identify the "choke point."
- **1.2.2**: **Examples**:
    - **Semi-conductors**: Track ASML shipments via MarineTraffic.
    - **M&A (Mergers)**: Track corporate jet movements via ADS-B Exchange.
    - **Agricultural/Commodity**: Track regional transport hubs vs. urban wholesale arrivals.

### Step 1.3: Verification Checklist
- [ ] Is the proxy directly linked to revenue? (Yes/No)
- [ ] Is the data accessible via free/low-cost means? (Yes/No)
- [ ] Does the proxy lead the price (predictive)? (Yes/No)
- [ ] **Context Check**: Have I identified the "Analog Gap"? (Yes/No)

**IF FAILURE**: Pivot to a different asset. Do not "force" a correlation.

---

## PHASE 2: DATA ACQUISITION (THE PIPELINE)
**Goal**: Move from "observation" to a "time-series dataset".

### Step 2.1: Establish the Connection
- **2.1.1**: Identify API/HTML structure.
- **2.1.2**: Perform "Single-Ping Test."
- **2.1.3**: Use `headers` to avoid bot detection.

### Step 2.2: Build the Collector
- **2.2.1**: Loop for fixed interval fetching.
- **2.2.2**: Implement `try-except` error handling.
- **2.2.3**: Store in CSV/SQLite.

---

## PHASE 3: VALIDATION (THE STRESS TEST)
**Goal**: Prove the signal is not noise.

### Step 3.1: Correlation Analysis
- **3.1.1**: Fetch historical price data.
- **3.1.2**: Align timestamps.
- **3.1.3**: Calculate Pearson Correlation.

### Step 3.2: Lead-Lag Testing
- **3.2.1**: Shift proxy signal forward (1, 3, 7, 14 days).
- **3.2.2**: Identify highest correlation shift.

---

## PHASE 4: LINEAR REFINEMENT (The "Single-Agent" Loop)
**Goal**: Iteratively improve the model for one specific asset.

### Step 4.1: Failure Analysis
- **4.1.1**: Compare prediction vs. actual price.
- **4.1.2**: Identify failure reason (e.g., "Symmetry Break," "Syndicate Move," "Spoilage").

### Step 4.2: Logic Update
- **4.2.1**: Add a "Filter" (e.g., "Only trade if Volume $> X$ AND Spoilage Risk $< Y$").
- **4.2.2**: Re-test correlation.

### Step 4.3: Final Verification Checklist
- [ ] Signal is physically grounded?
- [ ] Data pipeline handles errors?
- [ ] Correlation is statistically significant?
- [ ] **Context Check**: Is the "Perishability Variable" accounted for? (Yes/No)
- [ ] **Context Check**: Is the "Syndicate Filter" applied? (Yes/No)
- [ ] Model refined through at least one "Failure $\rightarrow$ Fix" cycle?
- [ ] Position sizing and stop-loss logic are defined?
