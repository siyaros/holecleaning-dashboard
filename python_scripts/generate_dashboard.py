#!/usr/bin/env python3
"""
CleanSight Dashboard Generator
==============================
Generates the interactive HTML dashboard from CleanSight data exports.

This creates the styled dashboard with:
- 4 tabs: Overview, Time Series, Cross-Plots, Analysis
- KPI cards with key metrics
- Interactive Chart.js visualizations
- Dark theme with professional styling

Usage:
    python generate_dashboard.py your_data.csv
    python generate_dashboard.py your_data.csv --output my_dashboard.html
"""

import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np

# Dashboard HTML Template
DASHBOARD_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CleanSight Hole Cleaning Analysis Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e14;
            --bg-secondary: #111820;
            --bg-card: #151d28;
            --bg-card-hover: #1a2432;
            --border: #2a3744;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #5c6670;
            --accent-orange: #ff6b35;
            --accent-orange-dim: rgba(255, 107, 53, 0.2);
            --accent-cyan: #00d9ff;
            --accent-cyan-dim: rgba(0, 217, 255, 0.15);
            --accent-green: #3fb950;
            --accent-green-dim: rgba(63, 185, 80, 0.15);
            --accent-yellow: #f0b429;
            --accent-yellow-dim: rgba(240, 180, 41, 0.15);
            --accent-red: #f85149;
            --accent-red-dim: rgba(248, 81, 73, 0.15);
            --accent-purple: #a371f7;
            --grid-line: rgba(255,255,255,0.06);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }

        .noise-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none; opacity: 0.03; z-index: 1000;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
        }

        header {
            background: linear-gradient(180deg, var(--bg-secondary) 0%, transparent 100%);
            border-bottom: 1px solid var(--border);
            padding: 20px 32px;
            position: sticky; top: 0; z-index: 100;
            backdrop-filter: blur(12px);
        }

        .header-content {
            max-width: 1800px; margin: 0 auto;
            display: flex; justify-content: space-between; align-items: center;
            flex-wrap: wrap; gap: 16px;
        }

        .logo-section { display: flex; align-items: center; gap: 16px; }

        .logo {
            width: 42px; height: 42px;
            background: linear-gradient(135deg, var(--accent-orange) 0%, #ff8c42 100%);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 18px; color: white;
            box-shadow: 0 4px 20px rgba(255, 107, 53, 0.3);
        }

        h1 { font-size: 22px; font-weight: 600; letter-spacing: -0.5px; }
        h1 span { color: var(--accent-orange); }

        .stats-bar { display: flex; gap: 24px; flex-wrap: wrap; }
        .stat-item { text-align: center; }
        .stat-value { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 600; color: var(--accent-cyan); }
        .stat-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }

        main { max-width: 1800px; margin: 0 auto; padding: 24px 32px; }

        .dashboard-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; }

        .card {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 12px; padding: 20px; transition: all 0.2s ease;
        }
        .card:hover {
            background: var(--bg-card-hover); border-color: var(--accent-orange);
            box-shadow: 0 0 30px rgba(255, 107, 53, 0.1);
        }

        .card-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border);
        }

        .card-title {
            font-size: 14px; font-weight: 600; color: var(--text-primary);
            display: flex; align-items: center; gap: 8px;
        }
        .card-title::before {
            content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--accent-orange);
        }

        .card-badge {
            font-family: 'JetBrains Mono', monospace; font-size: 10px;
            padding: 4px 8px; border-radius: 4px;
            background: var(--accent-cyan-dim); color: var(--accent-cyan);
        }

        .chart-container { position: relative; height: 280px; }
        .chart-container.tall { height: 350px; }
        .chart-container.short { height: 200px; }

        .col-12 { grid-column: span 12; }
        .col-8 { grid-column: span 8; }
        .col-6 { grid-column: span 6; }
        .col-4 { grid-column: span 4; }
        .col-3 { grid-column: span 3; }

        @media (max-width: 1400px) {
            .col-8, .col-6 { grid-column: span 12; }
            .col-4, .col-3 { grid-column: span 6; }
        }
        @media (max-width: 900px) {
            .col-4, .col-3 { grid-column: span 12; }
            main { padding: 16px; }
        }

        .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }

        .kpi-card {
            background: var(--bg-secondary); border: 1px solid var(--border);
            border-radius: 10px; padding: 16px; text-align: center; transition: all 0.2s ease;
        }
        .kpi-card:hover { transform: translateY(-2px); border-color: var(--accent-cyan); }

        .kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 700; margin-bottom: 4px; }
        .kpi-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }

        .kpi-card.orange .kpi-value { color: var(--accent-orange); }
        .kpi-card.cyan .kpi-value { color: var(--accent-cyan); }
        .kpi-card.green .kpi-value { color: var(--accent-green); }
        .kpi-card.yellow .kpi-value { color: var(--accent-yellow); }

        .legend-row { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; justify-content: center; }
        .legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-secondary); }
        .legend-dot { width: 10px; height: 10px; border-radius: 50%; }

        .alert-banner {
            background: linear-gradient(90deg, var(--accent-red-dim) 0%, transparent 100%);
            border: 1px solid var(--accent-red); border-radius: 8px;
            padding: 12px 16px; margin-bottom: 20px;
            display: flex; align-items: center; gap: 12px;
        }
        .alert-icon {
            width: 24px; height: 24px; background: var(--accent-red); border-radius: 50%;
            display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;
        }
        .alert-text { font-size: 13px; }
        .alert-text strong { color: var(--accent-red); }

        .tab-nav {
            display: flex; gap: 4px; margin-bottom: 20px;
            background: var(--bg-secondary); padding: 4px; border-radius: 8px; width: fit-content;
        }
        .tab-btn {
            padding: 10px 20px; border: none; background: transparent;
            color: var(--text-secondary); font-family: 'Space Grotesk', sans-serif;
            font-size: 13px; font-weight: 500; cursor: pointer; border-radius: 6px; transition: all 0.2s ease;
        }
        .tab-btn:hover { color: var(--text-primary); }
        .tab-btn.active { background: var(--accent-orange); color: white; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .footer { text-align: center; padding: 32px; color: var(--text-muted); font-size: 12px; }

        .insight-box {
            background: var(--accent-green-dim); border: 1px solid var(--accent-green);
            border-radius: 8px; padding: 14px 16px; font-size: 13px; line-height: 1.5;
        }
        .insight-box.warning { background: var(--accent-yellow-dim); border-color: var(--accent-yellow); }
        .insight-box.danger { background: var(--accent-red-dim); border-color: var(--accent-red); }
    </style>
</head>
<body>
    <div class="noise-overlay"></div>
    
    <header>
        <div class="header-content">
            <div class="logo-section">
                <div class="logo">CS</div>
                <div>
                    <h1>CleanSight <span>Analytics</span></h1>
                    <div style="font-size: 12px; color: var(--text-secondary);">Hole Cleaning Performance Dashboard</div>
                </div>
            </div>
            <div class="stats-bar">
                <div class="stat-item">
                    <div class="stat-value" id="stat-time-range">--</div>
                    <div class="stat-label">Time Range</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="stat-depth-range">--</div>
                    <div class="stat-label">Depth Range (m)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="stat-drilling-pct">--</div>
                    <div class="stat-label">Drilling Time</div>
                </div>
            </div>
        </div>
    </header>

    <main>
        <div class="tab-nav">
            <button class="tab-btn active" data-tab="overview">Overview</button>
            <button class="tab-btn" data-tab="timeseries">Time Series</button>
            <button class="tab-btn" data-tab="crossplots">Cross-Plots</button>
            <button class="tab-btn" data-tab="analysis">Analysis</button>
        </div>

        <!-- OVERVIEW TAB -->
        <div class="tab-content active" id="tab-overview">
            <div class="kpi-grid" style="margin-bottom: 24px;">
                <div class="kpi-card orange">
                    <div class="kpi-value" id="kpi-avg-crr">--</div>
                    <div class="kpi-label">Avg CRR (bbl/min)</div>
                </div>
                <div class="kpi-card cyan">
                    <div class="kpi-value" id="kpi-tcr-ratio">--</div>
                    <div class="kpi-label">TCR Recovery Ratio</div>
                </div>
                <div class="kpi-card green">
                    <div class="kpi-value" id="kpi-csd-p50">--</div>
                    <div class="kpi-label">Avg CSD P50 (mm)</div>
                </div>
                <div class="kpi-card yellow">
                    <div class="kpi-value" id="kpi-ufo-total">--</div>
                    <div class="kpi-label">UFO Events</div>
                </div>
            </div>

            <div id="alert-container"></div>

            <div class="dashboard-grid">
                <div class="card col-8">
                    <div class="card-header">
                        <div class="card-title">Cuttings Recovery: Measured vs Theoretical TCR</div>
                        <div class="card-badge">PRIMARY INDICATOR</div>
                    </div>
                    <div class="chart-container tall"><canvas id="chart-tcr-comparison"></canvas></div>
                    <div class="legend-row">
                        <div class="legend-item"><div class="legend-dot" style="background: var(--accent-orange);"></div> Measured TCR</div>
                        <div class="legend-item"><div class="legend-dot" style="background: var(--accent-cyan);"></div> Theoretical TCR</div>
                    </div>
                </div>
                <div class="card col-4">
                    <div class="card-header">
                        <div class="card-title">Recovery Ratio Trend</div>
                        <div class="card-badge">TCR RATIO</div>
                    </div>
                    <div class="chart-container tall"><canvas id="chart-tcr-ratio"></canvas></div>
                    <div class="insight-box" id="insight-tcr" style="margin-top: 12px;">Loading analysis...</div>
                </div>

                <div class="card col-6">
                    <div class="card-header">
                        <div class="card-title">CRR + ROP + Flow Correlation</div>
                        <div class="card-badge">TRANSPORT</div>
                    </div>
                    <div class="chart-container"><canvas id="chart-crr-rop-flow"></canvas></div>
                </div>
                <div class="card col-6">
                    <div class="card-header">
                        <div class="card-title">Cutting Size Distribution (CSD P50)</div>
                        <div class="card-badge">SIZE TREND</div>
                    </div>
                    <div class="chart-container"><canvas id="chart-csd-p50"></canvas></div>
                </div>
            </div>
        </div>

        <!-- TIME SERIES TAB -->
        <div class="tab-content" id="tab-timeseries">
            <div class="dashboard-grid">
                <div class="card col-12">
                    <div class="card-header">
                        <div class="card-title">Cuttings Recovery Rate (CRR) Over Time</div>
                        <div class="card-badge">bbl/min</div>
                    </div>
                    <div class="chart-container tall"><canvas id="chart-crr-time"></canvas></div>
                </div>

                <div class="card col-6">
                    <div class="card-header"><div class="card-title">Drilling Parameters: ROP & RPM</div></div>
                    <div class="chart-container"><canvas id="chart-rop-rpm"></canvas></div>
                </div>
                <div class="card col-6">
                    <div class="card-header"><div class="card-title">Hydraulics: Flow In & Pump Pressure</div></div>
                    <div class="chart-container"><canvas id="chart-flow-pressure"></canvas></div>
                </div>

                <div class="card col-6">
                    <div class="card-header"><div class="card-title">Mechanical: Hook Load & Block Height</div></div>
                    <div class="chart-container"><canvas id="chart-hookload-block"></canvas></div>
                </div>
                <div class="card col-6">
                    <div class="card-header"><div class="card-title">Depth Progression</div></div>
                    <div class="chart-container"><canvas id="chart-depth"></canvas></div>
                </div>

                <div class="card col-12">
                    <div class="card-header">
                        <div class="card-title">UFO (Caving) Events Timeline</div>
                        <div class="card-badge">STABILITY</div>
                    </div>
                    <div class="chart-container short"><canvas id="chart-ufo-timeline"></canvas></div>
                </div>
            </div>
        </div>

        <!-- CROSS-PLOTS TAB -->
        <div class="tab-content" id="tab-crossplots">
            <div class="dashboard-grid">
                <div class="card col-6">
                    <div class="card-header">
                        <div class="card-title">CRR vs ROP</div>
                        <div class="card-badge">DRILLING ONLY</div>
                    </div>
                    <div class="chart-container"><canvas id="chart-xplot-crr-rop"></canvas></div>
                    <div class="insight-box" style="margin-top: 12px;">Expected: linear relationship. Weak correlation may indicate lag effects or variable transport efficiency.</div>
                </div>
                <div class="card col-6">
                    <div class="card-header">
                        <div class="card-title">CRR vs Flow In</div>
                        <div class="card-badge">DRILLING ONLY</div>
                    </div>
                    <div class="chart-container"><canvas id="chart-xplot-crr-flow"></canvas></div>
                    <div class="insight-box" style="margin-top: 12px;">Higher flow should increase cuttings transport. Strong correlation indicates responsive system.</div>
                </div>
                <div class="card col-6">
                    <div class="card-header">
                        <div class="card-title">CRR vs RPM</div>
                        <div class="card-badge">DRILLING ONLY</div>
                    </div>
                    <div class="chart-container"><canvas id="chart-xplot-crr-rpm"></canvas></div>
                    <div class="insight-box" style="margin-top: 12px;">Rotation aids cuttings transport. Positive correlation expected in deviated wells.</div>
                </div>
                <div class="card col-6">
                    <div class="card-header">
                        <div class="card-title">CRR vs CSD P50</div>
                        <div class="card-badge">DRILLING ONLY</div>
                    </div>
                    <div class="chart-container"><canvas id="chart-xplot-crr-csd"></canvas></div>
                    <div class="insight-box" style="margin-top: 12px;">Larger cuttings = higher volume. Strong correlation confirms size contributes to CRR readings.</div>
                </div>
            </div>
        </div>

        <!-- ANALYSIS TAB -->
        <div class="tab-content" id="tab-analysis">
            <div class="dashboard-grid">
                <div class="card col-12">
                    <div class="card-header"><div class="card-title">Hole Cleaning Assessment Summary</div></div>
                    <div id="analysis-summary" style="line-height: 1.7;">Loading analysis...</div>
                </div>
                <div class="card col-6">
                    <div class="card-header">
                        <div class="card-title">Pit Volume Trend</div>
                        <div class="card-badge">GAIN/LOSS</div>
                    </div>
                    <div class="chart-container"><canvas id="chart-pit-volume"></canvas></div>
                </div>
                <div class="card col-6">
                    <div class="card-header"><div class="card-title">CRR Distribution: Drilling vs Non-Drilling</div></div>
                    <div class="chart-container"><canvas id="chart-crr-distribution"></canvas></div>
                </div>
            </div>
        </div>
    </main>

    <footer class="footer">
        CleanSight Data Analysis Dashboard • Generated from DrillDocs export
    </footer>

    <script>
    const DATA = %%DATA_PLACEHOLDER%%;

    Chart.defaults.color = '#8b949e';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
    Chart.defaults.font.family = "'JetBrains Mono', monospace";

    const chartOptions = {
        responsive: true, maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
            legend: { display: false },
            tooltip: { backgroundColor: '#151d28', borderColor: '#2a3744', borderWidth: 1, titleColor: '#e6edf3', bodyColor: '#8b949e', padding: 12, cornerRadius: 8 }
        },
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { maxTicksLimit: 10 } },
            y: { grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true }
        }
    };

    document.addEventListener('DOMContentLoaded', function() {
        populateStats();
        createCharts();
        setupTabs();
        generateAnalysis();
    });

    function populateStats() {
        document.getElementById('stat-time-range').textContent = DATA.stats.duration || '--';
        document.getElementById('stat-depth-range').textContent = `${DATA.stats.depth_start.toFixed(0)} - ${DATA.stats.depth_end.toFixed(0)}`;
        document.getElementById('stat-drilling-pct').textContent = `${DATA.stats.drilling_pct.toFixed(0)}%`;
        document.getElementById('kpi-avg-crr').textContent = DATA.stats.avg_crr_drilling.toFixed(3);
        document.getElementById('kpi-tcr-ratio').textContent = DATA.stats.avg_tcr_ratio.toFixed(2);
        document.getElementById('kpi-ufo-total').textContent = DATA.stats.ufo_total;
        const validCsd = DATA.csd_p50.filter(v => v > 0);
        const avgCsd = validCsd.length > 0 ? validCsd.reduce((a,b) => a+b, 0) / validCsd.length : 0;
        document.getElementById('kpi-csd-p50').textContent = avgCsd.toFixed(1);

        if (DATA.stats.avg_tcr_ratio > 1.2) {
            document.getElementById('alert-container').innerHTML = `
                <div class="alert-banner">
                    <div class="alert-icon">!</div>
                    <div class="alert-text">
                        <strong>Over-Recovery Detected:</strong> TCR ratio averaging ${DATA.stats.avg_tcr_ratio.toFixed(2)} 
                        suggests hole enlargement or calibration offset.
                    </div>
                </div>`;
        } else if (DATA.stats.avg_tcr_ratio < 0.8) {
            document.getElementById('alert-container').innerHTML = `
                <div class="alert-banner">
                    <div class="alert-icon">!</div>
                    <div class="alert-text">
                        <strong>Under-Recovery Detected:</strong> TCR ratio averaging ${DATA.stats.avg_tcr_ratio.toFixed(2)} 
                        suggests cuttings accumulation downhole.
                    </div>
                </div>`;
        }
    }

    function createCharts() {
        const labels = DATA.time.filter((_, i) => i % 6 === 0);
        const subsample = (arr) => arr.filter((_, i) => i % 6 === 0);

        // TCR Comparison
        new Chart(document.getElementById('chart-tcr-comparison'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Measured TCR', data: subsample(DATA.measured_tcr), borderColor: '#ff6b35', backgroundColor: 'rgba(255, 107, 53, 0.1)', fill: true, tension: 0.3, pointRadius: 0 },
                    { label: 'Theoretical TCR', data: subsample(DATA.theoretical_tcr), borderColor: '#00d9ff', backgroundColor: 'rgba(0, 217, 255, 0.1)', fill: true, tension: 0.3, pointRadius: 0 }
                ]
            },
            options: { ...chartOptions, plugins: { ...chartOptions.plugins, legend: { display: true, position: 'top' } } }
        });

        // TCR Ratio
        new Chart(document.getElementById('chart-tcr-ratio'), {
            type: 'line',
            data: { labels: labels, datasets: [{ label: 'Recovery Ratio', data: subsample(DATA.tcr_ratio), borderColor: '#3fb950', backgroundColor: 'rgba(63, 185, 80, 0.15)', fill: true, tension: 0.3, pointRadius: 0 }] },
            options: { ...chartOptions, scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, min: 0, max: 2 } } }
        });

        const avgRatio = DATA.stats.avg_tcr_ratio;
        let insightClass = 'insight-box', insightText = '';
        if (avgRatio > 1.2) { insightClass += ' warning'; insightText = `Average ratio of ${avgRatio.toFixed(2)} indicates over-recovery. Possible: hole enlargement, calibration offset.`; }
        else if (avgRatio < 0.8) { insightClass += ' danger'; insightText = `Average ratio of ${avgRatio.toFixed(2)} indicates under-recovery. Cuttings may be accumulating.`; }
        else { insightText = `Average ratio of ${avgRatio.toFixed(2)} is within normal range (0.85-1.15).`; }
        document.getElementById('insight-tcr').className = insightClass;
        document.getElementById('insight-tcr').textContent = insightText;

        // CRR + ROP + Flow
        new Chart(document.getElementById('chart-crr-rop-flow'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'CRR (bbl/min)', data: subsample(DATA.crr), borderColor: '#ff6b35', yAxisID: 'y', tension: 0.3, pointRadius: 0 },
                    { label: 'ROP (ft/h)', data: subsample(DATA.rop), borderColor: '#00d9ff', yAxisID: 'y1', tension: 0.3, pointRadius: 0 },
                    { label: 'Flow In (gpm)', data: subsample(DATA.flow_in), borderColor: '#3fb950', yAxisID: 'y2', tension: 0.3, pointRadius: 0, borderDash: [5, 5] }
                ]
            },
            options: {
                ...chartOptions,
                plugins: { ...chartOptions.plugins, legend: { display: true, position: 'top' } },
                scales: { x: chartOptions.scales.x, y: { type: 'linear', position: 'left', title: { display: true, text: 'CRR' } }, y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } }, y2: { display: false } }
            }
        });

        // CSD P50
        new Chart(document.getElementById('chart-csd-p50'), {
            type: 'line',
            data: { labels: labels, datasets: [{ label: 'CSD P50 (mm)', data: subsample(DATA.csd_p50), borderColor: '#a371f7', backgroundColor: 'rgba(163, 113, 247, 0.15)', fill: true, tension: 0.3, pointRadius: 0 }] },
            options: chartOptions
        });

        // CRR Over Time
        new Chart(document.getElementById('chart-crr-time'), {
            type: 'line',
            data: { labels: labels, datasets: [{ label: 'CRR (bbl/min)', data: subsample(DATA.crr), borderColor: '#ff6b35', backgroundColor: 'rgba(255, 107, 53, 0.1)', fill: true, tension: 0.3, pointRadius: 0 }] },
            options: chartOptions
        });

        // ROP & RPM
        new Chart(document.getElementById('chart-rop-rpm'), {
            type: 'line',
            data: { labels: labels, datasets: [
                { label: 'ROP (ft/h)', data: subsample(DATA.rop), borderColor: '#00d9ff', yAxisID: 'y', tension: 0.3, pointRadius: 0 },
                { label: 'RPM', data: subsample(DATA.rpm), borderColor: '#f0b429', yAxisID: 'y1', tension: 0.3, pointRadius: 0 }
            ]},
            options: { ...chartOptions, plugins: { ...chartOptions.plugins, legend: { display: true, position: 'top' } }, scales: { x: chartOptions.scales.x, y: { type: 'linear', position: 'left' }, y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } } } }
        });

        // Flow & Pressure
        new Chart(document.getElementById('chart-flow-pressure'), {
            type: 'line',
            data: { labels: labels, datasets: [
                { label: 'Flow In (gpm)', data: subsample(DATA.flow_in), borderColor: '#3fb950', yAxisID: 'y', tension: 0.3, pointRadius: 0 },
                { label: 'Pump Pressure (psi)', data: subsample(DATA.pump_pressure), borderColor: '#f85149', yAxisID: 'y1', tension: 0.3, pointRadius: 0 }
            ]},
            options: { ...chartOptions, plugins: { ...chartOptions.plugins, legend: { display: true, position: 'top' } }, scales: { x: chartOptions.scales.x, y: { type: 'linear', position: 'left' }, y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } } } }
        });

        // Hook Load & Block Height
        new Chart(document.getElementById('chart-hookload-block'), {
            type: 'line',
            data: { labels: labels, datasets: [
                { label: 'Hook Load (klbf)', data: subsample(DATA.hook_load), borderColor: '#a371f7', yAxisID: 'y', tension: 0.3, pointRadius: 0 },
                { label: 'Block Height (m)', data: subsample(DATA.block_height), borderColor: '#00d9ff', yAxisID: 'y1', tension: 0.3, pointRadius: 0 }
            ]},
            options: { ...chartOptions, plugins: { ...chartOptions.plugins, legend: { display: true, position: 'top' } }, scales: { x: chartOptions.scales.x, y: { type: 'linear', position: 'left' }, y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } } } }
        });

        // Depth
        new Chart(document.getElementById('chart-depth'), {
            type: 'line',
            data: { labels: labels, datasets: [
                { label: 'Bit Depth (m)', data: subsample(DATA.bit_depth), borderColor: '#ff6b35', tension: 0.3, pointRadius: 0 },
                { label: 'Hole Depth (m)', data: subsample(DATA.hole_depth), borderColor: '#00d9ff', borderDash: [5, 5], tension: 0.3, pointRadius: 0 }
            ]},
            options: { ...chartOptions, plugins: { ...chartOptions.plugins, legend: { display: true, position: 'top' } }, scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, reverse: true, beginAtZero: false } } }
        });

        // UFO Timeline
        if (DATA.ufo_times && DATA.ufo_times.length > 0) {
            new Chart(document.getElementById('chart-ufo-timeline'), {
                type: 'scatter',
                data: { datasets: [{ label: 'UFO Events', data: DATA.ufo_times.map((t, i) => ({ x: t, y: DATA.ufo_counts[i] })), backgroundColor: '#f85149', pointRadius: 8 }] },
                options: { ...chartOptions, scales: { x: { type: 'category', labels: DATA.ufo_times }, y: { min: 0, max: 5 } } }
            });
        }

        // Cross-plots
        createScatterPlot('chart-xplot-crr-rop', DATA.crossplot.rop, DATA.crossplot.crr, '#ff6b35');
        createScatterPlot('chart-xplot-crr-flow', DATA.crossplot.flow_in, DATA.crossplot.crr, '#3fb950');
        createScatterPlot('chart-xplot-crr-rpm', DATA.crossplot.rpm, DATA.crossplot.crr, '#f0b429');
        createScatterPlot('chart-xplot-crr-csd', DATA.crossplot.csd_p50, DATA.crossplot.crr, '#a371f7');

        // Pit Volume
        new Chart(document.getElementById('chart-pit-volume'), {
            type: 'line',
            data: { labels: labels, datasets: [{ label: 'Pit Volume (bbl)', data: subsample(DATA.pit_volume), borderColor: '#00d9ff', backgroundColor: 'rgba(0, 217, 255, 0.1)', fill: true, tension: 0.3, pointRadius: 0 }] },
            options: { ...chartOptions, scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, beginAtZero: false } } }
        });

        // CRR Distribution
        const drillingCRR = DATA.crr.filter((_, i) => DATA.is_drilling[i]);
        const nonDrillingCRR = DATA.crr.filter((_, i) => !DATA.is_drilling[i]);
        new Chart(document.getElementById('chart-crr-distribution'), {
            type: 'bar',
            data: { labels: ['Min', '25%', 'Median', '75%', 'Max'], datasets: [
                { label: 'Drilling', data: calcPercentiles(drillingCRR), backgroundColor: 'rgba(255, 107, 53, 0.7)' },
                { label: 'Non-Drilling', data: calcPercentiles(nonDrillingCRR), backgroundColor: 'rgba(0, 217, 255, 0.7)' }
            ]},
            options: { ...chartOptions, plugins: { ...chartOptions.plugins, legend: { display: true, position: 'top' } } }
        });
    }

    function createScatterPlot(id, xData, yData, color) {
        const data = xData.map((x, i) => ({ x, y: yData[i] })).filter(d => d.x > 0 && d.y > 0);
        new Chart(document.getElementById(id), {
            type: 'scatter',
            data: { datasets: [{ data: data, backgroundColor: color + '80', borderColor: color, pointRadius: 3 }] },
            options: chartOptions
        });
    }

    function calcPercentiles(arr) {
        const sorted = arr.filter(v => v > 0).sort((a, b) => a - b);
        if (!sorted.length) return [0,0,0,0,0];
        const p = pct => sorted[Math.floor(sorted.length * pct)] || 0;
        return [sorted[0], p(0.25), p(0.5), p(0.75), sorted[sorted.length - 1]];
    }

    function setupTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
            });
        });
    }

    function generateAnalysis() {
        const ratio = DATA.stats.avg_tcr_ratio, ufoCount = DATA.stats.ufo_total, drillingPct = DATA.stats.drilling_pct;
        let html = `
            <h3 style="color: var(--accent-orange); margin-bottom: 16px;">Dataset Overview</h3>
            <p><strong>Time Period:</strong> ${DATA.stats.time_start} to ${DATA.stats.time_end}</p>
            <p><strong>Depth Interval:</strong> ${DATA.stats.depth_start.toFixed(0)}m to ${DATA.stats.depth_end.toFixed(0)}m (${(DATA.stats.depth_end - DATA.stats.depth_start).toFixed(0)}m drilled)</p>
            <p><strong>Operational Time:</strong> ${drillingPct.toFixed(1)}% drilling</p>
            <h3 style="color: var(--accent-orange); margin: 20px 0 16px;">Hole Cleaning Assessment</h3>`;
        
        if (ratio > 1.2) {
            html += `<div class="insight-box warning" style="margin-bottom: 12px;"><strong>⚠️ Over-Recovery (TCR Ratio: ${ratio.toFixed(2)})</strong><br>Measured volume exceeds theoretical. Check: hole enlargement, calibration, previous bed cleanup.</div>`;
        } else if (ratio < 0.8) {
            html += `<div class="insight-box danger" style="margin-bottom: 12px;"><strong>🚨 Under-Recovery (TCR Ratio: ${ratio.toFixed(2)})</strong><br>Cuttings may be accumulating. Consider: increased flow, sweep pills.</div>`;
        } else {
            html += `<div class="insight-box" style="margin-bottom: 12px;"><strong>✓ Normal Recovery (TCR Ratio: ${ratio.toFixed(2)})</strong><br>Hole cleaning appears effective.</div>`;
        }
        
        if (ufoCount > 50) {
            html += `<div class="insight-box warning" style="margin-bottom: 12px;"><strong>⚠️ Elevated UFO Activity (${ufoCount} events)</strong><br>Review ECD management and mud weight.</div>`;
        }
        
        html += `
            <h3 style="color: var(--accent-orange); margin: 20px 0 16px;">Recommendations</h3>
            <ul style="margin-left: 20px;">
                <li>Verify theoretical volume inputs (bit diameter, porosity)</li>
                <li>Cross-reference CSD trends with formation tops</li>
                <li>Monitor TCR ratio during connections</li>
                <li>Track UFO events by depth</li>
            </ul>`;
        document.getElementById('analysis-summary').innerHTML = html;
    }
    </script>
</body>
</html>'''


def detect_encoding(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read(4)
    if raw.startswith(b'\xff\xfe'): return 'utf-16-le'
    elif raw.startswith(b'\xfe\xff'): return 'utf-16-be'
    elif raw.startswith(b'\xef\xbb\xbf'): return 'utf-8-sig'
    return 'utf-8'


def detect_delimiter(filepath, encoding):
    with open(filepath, 'r', encoding=encoding, errors='replace') as f:
        line = f.readline()
    if '\t' in line: return '\t'
    elif ';' in line: return ';'
    return ','


def load_data(filepath):
    """Load CleanSight CSV export."""
    encoding = detect_encoding(filepath)
    delimiter = detect_delimiter(filepath, encoding)
    
    df = pd.read_csv(filepath, encoding=encoding, sep=delimiter, low_memory=False)
    df.columns = df.columns.str.strip().str.replace('"', '').str.replace('\ufeff', '')
    
    # Standardize column names
    col_map = {
        'CRR (bbl/min)': 'crr', 'CRR (lbm/min)': 'crr_lbm',
        'Hole Depth (m)': 'hole_depth', 'Bit Depth (m)': 'bit_depth',
        'Flow In (gpm)': 'flow_in', 'ROP (ft/h)': 'rop',
        'Pump Pressure (psi)': 'pump_pressure', 'RPM': 'rpm',
        'Pit Volume (bbl)': 'pit_volume', 'Hook Load (klbf)': 'hook_load',
        'Block Height (m)': 'block_height', 'CSD P50 (mm)': 'csd_p50',
        'UFO Count': 'ufo_count', 'Measured TCR (bbl)': 'measured_tcr',
        'Theoretical TCR (bbl)': 'theoretical_tcr', 'time': 'time'
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    
    # Convert types
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
    
    numeric_cols = ['crr', 'hole_depth', 'bit_depth', 'flow_in', 'rop', 'pump_pressure', 
                    'rpm', 'pit_volume', 'hook_load', 'block_height', 'csd_p50', 
                    'ufo_count', 'measured_tcr', 'theoretical_tcr']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Derived metrics
    if 'measured_tcr' in df.columns and 'theoretical_tcr' in df.columns:
        mask = (df['theoretical_tcr'] > 0) & (df['measured_tcr'] > 0)
        df['tcr_ratio'] = np.nan
        df.loc[mask, 'tcr_ratio'] = df.loc[mask, 'measured_tcr'] / df.loc[mask, 'theoretical_tcr']
    
    if 'rop' in df.columns and 'rpm' in df.columns:
        df['is_drilling'] = (df['rop'] > 0.1) & (df['rpm'] > 5)
    else:
        df['is_drilling'] = False
    
    return df


def prepare_dashboard_data(df):
    """Prepare data structure for dashboard."""
    # Downsample for JSON (every 5 minutes)
    df_sub = df.iloc[::5].copy()
    
    data = {
        'time': df_sub['time'].dt.strftime('%Y-%m-%d %H:%M').tolist() if 'time' in df_sub.columns else [],
        'crr': df_sub['crr'].fillna(0).round(4).tolist() if 'crr' in df_sub.columns else [],
        'rop': df_sub['rop'].fillna(0).round(1).tolist() if 'rop' in df_sub.columns else [],
        'flow_in': df_sub['flow_in'].fillna(0).round(0).tolist() if 'flow_in' in df_sub.columns else [],
        'rpm': df_sub['rpm'].fillna(0).round(0).tolist() if 'rpm' in df_sub.columns else [],
        'pump_pressure': df_sub['pump_pressure'].fillna(0).round(0).tolist() if 'pump_pressure' in df_sub.columns else [],
        'hook_load': df_sub['hook_load'].fillna(0).round(1).tolist() if 'hook_load' in df_sub.columns else [],
        'block_height': df_sub['block_height'].fillna(0).round(2).tolist() if 'block_height' in df_sub.columns else [],
        'bit_depth': df_sub['bit_depth'].fillna(0).round(0).tolist() if 'bit_depth' in df_sub.columns else [],
        'hole_depth': df_sub['hole_depth'].fillna(0).round(0).tolist() if 'hole_depth' in df_sub.columns else [],
        'csd_p50': df_sub['csd_p50'].fillna(0).round(1).tolist() if 'csd_p50' in df_sub.columns else [],
        'pit_volume': df_sub['pit_volume'].fillna(0).round(0).tolist() if 'pit_volume' in df_sub.columns else [],
        'measured_tcr': df_sub['measured_tcr'].fillna(0).round(1).tolist() if 'measured_tcr' in df_sub.columns else [],
        'theoretical_tcr': df_sub['theoretical_tcr'].fillna(0).round(1).tolist() if 'theoretical_tcr' in df_sub.columns else [],
        'tcr_ratio': df_sub['tcr_ratio'].fillna(0).round(3).tolist() if 'tcr_ratio' in df_sub.columns else [],
        'is_drilling': df_sub['is_drilling'].tolist() if 'is_drilling' in df_sub.columns else []
    }
    
    # UFO events
    if 'ufo_count' in df.columns:
        ufo_df = df[df['ufo_count'].notna() & (df['ufo_count'] > 0)]
        data['ufo_times'] = ufo_df['time'].dt.strftime('%Y-%m-%d %H:%M').tolist() if 'time' in ufo_df.columns else []
        data['ufo_counts'] = ufo_df['ufo_count'].tolist()
        data['ufo_depths'] = ufo_df['bit_depth'].fillna(0).round(0).tolist() if 'bit_depth' in ufo_df.columns else []
    else:
        data['ufo_times'], data['ufo_counts'], data['ufo_depths'] = [], [], []
    
    # Cross-plot data (drilling only)
    drilling_df = df[df['is_drilling']].iloc[::3] if 'is_drilling' in df.columns else df.iloc[::3]
    data['crossplot'] = {
        'crr': drilling_df['crr'].fillna(0).round(4).tolist() if 'crr' in drilling_df.columns else [],
        'rop': drilling_df['rop'].fillna(0).round(1).tolist() if 'rop' in drilling_df.columns else [],
        'flow_in': drilling_df['flow_in'].fillna(0).round(0).tolist() if 'flow_in' in drilling_df.columns else [],
        'rpm': drilling_df['rpm'].fillna(0).round(0).tolist() if 'rpm' in drilling_df.columns else [],
        'csd_p50': drilling_df['csd_p50'].fillna(0).round(1).tolist() if 'csd_p50' in drilling_df.columns else []
    }
    
    # Statistics
    drilling_data = df[df['is_drilling']] if 'is_drilling' in df.columns else df
    duration = df['time'].max() - df['time'].min() if 'time' in df.columns else None
    duration_str = str(duration).split('.')[0] if duration else '--'
    
    data['stats'] = {
        'total_points': len(df),
        'time_start': df['time'].min().strftime('%Y-%m-%d %H:%M') if 'time' in df.columns else '--',
        'time_end': df['time'].max().strftime('%Y-%m-%d %H:%M') if 'time' in df.columns else '--',
        'duration': duration_str,
        'depth_start': float(df['hole_depth'].min()) if 'hole_depth' in df.columns else 0,
        'depth_end': float(df['hole_depth'].max()) if 'hole_depth' in df.columns else 0,
        'drilling_pct': float(df['is_drilling'].sum() / len(df) * 100) if 'is_drilling' in df.columns else 0,
        'avg_crr_drilling': float(drilling_data['crr'].mean()) if 'crr' in drilling_data.columns else 0,
        'avg_tcr_ratio': float(df['tcr_ratio'].dropna().mean()) if 'tcr_ratio' in df.columns else 1.0,
        'ufo_total': int(df['ufo_count'].sum()) if 'ufo_count' in df.columns else 0
    }
    
    return data


def generate_dashboard(filepath, output_path='cleansight_dashboard.html'):
    """Generate the interactive HTML dashboard."""
    print(f"Loading data from: {filepath}")
    df = load_data(filepath)
    print(f"  Loaded {len(df):,} rows")
    
    print("Preparing dashboard data...")
    data = prepare_dashboard_data(df)
    
    print("Generating dashboard...")
    html = DASHBOARD_TEMPLATE.replace('%%DATA_PLACEHOLDER%%', json.dumps(data))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Dashboard saved to: {output_path}")
    return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python generate_dashboard.py <data_file.csv> [--output dashboard.html]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    output = 'cleansight_dashboard.html'
    
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]
    
    generate_dashboard(filepath, output)
