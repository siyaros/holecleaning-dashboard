# CleanSight Data Explorer & CuC Analysis Tools

Personal portfolio of drilling data analysis tools and methodologies developed for hole cleaning optimization in oil & gas drilling operations.

## Overview

This repository contains tools and dashboards for analyzing Cuttings Return Rate (CRR) data to optimize Clean-up Circulation (CuC) operations during drilling.

### Key Methodologies Developed

1. **CuC Normalization Framework**
   - Normalizes CRR to % of CRR@TD (85% reduction = clean)
   - Normalizes time to BU (Bottoms Up) cycles
   - Allows comparison of any well regardless of hole size or depth

2. **TCBU (Theoretical Clean Bottoms Up) Factors**
   - Empirically derived multipliers based on wellbore inclination zones
   - Zone 0-30°: Factor 1.94×
   - Zone 30-60°: Factor 2.37×
   - Zone 60°+: Factor 3.70×
   - MAE = 0.82 BU cycles across 15 wells

3. **Data Cleaning Pipeline**
   - Handles sensor noise in inclination readings
   - Filters outliers using mode-based approach
   - Supports multiple CSV encodings (UTF-8, UTF-16-LE, CP1252)

## Repository Structure

```
├── dashboard/           # CleanSight Data Explorer (latest v3.3.6)
├── python_scripts/      # Analysis and data processing scripts
├── analysis/            # Interactive HTML dashboards
├── docs/                # PRDs and documentation
└── charts/              # Visualization outputs
```

## Dashboard Features

- Multi-well comparison analysis
- CRR normalization and overlay
- BU cycle calculation
- Dynamic clean threshold detection
- Support for 12.25" and 16.5" hole sections

## Technologies

- Python (pandas, numpy, scipy)
- HTML/CSS/JavaScript
- Chart.js for visualizations

## Author

Siya Rostami - Drilling Engineer & Data Analyst

## License

This work is proprietary. All rights reserved.
