#!/usr/bin/env python3
"""
CUC Analysis Charts for DrillDocs CleanSight
Generates 5 key charts for CUC optimization analysis

Requirements: pip install pandas matplotlib numpy

Usage: 
1. Place well_data.csv in the same folder as this script
2. Run: python cuc_analysis_charts.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'well_data.csv')

# Read data - try different encodings and separators
print(f"Reading data from: {csv_path}")
df = None
for encoding in ['utf-8', 'cp1252', 'latin-1', 'utf-16-le', 'utf-16']:
    for sep in [',', '\t', ';']:
        try:
            df = pd.read_csv(csv_path, encoding=encoding, sep=sep)
            if len(df.columns) > 3:
                print(f"  (used {encoding} encoding, '{sep}' separator)")
                break
        except:
            continue
    if df is not None and len(df.columns) > 3:
        break

print(f"Loaded {len(df)} wells")
print(f"Columns found: {list(df.columns)}\n")

# Extract Section from Well name (looks for "12.25" or "16.5" in the well name)
def get_section(well_name):
    well_str = str(well_name)
    if '12.25' in well_str or '12_25' in well_str:
        return 12.25
    elif '16.5' in well_str or '16_5' in well_str:
        return 16.5
    else:
        return 12.25  # default

# Find the right column names (flexible matching)
def find_col(df, patterns):
    for col in df.columns:
        col_lower = col.lower().strip()
        for p in patterns:
            if p.lower() in col_lower:
                return col
    return None

well_col = find_col(df, ['well'])
bu_col = find_col(df, ['bu cycles', 'bu_cycles'])
excess_col = find_col(df, ['excess circulation', 'excess_circulation', 'excess circ'])
time_clean_col = find_col(df, ['time to clean', 'time_to_clean'])
crr_reduction_col = find_col(df, ['crr reduction', 'crr_reduction', 'reduction'])

print(f"Mapped columns:")
print(f"  Well: {well_col}")
print(f"  BU Cycles: {bu_col}")
print(f"  Excess Circulation: {excess_col}")
print(f"  Time to Clean: {time_clean_col}")
print(f"  CRR Reduction: {crr_reduction_col}\n")

# Add Section column
df['Section'] = df[well_col].apply(get_section)

# Rename columns for easier use
df['Well'] = df[well_col]
df['BU Cycles'] = pd.to_numeric(df[bu_col], errors='coerce')
df['Excess Circulation (min)'] = pd.to_numeric(df[excess_col], errors='coerce')
df['Time to Clean (min)'] = pd.to_numeric(df[time_clean_col], errors='coerce')
if crr_reduction_col:
    df['CRR Reduction (%)'] = pd.to_numeric(df[crr_reduction_col], errors='coerce')
else:
    df['CRR Reduction (%)'] = 90  # default

# Drop any rows with missing key data
df = df.dropna(subset=['BU Cycles', 'Excess Circulation (min)', 'Time to Clean (min)'])
print(f"Processing {len(df)} wells with valid data\n")

# Sort by BU Cycles for better visualization
df_sorted = df.sort_values('BU Cycles', ascending=True)

# Define colors
COLOR_1225 = '#3b82f6'  # Blue for 12.25"
COLOR_165 = '#f97316'   # Orange for 16.5"
COLOR_CLEAN = '#10b981'  # Green
COLOR_EXCESS = '#ef4444'  # Red
BG_COLOR = '#1a1a2e'
GRID_COLOR = '#333355'
TEXT_COLOR = '#ffffff'
THRESHOLD_COLOR = '#ef4444'
AVG_COLOR = '#fbbf24'

plt.style.use('dark_background')

# ============================================================
# CHART 1: BU Cycles to Clean (Bar Chart)
# ============================================================
print("Generating Chart 1: BU Cycles Bar...")
fig1, ax1 = plt.subplots(figsize=(14, 7))
fig1.patch.set_facecolor(BG_COLOR)
ax1.set_facecolor(BG_COLOR)

# Create bars with section colors
colors = [COLOR_1225 if s == 12.25 else COLOR_165 for s in df_sorted['Section']]
bars = ax1.bar(range(len(df_sorted)), df_sorted['BU Cycles'], color=colors, edgecolor='white', linewidth=0.5)

# Add value labels on bars
for i, (bar, val) in enumerate(zip(bars, df_sorted['BU Cycles'])):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
             f'{val:.1f}', ha='center', va='bottom', fontsize=10, color=TEXT_COLOR, fontweight='bold')

# Average line
avg_bu = df_sorted['BU Cycles'].mean()
ax1.axhline(y=avg_bu, color=AVG_COLOR, linestyle='--', linewidth=2, label=f'Avg: {avg_bu:.2f} BU')
ax1.text(len(df_sorted)-0.5, avg_bu + 0.15, f'Avg: {avg_bu:.2f}', color=AVG_COLOR, fontsize=11, fontweight='bold', ha='right')

# 3 BU "slow cleaner" threshold
ax1.axhline(y=3.0, color=THRESHOLD_COLOR, linestyle=':', linewidth=1.5, alpha=0.7)
ax1.text(len(df_sorted)-0.5, 3.1, 'Slow cleaner (>3 BU)', color=THRESHOLD_COLOR, fontsize=9, ha='right', alpha=0.8)

# Labels and formatting
ax1.set_xticks(range(len(df_sorted)))
ax1.set_xticklabels(df_sorted['Well'], rotation=45, ha='right', fontsize=9)
ax1.set_ylabel('BU Cycles to Clean', fontsize=12, color=TEXT_COLOR)
ax1.set_xlabel('Well / Trip', fontsize=12, color=TEXT_COLOR)
ax1.set_title('BU Cycles to Clean — All AkerBP Wells', fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15)
ax1.set_ylim(0, max(df_sorted['BU Cycles']) + 1)
ax1.grid(axis='y', color=GRID_COLOR, alpha=0.3)

# Legend
legend_1225 = mpatches.Patch(color=COLOR_1225, label='12.25" section')
legend_165 = mpatches.Patch(color=COLOR_165, label='16.5" section')
ax1.legend(handles=[legend_1225, legend_165], loc='upper left', fontsize=10)

plt.tight_layout()
fig1.savefig(os.path.join(script_dir, 'bu_cycles_bar.png'), dpi=150, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
print("  Saved: bu_cycles_bar.png")

# ============================================================
# CHART 2: Excess Circulation (Bar Chart)
# ============================================================
print("Generating Chart 2: Excess Circulation Bar...")
df_excess = df.sort_values('Excess Circulation (min)', ascending=True)

fig2, ax2 = plt.subplots(figsize=(14, 7))
fig2.patch.set_facecolor(BG_COLOR)
ax2.set_facecolor(BG_COLOR)

# Create bars with section colors
colors = [COLOR_1225 if s == 12.25 else COLOR_165 for s in df_excess['Section']]
bars = ax2.bar(range(len(df_excess)), df_excess['Excess Circulation (min)'], color=colors, edgecolor='white', linewidth=0.5)

# Add value labels on bars
for i, (bar, val) in enumerate(zip(bars, df_excess['Excess Circulation (min)'])):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3, 
             f'{int(val)}', ha='center', va='bottom', fontsize=10, color=TEXT_COLOR, fontweight='bold')

# Average line
avg_excess = df_excess['Excess Circulation (min)'].mean()
ax2.axhline(y=avg_excess, color=AVG_COLOR, linestyle='--', linewidth=2)
ax2.text(len(df_excess)-0.5, avg_excess + 5, f'Avg: {avg_excess:.0f} min', color=AVG_COLOR, fontsize=11, fontweight='bold', ha='right')

# Labels and formatting
ax2.set_xticks(range(len(df_excess)))
ax2.set_xticklabels(df_excess['Well'], rotation=45, ha='right', fontsize=9)
ax2.set_ylabel('Excess Circulation (minutes)', fontsize=12, color=TEXT_COLOR)
ax2.set_xlabel('Well / Trip', fontsize=12, color=TEXT_COLOR)
ax2.set_title('Excess Circulation — Time Wasted After Hole Was Already Clean', fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15)
ax2.set_ylim(0, max(df_excess['Excess Circulation (min)']) + 20)
ax2.grid(axis='y', color=GRID_COLOR, alpha=0.3)

# Legend
ax2.legend(handles=[legend_1225, legend_165], loc='upper left', fontsize=10)

plt.tight_layout()
fig2.savefig(os.path.join(script_dir, 'excess_circulation_bar.png'), dpi=150, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
print("  Saved: excess_circulation_bar.png")

# ============================================================
# CHART 3: BU Cycles vs Excess Circulation (Scatter)
# ============================================================
print("Generating Chart 3: BU vs Excess Scatter...")
fig3, ax3 = plt.subplots(figsize=(10, 8))
fig3.patch.set_facecolor(BG_COLOR)
ax3.set_facecolor(BG_COLOR)

# Scatter with section colors
for section, color, label in [(12.25, COLOR_1225, '12.25"'), (16.5, COLOR_165, '16.5"')]:
    mask = df['Section'] == section
    if mask.sum() > 0:
        ax3.scatter(df[mask]['BU Cycles'], df[mask]['Excess Circulation (min)'], 
                    c=color, s=120, alpha=0.8, edgecolors='white', linewidth=1, label=label)
        
        # Add well labels
        for _, row in df[mask].iterrows():
            ax3.annotate(row['Well'].split(' - ')[0], (row['BU Cycles'], row['Excess Circulation (min)']), 
                        textcoords="offset points", xytext=(5, 5), fontsize=8, color=TEXT_COLOR, alpha=0.7)

# Labels and formatting
ax3.set_xlabel('BU Cycles to Clean', fontsize=12, color=TEXT_COLOR)
ax3.set_ylabel('Excess Circulation (minutes)', fontsize=12, color=TEXT_COLOR)
ax3.set_title('BU Cycles vs Excess Circulation\nNo Correlation = Operators Not Using CRR Data', fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15)
ax3.grid(True, color=GRID_COLOR, alpha=0.3)
ax3.legend(loc='upper right', fontsize=10)

plt.tight_layout()
fig3.savefig(os.path.join(script_dir, 'bu_vs_excess_scatter.png'), dpi=150, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
print("  Saved: bu_vs_excess_scatter.png")

# ============================================================
# CHART 4: Section Comparison (Grouped Bar)
# ============================================================
print("Generating Chart 4: Section Comparison...")
fig4, ax4 = plt.subplots(figsize=(10, 6))
fig4.patch.set_facecolor(BG_COLOR)
ax4.set_facecolor(BG_COLOR)

# Calculate section averages
section_stats = df.groupby('Section').agg({
    'BU Cycles': 'mean',
    'Excess Circulation (min)': 'mean',
    'Time to Clean (min)': 'mean',
}).round(1)

metrics = ['BU Cycles', 'Excess Circ (min/10)', 'Time to Clean (min/100)']
x = np.arange(len(metrics))
width = 0.35

# Normalize for display
vals_1225 = [section_stats.loc[12.25, 'BU Cycles'], 
             section_stats.loc[12.25, 'Excess Circulation (min)']/10,
             section_stats.loc[12.25, 'Time to Clean (min)']/100]
vals_165 = [section_stats.loc[16.5, 'BU Cycles'], 
            section_stats.loc[16.5, 'Excess Circulation (min)']/10,
            section_stats.loc[16.5, 'Time to Clean (min)']/100]

bars1 = ax4.bar(x - width/2, vals_1225, width, label='12.25"', color=COLOR_1225, edgecolor='white', linewidth=0.5)
bars2 = ax4.bar(x + width/2, vals_165, width, label='16.5"', color=COLOR_165, edgecolor='white', linewidth=0.5)

# Add value labels (actual values)
actual_1225 = [section_stats.loc[12.25, 'BU Cycles'], 
               section_stats.loc[12.25, 'Excess Circulation (min)'],
               section_stats.loc[12.25, 'Time to Clean (min)']]
actual_165 = [section_stats.loc[16.5, 'BU Cycles'], 
              section_stats.loc[16.5, 'Excess Circulation (min)'],
              section_stats.loc[16.5, 'Time to Clean (min)']]

for bar, val in zip(bars1, actual_1225):
    label = f'{val:.1f}' if val < 10 else f'{int(val)}'
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, label, 
             ha='center', va='bottom', fontsize=10, color=TEXT_COLOR, fontweight='bold')
for bar, val in zip(bars2, actual_165):
    label = f'{val:.1f}' if val < 10 else f'{int(val)}'
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, label, 
             ha='center', va='bottom', fontsize=10, color=TEXT_COLOR, fontweight='bold')

ax4.set_xticks(x)
ax4.set_xticklabels(metrics, fontsize=11)
ax4.set_ylabel('Value (normalized for display)', fontsize=11, color=TEXT_COLOR)
ax4.set_title('Section Comparison — 12.25" vs 16.5"', fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15)
ax4.legend(loc='upper right', fontsize=10)
ax4.grid(axis='y', color=GRID_COLOR, alpha=0.3)

plt.tight_layout()
fig4.savefig(os.path.join(script_dir, 'section_comparison.png'), dpi=150, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
print("  Saved: section_comparison.png")

# ============================================================
# CHART 5: Stacked Excess Circulation (Green/Red with clean lines)
# ============================================================
print("Generating Chart 5: Stacked Excess Circulation...")

# Sort by total time at TD
df['Total Time at TD (min)'] = df['Time to Clean (min)'] + df['Excess Circulation (min)']
df_stacked = df.sort_values('Total Time at TD (min)', ascending=True)

fig5, ax5 = plt.subplots(figsize=(14, 8))
fig5.patch.set_facecolor(BG_COLOR)
ax5.set_facecolor(BG_COLOR)

y_pos = np.arange(len(df_stacked))
bar_height = 0.7

# Stacked horizontal bars: Green (time to clean) + Red (excess)
bars_clean = ax5.barh(y_pos, df_stacked['Time to Clean (min)'], height=bar_height, 
                      color=COLOR_CLEAN, edgecolor='white', linewidth=0.5, label='Time to clean')

bars_excess = ax5.barh(y_pos, df_stacked['Excess Circulation (min)'], height=bar_height,
                       left=df_stacked['Time to Clean (min)'], color=COLOR_EXCESS, 
                       edgecolor='white', linewidth=0.5, label='Excess circulation')

# Add dashed vertical line at each "clean" point
for i, (idx, row) in enumerate(df_stacked.iterrows()):
    clean_time = row['Time to Clean (min)']
    ax5.axvline(x=clean_time, ymin=(i - 0.35 + 0.5) / len(df_stacked), ymax=(i + 0.35 + 0.5) / len(df_stacked),
               color='white', linestyle='--', linewidth=1.5, alpha=0.9)

# Add value labels
for i, (idx, row) in enumerate(df_stacked.iterrows()):
    # Clean time label (inside green bar)
    if row['Time to Clean (min)'] > 40:
        ax5.text(row['Time to Clean (min)'] / 2, i, f"{int(row['Time to Clean (min)'])} min", 
                ha='center', va='center', fontsize=9, color='white', fontweight='bold')
    
    # Excess time label (inside red bar if big enough, else outside)
    excess = row['Excess Circulation (min)']
    if excess > 30:
        ax5.text(row['Time to Clean (min)'] + excess / 2, i, f"+{int(excess)}", 
                ha='center', va='center', fontsize=9, color='white', fontweight='bold')
    else:
        ax5.text(row['Time to Clean (min)'] + excess + 5, i, f"+{int(excess)}", 
                ha='left', va='center', fontsize=8, color=COLOR_EXCESS, fontweight='bold')

# Labels and formatting
ax5.set_yticks(y_pos)
ax5.set_yticklabels(df_stacked['Well'], fontsize=9)
ax5.set_xlabel('Minutes at TD', fontsize=12, color=TEXT_COLOR)
ax5.set_title('Time to Clean vs Excess Circulation\nDashed line = hole was clean, red = wasted time after', 
             fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15)
ax5.set_xlim(0, max(df_stacked['Total Time at TD (min)']) + 30)
ax5.grid(axis='x', color=GRID_COLOR, alpha=0.3)

# Legend
legend_clean = mpatches.Patch(color=COLOR_CLEAN, label='Time to clean (useful)')
legend_excess = mpatches.Patch(color=COLOR_EXCESS, label='Excess circulation (wasted)')
ax5.legend(handles=[legend_clean, legend_excess], loc='upper right', fontsize=11)

# Add annotation
total_excess = df_stacked['Excess Circulation (min)'].sum()
ax5.text(0.98, 0.02, f"Total wasted: {int(total_excess)} min ({total_excess/60:.1f} hrs)", 
        transform=ax5.transAxes, ha='right', va='bottom', fontsize=11, 
        color=COLOR_EXCESS, fontweight='bold',
        bbox=dict(boxstyle='round', facecolor=BG_COLOR, edgecolor=COLOR_EXCESS, alpha=0.8))

plt.tight_layout()
fig5.savefig(os.path.join(script_dir, 'excess_circulation_stacked.png'), dpi=150, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
print("  Saved: excess_circulation_stacked.png")

# ============================================================
# Print Summary Stats
# ============================================================
print("\n" + "="*60)
print("SUMMARY STATISTICS")
print("="*60)
print(f"\n12.25\" Section ({len(df[df['Section']==12.25])} wells):")
print(f"  Avg BU Cycles: {df[df['Section']==12.25]['BU Cycles'].mean():.2f}")
print(f"  Avg Excess Circ: {df[df['Section']==12.25]['Excess Circulation (min)'].mean():.0f} min")
print(f"  Avg Time to Clean: {df[df['Section']==12.25]['Time to Clean (min)'].mean():.0f} min")

print(f"\n16.5\" Section ({len(df[df['Section']==16.5])} wells):")
print(f"  Avg BU Cycles: {df[df['Section']==16.5]['BU Cycles'].mean():.2f}")
print(f"  Avg Excess Circ: {df[df['Section']==16.5]['Excess Circulation (min)'].mean():.0f} min")
print(f"  Avg Time to Clean: {df[df['Section']==16.5]['Time to Clean (min)'].mean():.0f} min")

print(f"\nAll Wells ({len(df)} total):")
print(f"  Avg BU Cycles: {df['BU Cycles'].mean():.2f}")
print(f"  Avg Excess Circ: {df['Excess Circulation (min)'].mean():.0f} min")
print(f"  Total Excess Time: {df['Excess Circulation (min)'].sum():.0f} min ({df['Excess Circulation (min)'].sum()/60:.1f} hrs)")

print("\nSlow Cleaners (>3 BU):")
slow = df[df['BU Cycles'] > 3]
for _, row in slow.iterrows():
    print(f"  {row['Well'].split(' - ')[0]}: {row['BU Cycles']:.2f} BU")

print("\nHighest Excess Circulation:")
top_excess = df.nlargest(3, 'Excess Circulation (min)')
for _, row in top_excess.iterrows():
    print(f"  {row['Well'].split(' - ')[0]}: {int(row['Excess Circulation (min)'])} min wasted")

print("\n" + "="*60)
print("Done! All charts saved to script directory.")
