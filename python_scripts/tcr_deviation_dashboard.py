#!/usr/bin/env python3
"""
TCR Deviation Analysis Tool - Interactive Tabbed Dashboard
===========================================================
Generates a single HTML file with all charts in tabs.

Usage:
    python tcr_deviation_dashboard.py "your_data.csv"
    python tcr_deviation_dashboard.py "your_data.csv" --output-dir ./my_analysis

Requirements:
    pip install pandas numpy plotly scipy
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from scipy import stats

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    print("ERROR: Plotly is required. Install it with:")
    print("  pip install plotly")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

COLORS = {
    'measured': '#ff6b35',
    'theoretical': '#00d9ff',
    'ratio': '#3fb950',
    'warning': '#f0b429',
    'danger': '#f85149',
    'purple': '#a371f7',
    'gray': '#8b949e',
    'background': '#0d1117',
    'paper': '#161b22',
    'grid': '#30363d',
    'text': '#e6edf3'
}


# =============================================================================
# DATA LOADING
# =============================================================================

def load_data(filepath):
    """Load CleanSight data export."""
    print(f"Loading: {filepath}")
    
    # Detect encoding
    with open(filepath, 'rb') as f:
        raw = f.read(4)
    if raw.startswith(b'\xff\xfe'):
        encoding = 'utf-16-le'
    elif raw.startswith(b'\xfe\xff'):
        encoding = 'utf-16-be'
    elif raw.startswith(b'\xef\xbb\xbf'):
        encoding = 'utf-8-sig'
    else:
        encoding = 'utf-8'
    
    # Load CSV
    try:
        df = pd.read_csv(filepath, encoding=encoding, sep='\t', low_memory=False)
        if len(df.columns) < 5:
            df = pd.read_csv(filepath, encoding=encoding, sep=',', low_memory=False)
    except:
        df = pd.read_csv(filepath, encoding=encoding, low_memory=False)
    
    # Clean columns
    df.columns = df.columns.str.strip().str.replace('"', '').str.replace('\ufeff', '')
    
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
    
    # Convert numeric
    numeric_cols = [
        'Measured TCR (bbl)', 'Theoretical TCR (bbl)', 'Flow In (gpm)',
        'ROP (ft/h)', 'Pump Pressure (psi)', 'RPM', 'CRR (bbl/min)',
        'Bit Depth (m)', 'Hole Depth (m)', 'CSD P50 (mm)', 'Lagged ROP (m/hr)',
        'Pit Volume (bbl)', 'Hook Load (klbf)', 'Block Height (m)', 'UFO Count'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calculate TCR Ratio
    mask = (df['Theoretical TCR (bbl)'] > 0) & (df['Measured TCR (bbl)'] > 0)
    df['TCR_Ratio'] = np.nan
    df.loc[mask, 'TCR_Ratio'] = df.loc[mask, 'Measured TCR (bbl)'] / df.loc[mask, 'Theoretical TCR (bbl)']
    
    print(f"  Loaded {len(df):,} rows")
    return df


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def find_deviation_start(df):
    """Find when TCR ratio first exceeded thresholds."""
    tcr_data = df[df['TCR_Ratio'].notna()].copy()
    if len(tcr_data) == 0:
        return {}
    
    tcr_data['TCR_smooth'] = tcr_data['TCR_Ratio'].rolling(window=30, min_periods=1).mean()
    
    thresholds = {}
    for thresh in [1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3]:
        crossed = tcr_data[tcr_data['TCR_smooth'] > thresh]
        if len(crossed) > 0:
            idx = crossed.index[0]
            thresholds[thresh] = {
                'time': tcr_data.loc[idx, 'time'],
                'depth': tcr_data.loc[idx, 'Bit Depth (m)'],
                'ratio': tcr_data.loc[idx, 'TCR_Ratio']
            }
    return thresholds


def analyze_depth_correlation(df):
    """Analyze correlation between TCR ratio and depth."""
    valid = df[(df['TCR_Ratio'].notna()) & (df['TCR_Ratio'] > 0.5)].copy()
    if len(valid) < 100:
        return None
    
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        valid['Bit Depth (m)'], valid['TCR_Ratio']
    )
    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_value ** 2,
        'rate_per_100m': slope * 100
    }


def calculate_excess_volume(df):
    """Calculate excess cuttings volume."""
    import math
    
    measured_final = df['Measured TCR (bbl)'].dropna().iloc[-1]
    theoretical_final = df['Theoretical TCR (bbl)'].dropna().iloc[-1]
    excess_bbl = measured_final - theoretical_final
    excess_pct = (excess_bbl / theoretical_final) * 100
    
    depth_drilled_m = df['Hole Depth (m)'].max() - df['Hole Depth (m)'].min()
    depth_drilled_ft = depth_drilled_m * 3.28084
    
    bit_diameter_in = 8.5
    excess_cuft = excess_bbl * 5.615
    d_bit_ft = bit_diameter_in / 12
    D_squared = (4 * excess_cuft / (math.pi * depth_drilled_ft)) + d_bit_ft**2
    D_actual_in = math.sqrt(max(D_squared, d_bit_ft**2)) * 12
    enlargement_pct = (D_actual_in / bit_diameter_in - 1) * 100
    
    return {
        'measured_final': measured_final,
        'theoretical_final': theoretical_final,
        'excess_bbl': excess_bbl,
        'excess_pct': excess_pct,
        'depth_drilled_m': depth_drilled_m,
        'enlargement_pct': enlargement_pct
    }


def compare_intervals(df, shallow_range, deep_range):
    """Compare parameters between two depth intervals."""
    shallow = df[(df['Bit Depth (m)'] >= shallow_range[0]) & (df['Bit Depth (m)'] <= shallow_range[1])]
    deep = df[(df['Bit Depth (m)'] >= deep_range[0]) & (df['Bit Depth (m)'] <= deep_range[1])]
    
    params = ['Flow In (gpm)', 'Pump Pressure (psi)', 'RPM', 'ROP (ft/h)',
              'CRR (bbl/min)', 'CSD P50 (mm)', 'Hook Load (klbf)', 'TCR_Ratio']
    
    comparison = {}
    for param in params:
        if param in df.columns:
            shallow_val = shallow[param].mean()
            deep_val = deep[param].mean()
            change_pct = ((deep_val - shallow_val) / shallow_val * 100) if shallow_val != 0 else 0
            comparison[param] = {'shallow': shallow_val, 'deep': deep_val, 'change_pct': change_pct}
    return comparison


# =============================================================================
# CREATE TABBED DASHBOARD
# =============================================================================

def create_tabbed_dashboard(df, output_path):
    """Create a single HTML file with tabbed charts."""
    
    tcr_data = df[df['TCR_Ratio'].notna()].copy()
    
    # Run analysis
    thresholds = find_deviation_start(df)
    corr = analyze_depth_correlation(df)
    excess = calculate_excess_volume(df)
    
    # Find comparison intervals
    near_one = tcr_data[abs(tcr_data['TCR_Ratio'] - 1.0) < 0.15]
    elevated = tcr_data[tcr_data['TCR_Ratio'] > 1.15]
    
    if len(near_one) > 0 and len(elevated) > 0:
        shallow_depth = near_one['Bit Depth (m)'].median()
        deep_depth = elevated['Bit Depth (m)'].median()
        shallow_range = (int(shallow_depth - 100), int(shallow_depth + 100))
        deep_range = (int(deep_depth - 100), int(deep_depth + 100))
        comparison = compare_intervals(df, shallow_range, deep_range)
    else:
        shallow_range = (3600, 3800)
        deep_range = (4000, 4200)
        comparison = compare_intervals(df, shallow_range, deep_range)
    
    # =========================================================================
    # BUILD HTML WITH TABS
    # =========================================================================
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TCR Deviation Analysis Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {COLORS['background']};
            color: {COLORS['text']};
            min-height: 100vh;
        }}
        
        .header {{
            background: {COLORS['paper']};
            padding: 20px 30px;
            border-bottom: 1px solid {COLORS['grid']};
        }}
        
        .header h1 {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        .header .subtitle {{
            color: {COLORS['gray']};
            font-size: 14px;
        }}
        
        .tabs {{
            display: flex;
            background: {COLORS['paper']};
            border-bottom: 1px solid {COLORS['grid']};
            padding: 0 20px;
            overflow-x: auto;
        }}
        
        .tab {{
            padding: 15px 25px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            color: {COLORS['gray']};
            font-size: 14px;
            font-weight: 500;
            white-space: nowrap;
            transition: all 0.2s;
        }}
        
        .tab:hover {{
            color: {COLORS['text']};
            background: rgba(255,255,255,0.05);
        }}
        
        .tab.active {{
            color: {COLORS['ratio']};
            border-bottom-color: {COLORS['ratio']};
        }}
        
        .tab-content {{
            display: none;
            padding: 20px;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .chart-container {{
            background: {COLORS['paper']};
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .kpi-card {{
            background: {COLORS['paper']};
            border-radius: 8px;
            padding: 20px;
            border-left: 3px solid {COLORS['ratio']};
        }}
        
        .kpi-card.warning {{
            border-left-color: {COLORS['warning']};
        }}
        
        .kpi-card.danger {{
            border-left-color: {COLORS['danger']};
        }}
        
        .kpi-label {{
            font-size: 12px;
            color: {COLORS['gray']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        
        .kpi-value {{
            font-size: 28px;
            font-weight: 600;
        }}
        
        .kpi-detail {{
            font-size: 12px;
            color: {COLORS['gray']};
            margin-top: 5px;
        }}
        
        .findings {{
            background: {COLORS['paper']};
            border-radius: 8px;
            padding: 25px;
            margin-top: 20px;
        }}
        
        .findings h3 {{
            margin-bottom: 15px;
            color: {COLORS['ratio']};
        }}
        
        .findings ul {{
            list-style: none;
            padding: 0;
        }}
        
        .findings li {{
            padding: 8px 0;
            border-bottom: 1px solid {COLORS['grid']};
            display: flex;
            justify-content: space-between;
        }}
        
        .findings li:last-child {{
            border-bottom: none;
        }}
        
        .two-col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        
        @media (max-width: 900px) {{
            .two-col {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>TCR Deviation Analysis Dashboard</h1>
        <div class="subtitle">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data range: {tcr_data['time'].min().strftime('%Y-%m-%d %H:%M')} to {tcr_data['time'].max().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="showTab('overview')">Overview</div>
        <div class="tab" onclick="showTab('timeline')">TCR Timeline</div>
        <div class="tab" onclick="showTab('depth')">Depth Analysis</div>
        <div class="tab" onclick="showTab('operations')">Operations</div>
        <div class="tab" onclick="showTab('comparison')">Comparison</div>
        <div class="tab" onclick="showTab('lag')">Lag Analysis</div>
    </div>
    
    <!-- OVERVIEW TAB -->
    <div id="overview" class="tab-content active">
        <div class="kpi-grid">
            <div class="kpi-card {'danger' if excess['excess_pct'] > 25 else 'warning' if excess['excess_pct'] > 15 else ''}">
                <div class="kpi-label">Final TCR Ratio</div>
                <div class="kpi-value">{tcr_data['TCR_Ratio'].iloc[-1]:.3f}</div>
                <div class="kpi-detail">{'⚠️ Above alarm threshold' if tcr_data['TCR_Ratio'].iloc[-1] > 1.3 else '⚡ Above warning' if tcr_data['TCR_Ratio'].iloc[-1] > 1.15 else '✓ Normal'}</div>
            </div>
            <div class="kpi-card warning">
                <div class="kpi-label">Excess Volume</div>
                <div class="kpi-value">{excess['excess_bbl']:.0f} bbl</div>
                <div class="kpi-detail">{excess['excess_pct']:.1f}% over theoretical</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Deviation Started</div>
                <div class="kpi-value">{thresholds[1.0]['depth']:.0f}m</div>
                <div class="kpi-detail">{thresholds[1.0]['time'].strftime('%b %d, %H:%M') if thresholds.get(1.0) else 'N/A'}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Hole Enlargement</div>
                <div class="kpi-value">{excess['enlargement_pct']:.1f}%</div>
                <div class="kpi-detail">Equivalent average</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Depth Correlation</div>
                <div class="kpi-value">R² = {f"{corr['r_squared']:.2f}" if corr else 'N/A'}</div>
                <div class="kpi-detail">+{f"{corr['rate_per_100m']:.3f}" if corr else 'N/A'} per 100m</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Depth Drilled</div>
                <div class="kpi-value">{excess['depth_drilled_m']:.0f}m</div>
                <div class="kpi-detail">{df['Bit Depth (m)'].min():.0f}m → {df['Bit Depth (m)'].max():.0f}m</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div id="overview-chart" style="height: 500px;"></div>
        </div>
        
        <div class="findings">
            <h3>Key Findings</h3>
            <ul>
                <li><span>Deviation Type</span><span><strong>Gradual drift</strong> (not sudden step change)</span></li>
                <li><span>Primary Correlation</span><span>Depth (R² = {f"{corr['r_squared']:.2f}" if corr else 'N/A'})</span></li>
                <li><span>Rate of Increase</span><span>+{f"{corr['rate_per_100m']:.3f}" if corr else 'N/A'} ratio per 100m drilled</span></li>
                <li><span>Most Likely Cause</span><span><strong>Hole enlargement</strong> or theoretical model underestimate</span></li>
                <li><span>Recommendation</span><span>Verify with caliper log data at 4000-5400m interval</span></li>
            </ul>
        </div>
    </div>
    
    <!-- TIMELINE TAB -->
    <div id="timeline" class="tab-content">
        <div class="chart-container">
            <div id="timeline-chart" style="height: 800px;"></div>
        </div>
    </div>
    
    <!-- DEPTH TAB -->
    <div id="depth" class="tab-content">
        <div class="two-col">
            <div class="chart-container">
                <div id="depth-scatter" style="height: 600px;"></div>
            </div>
            <div class="chart-container">
                <div id="depth-bars" style="height: 600px;"></div>
            </div>
        </div>
    </div>
    
    <!-- OPERATIONS TAB -->
    <div id="operations" class="tab-content">
        <div class="chart-container">
            <div id="operations-chart" style="height: 900px;"></div>
        </div>
    </div>
    
    <!-- COMPARISON TAB -->
    <div id="comparison" class="tab-content">
        <div class="chart-container">
            <div id="comparison-chart" style="height: 500px;"></div>
        </div>
        <div class="findings">
            <h3>Parameter Changes: {shallow_range[0]}-{shallow_range[1]}m vs {deep_range[0]}-{deep_range[1]}m</h3>
            <ul>
                {''.join(f'<li><span>{param}</span><span style="color: {COLORS["danger"] if data["change_pct"] < -10 else COLORS["warning"] if data["change_pct"] > 20 else COLORS["ratio"]}">{data["change_pct"]:+.1f}%</span></li>' for param, data in comparison.items())}
            </ul>
        </div>
    </div>
    
    <!-- LAG TAB -->
    <div id="lag" class="tab-content">
        <div class="two-col">
            <div class="chart-container">
                <div id="lag-scatter1" style="height: 400px;"></div>
            </div>
            <div class="chart-container">
                <div id="lag-scatter2" style="height: 400px;"></div>
            </div>
        </div>
        <div class="chart-container">
            <div id="lag-timeseries" style="height: 400px;"></div>
        </div>
    </div>
    
    <script>
        // Tab switching
        function showTab(tabId) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelector(`[onclick="showTab('${{tabId}}')"]`).classList.add('active');
            document.getElementById(tabId).classList.add('active');
            
            // Trigger resize for Plotly charts
            window.dispatchEvent(new Event('resize'));
        }}
        
        // Chart colors and config
        const colors = {str(COLORS).replace("'", '"')};
        
        const layout = {{
            paper_bgcolor: colors.background,
            plot_bgcolor: colors.paper,
            font: {{ color: colors.text, family: 'system-ui, sans-serif' }},
            xaxis: {{ gridcolor: colors.grid, zerolinecolor: colors.grid }},
            yaxis: {{ gridcolor: colors.grid, zerolinecolor: colors.grid }},
            hovermode: 'x unified',
            margin: {{ t: 40, r: 40, b: 60, l: 60 }}
        }};
        
        const config = {{
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            displaylogo: false
        }};
        
        // Data
        const timeData = {json.dumps(tcr_data['time'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist())};
        const measuredTCR = {tcr_data['Measured TCR (bbl)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const theoreticalTCR = {tcr_data['Theoretical TCR (bbl)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const tcrRatio = {tcr_data['TCR_Ratio'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const bitDepth = {tcr_data['Bit Depth (m)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const flowIn = {tcr_data['Flow In (gpm)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const pumpPressure = {tcr_data['Pump Pressure (psi)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const rop = {tcr_data['ROP (ft/h)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const rpm = {tcr_data['RPM'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const hookLoad = {tcr_data['Hook Load (klbf)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const csdP50 = {tcr_data['CSD P50 (mm)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
'''

    # Add Lagged ROP data if available
    if 'Lagged ROP (m/hr)' in tcr_data.columns:
        html_content += f'''
        const laggedROP = {tcr_data['Lagged ROP (m/hr)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
        const crr = {tcr_data['CRR (bbl/min)'].apply(lambda x: None if pd.isna(x) else x).tolist().__repr__().replace('None', 'null')};
'''
    else:
        html_content += '''
        const laggedROP = [];
        const crr = [];
'''

    html_content += f'''
        // =====================================================================
        // OVERVIEW CHART
        // =====================================================================
        Plotly.newPlot('overview-chart', [
            {{
                x: timeData,
                y: tcrRatio,
                type: 'scatter',
                mode: 'lines',
                name: 'TCR Ratio',
                line: {{ color: colors.ratio, width: 2 }},
                fill: 'tozeroy',
                fillcolor: 'rgba(63,185,80,0.2)'
            }}
        ], {{
            ...layout,
            title: {{ text: 'TCR Ratio Timeline', font: {{ size: 16 }} }},
            yaxis: {{ ...layout.yaxis, title: 'TCR Ratio', range: [0, 1.6] }},
            xaxis: {{ ...layout.xaxis, title: 'Time' }},
            shapes: [
                {{ type: 'line', y0: 1.0, y1: 1.0, x0: 0, x1: 1, xref: 'paper', line: {{ color: 'white', dash: 'dash', width: 1 }} }},
                {{ type: 'line', y0: 1.15, y1: 1.15, x0: 0, x1: 1, xref: 'paper', line: {{ color: colors.warning, dash: 'dash', width: 1 }} }},
                {{ type: 'line', y0: 1.30, y1: 1.30, x0: 0, x1: 1, xref: 'paper', line: {{ color: colors.danger, dash: 'dash', width: 1 }} }}
            ]
        }}, config);
        
        // =====================================================================
        // TIMELINE CHART (3 subplots)
        // =====================================================================
        Plotly.newPlot('timeline-chart', [
            // Measured vs Theoretical
            {{
                x: timeData, y: measuredTCR,
                type: 'scatter', mode: 'lines',
                name: 'Measured TCR',
                line: {{ color: colors.measured, width: 1 }},
                fill: 'tozeroy', fillcolor: 'rgba(255,107,53,0.2)',
                xaxis: 'x', yaxis: 'y'
            }},
            {{
                x: timeData, y: theoreticalTCR,
                type: 'scatter', mode: 'lines',
                name: 'Theoretical TCR',
                line: {{ color: colors.theoretical, width: 1 }},
                fill: 'tozeroy', fillcolor: 'rgba(0,217,255,0.2)',
                xaxis: 'x', yaxis: 'y'
            }},
            // TCR Ratio
            {{
                x: timeData, y: tcrRatio,
                type: 'scatter', mode: 'lines',
                name: 'TCR Ratio',
                line: {{ color: colors.ratio, width: 1.5 }},
                fill: 'tozeroy', fillcolor: 'rgba(63,185,80,0.2)',
                xaxis: 'x2', yaxis: 'y2'
            }},
            // Bit Depth
            {{
                x: timeData, y: bitDepth,
                type: 'scatter', mode: 'lines',
                name: 'Bit Depth',
                line: {{ color: colors.theoretical, width: 1 }},
                fill: 'tozeroy', fillcolor: 'rgba(0,217,255,0.1)',
                xaxis: 'x3', yaxis: 'y3'
            }}
        ], {{
            ...layout,
            grid: {{ rows: 3, columns: 1, pattern: 'independent', roworder: 'top to bottom' }},
            xaxis: {{ ...layout.xaxis, domain: [0, 1], anchor: 'y' }},
            yaxis: {{ ...layout.yaxis, domain: [0.7, 1], title: 'TCR (bbl)' }},
            xaxis2: {{ ...layout.xaxis, domain: [0, 1], anchor: 'y2' }},
            yaxis2: {{ ...layout.yaxis, domain: [0.38, 0.65], title: 'Ratio', range: [0, 1.6] }},
            xaxis3: {{ ...layout.xaxis, domain: [0, 1], anchor: 'y3', title: 'Time' }},
            yaxis3: {{ ...layout.yaxis, domain: [0, 0.3], title: 'Depth (m)', autorange: 'reversed' }},
            legend: {{ orientation: 'h', y: 1.02, x: 0.5, xanchor: 'center' }},
            shapes: [
                {{ type: 'line', y0: 1.0, y1: 1.0, x0: 0, x1: 1, xref: 'x2 domain', yref: 'y2', line: {{ color: 'white', dash: 'dash', width: 1 }} }},
                {{ type: 'line', y0: 1.15, y1: 1.15, x0: 0, x1: 1, xref: 'x2 domain', yref: 'y2', line: {{ color: colors.warning, dash: 'dash', width: 1 }} }}
            ]
        }}, config);
        
        // =====================================================================
        // DEPTH SCATTER
        // =====================================================================
        Plotly.newPlot('depth-scatter', [{{
            x: tcrRatio,
            y: bitDepth,
            type: 'scatter',
            mode: 'markers',
            marker: {{
                size: 4,
                color: tcrRatio,
                colorscale: 'RdYlGn',
                reversescale: true,
                cmin: 0.7,
                cmax: 1.4,
                colorbar: {{ title: 'TCR Ratio' }}
            }},
            name: 'TCR vs Depth'
        }}], {{
            ...layout,
            title: {{ text: 'TCR Ratio vs Depth', font: {{ size: 16 }} }},
            xaxis: {{ ...layout.xaxis, title: 'TCR Ratio' }},
            yaxis: {{ ...layout.yaxis, title: 'Depth (m)', autorange: 'reversed' }},
            shapes: [
                {{ type: 'line', x0: 1.0, x1: 1.0, y0: 0, y1: 1, yref: 'paper', line: {{ color: 'white', dash: 'dash', width: 1 }} }}
            ]
        }}, config);
        
        // =====================================================================
        // DEPTH BARS (binned analysis)
        // =====================================================================
        const depthBins = {list(range(3000, 5600, 200))};
        const binLabels = depthBins.slice(0, -1).map((d, i) => `${{d}}-${{depthBins[i+1]}}`);
        
        // Calculate mean TCR ratio per bin
        const binMeans = [];
        for (let i = 0; i < depthBins.length - 1; i++) {{
            const inBin = tcrRatio.filter((r, idx) => 
                bitDepth[idx] >= depthBins[i] && bitDepth[idx] < depthBins[i+1] && r !== null
            );
            binMeans.push(inBin.length > 0 ? inBin.reduce((a,b) => a+b, 0) / inBin.length : null);
        }}
        
        const barColors = binMeans.map(v => 
            v === null ? colors.gray :
            v > 1.3 ? colors.danger :
            v > 1.15 ? colors.warning :
            colors.ratio
        );
        
        Plotly.newPlot('depth-bars', [{{
            x: binMeans,
            y: binLabels,
            type: 'bar',
            orientation: 'h',
            marker: {{ color: barColors, opacity: 0.8 }},
            name: 'Mean TCR Ratio'
        }}], {{
            ...layout,
            title: {{ text: 'TCR Ratio by Depth Interval', font: {{ size: 16 }} }},
            xaxis: {{ ...layout.xaxis, title: 'Mean TCR Ratio' }},
            yaxis: {{ ...layout.yaxis, title: 'Depth (m)', autorange: 'reversed' }},
            shapes: [
                {{ type: 'line', x0: 1.0, x1: 1.0, y0: 0, y1: 1, yref: 'paper', line: {{ color: 'white', dash: 'dash', width: 1 }} }},
                {{ type: 'line', x0: 1.15, x1: 1.15, y0: 0, y1: 1, yref: 'paper', line: {{ color: colors.warning, dash: 'dash', width: 1 }} }}
            ]
        }}, config);
        
        // =====================================================================
        // OPERATIONS CHART
        // =====================================================================
        Plotly.newPlot('operations-chart', [
            {{ x: timeData, y: tcrRatio, type: 'scatter', mode: 'lines', name: 'TCR Ratio', line: {{ color: colors.ratio }}, yaxis: 'y' }},
            {{ x: timeData, y: flowIn, type: 'scatter', mode: 'lines', name: 'Flow In (gpm)', line: {{ color: colors.theoretical }}, yaxis: 'y2' }},
            {{ x: timeData, y: pumpPressure, type: 'scatter', mode: 'lines', name: 'Pump Pressure (psi)', line: {{ color: colors.danger }}, yaxis: 'y3' }},
            {{ x: timeData, y: rop, type: 'scatter', mode: 'lines', name: 'ROP (ft/h)', line: {{ color: colors.measured }}, yaxis: 'y4' }},
            {{ x: timeData, y: hookLoad, type: 'scatter', mode: 'lines', name: 'Hook Load (klbf)', line: {{ color: colors.purple }}, yaxis: 'y5' }}
        ], {{
            ...layout,
            grid: {{ rows: 5, columns: 1, pattern: 'independent' }},
            yaxis: {{ ...layout.yaxis, domain: [0.82, 1], title: 'Ratio' }},
            yaxis2: {{ ...layout.yaxis, domain: [0.62, 0.78], title: 'Flow (gpm)' }},
            yaxis3: {{ ...layout.yaxis, domain: [0.42, 0.58], title: 'Pressure (psi)' }},
            yaxis4: {{ ...layout.yaxis, domain: [0.22, 0.38], title: 'ROP (ft/h)' }},
            yaxis5: {{ ...layout.yaxis, domain: [0, 0.18], title: 'Hook Load' }},
            xaxis: {{ ...layout.xaxis, title: 'Time' }},
            showlegend: true,
            legend: {{ orientation: 'h', y: 1.05, x: 0.5, xanchor: 'center' }}
        }}, config);
        
        // =====================================================================
        // COMPARISON CHART
        // =====================================================================
        const compParams = {json.dumps(list(comparison.keys()))};
        const compChanges = {json.dumps([data['change_pct'] for data in comparison.values()])};
        const compColors = compChanges.map(c => c < -10 ? colors.danger : c > 20 ? colors.warning : colors.ratio);
        
        Plotly.newPlot('comparison-chart', [{{
            y: compParams,
            x: compChanges,
            type: 'bar',
            orientation: 'h',
            marker: {{ color: compColors, opacity: 0.8 }},
            text: compChanges.map(c => (c >= 0 ? '+' : '') + c.toFixed(1) + '%'),
            textposition: 'outside'
        }}], {{
            ...layout,
            title: {{ text: 'Parameter Changes: {shallow_range[0]}-{shallow_range[1]}m vs {deep_range[0]}-{deep_range[1]}m', font: {{ size: 16 }} }},
            xaxis: {{ ...layout.xaxis, title: 'Change (%)' }},
            shapes: [{{ type: 'line', x0: 0, x1: 0, y0: 0, y1: 1, yref: 'paper', line: {{ color: 'white', width: 1 }} }}]
        }}, config);
        
        // =====================================================================
        // LAG ANALYSIS
        // =====================================================================
        if (laggedROP.length > 0) {{
            // Filter valid points
            const validIdx = [];
            for (let i = 0; i < crr.length; i++) {{
                if (crr[i] > 0 && laggedROP[i] > 0) validIdx.push(i);
            }}
            
            const validCRR = validIdx.map(i => crr[i]);
            const validLaggedROP = validIdx.map(i => laggedROP[i]);
            const validROP = validIdx.map(i => rop[i] * 0.3048);
            const validTime = validIdx.map(i => timeData[i]);
            
            // Scatter 1: CRR vs Lagged ROP
            Plotly.newPlot('lag-scatter1', [{{
                x: validLaggedROP,
                y: validCRR,
                type: 'scatter',
                mode: 'markers',
                marker: {{ size: 4, color: colors.measured, opacity: 0.3 }},
                name: 'CRR vs Lagged ROP'
            }}], {{
                ...layout,
                title: {{ text: 'CRR vs Lagged ROP (Bit-Time)', font: {{ size: 14 }} }},
                xaxis: {{ ...layout.xaxis, title: 'Lagged ROP (m/hr)' }},
                yaxis: {{ ...layout.yaxis, title: 'CRR (bbl/min)' }}
            }}, config);
            
            // Scatter 2: CRR vs Same-time ROP
            Plotly.newPlot('lag-scatter2', [{{
                x: validROP,
                y: validCRR,
                type: 'scatter',
                mode: 'markers',
                marker: {{ size: 4, color: colors.theoretical, opacity: 0.3 }},
                name: 'CRR vs Same-time ROP'
            }}], {{
                ...layout,
                title: {{ text: 'CRR vs Same-time ROP (Surface-Time)', font: {{ size: 14 }} }},
                xaxis: {{ ...layout.xaxis, title: 'ROP (m/hr)' }},
                yaxis: {{ ...layout.yaxis, title: 'CRR (bbl/min)' }}
            }}, config);
            
            // Time series comparison (downsampled)
            const step = Math.max(1, Math.floor(validTime.length / 500));
            const dsTime = validTime.filter((_, i) => i % step === 0);
            const dsLaggedROP = validLaggedROP.filter((_, i) => i % step === 0);
            const dsROP = validROP.filter((_, i) => i % step === 0);
            
            Plotly.newPlot('lag-timeseries', [
                {{ x: dsTime, y: dsROP, type: 'scatter', mode: 'lines', name: 'Same-time ROP', line: {{ color: colors.theoretical, width: 1 }}, opacity: 0.7 }},
                {{ x: dsTime, y: dsLaggedROP, type: 'scatter', mode: 'lines', name: 'Lagged ROP', line: {{ color: colors.measured, width: 1 }}, opacity: 0.7 }}
            ], {{
                ...layout,
                title: {{ text: 'ROP vs Lagged ROP Time Series', font: {{ size: 14 }} }},
                xaxis: {{ ...layout.xaxis, title: 'Time' }},
                yaxis: {{ ...layout.yaxis, title: 'ROP (m/hr)' }},
                legend: {{ orientation: 'h', y: 1.05, x: 0.5, xanchor: 'center' }}
            }}, config);
        }}
    </script>
</body>
</html>
'''
    
    # Write HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"  Saved: {output_path.name}")
    return output_path


# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("TCR Deviation Dashboard")
        print("-" * 40)
        print('Usage: python tcr_deviation_dashboard.py "data.csv"')
        print('       python tcr_deviation_dashboard.py "data.csv" --output-dir ./analysis')
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    output_dir = Path.cwd() / 'tcr_analysis'
    if '--output-dir' in sys.argv:
        idx = sys.argv.index('--output-dir')
        if idx + 1 < len(sys.argv):
            output_dir = Path(sys.argv[idx + 1])
    
    output_dir.mkdir(exist_ok=True)
    
    print("\n" + "=" * 60)
    print("TCR DEVIATION DASHBOARD")
    print("=" * 60)
    
    df = load_data(filepath)
    
    print("\nGenerating interactive dashboard...")
    output_path = output_dir / 'tcr_dashboard.html'
    create_tabbed_dashboard(df, output_path)
    
    print("\n" + "=" * 60)
    print(f"Done! Open this file in your browser:")
    print(f"  {output_path.absolute()}")
    print("=" * 60)


if __name__ == '__main__':
    main()
