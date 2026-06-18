#!/usr/bin/env python3
"""
CleanSight Local Analysis Toolkit
=================================
Run this script locally on your machine to process any CleanSight well data.

USAGE:
    python cleansight_local_analysis_toolkit.py <data_folder> [output_folder]

EXAMPLES:
    python cleansight_local_analysis_toolkit.py "C:/DrillDocs/WellData"
    python cleansight_local_analysis_toolkit.py "C:/DrillDocs/WellData" "C:/DrillDocs/Output"
    
REQUIREMENTS:
    pip install pandas numpy openpyxl

OUTPUT FILES:
    - well_summary_statistics.csv   : Per-well metrics
    - master_cleansight_data.csv    : Combined raw data
    - section_benchmarks.csv        : 17.5" and 12.25" baselines
    - cross_well_comparison.xlsx    : Excel workbook with analysis
    - analysis_report.txt           : Summary findings

Author: DrillDocs Analysis Team
Date: May 2026
"""

import os
import sys
import re
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path


# =============================================================================
# CONFIGURATION - Customize these for your wells
# =============================================================================

# Known well issues - add your wells here
WELL_ISSUES = {
    'HH_1i01': {'severity': 3, '17.5': ['pack-off', 'backream', 'cavings'], '12.25': ['cavings', 'target circ', 'pack-off']},
    'LIZ_3P13': {'severity': 0, '17.5': [], '12.25': []},  # CLEAN BENCHMARK
    'LIZ_3i11': {'severity': 1, '17.5': [], '12.25': ['target circulations']},
    'PY_1P4': {'severity': 1, '17.5': ['increased circulations'], '12.25': ['circulation at TD']},
    'UA_2i02': {'severity': 2, '17.5': ['drag in riser', 'pack-off'], '12.25': ['drag at Base MTCs']},
    'UA_3P06': {'severity': 1, '17.5': [], '12.25': []},
    'WT_1P05': {'severity': 2, '17.5': ['drag in riser', 'pack-off'], '12.25': []},
    'WT_1P06': {'severity': 2, '17.5': ['drag in riser', 'pack-off'], '12.25': ['pack-off below base MTC']},
    'WT_1P11': {'severity': 1, '17.5': [], '12.25': []},
    'WT_5P02': {'severity': 3, '17.5': [], '12.25': ['restrictions', 'pack-off', 'cavings']},
    'YT_1i10': {'severity': 3, '17.5': [], '12.25': ['cuttings beds', 'pack-off', 'cavings']},
    'YT_1P10': {'severity': 3, '17.5': [], '12.25': ['80k drag', 'Type II/III cavings']},
    'YT_3P01A': {'severity': 3, '17.5': ['drag', 'swabbing'], '12.25': ['200k drag RIH casing']},
    'YT_3P06': {'severity': 0, '17.5': [], '12.25': ['target circ - success']},  # IMPROVED
}

# TCR Ratio thresholds
TCR_THRESHOLDS = {
    'normal_low': 0.85,
    'normal_high': 1.05,
    'warning_high': 1.15,
    'alarm_high': 1.30,
    'suspect_low': 0.20,  # Below this = likely data issue
}

# UFO Rate thresholds (per hour)
UFO_THRESHOLDS = {
    'normal': 2.0,
    'elevated': 5.0,
    'high': 10.0,
    'extreme': 15.0,
}


# =============================================================================
# FILE READING FUNCTIONS
# =============================================================================

def parse_filename(filename):
    """Extract well name and section size from filename."""
    name = filename.replace('.csv', '').replace('.CSV', '')
    
    # Detect section size
    if '12_25' in name or '12.25' in name:
        section = '12.25'
    elif '17_5' in name or '17.5' in name:
        section = '17.5'
    else:
        section = 'Unknown'
    
    # Extract well name - look for common patterns
    well_patterns = [
        r'(HH_\w+)',
        r'(LIZ_\w+)',
        r'(PY_\w+)',
        r'(UA_\w+)',
        r'(WT_\w+)',
        r'(YT_\w+)',
    ]
    
    well_name = 'Unknown'
    for pattern in well_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            well_name = match.group(1).upper()
            # Clean up the well name
            well_name = re.sub(r'_?(17_5|12_25|17\.5|12\.25).*', '', well_name)
            break
    
    return well_name, section


def read_cleansight_csv(filepath):
    """
    Read CleanSight CSV file with proper encoding handling.
    CleanSight exports are typically UTF-16-LE with tab separators.
    """
    encodings = ['utf-16-le', 'utf-16', 'utf-8-sig', 'utf-8', 'cp1252', 'latin1']
    separators = ['\t', ',']
    
    for encoding in encodings:
        for sep in separators:
            try:
                df = pd.read_csv(filepath, encoding=encoding, sep=sep, on_bad_lines='skip')
                # Check if it looks like valid data (more than 5 columns)
                if len(df.columns) > 5:
                    return df, encoding, sep
            except Exception:
                continue
    
    return None, None, None


def clean_column_names(df):
    """Standardize column names by removing BOM characters and extra spaces."""
    cleaned = []
    for col in df.columns:
        col = str(col)
        # Remove BOM and special characters
        col = col.replace('\ufeff', '').replace('"', '').strip()
        # Normalize whitespace
        col = re.sub(r'\s+', ' ', col)
        cleaned.append(col)
    df.columns = cleaned
    return df


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def find_column(df, keywords):
    """Find a column by keyword matching (case-insensitive)."""
    cols_lower = {c.lower().replace(' ', '').replace('(', '').replace(')', ''): c for c in df.columns}
    
    for kw in keywords:
        kw_clean = kw.lower().replace(' ', '').replace('(', '').replace(')', '')
        if kw_clean in cols_lower:
            return cols_lower[kw_clean]
        # Partial match
        for col_key, col_name in cols_lower.items():
            if kw_clean in col_key:
                return col_name
    return None


def calculate_well_statistics(df, well_name, section):
    """Calculate comprehensive statistics for a well/section."""
    stats = {
        'Well': well_name,
        'Section': section,
        'Records': len(df),
        'Data_Quality': 'Good',
        'Data_Issues': [],
    }
    
    # ----- TIME ANALYSIS -----
    time_col = find_column(df, ['time', 'datetime', 'timestamp'])
    if time_col:
        try:
            df['_time'] = pd.to_datetime(df[time_col], errors='coerce')
            valid_times = df['_time'].dropna()
            if len(valid_times) > 0:
                stats['Start_Time'] = str(valid_times.min())
                stats['End_Time'] = str(valid_times.max())
                duration = (valid_times.max() - valid_times.min()).total_seconds() / 3600
                stats['Duration_Hours'] = round(duration, 1)
        except:
            pass
    
    if 'Duration_Hours' not in stats:
        # Estimate from record count (10 second intervals)
        stats['Duration_Hours'] = round(len(df) * 10 / 3600, 1)
        stats['Data_Issues'].append('Time parsing failed - estimated duration')
    
    # ----- DEPTH ANALYSIS -----
    depth_col = find_column(df, ['holedepthm', 'holedepth', 'bitdepthm', 'bitdepth'])
    if depth_col:
        depth_data = pd.to_numeric(df[depth_col], errors='coerce').dropna()
        if len(depth_data) > 0:
            stats['Min_Depth_m'] = round(depth_data.min(), 1)
            stats['Max_Depth_m'] = round(depth_data.max(), 1)
            stats['Depth_Drilled_m'] = round(depth_data.max() - depth_data.min(), 1)
    
    # ----- TCR ANALYSIS -----
    measured_col = find_column(df, ['measuredtcrbbl', 'measuredtcr'])
    theoretical_col = find_column(df, ['theoreticaltcrbbl', 'theoreticaltcr'])
    lag_theoretical_col = find_column(df, ['theoreticallagdepthtcrbbl', 'theoreticallagdepthtcr', 'lagdepthtcr'])
    
    tcr_source = 'standard'
    
    if measured_col and theoretical_col:
        measured = pd.to_numeric(df[measured_col], errors='coerce').dropna()
        theoretical = pd.to_numeric(df[theoretical_col], errors='coerce').dropna()
        
        if len(measured) > 0 and len(theoretical) > 0:
            final_m = measured.iloc[-1]
            final_t = theoretical.iloc[-1]
            
            stats['Measured_TCR_bbl'] = round(final_m, 2)
            stats['Theoretical_TCR_bbl'] = round(final_t, 2)
            
            # Check for data issues
            if final_t > 3000 and final_m < 1500:
                stats['Data_Issues'].append(f'Theoretical TCR suspiciously high ({final_t:.0f} bbl) - may include previous sections')
                stats['Data_Quality'] = 'Suspect'
                
                # Try using Lag Depth TCR instead
                if lag_theoretical_col:
                    lag_theoretical = pd.to_numeric(df[lag_theoretical_col], errors='coerce').dropna()
                    if len(lag_theoretical) > 0:
                        final_lag_t = lag_theoretical.iloc[-1]
                        if final_lag_t > 0 and final_lag_t < 3000:
                            stats['Theoretical_TCR_bbl_Corrected'] = round(final_lag_t, 2)
                            stats['TCR_Ratio_Corrected'] = round(final_m / final_lag_t, 3)
                            tcr_source = 'lag_depth_corrected'
            
            if final_t > 0:
                stats['TCR_Ratio'] = round(final_m / final_t, 3)
                stats['Excess_Volume_bbl'] = round(final_m - final_t, 2)
                stats['Excess_Percent'] = round((final_m / final_t - 1) * 100, 1)
            
            stats['TCR_Source'] = tcr_source
    
    # ----- UFO ANALYSIS -----
    ufo_col = find_column(df, ['ufocount', 'ufo'])
    if ufo_col:
        ufo = pd.to_numeric(df[ufo_col], errors='coerce').dropna()
        if len(ufo) > 0:
            stats['UFO_Total'] = int(ufo.sum())
            stats['UFO_Max_Single'] = int(ufo.max())
            duration = stats.get('Duration_Hours', 1)
            if duration > 0:
                stats['UFO_Rate_per_hr'] = round(stats['UFO_Total'] / duration, 2)
            
            # Classify UFO severity
            rate = stats.get('UFO_Rate_per_hr', 0)
            if rate >= UFO_THRESHOLDS['extreme']:
                stats['UFO_Severity'] = 'EXTREME'
            elif rate >= UFO_THRESHOLDS['high']:
                stats['UFO_Severity'] = 'HIGH'
            elif rate >= UFO_THRESHOLDS['elevated']:
                stats['UFO_Severity'] = 'ELEVATED'
            else:
                stats['UFO_Severity'] = 'NORMAL'
    
    # ----- CSD ANALYSIS -----
    csd_col = find_column(df, ['csdp50mm', 'csdp50', 'cuttingsizedistribution'])
    if csd_col:
        csd = pd.to_numeric(df[csd_col], errors='coerce').dropna()
        if len(csd) > 0:
            stats['CSD_P50_Mean_mm'] = round(csd.mean(), 1)
            stats['CSD_P50_Max_mm'] = round(csd.max(), 1)
            stats['CSD_P50_Std_mm'] = round(csd.std(), 2)
    
    # ----- CRR ANALYSIS -----
    crr_col = find_column(df, ['crrbblmin', 'crr'])
    if crr_col:
        crr = pd.to_numeric(df[crr_col], errors='coerce').dropna()
        if len(crr) > 0:
            stats['CRR_Mean'] = round(crr.mean(), 4)
            stats['CRR_Max'] = round(crr.max(), 4)
    
    # ----- ROP & DRILLING EFFICIENCY -----
    rop_col = find_column(df, ['ropfth', 'rop', 'laggedropmhr'])
    if rop_col:
        rop = pd.to_numeric(df[rop_col], errors='coerce').dropna()
        if len(rop) > 0:
            stats['ROP_Mean'] = round(rop.mean(), 1)
            stats['ROP_Max'] = round(rop.max(), 1)
            # Drilling time = ROP > 5 (ft/hr or m/hr)
            drilling_time = (rop > 5).sum()
            stats['Drilling_Efficiency_Pct'] = round(drilling_time / len(rop) * 100, 1)
    
    # ----- ADD KNOWN ISSUES -----
    well_base = well_name.replace('_PH', '').split('_')[0] + '_' + well_name.replace('_PH', '').split('_')[1] if '_' in well_name else well_name
    
    for known_well in WELL_ISSUES.keys():
        if known_well.replace('_', '').lower() in well_name.replace('_', '').lower():
            stats['Issue_Severity'] = WELL_ISSUES[known_well]['severity']
            section_key = '12.25' if '12' in section else '17.5'
            stats['Documented_Issues'] = '; '.join(WELL_ISSUES[known_well].get(section_key, []))
            break
    
    # Convert data issues list to string
    stats['Data_Issues'] = '; '.join(stats['Data_Issues']) if stats['Data_Issues'] else ''
    
    return stats


def classify_tcr(ratio):
    """Classify TCR ratio into categories."""
    if ratio is None:
        return 'NO_DATA'
    if ratio < TCR_THRESHOLDS['suspect_low']:
        return 'SUSPECT_DATA'
    if ratio < TCR_THRESHOLDS['normal_low']:
        return 'UNDER_RECOVERY'
    if ratio <= TCR_THRESHOLDS['normal_high']:
        return 'NORMAL'
    if ratio <= TCR_THRESHOLDS['warning_high']:
        return 'ELEVATED'
    if ratio <= TCR_THRESHOLDS['alarm_high']:
        return 'WARNING'
    return 'ALARM'


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_folder(data_folder, output_folder=None):
    """Process all CSV files in a folder."""
    
    data_path = Path(data_folder)
    if output_folder:
        output_path = Path(output_folder)
    else:
        output_path = data_path / 'CleanSight_Analysis_Output'
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("CleanSight Multi-Well Analysis Toolkit")
    print("=" * 70)
    print(f"Data folder:   {data_path}")
    print(f"Output folder: {output_path}")
    print("=" * 70)
    
    # Find CSV files
    csv_files = list(data_path.glob('*.csv')) + list(data_path.glob('*.CSV'))
    
    # Filter to well data files only
    well_files = []
    for f in csv_files:
        fname = f.name.upper()
        if any(prefix in fname for prefix in ['HH_', 'LIZ_', 'PY_', 'UA_', 'WT_', 'YT_']):
            well_files.append(f)
    
    print(f"\nFound {len(well_files)} well data files\n")
    
    if not well_files:
        print("ERROR: No well data files found!")
        print("Expected filenames containing: HH_, LIZ_, PY_, UA_, WT_, YT_")
        return
    
    # Process each file
    all_stats = []
    all_data = []
    
    for filepath in sorted(well_files):
        print(f"Processing: {filepath.name}")
        
        well, section = parse_filename(filepath.name)
        print(f"  → Well: {well}, Section: {section}\"")
        
        df, encoding, sep = read_cleansight_csv(filepath)
        if df is None:
            print(f"  ✗ ERROR: Could not read file")
            continue
        
        df = clean_column_names(df)
        print(f"  → Rows: {len(df):,}, Columns: {len(df.columns)}")
        
        # Calculate statistics
        stats = calculate_well_statistics(df, well, section)
        all_stats.append(stats)
        
        # Add metadata for master dataset
        df['_Well'] = well
        df['_Section'] = section
        df['_Source_File'] = filepath.name
        all_data.append(df)
        
        # Print key metrics
        tcr = stats.get('TCR_Ratio', 'N/A')
        tcr_corrected = stats.get('TCR_Ratio_Corrected', '')
        ufo = stats.get('UFO_Total', 'N/A')
        quality = stats.get('Data_Quality', 'Unknown')
        
        print(f"  → TCR Ratio: {tcr}", end='')
        if tcr_corrected:
            print(f" (Corrected: {tcr_corrected})", end='')
        print(f", UFO Total: {ufo}, Quality: {quality}")
        
        if stats.get('Data_Issues'):
            print(f"  ⚠ Issues: {stats['Data_Issues']}")
        print()
    
    # Create output files
    print("=" * 70)
    print("Creating output files...")
    print("=" * 70)
    
    # 1. Well Summary Statistics
    stats_df = pd.DataFrame(all_stats)
    stats_df = stats_df.sort_values(['Well', 'Section'])
    
    # Add TCR classification
    stats_df['TCR_Classification'] = stats_df['TCR_Ratio'].apply(classify_tcr)
    
    stats_path = output_path / 'well_summary_statistics.csv'
    stats_df.to_csv(stats_path, index=False)
    print(f"✓ Well statistics: {stats_path}")
    
    # 2. Master Dataset
    if all_data:
        master_df = pd.concat(all_data, ignore_index=True)
        master_path = output_path / 'master_cleansight_data.csv'
        master_df.to_csv(master_path, index=False)
        print(f"✓ Master dataset: {master_path} ({len(master_df):,} rows)")
    
    # 3. Section Benchmarks
    create_benchmarks(stats_df, output_path)
    
    # 4. Excel Workbook
    create_excel_workbook(stats_df, output_path)
    
    # 5. Analysis Report
    create_report(stats_df, output_path)
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nOutput files saved to: {output_path}")
    
    return stats_df


def create_benchmarks(stats_df, output_path):
    """Create section benchmark statistics."""
    benchmarks = []
    
    for section in ['12.25', '17.5']:
        section_data = stats_df[stats_df['Section'] == section].copy()
        if len(section_data) == 0:
            continue
        
        # Only use wells with good data quality for benchmarks
        good_data = section_data[section_data['Data_Quality'] == 'Good']
        clean_wells = good_data[good_data['Issue_Severity'] == 0]
        problem_wells = good_data[good_data['Issue_Severity'] >= 2]
        
        bench = {
            'Section': section,
            'Total_Wells': len(section_data),
            'Good_Data_Wells': len(good_data),
            'Clean_Wells': len(clean_wells),
            'Problem_Wells': len(problem_wells),
        }
        
        # TCR benchmarks (from good data only)
        if 'TCR_Ratio' in good_data.columns and len(good_data) > 0:
            tcr_data = good_data['TCR_Ratio'].dropna()
            if len(tcr_data) > 0:
                bench['TCR_Ratio_Mean'] = round(tcr_data.mean(), 3)
                bench['TCR_Ratio_Std'] = round(tcr_data.std(), 3)
                bench['TCR_Ratio_Min'] = round(tcr_data.min(), 3)
                bench['TCR_Ratio_Max'] = round(tcr_data.max(), 3)
            
            if len(clean_wells) > 0:
                clean_tcr = clean_wells['TCR_Ratio'].dropna()
                if len(clean_tcr) > 0:
                    bench['TCR_Ratio_Clean_Mean'] = round(clean_tcr.mean(), 3)
        
        # UFO benchmarks
        if 'UFO_Rate_per_hr' in good_data.columns:
            ufo_data = good_data['UFO_Rate_per_hr'].dropna()
            if len(ufo_data) > 0:
                bench['UFO_Rate_Mean'] = round(ufo_data.mean(), 2)
                bench['UFO_Rate_Max'] = round(ufo_data.max(), 2)
        
        benchmarks.append(bench)
    
    if benchmarks:
        bench_df = pd.DataFrame(benchmarks)
        bench_path = output_path / 'section_benchmarks.csv'
        bench_df.to_csv(bench_path, index=False)
        print(f"✓ Section benchmarks: {bench_path}")


def create_excel_workbook(stats_df, output_path):
    """Create Excel workbook with multiple sheets."""
    try:
        excel_path = output_path / 'cross_well_comparison.xlsx'
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Sheet 1: Full summary
            stats_df.to_excel(writer, sheet_name='All Wells', index=False)
            
            # Sheet 2: 17.5" section only
            section_175 = stats_df[stats_df['Section'] == '17.5']
            if len(section_175) > 0:
                section_175.to_excel(writer, sheet_name='17.5 Section', index=False)
            
            # Sheet 3: 12.25" section only
            section_1225 = stats_df[stats_df['Section'] == '12.25']
            if len(section_1225) > 0:
                section_1225.to_excel(writer, sheet_name='12.25 Section', index=False)
            
            # Sheet 4: Problem wells only
            problems = stats_df[stats_df['Issue_Severity'] >= 2]
            if len(problems) > 0:
                problems.to_excel(writer, sheet_name='Problem Wells', index=False)
            
            # Sheet 5: Clean wells (benchmarks)
            clean = stats_df[stats_df['Issue_Severity'] == 0]
            if len(clean) > 0:
                clean.to_excel(writer, sheet_name='Clean Wells', index=False)
        
        print(f"✓ Excel workbook: {excel_path}")
    except ImportError:
        print("⚠ openpyxl not installed - skipping Excel output")
        print("  Install with: pip install openpyxl")


def create_report(stats_df, output_path):
    """Create text analysis report."""
    report_path = output_path / 'analysis_report.txt'
    
    with open(report_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("CLEANSIGHT MULTI-WELL ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")
        
        # Summary
        f.write("SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total wells analyzed: {stats_df['Well'].nunique()}\n")
        f.write(f"Total well/section combinations: {len(stats_df)}\n")
        
        good_data = stats_df[stats_df['Data_Quality'] == 'Good']
        f.write(f"Good quality data: {len(good_data)} / {len(stats_df)}\n")
        
        suspect_data = stats_df[stats_df['Data_Quality'] == 'Suspect']
        if len(suspect_data) > 0:
            f.write(f"Suspect data quality: {len(suspect_data)}\n")
        f.write("\n")
        
        # Data quality issues
        if len(suspect_data) > 0:
            f.write("DATA QUALITY ISSUES\n")
            f.write("-" * 40 + "\n")
            for _, row in suspect_data.iterrows():
                f.write(f"  {row['Well']} {row['Section']}\": {row.get('Data_Issues', 'Unknown')}\n")
            f.write("\n")
        
        # TCR Summary
        f.write("TCR RATIO SUMMARY (Good Data Only)\n")
        f.write("-" * 40 + "\n")
        
        for section in ['17.5', '12.25']:
            section_data = good_data[good_data['Section'] == section]
            if len(section_data) > 0:
                tcr_data = section_data['TCR_Ratio'].dropna()
                if len(tcr_data) > 0:
                    f.write(f"\n{section}\" Section:\n")
                    f.write(f"  Mean: {tcr_data.mean():.3f}\n")
                    f.write(f"  Std:  {tcr_data.std():.3f}\n")
                    f.write(f"  Min:  {tcr_data.min():.3f}\n")
                    f.write(f"  Max:  {tcr_data.max():.3f}\n")
        
        f.write("\n")
        
        # High TCR (over-recovery) wells
        high_tcr = good_data[good_data['TCR_Ratio'] > TCR_THRESHOLDS['warning_high']]
        if len(high_tcr) > 0:
            f.write("HIGH TCR RATIO WELLS (>1.15 = Over-recovery)\n")
            f.write("-" * 40 + "\n")
            for _, row in high_tcr.sort_values('TCR_Ratio', ascending=False).iterrows():
                f.write(f"  {row['Well']} {row['Section']}\": TCR={row['TCR_Ratio']:.3f} (+{row.get('Excess_Percent', 0):.1f}%)\n")
            f.write("\n")
        
        # UFO Summary
        f.write("UFO RATE SUMMARY\n")
        f.write("-" * 40 + "\n")
        high_ufo = stats_df[stats_df['UFO_Rate_per_hr'] > UFO_THRESHOLDS['elevated']].sort_values('UFO_Rate_per_hr', ascending=False)
        if len(high_ufo) > 0:
            for _, row in high_ufo.iterrows():
                f.write(f"  {row['Well']} {row['Section']}\": {row['UFO_Rate_per_hr']:.1f}/hr ({row.get('UFO_Severity', 'N/A')})\n")
        f.write("\n")
        
        # Recommendations
        f.write("RECOMMENDATIONS\n")
        f.write("-" * 40 + "\n")
        f.write("1. Review wells with 'Suspect' data quality - Theoretical TCR may include\n")
        f.write("   previous sections. Consider using 'Theoretical Lag Depth TCR' instead.\n\n")
        f.write("2. High TCR wells (>1.15) indicate over-recovery, suggesting:\n")
        f.write("   - Hole enlargement / washout\n")
        f.write("   - Cavings from unstable formations\n")
        f.write("   - Inadequate hole cleaning during earlier operations\n\n")
        f.write("3. Elevated UFO rates (>5/hr) correlate with:\n")
        f.write("   - Pack-off events\n")
        f.write("   - Cavings incidents\n")
        f.write("   - Casing run difficulties\n\n")
    
    print(f"✓ Analysis report: {report_path}")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nERROR: Please provide the data folder path")
        print("\nExample:")
        print('  python cleansight_local_analysis_toolkit.py "C:/DrillDocs/WellData"')
        sys.exit(1)
    
    data_folder = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(data_folder):
        print(f"ERROR: Folder not found: {data_folder}")
        sys.exit(1)
    
    process_folder(data_folder, output_folder)


if __name__ == '__main__':
    main()
