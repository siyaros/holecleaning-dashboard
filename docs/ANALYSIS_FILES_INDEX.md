# DrillDocs CleanSight Analysis Files Index
## Cross-Well Comparison Data Repository

Generated: April 30, 2026

---

## 🛠️ PYTHON ANALYSIS TOOLS (Reusable)

| File | Description | Usage |
|------|-------------|-------|
| `cleansight_analyzer.py` | **MAIN CLI TOOL** - Full analysis suite | `python cleansight_analyzer.py --input data.csv` |
| `tcr_deviation_dashboard.py` | Interactive TCR deviation dashboard generator | `python tcr_deviation_dashboard.py` |
| `tcr_deviation_analysis.py` | TCR analysis with depth correlation | Standalone analysis |
| `tcr_deviation_analysis_interactive.py` | Interactive version with widgets | Jupyter/interactive use |
| `generate_dashboard.py` | HTML dashboard generator | `python generate_dashboard.py` |

---

## 📊 INTERACTIVE DASHBOARDS

| File | Description |
|------|-------------|
| `sidetrack_analysis_dashboard.html` | **Cross-well sidetrack comparison** (D-11 vs D-12) |
| `cleansight_dashboard.html` | Main CleanSight dashboard with TCR deviation analysis |
| `caliper_analysis_dashboard.html` | Caliper-based hole enlargement validation |

---

## 📄 MARKETING DELIVERABLES

| File | Description |
|------|-------------|
| `DrillDocs_CleanSight_Pitch_Deck.pptx` | 12-slide sales presentation |
| `DrillDocs_CleanSight_Onboarding_Guide.docx` | Client onboarding guide with decision matrix |
| `wellbore_caliper_schematic_clean.svg` | Wellbore schematic visualization |

---

## 📊 SIDETRACK ANALYSIS FILES

### Summary & Analysis
| File | Description |
|------|-------------|
| `sidetrack_analysis_summary.csv` | High-level summary of all 10 sidetracks (both wells) with TCR, UFO, efficiency metrics |
| `sidetrack_summary.csv` | Detailed breakdown by sidetrack with timestamps and outcomes |
| `combined_sidetrack_data.csv` | **MASTER FILE** - All 73,333 rows of time-series data from both wells combined |

### Interactive Dashboards
| File | Description |
|------|-------------|
| `sidetrack_analysis_dashboard.html` | Interactive dashboard comparing D-11 and D-12 sidetracks |
| `cleansight_dashboard.html` | Main CleanSight dashboard with TCR deviation analysis |
| `caliper_analysis_dashboard.html` | Caliper-based hole enlargement analysis |

---

## 📁 INDIVIDUAL WELL DATA (UTF-8 Cleaned)

### Well 25_2-D-11 (12.25" Section)
| File | Sidetrack | Period | Rows |
|------|-----------|--------|------|
| `25_2_D11_Original_cleaned.csv` | Original | Dec 18-22, 2025 | 5,601 |
| `25_2_D11_T2_cleaned.csv` | T2 | Dec 23-25, 2025 | 3,064 |
| `25_2_D11_T3_cleaned.csv` | T3 | Dec 26 - Jan 3 | 12,216 |
| `25_2_D11_T4_cleaned.csv` | T4 | Jan 6-14, 2026 | 12,389 |
| `25_2_D11_T5_cleaned.csv` | T5 | Apr 15-18, 2026 | 3,839 |

### Well 25_2-D-12 (12.25" Section)
| File | Sidetrack | Period | Rows |
|------|-----------|--------|------|
| `25_2_D12_Original_cleaned.csv` | Original | Jan 20-23, 2026 | 5,369 |
| `25_2_D12_T2_cleaned.csv` | T2 | Jan 25-30, 2026 | 8,170 |
| `25_2_D12_T3_cleaned.csv` | T3 | Feb 1-10, 2026 | 13,213 |
| `25_2_D12_T4_cleaned.csv` | T4 | Feb 14-19, 2026 | 7,733 |
| `25_2_D12_T5_cleaned.csv` | T5 | Feb 24-26, 2026 | 3,193 |

---

## 📁 CALIPER & LWD ANALYSIS (HH_1i01_PH Well)

| File | Description |
|------|-------------|
| `lwd_caliper_manual_entry_enhanced.csv` | 111 manual caliper points with enlargement % |
| `caliper_excess_cuttings_detailed.csv` | Interval-by-interval excess calculations |
| `caliper_excess_cuttings_by_zone.csv` | Summary by hole condition zone |
| `caliper_analysis_summary.csv` | Overall caliper validation metrics |
| `theoretical_cuttings_results.csv` | Theoretical vs measured cuttings comparison |

---

## 🔑 KEY METRICS REFERENCE

### TCR Ratio Thresholds
| Range | Status | Meaning |
|-------|--------|---------|
| 0.95 - 1.05 | ✅ Normal | Hole cleaning as expected |
| 1.05 - 1.15 | ⚠️ Monitor | Slight excess, check CSD |
| 1.15 - 1.30 | 🟠 Warning | Significant excess, possible cavings |
| > 1.30 | 🔴 Alarm | Major instability, consider action |
| < 0.85 | 🔵 Under-recovery | Cuttings not reaching surface |

### UFO Rate Thresholds
| Rate | Status |
|------|--------|
| < 1.0/hr | Normal baseline |
| 1.0 - 2.0/hr | Elevated, monitor |
| > 3.0/hr | Severe cavings activity |

---

## 📈 CROSS-WELL COMPARISON FINDINGS

### D-11 vs D-12 Summary
| Metric | 25_2-D-11 | 25_2-D-12 |
|--------|-----------|-----------|
| Total Sidetracks | 5 | 5 |
| Total Duration | 618 hrs (26 days) | 628 hrs (26 days) |
| Total UFO Events | 424 | 1,187 |
| Failed Sidetracks | 1 (T2) | 2 (T2, T4) |
| Max TCR Deviation | +7% (T3) | +36% (T4) |
| Best Efficiency | 36% (T5) | 20% (T5) |

### Critical Events Detected
1. **D-11 T2**: UFO 3.1/hr + TCR 0.82 → Failed (poor cleaning)
2. **D-12 T2**: 424 UFOs + zero progress → Failed (instability)
3. **D-12 T4**: 598 UFOs + TCR 1.36 → Near-failure (severe cavings)

---

## 🛠️ HOW TO USE THIS DATA

### For Cross-Well Comparison:
```python
import pandas as pd

# Load combined data
df = pd.read_csv('combined_sidetrack_data.csv')

# Filter by well
d11 = df[df['Well'] == 'D-11']
d12 = df[df['Well'] == 'D-12']

# Compare TCR ratios
d11_tcr = d11.groupby('Sidetrack')['TCR_Ratio'].last()
d12_tcr = d12.groupby('Sidetrack')['TCR_Ratio'].last()
```

### For Individual Sidetrack Analysis:
```python
# Load specific sidetrack
t2 = pd.read_csv('25_2_D12_T2_cleaned.csv', sep='\t')

# Analyze UFO trend
ufo_hourly = t2.groupby(t2['time'].dt.floor('H'))['UFO Count'].sum()
```

---

## 📞 SUPPORT

**DrillDocs Remote Monitoring**: remote-monitoring@drilldocs.com
**Technical Support**: customer-support@drilldocs.com
**Website**: www.drilldocs.com

---

*Generated by CleanSight Analysis Tools*
*© 2026 DrillDocs*
