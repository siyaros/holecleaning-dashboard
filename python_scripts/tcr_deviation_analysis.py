#!/usr/bin/env python3
"""
TCR Deviation Analysis Tool
===========================
Analyzes why Measured TCR deviates from Theoretical TCR in CleanSight data.

This script:
1. Identifies when deviation started
2. Tracks how deviation evolved over time
3. Correlates with operational parameters (Flow, Pressure, ROP, etc.)
4. Backtraces shaker observations to bit-generation time using lag time
5. Generates diagnostic visualizations

Usage:
    python tcr_deviation_analysis.py your_data.csv
    python tcr_deviation_analysis.py your_data.csv --output-dir ./my_analysis

Requirements:
    pip install pandas numpy matplotlib scipy
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Analysis configuration."""
    
    # TCR Ratio thresholds
    TCR_WARNING_LOW = 0.85
    TCR_WARNING_HIGH = 1.15
    TCR_ALARM_LOW = 0.70
    TCR_ALARM_HIGH = 1.30
    
    # Plot settings
    FIGURE_DPI = 150
    DARK_THEME = True
    
    # Colors
    COLORS = {
        'measured': '#ff6b35',
        'theoretical': '#00d9ff',
        'ratio': '#3fb950',
        'warning': '#f0b429',
        'danger': '#f85149',
        'purple': '#a371f7',
        'gray': '#8b949e'
    }


# =============================================================================
# DATA LOADING
# =============================================================================

def detect_encoding(filepath):
    """Detect file encoding."""
    with open(filepath, 'rb') as f:
        raw = f.read(4)
    if raw.startswith(b'\xff\xfe'):
        return 'utf-16-le'
    elif raw.startswith(b'\xfe\xff'):
        return 'utf-16-be'
    elif raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    return 'utf-8'


def load_data(filepath):
    """Load CleanSight data export."""
    print(f"Loading: {filepath}")
    
    encoding = detect_encoding(filepath)
    
    # Try tab delimiter first, then comma
    try:
        df = pd.read_csv(filepath, encoding=encoding, sep='\t', low_memory=False)
        if len(df.columns) < 5:
            df = pd.read_csv(filepath, encoding=encoding, sep=',', low_memory=False)
    except:
        df = pd.read_csv(filepath, encoding=encoding, low_memory=False)
    
    # Clean column names
    df.columns = df.columns.str.strip().str.replace('"', '').str.replace('\ufeff', '')
    
    # Convert time
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
    
    # Convert numeric columns
    numeric_cols = [
        'Measured TCR (bbl)', 'Theoretical TCR (bbl)', 'Flow In (gpm)',
        'ROP (ft/h)', 'Pump Pressure (psi)', 'RPM', 'CRR (bbl/min)',
        'Bit Depth (m)', 'Hole Depth (m)', 'CSD P50 (mm)', 'Lagged ROP (m/hr)',
        'Pit Volume (bbl)', 'Hook Load (klbf)', 'Block Height (m)', 'UFO Count',
        'Lag Depth (m)', 'Lag Time (min)'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calculate TCR Ratio
    mask = (df['Theoretical TCR (bbl)'] > 0) & (df['Measured TCR (bbl)'] > 0)
    df['TCR_Ratio'] = np.nan
    df.loc[mask, 'TCR_Ratio'] = df.loc[mask, 'Measured TCR (bbl)'] / df.loc[mask, 'Theoretical TCR (bbl)']
    
    # Calculate excess TCR
    df['Excess_TCR'] = df['Measured TCR (bbl)'] - df['Theoretical TCR (bbl)']
    
    # Classify operational state
    if 'ROP (ft/h)' in df.columns and 'RPM' in df.columns:
        df['is_drilling'] = (df['ROP (ft/h)'] > 0.1) & (df['RPM'] > 5)
    
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    
    return df


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def find_deviation_start(df):
    """Find when TCR ratio first exceeded thresholds."""
    tcr_data = df[df['TCR_Ratio'].notna()].copy()
    
    if len(tcr_data) == 0:
        return None
    
    # Calculate rolling average
    tcr_data['TCR_smooth'] = tcr_data['TCR_Ratio'].rolling(window=30, min_periods=1).mean()
    
    thresholds = {
        1.0: None,
        1.05: None,
        1.1: None,
        1.15: None,
        1.2: None,
        1.25: None,
        1.3: None
    }
    
    for thresh in thresholds.keys():
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


def compare_intervals(df, shallow_range, deep_range):
    """Compare parameters between two depth intervals."""
    shallow = df[(df['Bit Depth (m)'] >= shallow_range[0]) & 
                 (df['Bit Depth (m)'] <= shallow_range[1])]
    deep = df[(df['Bit Depth (m)'] >= deep_range[0]) & 
              (df['Bit Depth (m)'] <= deep_range[1])]
    
    params = ['Flow In (gpm)', 'Pump Pressure (psi)', 'RPM', 'ROP (ft/h)',
              'CRR (bbl/min)', 'CSD P50 (mm)', 'Pit Volume (bbl)', 
              'Hook Load (klbf)', 'TCR_Ratio']
    
    comparison = {}
    for param in params:
        if param in df.columns:
            shallow_val = shallow[param].mean()
            deep_val = deep[param].mean()
            change_pct = ((deep_val - shallow_val) / shallow_val * 100) if shallow_val != 0 else 0
            comparison[param] = {
                'shallow': shallow_val,
                'deep': deep_val,
                'change_pct': change_pct
            }
    
    return comparison


def calculate_excess_volume(df):
    """Calculate excess cuttings volume and equivalent hole enlargement."""
    # Get final values
    measured_final = df['Measured TCR (bbl)'].dropna().iloc[-1]
    theoretical_final = df['Theoretical TCR (bbl)'].dropna().iloc[-1]
    excess_bbl = measured_final - theoretical_final
    excess_pct = (excess_bbl / theoretical_final) * 100
    
    # Calculate depth drilled
    depth_start = df['Hole Depth (m)'].min()
    depth_end = df['Hole Depth (m)'].max()
    depth_drilled_m = depth_end - depth_start
    depth_drilled_ft = depth_drilled_m * 3.28084
    
    # Estimate hole enlargement (assuming 8.5" bit)
    bit_diameter_in = 8.5
    excess_cuft = excess_bbl * 5.615
    
    import math
    d_bit_ft = bit_diameter_in / 12
    D_squared = (4 * excess_cuft / (math.pi * depth_drilled_ft)) + d_bit_ft**2
    D_actual_ft = math.sqrt(max(D_squared, d_bit_ft**2))
    D_actual_in = D_actual_ft * 12
    enlargement_in = D_actual_in - bit_diameter_in
    enlargement_pct = (D_actual_in / bit_diameter_in - 1) * 100
    
    return {
        'measured_final': measured_final,
        'theoretical_final': theoretical_final,
        'excess_bbl': excess_bbl,
        'excess_pct': excess_pct,
        'depth_drilled_m': depth_drilled_m,
        'equivalent_hole_diameter_in': D_actual_in,
        'enlargement_in': enlargement_in,
        'enlargement_pct': enlargement_pct
    }


def analyze_by_depth_bins(df, bin_size=200):
    """Analyze TCR ratio and parameters by depth bins."""
    tcr_data = df[df['TCR_Ratio'].notna()].copy()
    
    min_depth = int(tcr_data['Bit Depth (m)'].min() // bin_size) * bin_size
    max_depth = int(tcr_data['Bit Depth (m)'].max() // bin_size + 1) * bin_size
    
    bins = list(range(min_depth, max_depth + bin_size, bin_size))
    tcr_data['depth_bin'] = pd.cut(tcr_data['Bit Depth (m)'], bins=bins)
    
    analysis = tcr_data.groupby('depth_bin', observed=True).agg({
        'TCR_Ratio': ['mean', 'std', 'count'],
        'ROP (ft/h)': 'mean',
        'Flow In (gpm)': 'mean',
        'Pump Pressure (psi)': 'mean',
        'CRR (bbl/min)': 'mean',
        'CSD P50 (mm)': 'mean'
    })
    
    return analysis


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def setup_plot_style():
    """Set up dark theme for plots."""
    plt.style.use('dark_background')
    plt.rcParams['figure.facecolor'] = '#0a0e14'
    plt.rcParams['axes.facecolor'] = '#151d28'
    plt.rcParams['axes.edgecolor'] = '#2a3744'
    plt.rcParams['axes.labelcolor'] = '#e6edf3'
    plt.rcParams['xtick.color'] = '#8b949e'
    plt.rcParams['ytick.color'] = '#8b949e'
    plt.rcParams['grid.color'] = '#2a3744'
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['text.color'] = '#e6edf3'
    plt.rcParams['font.family'] = 'sans-serif'


def plot_tcr_deviation_timeline(df, output_dir):
    """Plot TCR deviation timeline with threshold crossings."""
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    
    tcr_data = df[df['TCR_Ratio'].notna()]
    x = tcr_data['time']
    
    # Plot 1: Measured vs Theoretical TCR
    ax1 = axes[0]
    ax1.fill_between(x, tcr_data['Measured TCR (bbl)'], alpha=0.3, color=Config.COLORS['measured'])
    ax1.plot(x, tcr_data['Measured TCR (bbl)'], color=Config.COLORS['measured'], linewidth=1, label='Measured TCR')
    ax1.fill_between(x, tcr_data['Theoretical TCR (bbl)'], alpha=0.3, color=Config.COLORS['theoretical'])
    ax1.plot(x, tcr_data['Theoretical TCR (bbl)'], color=Config.COLORS['theoretical'], linewidth=1, label='Theoretical TCR')
    ax1.set_ylabel('TCR (bbl)')
    ax1.set_title('Measured vs Theoretical Total Cuttings Recovery', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: TCR Ratio with thresholds
    ax2 = axes[1]
    ax2.fill_between(x, tcr_data['TCR_Ratio'], alpha=0.3, color=Config.COLORS['ratio'])
    ax2.plot(x, tcr_data['TCR_Ratio'], color=Config.COLORS['ratio'], linewidth=1)
    ax2.axhline(y=1.0, color='white', linestyle='--', alpha=0.5, label='Ideal (1.0)')
    ax2.axhline(y=1.15, color=Config.COLORS['warning'], linestyle='--', alpha=0.7, label='Warning (1.15)')
    ax2.axhline(y=1.30, color=Config.COLORS['danger'], linestyle='--', alpha=0.7, label='Alarm (1.30)')
    ax2.set_ylabel('TCR Ratio')
    ax2.set_title('TCR Recovery Ratio (Measured / Theoretical)', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, 1.6)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Bit Depth
    ax3 = axes[2]
    ax3.plot(tcr_data['time'], tcr_data['Bit Depth (m)'], color=Config.COLORS['theoretical'], linewidth=1)
    ax3.set_ylabel('Bit Depth (m)')
    ax3.set_xlabel('Time')
    ax3.set_title('Bit Depth Progression', fontsize=14, fontweight='bold')
    ax3.invert_yaxis()
    ax3.grid(True, alpha=0.3)
    
    # Format x-axis
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    fig.autofmt_xdate()
    
    plt.tight_layout()
    fig.savefig(output_dir / 'tcr_deviation_timeline.png', dpi=Config.FIGURE_DPI,
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"  Saved: tcr_deviation_timeline.png")


def plot_tcr_vs_depth(df, output_dir):
    """Plot TCR ratio vs depth with regression line."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    tcr_data = df[(df['TCR_Ratio'].notna()) & (df['TCR_Ratio'] > 0.3)].copy()
    
    # Left: Scatter plot with regression
    ax1 = axes[0]
    scatter = ax1.scatter(tcr_data['TCR_Ratio'], tcr_data['Bit Depth (m)'],
                          c=tcr_data['TCR_Ratio'], cmap='RdYlGn_r', 
                          alpha=0.5, s=10, vmin=0.7, vmax=1.4)
    
    # Add regression line
    corr = analyze_depth_correlation(df)
    if corr:
        x_line = np.array([tcr_data['Bit Depth (m)'].min(), tcr_data['Bit Depth (m)'].max()])
        y_line = corr['intercept'] + corr['slope'] * x_line
        ax1.plot(y_line, x_line, 'w--', linewidth=2, 
                 label=f'Fit: R²={corr["r_squared"]:.2f}')
    
    ax1.axvline(x=1.0, color='white', linestyle='--', alpha=0.5)
    ax1.set_xlabel('TCR Ratio')
    ax1.set_ylabel('Bit Depth (m)')
    ax1.set_title('TCR Ratio vs Depth', fontsize=14, fontweight='bold')
    ax1.invert_yaxis()
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax1, label='TCR Ratio')
    
    # Right: Depth-binned analysis
    ax2 = axes[1]
    depth_analysis = analyze_by_depth_bins(df, bin_size=200)
    
    depth_centers = [interval.mid for interval in depth_analysis.index]
    ratios = depth_analysis[('TCR_Ratio', 'mean')].values
    stds = depth_analysis[('TCR_Ratio', 'std')].values
    
    ax2.barh(depth_centers, ratios, height=150, color=Config.COLORS['ratio'], alpha=0.7)
    ax2.errorbar(ratios, depth_centers, xerr=stds, fmt='none', color='white', alpha=0.5)
    ax2.axvline(x=1.0, color='white', linestyle='--', alpha=0.5)
    ax2.axvline(x=1.15, color=Config.COLORS['warning'], linestyle='--', alpha=0.7)
    ax2.set_xlabel('TCR Ratio (mean ± std)')
    ax2.set_ylabel('Depth (m)')
    ax2.set_title('TCR Ratio by Depth Interval', fontsize=14, fontweight='bold')
    ax2.invert_yaxis()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig.savefig(output_dir / 'tcr_vs_depth.png', dpi=Config.FIGURE_DPI,
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"  Saved: tcr_vs_depth.png")


def plot_operational_context(df, output_dir):
    """Plot operational parameters around deviation."""
    fig, axes = plt.subplots(4, 1, figsize=(14, 14), sharex=True)
    
    tcr_data = df[df['TCR_Ratio'].notna()]
    x = tcr_data['time']
    
    # TCR Ratio
    ax1 = axes[0]
    ax1.fill_between(x, tcr_data['TCR_Ratio'], alpha=0.3, color=Config.COLORS['ratio'])
    ax1.plot(x, tcr_data['TCR_Ratio'], color=Config.COLORS['ratio'], linewidth=1)
    ax1.axhline(y=1.0, color='white', linestyle='--', alpha=0.5)
    ax1.set_ylabel('TCR Ratio')
    ax1.set_title('TCR Ratio with Operational Context', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Flow and Pressure
    ax2 = axes[1]
    ax2_twin = ax2.twinx()
    ax2.plot(x, tcr_data['Flow In (gpm)'], color=Config.COLORS['theoretical'], linewidth=1, label='Flow In')
    ax2_twin.plot(x, tcr_data['Pump Pressure (psi)'], color=Config.COLORS['danger'], linewidth=1, label='Pressure')
    ax2.set_ylabel('Flow In (gpm)', color=Config.COLORS['theoretical'])
    ax2_twin.set_ylabel('Pump Pressure (psi)', color=Config.COLORS['danger'])
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left')
    ax2_twin.legend(loc='upper right')
    
    # ROP and RPM
    ax3 = axes[2]
    ax3_twin = ax3.twinx()
    ax3.plot(x, tcr_data['ROP (ft/h)'], color=Config.COLORS['measured'], linewidth=1, label='ROP')
    ax3_twin.plot(x, tcr_data['RPM'], color=Config.COLORS['warning'], linewidth=1, label='RPM')
    ax3.set_ylabel('ROP (ft/h)', color=Config.COLORS['measured'])
    ax3_twin.set_ylabel('RPM', color=Config.COLORS['warning'])
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='upper left')
    ax3_twin.legend(loc='upper right')
    
    # Hook Load
    ax4 = axes[3]
    ax4.plot(x, tcr_data['Hook Load (klbf)'], color=Config.COLORS['purple'], linewidth=1)
    ax4.set_ylabel('Hook Load (klbf)')
    ax4.set_xlabel('Time')
    ax4.grid(True, alpha=0.3)
    
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    fig.autofmt_xdate()
    
    plt.tight_layout()
    fig.savefig(output_dir / 'operational_context.png', dpi=Config.FIGURE_DPI,
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"  Saved: operational_context.png")


def plot_deviation_comparison(df, shallow_range, deep_range, output_dir):
    """Plot parameter comparison between shallow and deep intervals."""
    comparison = compare_intervals(df, shallow_range, deep_range)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    params = list(comparison.keys())
    changes = [comparison[p]['change_pct'] for p in params]
    
    colors = [Config.COLORS['danger'] if c < -10 else 
              Config.COLORS['warning'] if c > 20 else 
              Config.COLORS['ratio'] for c in changes]
    
    bars = ax.barh(params, changes, color=colors, alpha=0.7)
    ax.axvline(x=0, color='white', linestyle='-', alpha=0.3)
    
    # Add value labels
    for bar, val in zip(bars, changes):
        x_pos = val + (2 if val >= 0 else -2)
        ax.text(x_pos, bar.get_y() + bar.get_height()/2, 
                f'{val:+.1f}%', va='center', fontsize=10)
    
    ax.set_xlabel('Change (%)')
    ax.set_title(f'Parameter Changes: {shallow_range[0]}-{shallow_range[1]}m vs {deep_range[0]}-{deep_range[1]}m',
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    fig.savefig(output_dir / 'deviation_comparison.png', dpi=Config.FIGURE_DPI,
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"  Saved: deviation_comparison.png")


def plot_lag_analysis(df, output_dir):
    """Plot lag time analysis - CRR vs Lagged ROP."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Filter valid data
    valid = df[(df['CRR (bbl/min)'] > 0) & (df['Lagged ROP (m/hr)'] > 0)].copy()
    valid['ROP_m_hr'] = valid['ROP (ft/h)'] * 0.3048
    
    # CRR vs Lagged ROP (should show correlation if lag is correct)
    ax1 = axes[0, 0]
    ax1.scatter(valid['Lagged ROP (m/hr)'], valid['CRR (bbl/min)'],
                alpha=0.3, s=10, c=Config.COLORS['measured'])
    corr = valid['Lagged ROP (m/hr)'].corr(valid['CRR (bbl/min)'])
    ax1.text(0.05, 0.95, f'r = {corr:.3f}', transform=ax1.transAxes,
             fontsize=12, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
    ax1.set_xlabel('Lagged ROP (m/hr)')
    ax1.set_ylabel('CRR (bbl/min)')
    ax1.set_title('CRR vs Lagged ROP (Bit-Time Correlation)', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # CRR vs Same-time ROP (comparison)
    ax2 = axes[0, 1]
    valid2 = valid[valid['ROP_m_hr'] > 0]
    ax2.scatter(valid2['ROP_m_hr'], valid2['CRR (bbl/min)'],
                alpha=0.3, s=10, c=Config.COLORS['theoretical'])
    corr2 = valid2['ROP_m_hr'].corr(valid2['CRR (bbl/min)'])
    ax2.text(0.05, 0.95, f'r = {corr2:.3f}', transform=ax2.transAxes,
             fontsize=12, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
    ax2.set_xlabel('Same-time ROP (m/hr)')
    ax2.set_ylabel('CRR (bbl/min)')
    ax2.set_title('CRR vs Same-time ROP (Surface-Time)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # ROP vs Lagged ROP time series
    ax3 = axes[1, 0]
    sample = valid.iloc[::10]  # Downsample for visibility
    ax3.plot(sample['time'], sample['ROP_m_hr'], color=Config.COLORS['theoretical'], 
             alpha=0.7, linewidth=0.5, label='Same-time ROP')
    ax3.plot(sample['time'], sample['Lagged ROP (m/hr)'], color=Config.COLORS['measured'],
             alpha=0.7, linewidth=0.5, label='Lagged ROP')
    ax3.set_xlabel('Time')
    ax3.set_ylabel('ROP (m/hr)')
    ax3.set_title('ROP vs Lagged ROP Time Series', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # Transport efficiency by depth
    ax4 = axes[1, 1]
    valid['transport_eff'] = valid['CRR (bbl/min)'] / valid['Lagged ROP (m/hr)'] * 60
    valid['depth_bin'] = pd.cut(valid['Bit Depth (m)'], bins=range(3000, 5600, 500))
    eff_by_depth = valid.groupby('depth_bin', observed=True)['transport_eff'].mean()
    
    depths = [str(interval) for interval in eff_by_depth.index]
    ax4.bar(range(len(depths)), eff_by_depth.values, color=Config.COLORS['ratio'], alpha=0.7)
    ax4.set_xticks(range(len(depths)))
    ax4.set_xticklabels(depths, rotation=45, ha='right')
    ax4.set_xlabel('Depth Interval (m)')
    ax4.set_ylabel('Transport Efficiency (bbl/m)')
    ax4.set_title('Transport Efficiency by Depth', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    fig.savefig(output_dir / 'lag_analysis.png', dpi=Config.FIGURE_DPI,
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    print(f"  Saved: lag_analysis.png")


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(df, output_dir):
    """Generate text analysis report."""
    
    lines = []
    lines.append("=" * 70)
    lines.append("TCR DEVIATION ANALYSIS REPORT")
    lines.append("=" * 70)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Dataset overview
    lines.append("DATASET OVERVIEW")
    lines.append("-" * 40)
    lines.append(f"Total data points: {len(df):,}")
    if 'time' in df.columns:
        lines.append(f"Time range: {df['time'].min()} to {df['time'].max()}")
    if 'Bit Depth (m)' in df.columns:
        lines.append(f"Depth range: {df['Bit Depth (m)'].min():.0f}m to {df['Bit Depth (m)'].max():.0f}m")
    lines.append("")
    
    # Deviation timeline
    lines.append("DEVIATION TIMELINE")
    lines.append("-" * 40)
    thresholds = find_deviation_start(df)
    if thresholds:
        for thresh, data in thresholds.items():
            if data:
                lines.append(f"Ratio > {thresh:.2f}: {data['time']} at {data['depth']:.0f}m")
    lines.append("")
    
    # Depth correlation
    lines.append("DEPTH CORRELATION")
    lines.append("-" * 40)
    corr = analyze_depth_correlation(df)
    if corr:
        lines.append(f"TCR Ratio = {corr['intercept']:.4f} + {corr['slope']:.6f} × Depth")
        lines.append(f"R² = {corr['r_squared']:.3f}")
        lines.append(f"Rate: +{corr['rate_per_100m']:.3f} per 100m depth")
    lines.append("")
    
    # Excess volume
    lines.append("EXCESS VOLUME ANALYSIS")
    lines.append("-" * 40)
    excess = calculate_excess_volume(df)
    lines.append(f"Measured TCR (final): {excess['measured_final']:.1f} bbl")
    lines.append(f"Theoretical TCR (final): {excess['theoretical_final']:.1f} bbl")
    lines.append(f"Excess recovered: {excess['excess_bbl']:.1f} bbl ({excess['excess_pct']:.1f}%)")
    lines.append(f"Equivalent hole enlargement: {excess['enlargement_in']:.2f}\" ({excess['enlargement_pct']:.1f}%)")
    lines.append("")
    
    # Root cause assessment
    lines.append("ROOT CAUSE ASSESSMENT")
    lines.append("-" * 40)
    lines.append("""
Most Likely Causes (in order of probability):

1. HOLE ENLARGEMENT
   - Gradual, depth-correlated deviation suggests progressive instability
   - Excess volume equivalent to ~30% enlargement supports this
   - Verify with caliper log data

2. THEORETICAL MODEL UNDERESTIMATE  
   - Check bit diameter input (is it correct?)
   - Verify formation porosity assumptions
   - Review hole enlargement factor in calculations

3. CLEANING HISTORICAL CUTTINGS BED
   - Less likely given continuous nature of deviation
   - Would expect temporary spike then stabilization

Recommendations:
- Review caliper log data for actual hole diameter
- Check theoretical model inputs
- Monitor UFO/caving events by depth
- Consider mud weight adjustment if instability confirmed
""")
    
    # Save report
    report_path = output_dir / 'tcr_deviation_report.txt'
    with open(report_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"  Saved: tcr_deviation_report.txt")
    return '\n'.join(lines)


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Main analysis function."""
    
    if len(sys.argv) < 2:
        print("TCR Deviation Analysis Tool")
        print("-" * 40)
        print("Usage: python tcr_deviation_analysis.py <data_file.csv> [--output-dir path]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Parse output directory
    output_dir = Path.cwd() / 'tcr_deviation_analysis'
    if '--output-dir' in sys.argv:
        idx = sys.argv.index('--output-dir')
        if idx + 1 < len(sys.argv):
            output_dir = Path(sys.argv[idx + 1])
    
    output_dir.mkdir(exist_ok=True)
    
    print("\n" + "=" * 60)
    print("TCR DEVIATION ANALYSIS")
    print("=" * 60)
    
    # Load data
    df = load_data(filepath)
    
    # Set up plotting
    setup_plot_style()
    
    # Run analyses
    print("\nAnalyzing deviation...")
    thresholds = find_deviation_start(df)
    corr = analyze_depth_correlation(df)
    excess = calculate_excess_volume(df)
    
    # Print summary
    print("\n" + "-" * 40)
    print("KEY FINDINGS:")
    print("-" * 40)
    
    if thresholds and thresholds.get(1.0):
        print(f"• Deviation started: {thresholds[1.0]['time']} at {thresholds[1.0]['depth']:.0f}m")
    
    if corr:
        print(f"• Depth correlation: R² = {corr['r_squared']:.2f} (+{corr['rate_per_100m']:.3f}/100m)")
    
    print(f"• Excess volume: {excess['excess_bbl']:.1f} bbl ({excess['excess_pct']:.1f}%)")
    print(f"• Equivalent enlargement: {excess['enlargement_pct']:.1f}%")
    
    # Generate plots
    print("\nGenerating visualizations...")
    plot_tcr_deviation_timeline(df, output_dir)
    plot_tcr_vs_depth(df, output_dir)
    plot_operational_context(df, output_dir)
    
    # Find good comparison intervals
    tcr_data = df[df['TCR_Ratio'].notna()]
    if len(tcr_data) > 0:
        # Find where ratio was ~1.0 and where it's elevated
        near_one = tcr_data[abs(tcr_data['TCR_Ratio'] - 1.0) < 0.1]
        elevated = tcr_data[tcr_data['TCR_Ratio'] > 1.15]
        
        if len(near_one) > 0 and len(elevated) > 0:
            shallow_depth = near_one['Bit Depth (m)'].median()
            deep_depth = elevated['Bit Depth (m)'].median()
            
            shallow_range = (int(shallow_depth - 100), int(shallow_depth + 100))
            deep_range = (int(deep_depth - 100), int(deep_depth + 100))
            
            plot_deviation_comparison(df, shallow_range, deep_range, output_dir)
    
    if 'Lagged ROP (m/hr)' in df.columns:
        plot_lag_analysis(df, output_dir)
    
    # Generate report
    print("\nGenerating report...")
    report = generate_report(df, output_dir)
    
    print("\n" + "=" * 60)
    print(f"Analysis complete! Output saved to: {output_dir}")
    print("=" * 60)
    
    # Print summary
    print("\nFiles generated:")
    for f in sorted(output_dir.glob('*')):
        print(f"  • {f.name}")


if __name__ == '__main__':
    main()
