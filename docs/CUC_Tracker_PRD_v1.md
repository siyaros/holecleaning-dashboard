# CUC Tracker — Product Requirements Document

**Version:** 1.0  
**Author:** Siya Rostami  
**Date:** May 28, 2026  
**Status:** Draft for Review

---

## 1. Executive Summary

### 1.1 What is CUC Tracker?

CUC Tracker (Cleanup Cycle Tracker) is a decision-support tool that provides **objective, quantitative guidance** for when a wellbore is clean enough to trip. It replaces subjective "shakers look clean" observations with data-driven thresholds based on real-time Cuttings Return Rate (CRR) measurements.

### 1.2 The Problem We're Solving

**Current Industry Practice:**
- Drillers decide to trip based on visual shaker inspection ("shakers look clean")
- Rule-of-thumb: "circulate 2 bottoms-up" — but this varies by well, formation, and driller
- No quantitative threshold for "clean enough"

**Consequences:**
- **Over-circulation:** Wasted rig time ($100k+/day)
- **Under-circulation:** Stuck pipe, packoff, BHA left in hole ($1M+ events)
- **Inconsistency:** Same well, different crews = different decisions

**Our Solution:**
- Track CRR through each BU cycle
- Identify when CRR drops below a validated threshold (e.g., <0.006 m³/min)
- Provide visual "Ready to Trip" / "Keep Circulating" indicator
- Log all cleanup cycles for post-well analysis and benchmarking

---

## 2. Data Requirements

### 2.1 Data We HAVE (from CleanSight CSV exports)

| Parameter | Column Name | Unit | Status |
|-----------|-------------|------|--------|
| Timestamp | `time` | datetime | ✅ Available |
| CRR | `CRR (m3/min)` | m³/min | ✅ Available |
| Hole Depth | `Hole Depth (m)` | m | ✅ Available |
| Bit Depth | `Bit Depth (m)` | m | ✅ Available |
| Lag Depth | `Lag Depth (m)` | m | ✅ Available |
| Lag Time | `Lag Time (sec)` | seconds | ✅ Available |
| Flow In | `Flow In (L/m3)` | L/min | ✅ Available |
| Pump Pressure (SPP) | `Pump Pressure (psi)` | psi | ✅ Available |
| ECD | `ECD (kg/gal)` | kg/gal | ✅ Available |
| Inclination | `Inclination (degrees)` | degrees | ✅ Available |
| RPM | `RPM` | rpm | ✅ Available |
| Pit Volume | `Pit Volume (m3)` | m³ | ✅ Available |
| Gas | `GAS` | units | ✅ Available |
| Hook Load | `Hook Load (klbf)` | klbf | ✅ Available |
| Block Height | `Block Height (m)` | m | ✅ Available |
| CSD P50 | `CSD P50 (mm)` | mm | ✅ Available |
| UFO Count | `UFO Count` | count | ✅ Available |
| Rig Message | `Rig Message` | text | ✅ Available |
| ROP | `ROP (m/h)` | m/hr | ✅ Available |
| Lagged ROP | `Lagged ROP (m/hr)` | m/hr | ✅ Available |
| Theoretical TCR | `Theoretical TCR (m3)` | m³ | ✅ Available |
| Theoretical Lag TCR | `Theoretical Lag TCR (m3)` | m³ | ✅ Available |
| Measured TCR | `Measured TCR (m3)` | m³ | ✅ Available |
| Gamma | `Gamma` | API | ✅ Available (some wells) |
| Annotation | `annotation` | text | ✅ Available |

**File Format:** UTF-16-LE, Tab-separated  
**Sample Rate:** 1 minute intervals  

---

### 2.2 Data We NEED (from DDRs / Manual Entry)

These parameters are in Calvin's tracking sheet but NOT in our CSV exports:

| Parameter | Source | Why Needed | Priority |
|-----------|--------|------------|----------|
| **Reciprocation (y/n)** | DDR / Driller's notes | Affects bed disturbance during BU | HIGH |
| **Sweep (y/n)** | DDR / Driller's notes | Sweeps change CRR signature | HIGH |
| **Overpull events** | DDR / Driller's notes | Indicates hole condition issues | MEDIUM |
| **Pump Stop (y/n)** | DDR or infer from Flow=0 | Transport interruption | MEDIUM |
| **Torque** | WITS (not in CleanSight export) | Should decrease during cleanup | MEDIUM |
| **Mud Weight** | Mud report | Normalization | LOW |
| **Mud Type (OBM/WBM)** | Mud report | Affects CRR behavior | LOW |
| **Bypass Tool (y/n)** | DDR | Changes circulation path | LOW |

**Action Required:**
1. Request torque data be added to CleanSight exports (Alfonso)
2. Create DDR data extraction template for manual parameters
3. Define which parameters are "nice to have" vs "must have"

---

### 2.3 Data We NEED (for Trip Outcome Correlation)

To validate that our CRR threshold actually predicts successful trips:

| Parameter | Source | Why Needed |
|-----------|--------|------------|
| **Trip Outcome** | DDR | Did trip succeed? (Success / Stuck / Overpull / Fill / BHA LIH) |
| **Backreaming (y/n)** | DDR | Was backreaming required? |
| **Trip Obstruction depth** | DDR | Where did problems occur? |
| **Casing Run Obstruction** | DDR | Issues during casing run? |
| **Hole Fill** | DDR | Fill encountered on re-entry? |
| **Bad Cement Job** | DDR | Cement issues post-trip? |

**Action Required:**
1. Extract trip outcomes from D11/D12 DDRs for all 10 trips
2. Correlate outcomes with CRR at POOH decision point

---

### 2.4 Data We Have But Needs Validation

| Parameter | Issue | Resolution |
|-----------|-------|------------|
| **UFO Count** | Calvin flagged as manually entered by operators — unreliable | Use with caution, note data quality limitation |
| **CRR during pump-off** | CRR=0 when Flow=0, need to filter these periods | Filter data where Flow In < threshold |
| **ECD units** | Shows "kg/gal" which is unusual — verify with Alfonso | Confirm unit conversion |

---

## 3. Derived Calculations

### 3.1 Calculations the System Must Perform

| Metric | Formula | Purpose |
|--------|---------|---------|
| **TD Detection** | MAX(Hole Depth) | Identify when section TD is reached |
| **TD Timestamp** | First timestamp where Hole Depth = TD | Mark start of cleanup cycle |
| **BU Cycle Count** | Count from lag depth reaching TD to POOH | Number of bottoms-up circulated |
| **Lag Reaches TD** | First timestamp where Lag Depth >= (TD - 2m) | First BU complete |
| **CRR at TD** | CRR value at TD timestamp | Starting point for cleanup tracking |
| **CRR Clean Time** | First timestamp after TD where CRR <= threshold | When "shakers clean" achieved |
| **Time to Clean** | CRR Clean Time - TD Time | Duration of cleanup cycle |
| **CRR Decay Rate** | Slope of CRR vs time during BU | How fast hole is cleaning |
| **ACR %** | (Measured TCR / Theoretical TCR) × 100 | Actual Cuttings Recovery percentage |
| **TCR Ratio** | Measured TCR / Theoretical Lag TCR | Recovery ratio accounting for lag |

### 3.2 Threshold Definitions (Based on D11/D12 Analysis)

| Threshold | Value | Meaning |
|-----------|-------|---------|
| **CRR Clean** | < 0.006 m³/min | "Shakers clean" — ready to trip |
| **CRR Warning** | 0.006 - 0.010 m³/min | Close to clean, continue monitoring |
| **CRR Active** | > 0.010 m³/min | Active cuttings return, keep circulating |

**Note:** These thresholds are for 12.25" section. May need adjustment for 17.5" and 8.5" sections.

---

## 4. CUC Tracker Feature Requirements

### 4.1 Real-Time Display (During Cleanup Cycle)

**Header Panel:**
- Current Well / Section / Trip identifier
- Current Depth (TD)
- Time at TD
- Current BU count

**Main Gauge:**
- Large circular gauge showing CRR value
- Color-coded: Green (<0.006), Yellow (0.006-0.010), Red (>0.010)
- "READY TO TRIP" / "KEEP CIRCULATING" text indicator

**CRR Trend Chart:**
- X-axis: Time since TD
- Y-axis: CRR (m³/min) — log scale recommended
- Horizontal line at 0.006 threshold
- Shaded green zone below threshold
- Annotations for each BU cycle start

**Secondary Metrics Panel:**
- ACR % (with trend arrow)
- Current Lag Depth
- Lag Time (minutes)
- Flow Rate
- RPM
- ECD

**BU Cycle Table:**
| BU # | Start Time | End Time | CRR Start | CRR End | Duration |
|------|------------|----------|-----------|---------|----------|
| 1 | 14:20 | 15:05 | 0.0131 | 0.0082 | 45 min |
| 2 | 15:05 | 15:52 | 0.0082 | 0.0054 | 47 min |

### 4.2 Post-Trip Analysis View

**Summary Card:**
- Well / Section / Trip
- TD reached: [datetime]
- POOH decision: [datetime]
- Total cleanup time: [hours:minutes]
- BU cycles: [count]
- CRR at TD: [value]
- CRR at POOH: [value]
- CRR reduction: [%]
- Trip outcome: [Success / Issues / Stuck]

**CRR Decay Chart:**
- Full cleanup cycle from TD to POOH
- Each BU cycle annotated
- Threshold line with "clean zone" shading

**Comparison Panel:**
- Compare this cleanup cycle to:
  - Previous trips on same well
  - Other wells in campaign
  - Benchmark database

### 4.3 Historical Database / Benchmarking

**Data to Store Per Cleanup Cycle:**
```
{
  "well_id": "25/2-D-11",
  "trip_id": "T5",
  "section": "12.25",
  "td_depth_m": 2685,
  "td_timestamp": "2026-04-16T13:32:00",
  "pooh_timestamp": "2026-04-16T17:00:00",
  "bu_count": 4,
  "crr_at_td": 0.0131,
  "crr_at_pooh": 0.0052,
  "crr_reduction_pct": 96,
  "time_to_clean_min": 82,
  "inclination_deg": 90,
  "flow_rate_lpm": 3800,
  "rpm": 140,
  "mud_weight_sg": 1.417,
  "trip_outcome": "success",
  "notes": "Cement issue encountered, unrelated to hole cleaning"
}
```

**Benchmarking Queries:**
- Average BU cycles by section size
- Average time to clean by inclination band
- CRR decay rate by formation
- Trip success rate by CRR at POOH

---

## 5. Gap Analysis: What's Missing

### 5.1 Data Gaps (CRITICAL)

| Gap | Impact | Resolution | Owner | Timeline |
|-----|--------|------------|-------|----------|
| **No trip outcome data in system** | Cannot correlate CRR threshold to trip success | Extract from DDRs, add to database | Siya | Week 1-2 |
| **No torque in CSV exports** | Cannot track "should decrease" parameter | Request from Alfonso | Alfonso | Week 1 |
| **No sweep/reciprocation flags** | Cannot correlate operational actions to CRR changes | Manual extraction from DDRs | Siya | Week 2-3 |
| **BU cycle boundaries not marked** | Must infer from lag depth reaching TD | Algorithm development | Dev team | Week 2 |

### 5.2 Algorithm Gaps (HIGH)

| Gap | Impact | Resolution | Owner | Timeline |
|-----|--------|------------|-------|----------|
| **TD detection logic** | Need to reliably identify when TD is reached | Use MAX(Hole Depth) + ROP=0 + time threshold | Dev team | Week 1 |
| **BU cycle detection** | Need to count BU cycles automatically | Track when Lag Depth reaches TD each time | Dev team | Week 2 |
| **Pump-off filtering** | CRR=0 during pump stops skews data | Filter where Flow < 500 L/min | Dev team | Week 1 |
| **Threshold validation** | 0.006 threshold needs statistical validation | Compare against all 10 D11/D12 trips | Siya | Week 2-3 |

### 5.3 Integration Gaps (MEDIUM)

| Gap | Impact | Resolution | Owner | Timeline |
|-----|--------|------------|-------|----------|
| **No real-time data feed** | Current analysis is post-hoc on CSV exports | Integrate with Grafana/live data stream | Mert/Dev | Phase 2 |
| **No alert system** | Cannot notify driller when threshold reached | Add to existing alert infrastructure | Dev team | Phase 2 |
| **No DDR integration** | Trip outcomes require manual entry | API to DDR system or manual workflow | TBD | Phase 2 |

### 5.4 UI/UX Gaps (LOW - Phase 2)

| Gap | Impact | Resolution | Owner | Timeline |
|-----|--------|------------|-------|----------|
| **No CUC tab in current dashboard** | Feature doesn't exist yet | Add to CleanSight dashboard | Dev team | Phase 2 |
| **No "Ready to Trip" banner** | Driller has no visual cue | Design and implement | Dev team | Phase 2 |
| **No historical comparison UI** | Cannot benchmark on-the-fly | Design comparison view | Dev team | Phase 2 |

---

## 6. Development Roadmap

### Phase 1: Proof of Concept / Paper (Current)
**Timeline:** 6-8 weeks  
**Goal:** Validate CRR threshold using D11/D12 data, publish technical paper

| Task | Deliverable | Owner | Hours Est. |
|------|-------------|-------|------------|
| Extract TD, BU cycle, CRR data for all 10 trips | Data table | Siya | 20-30 |
| Extract trip outcomes from DDRs | Outcome mapping | Siya | 8-12 |
| Correlate CRR at POOH with trip outcome | Analysis table | Siya | 8-12 |
| Validate 0.006 threshold statistically | Threshold recommendation | Siya | 8-12 |
| Write technical paper | Paper draft | Siya | 20-30 |
| Review with Calvin | Feedback | Calvin/Siya | 4-6 |
| **Total Phase 1** | | | **70-100 hrs** |

### Phase 2: MVP Product Development
**Timeline:** 8-12 weeks after Phase 1  
**Goal:** Working CUC Tracker feature in CleanSight dashboard

| Task | Deliverable | Owner | Dependency |
|------|-------------|-------|------------|
| Define data schema for CUC records | Schema doc | Siya | — |
| Implement TD detection algorithm | Code | Dev team | Schema |
| Implement BU cycle detection algorithm | Code | Dev team | TD detection |
| Build real-time CRR gauge component | UI component | Dev team | Algorithms |
| Build CRR trend chart with threshold | UI component | Dev team | Algorithms |
| Add "Ready to Trip" banner to dashboard | UI component | Dev team | Gauge |
| Build post-trip summary view | UI view | Dev team | Data storage |
| Implement historical storage | Database | Dev team | Schema |
| Add CUC tab to dashboard | Navigation | Dev team | All above |
| Testing on live well | Validation | All | All above |

### Phase 3: Advanced Features
**Timeline:** TBD  
**Goal:** Predictive capabilities, expanded benchmarking

| Feature | Description |
|---------|-------------|
| **Time to Clean Prediction** | Based on CRR decay rate, predict when threshold will be reached |
| **Optimal BU Recommendation** | Suggest number of BU cycles based on historical data |
| **Formation-Specific Thresholds** | Adjust threshold based on lithology if available |
| **Multi-Well Campaign Dashboard** | Track CUC performance across all wells in campaign |
| **Caliper Correlation** | Correlate CRR with post-trip caliper for washout analysis |

---

## 7. Data Dictionary for Developers

### 7.1 Input Data (from CleanSight CSV)

```python
# File format
ENCODING = "UTF-16-LE"
DELIMITER = "\t"
SAMPLE_RATE = "1 minute"

# Key columns for CUC Tracker
COLUMNS = {
    "time": "datetime",              # Timestamp
    "CRR (m3/min)": "float",         # Cuttings Return Rate
    "Hole Depth (m)": "float",       # Current hole depth
    "Bit Depth (m)": "float",        # Bit position
    "Lag Depth (m)": "float",        # Lagged depth (cuttings origin)
    "Lag Time (sec)": "float",       # Lag time in seconds
    "Flow In (L/m3)": "float",       # Flow rate (note: unit may be L/min)
    "RPM": "float",                  # Drillstring rotation
    "ECD (kg/gal)": "float",         # Equivalent Circulating Density
    "Theoretical TCR (m3)": "float", # Expected cuttings volume
    "Measured TCR (m3)": "float",    # Actual measured cuttings volume
}
```

### 7.2 Derived Data (calculated by system)

```python
# CUC Tracker calculations
def detect_td(df):
    """Find section TD and timestamp"""
    td_depth = df["Hole Depth (m)"].max()
    td_time = df[df["Hole Depth (m)"] == td_depth]["time"].iloc[0]
    return td_depth, td_time

def count_bu_cycles(df, td_depth, tolerance=2.0):
    """Count BU cycles by tracking when lag depth reaches TD"""
    # BU cycle completes when Lag Depth >= (TD - tolerance)
    bu_events = df[df["Lag Depth (m)"] >= (td_depth - tolerance)]
    # Group by continuous periods
    # Return count of distinct BU cycles
    pass

def find_clean_time(df, td_time, threshold=0.006):
    """Find first timestamp after TD where CRR drops below threshold"""
    post_td = df[df["time"] > td_time]
    clean = post_td[post_td["CRR (m3/min)"] <= threshold]
    if len(clean) > 0:
        return clean["time"].iloc[0]
    return None
```

### 7.3 Output Data (stored per cleanup cycle)

```json
{
  "cuc_record": {
    "id": "uuid",
    "well_id": "string",
    "trip_id": "string",
    "section_size_in": "float",
    "td_depth_m": "float",
    "td_timestamp": "datetime",
    "pooh_timestamp": "datetime",
    "bu_count": "int",
    "bu_cycles": [
      {
        "bu_number": 1,
        "start_time": "datetime",
        "end_time": "datetime",
        "crr_start": "float",
        "crr_end": "float",
        "duration_min": "float"
      }
    ],
    "crr_at_td": "float",
    "crr_at_pooh": "float",
    "crr_reduction_pct": "float",
    "time_to_clean_min": "float",
    "threshold_used": "float",
    "parameters": {
      "inclination_deg": "float",
      "flow_rate_lpm": "float",
      "rpm": "float",
      "mud_weight_sg": "float"
    },
    "trip_outcome": "enum(success, stuck, overpull, fill, bha_lih, other)",
    "outcome_notes": "string",
    "created_at": "datetime",
    "created_by": "string"
  }
}
```

---

## 8. Acceptance Criteria

### 8.1 Phase 1 (Paper) — Definition of Done

- [ ] TD, CRR at TD, CRR at POOH extracted for all 10 D11/D12 trips
- [ ] BU cycle count validated against DDR records
- [ ] Trip outcome documented for all 10 trips
- [ ] Statistical analysis of CRR threshold completed
- [ ] Technical paper draft reviewed by Calvin
- [ ] Paper submitted for IADC consideration

### 8.2 Phase 2 (MVP) — Definition of Done

- [ ] CUC Tracker displays real-time CRR during cleanup cycle
- [ ] "Ready to Trip" indicator shows green when CRR < threshold
- [ ] BU cycle count is automatically tracked and displayed
- [ ] Post-trip summary is generated and stored
- [ ] Historical comparison with previous trips is available
- [ ] Feature tested on at least 1 live well

---

## 9. Open Questions

| Question | Who Can Answer | Priority |
|----------|----------------|----------|
| Is 0.006 m³/min the right threshold for all section sizes? | Analysis needed | HIGH |
| Should threshold be adjusted for inclination? | Calvin + Analysis | HIGH |
| Can we get torque added to CleanSight exports? | Alfonso | MEDIUM |
| How do we handle wells with no Measured TCR data? | Dev team | MEDIUM |
| What's the latency requirement for real-time display? | Product/Dev | LOW |
| Should we alert the driller automatically or just display? | Calvin/Operators | LOW |

---

## 10. Appendix

### A. Reference Data: D11/D12 BU Verification (from Calvin's sheet)

| Well | TD (m) | TD Time | Lag at TD | Lag Reaches TD | CRR at TD | CRR Clean Time |
|------|--------|---------|-----------|----------------|-----------|----------------|
| D11-Base | 2809 | 2025-12-19 11:22 | 2762 | 12:08 | 0.0243 | 12:47 |
| D11-T2 | 2770 | 2025-12-24 03:17 | 2724 | 04:06 | 0.0103 | 04:17 |
| D11-T3 | 2811 | 2025-12-27 16:33 | 2739 | 17:25 | 0.0255 | 18:26 |
| D11-T4 | 2705 | 2026-01-08 20:36 | 2673 | 21:23 | 0.0197 | 21:39 |
| D11-T5 | 2685 | 2026-04-16 13:32 | 2662 | 14:20 | 0.0131 | 14:54 |
| D12-Base | 2469 | 2026-01-20 17:29 | 2439 | 18:06 | 0.0257 | 18:38 |
| D12-T2 | 2457 | 2026-01-26 12:41 | 2426 | 13:20 | 0.0616 | 13:54 |
| D12-T3 | 2502 | 2026-02-01 18:24 | 2438 | 19:58 | 0.00351 | — |
| D12-T4 | 2546 | 2026-02-14 17:30 | 2521 | 18:15 | 0.0174 | 18:59 |
| D12-T5 | 2261 | 2026-02-24 20:49 | 2243 | 21:24 | 0.0202 | 21:40 |

### B. DDR Extract Example (D11-T5)

From DDR 04/16/2026:
```
Circulated hole clean with 4.0 x BU
Parameters:
- 3800lpm / 249bar
- 140rpm / 24kNm
- Recked back 1 stand for each BU
- Shakers started to clean up and active volume leveled off after 3.4 x BU
- Recovered 9.7mt cuttings during circulation
```

**Key data points:**
- BU count: 4.0 (shakers clean at 3.4)
- Flow: 3800 lpm
- RPM: 140
- Cuttings recovered: 9.7 MT

### C. Data File Locations

**AkerBP D11/D12 Files:**
```
Data_Export__Rig_Data___25_2D11__12_25_*.csv       # D11 Base
Data_Export__Rig_Data___25_2D11_T2__12_25_*.csv    # D11 T2
Data_Export__Rig_Data___25_2D11_T3__12_25_*.csv    # D11 T3
Data_Export__Rig_Data___25_2D11_T4__12_25_*.csv    # D11 T4
Data_Export__Rig_Data___25_2D11_T5__12_25_*.csv    # D11 T5
Data_Export__Rig_Data___25_2D12__12_25_*.csv       # D12 Base
Data_Export__Rig_Data___25_2D12_T2__12_25_*.csv    # D12 T2
Data_Export__Rig_Data___25_2D12_T3__12_25_*.csv    # D12 T3
Data_Export__Rig_Data___25_2D12_T4__12_25_*.csv    # D12 T4
Data_Export__Rig_Data___25_2D12_T5__12_25_*.csv    # D12 T5
```

**DDR Files Available:**
```
252d11_T5_DDR_04_15_2026.pdf
252d11_T5_DDR_04_16_2026.PDF
252d11_T5_DDR_04_17_2026.pdf
252d11_T5_DDR_04_18_2026.PDF
nobleintegrator252d11t5drillscenedrilltronicsdailyreport160425_1.pdf
nobleintegrator252d11t5drillscenedrilltronicsdailyreport170425.pdf
nobleintegrator252d11t5drillscenedrilltronicsdailyreport180425.pdf
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-28 | Siya Rostami | Initial draft |

