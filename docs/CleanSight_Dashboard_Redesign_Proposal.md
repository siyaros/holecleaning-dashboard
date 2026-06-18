# CleanSight Dashboard 2.0 Redesign Proposal
## From Data Display to Decision Support

**Prepared by:** Siyar (Consultant)  
**Date:** April 30, 2026  
**Version:** 1.0

---

## Executive Summary

Based on extensive analysis of CleanSight data from multiple wells (HH_1i01_PH, 25_2-D-11, 25_2-D-12), I'm proposing a redesign that transforms the dashboard from a **data visualization tool** into a **decision support system**. The key insight: drilling teams don't need more data—they need **actionable intelligence at the right moment**.

### Core Philosophy
> **"If you see X, do Y"** — Every screen should answer: "What should I do right now?"

---

## Current State Analysis

### What Dashboard 2.0 Proposes (from your PDF):
1. **Tab 1: Drilling Operations** — Generic drilling data display
2. **Tab 2: Digital Shaker Display** — ACR, CSD, UFO panels
3. **Tab 3: Free Panels** — Customizable charts + data export

### What's Missing:
| Gap | Impact |
|-----|--------|
| No decision thresholds | Users see data but don't know when to act |
| No predictive alerts | Problems detected after they happen |
| No cross-well context | Each well analyzed in isolation |
| No OK2Trip integration | Circulation decisions still subjective |
| No role-based views | Driller sees same screen as engineer |

---

## Proposed Redesign: 4-Tab Architecture

### Tab 1: COMMAND CENTER (Primary View)
**Purpose:** Single-screen situational awareness with decision prompts

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLEANSIGHT COMMAND CENTER                           Well: 25_2-D-11 T3    │
│  ══════════════════════════════════════════════════════════════════════════│
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   TCR %     │  │   UFO/hr    │  │  OK2Trip    │  │  Efficiency │       │
│  │   [1.07]    │  │   [0.4]     │  │   [READY]   │  │   [12%]     │       │
│  │   ✓ NORMAL  │  │   ✓ NORMAL  │  │   ✓ GREEN   │  │   ⚠ LOW     │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DECISION PROMPT                                                     │   │
│  │  ════════════════                                                    │   │
│  │  ✓ Hole cleaning normal. Continue operations.                       │   │
│  │                                                                      │   │
│  │  WATCH: Drilling efficiency at 12% — consider reviewing parameters  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌────────────────────────────────┐  ┌────────────────────────────────┐   │
│  │  TCR TREND (Last 6 Hours)      │  │  CRR vs DEPTH                  │   │
│  │  ┌─────────────────────────┐   │  │  ┌─────────────────────────┐   │   │
│  │  │    ___      ___         │   │  │  │ ████                    │   │   │
│  │  │ __/   \____/   \___     │   │  │  │ ████████                │   │   │
│  │  │                    1.0  │   │  │  │ ██████                  │   │   │
│  │  └─────────────────────────┘   │  │  └─────────────────────────┘   │   │
│  └────────────────────────────────┘  └────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  RECENT ALERTS                                                       │   │
│  │  ────────────────────────────────────────────────────────────────── │   │
│  │  14:32  UFO detected at 2456m - Tabular shape - [View Video]        │   │
│  │  13:45  TCR crossed 1.10 threshold - monitoring                     │   │
│  │  11:20  Circulation complete - CRR returned to baseline             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Key Features:
1. **Traffic Light KPIs** — Instant status: Green/Yellow/Red
2. **Decision Prompt Box** — Plain English: "What should I do?"
3. **Threshold-Based Alerts** — Auto-trigger at TCR >1.15, UFO >2/hr, etc.
4. **Trend Sparklines** — See direction without deep analysis
5. **Alert Feed** — Clickable history with video links

---

### Tab 2: HOLE CLEANING ANALYSIS (Deep Dive)
**Purpose:** Detailed metrics for engineering analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  HOLE CLEANING ANALYSIS                                                     │
│  ══════════════════════════════════════════════════════════════════════════│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  TCR DEVIATION ANALYSIS                                              │   │
│  │  ════════════════════                                                │   │
│  │                                                                      │   │
│  │  [Measured TCR]  ████████████████████████████████████  1491 bbl     │   │
│  │  [Theoretical]   █████████████████████████████         1103 bbl     │   │
│  │  [Excess]        ████████                               388 bbl     │   │
│  │                                                                      │   │
│  │  TCR Ratio: 1.35 (+35%)  ⚠ ELEVATED - Check caliper correlation    │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │              TCR Ratio vs Depth                              │    │   │
│  │  │  1.4 ┤                              ████                     │    │   │
│  │  │  1.2 ┤                    ██████████                         │    │   │
│  │  │  1.0 ┤████████████████████                                   │    │   │
│  │  │  0.8 ┤                                                       │    │   │
│  │  │      └────────────────────────────────────────────────────   │    │   │
│  │  │       3000m              3500m              4000m            │    │   │
│  │  │                                                              │    │   │
│  │  │       ↑ Deviation started: ~4073m (Apr 10, 16:00)           │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────────────────────┐   │
│  │  RECOVERY BY DEPTH       │  │  CSD DISTRIBUTION                    │   │
│  │  ════════════════        │  │  ════════════════                    │   │
│  │  [Heatmap showing        │  │  [Bell curve showing particle       │   │
│  │   measured vs expected   │  │   size distribution with            │   │
│  │   cuttings per meter]    │  │   UFO zone (>30mm) highlighted]     │   │
│  │                          │  │                                      │   │
│  │  ▓▓▓░░░░░░░░░░ 100%+     │  │       ▄▄████▄▄                      │   │
│  │  ▓▓▓▓▓▓░░░░░░░ 80-100%   │  │     ▄██████████▄    ← Normal        │   │
│  │  ▓▓▓▓▓▓▓▓▓░░░░ 60-80%    │  │   ▄████████████████▄                │   │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓░ <60%      │  │  ████████████████████ ███ UFO Zone │   │
│  └──────────────────────────┘  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Key Features:
1. **TCR Deviation Chart** — Show exactly where problems started
2. **Depth Correlation** — Link TCR anomalies to specific intervals
3. **Recovery Heatmap** — Visual "fingerprint" of hole cleaning by depth
4. **CSD Histogram** — With UFO zone (>30mm) clearly marked
5. **Comparison Mode** — Overlay historical wells for benchmarking

---

### Tab 3: OK2TRIP MONITOR (Circulation Decision Support)
**Purpose:** Real-time guidance for circulation completion

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  OK2TRIP MONITOR                                          Status: ACTIVE   │
│  ══════════════════════════════════════════════════════════════════════════│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │   ██████████████████████████████████████████████░░░░░░░░░░░░░░░░░   │   │
│  │   ║                                              ║                   │   │
│  │   ║              CRR RETURNING TO BASELINE       ║                   │   │
│  │   ║                                              ║                   │   │
│  │   ████████████████████████████████████████████████████░░░░░░░░░░░   │   │
│  │                                                                      │   │
│  │   Current CRR: 0.012 m³/min    Baseline: 0.003 m³/min               │   │
│  │   Time circulating: 32 min     Est. remaining: 8-12 min             │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌───────────────────────────────┐  ┌───────────────────────────────────┐ │
│  │  STATUS                       │  │  RECOMMENDATION                   │ │
│  │  ════════                     │  │  ══════════════                   │ │
│  │                               │  │                                   │ │
│  │   🟡 CIRCULATING              │  │  Continue circulating.            │ │
│  │                               │  │  CRR still 4x baseline.           │ │
│  │   Cuttings still returning    │  │                                   │ │
│  │   Do NOT trip yet             │  │  When CRR < 0.005 m³/min for     │ │
│  │                               │  │  5+ minutes → OK to trip          │ │
│  └───────────────────────────────┘  └───────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CRR TREND (This Circulation)                                        │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │  0.08 ┤ ▄▄                                                    │   │   │
│  │  │  0.06 ┤ ██▄                                                   │   │   │
│  │  │  0.04 ┤ ████▄▄                                                │   │   │
│  │  │  0.02 ┤ ████████▄▄▄▄▄▄___                                     │   │   │
│  │  │  0.00 ┤ ─────────────────────────────────────  ← Baseline     │   │   │
│  │  │       └───────────────────────────────────────────────────    │   │   │
│  │  │        0      10      20      30      40      50 min          │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  [▶ START TIMER]  [📊 VIEW HISTORY]  [⚙️ SET BASELINE]              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Key Features:
1. **Visual Progress Bar** — How close to "clean" are we?
2. **CRR Trend Chart** — Real-time with baseline overlay
3. **Plain English Status** — "OK to trip" / "Continue circulating"
4. **Estimated Time** — Based on current decay rate
5. **History Button** — Compare to previous circulations

---

### Tab 4: WELL COMPARISON (Cross-Well Intelligence)
**Purpose:** Learn from other wells, benchmark performance

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WELL COMPARISON                                                            │
│  ══════════════════════════════════════════════════════════════════════════│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SELECT WELLS TO COMPARE                                             │   │
│  │  ═══════════════════════                                             │   │
│  │                                                                      │   │
│  │  [✓] 25_2-D-11 (Current)    [✓] 25_2-D-12    [ ] HH_1i01_PH         │   │
│  │                                                                      │   │
│  │  Section: [12.25" ▼]   Metric: [TCR Ratio ▼]   Period: [All ▼]      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  COMPARISON MATRIX                                                   │   │
│  │  ══════════════════                                                  │   │
│  │                                                                      │   │
│  │  Well        │ Sidetracks │ Total Hrs │ UFO Total │ Avg TCR │ Best  │   │
│  │  ────────────┼────────────┼───────────┼───────────┼─────────┼───────│   │
│  │  25_2-D-11   │     5      │    618    │    424    │  0.98   │  T5   │   │
│  │  25_2-D-12   │     5      │    628    │   1,187   │  1.12   │  T3   │   │
│  │  HH_1i01_PH  │     1      │     93    │     75    │  1.35   │  -    │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────────────────────┐   │
│  │  TCR COMPARISON          │  │  LESSONS LEARNED                     │   │
│  │  ══════════════          │  │  ═══════════════                     │   │
│  │                          │  │                                      │   │
│  │  [Overlay chart showing  │  │  • D-12 T2: 424 UFOs, zero progress │   │
│  │   TCR trends from        │  │    → Early sidetrack recommended    │   │
│  │   selected wells]        │  │                                      │   │
│  │                          │  │  • D-12 T4: TCR 1.36 (+36% excess)  │   │
│  │   ─── D-11               │  │    → Correlates with 598 UFO events │   │
│  │   ─── D-12               │  │                                      │   │
│  │   ─── HH_1i01            │  │  • D-11 T2: Low TCR (0.82)          │   │
│  │                          │  │    → Poor cleaning before failure   │   │
│  └──────────────────────────┘  └──────────────────────────────────────┘   │
│                                                                             │
│  [📥 EXPORT COMPARISON]  [📄 GENERATE REPORT]  [📊 ADD TO BENCHMARK]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Key Features:
1. **Multi-Well Selection** — Compare 2-5 wells simultaneously
2. **Sortable Matrix** — Rank by any metric
3. **Overlay Charts** — Visual comparison of trends
4. **Lessons Learned Panel** — Auto-generated insights
5. **Export/Report** — One-click PDF generation

---

## Decision Thresholds (Built Into Dashboard)

### TCR Ratio Thresholds
| Value | Color | Status | Dashboard Action |
|-------|-------|--------|------------------|
| 0.95 - 1.05 | 🟢 Green | Normal | "Continue operations" |
| 1.05 - 1.15 | 🟡 Yellow | Monitor | "Check CSD for changes" |
| 1.15 - 1.30 | 🟠 Orange | Warning | "Review with drilling engineer" |
| > 1.30 | 🔴 Red | Alarm | "STOP - Consider circulation/wiper trip" |
| < 0.85 | 🔵 Blue | Under-recovery | "Increase flow rate" |

### UFO Rate Thresholds
| Value | Color | Status | Dashboard Action |
|-------|-------|--------|------------------|
| < 1.0/hr | 🟢 Green | Normal | No action needed |
| 1.0 - 2.0/hr | 🟡 Yellow | Elevated | "Monitor - check video links" |
| > 3.0/hr | 🔴 Red | Severe | "ALERT - Active cavings" |

### OK2Trip Criteria
| Condition | Status | Action |
|-----------|--------|--------|
| CRR > 2x baseline | 🔴 Not Ready | "Continue circulating" |
| CRR 1-2x baseline | 🟡 Almost | "5-10 more minutes" |
| CRR < 1.2x baseline for 5 min | 🟢 Ready | "OK TO TRIP" |

---

## Role-Based Views (Toggle in Header)

### Driller View
- Command Center (default)
- OK2Trip Monitor
- Simplified metrics (CRR, UFO alerts)
- Large fonts, touch-friendly

### WSG View
- Hole Cleaning Analysis (default)
- CSD/UFO focus
- Formation correlation
- Depth-indexed displays

### Drilling Engineer View
- Full access to all tabs
- TCR deviation analysis
- Cross-well comparison
- Data export tools

### Company Man View
- Command Center summary
- Efficiency metrics
- Cost tracking ($ saved)
- End-of-section reports

---

## Technical Recommendations

### 1. Alert System
```
Priority 1 (Immediate popup):
  - TCR > 1.30
  - UFO > 5/hr sustained
  - CRR spike > 3x baseline

Priority 2 (Banner notification):
  - TCR > 1.15
  - UFO > 2/hr
  - Efficiency < 10%

Priority 3 (Log entry):
  - Threshold crossings
  - Circulation start/stop
  - Depth milestones
```

### 2. Data Refresh Rates
| Component | Refresh Rate |
|-----------|-------------|
| KPI cards | 10 seconds |
| Trend charts | 30 seconds |
| Alert feed | Real-time (push) |
| Comparison data | On demand |

### 3. Offline Capability
- Cache last 24 hours of data locally
- Queue alerts when connectivity lost
- Sync automatically when reconnected

### 4. Mobile Considerations
- Command Center optimized for tablet
- OK2Trip works on phone
- Push notifications for Priority 1 alerts

---

## Implementation Phases

### Phase 1 (4 weeks): Command Center + OK2Trip
- Traffic light KPIs with thresholds
- Decision prompt engine
- Basic alert feed
- OK2Trip real-time monitor

### Phase 2 (4 weeks): Hole Cleaning Analysis
- TCR deviation charts
- Recovery heatmap
- CSD visualization
- UFO video integration

### Phase 3 (4 weeks): Cross-Well Comparison
- Multi-well selection
- Comparison matrix
- Overlay charts
- Report generation

### Phase 4 (2 weeks): Polish & Role Views
- Role-based presets
- Mobile optimization
- Alert tuning
- User feedback integration

---

## Mockup: Command Center (Full Design)

I've created an interactive HTML mockup that demonstrates the Command Center concept. See the attached file:

**`cleansight_dashboard_redesign_mockup.html`**

This shows:
- Traffic light KPIs
- Decision prompt box
- Real-time trend charts
- Alert feed with timestamps
- Dark theme matching DrillDocs brand

---

## Summary: What Makes This Different

| Current Approach | Proposed Approach |
|------------------|-------------------|
| Shows data | Drives decisions |
| User interprets | System recommends |
| Static thresholds | Context-aware alerts |
| Single well focus | Cross-well learning |
| Engineer-centric | Role-optimized |
| Passive display | Active guidance |

**The goal:** A driller should be able to glance at the dashboard and know in 3 seconds: "Am I OK, or do I need to act?"

---

## Next Steps

1. **Review this proposal** with DrillDocs development team
2. **Prioritize features** for MVP vs future releases
3. **Create detailed wireframes** for approved tabs
4. **Define API requirements** for new visualizations
5. **User testing** with actual rig personnel

---

*Prepared by Siyar | DrillDocs Consulting*
*Contact: [your email]*
