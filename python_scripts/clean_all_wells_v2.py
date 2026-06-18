"""
CLEAN INCLINATION DATA - AUTOMATIC WELL DETECTION
==================================================

This script:
1. Scans a folder for all CSV files
2. Extracts well name and section size from filename
3. Cleans the inclination data
4. Outputs Excel files for verification

Filename format expected:
  "D-11 T5 - 12.25-2026-04-20 18_32_31.csv"
   ^^^^^^^   ^^^^^
   Well name  Section size

Author: DrillDocs / CleanSight
Date: June 2026
"""

import pandas as pd
import numpy as np
import os
import re
import glob


#######################################################################
# CONFIGURATION - UPDATE THESE PATHS FOR YOUR LOCAL MACHINE
#######################################################################

# Folder where your CSV files are located
INPUT_FOLDER = r'C:\Users\YourName\Path\To\CSV\Files'  # <-- CHANGE THIS

# Folder where you want the cleaned Excel files saved
OUTPUT_FOLDER = r'C:\Users\YourName\Path\To\Output'  # <-- CHANGE THIS


#######################################################################
# DATA CLEANING FUNCTIONS
#######################################################################

def get_consistent_inclination(group):
    """
    For a group of readings at the same depth, return the most consistent value.
    Filters out garbage readings (sensor errors during circulation).
    """
    values = group['Inclination (degrees)']
    
    if len(values) == 1:
        return values.iloc[0]
    
    rounded = values.round(0)
    mode_rounded = rounded.mode()
    
    if len(mode_rounded) == 0:
        return values.median()
    
    dominant = mode_rounded.iloc[0]
    mask = (values >= dominant - 5) & (values <= dominant + 5)
    filtered = values[mask]
    
    if len(filtered) == 0:
        return values.median()
    
    return filtered.median()


def find_column(df, patterns):
    """Find a column that matches any of the given patterns (case-insensitive)"""
    for col in df.columns:
        col_lower = col.lower().strip()
        for pattern in patterns:
            if pattern.lower() in col_lower:
                return col
    return None


def detect_encoding_and_separator(filepath):
    """
    Try different encoding/separator combinations to read the file.
    Returns (encoding, separator) that works.
    """
    combinations = [
        ('utf-8', ','),
        ('utf-8', '\t'),
        ('utf-8', ';'),
        ('utf-16-le', '\t'),
        ('utf-16-le', ','),
        ('utf-16', '\t'),
        ('cp1252', ','),
        ('cp1252', '\t'),
        ('latin-1', ','),
    ]
    
    for encoding, sep in combinations:
        try:
            df = pd.read_csv(filepath, encoding=encoding, sep=sep, nrows=5)
            # Check if we got reasonable number of columns (more than 1)
            if len(df.columns) > 1:
                # Check if we can find the columns we need
                depth_col = find_column(df, ['hole depth', 'depth'])
                inc_col = find_column(df, ['inclination', 'inc'])
                if depth_col and inc_col:
                    return encoding, sep
        except:
            continue
    
    return None, None


def parse_filename(filename):
    """
    Extract well name and section size from filename.
    
    Examples:
      "D-11 T5 - 12.25-2026-04-20 18_32_31.csv" -> ("D-11 T5", "12.25")
      "D-13 - 16.5-06-01 19_20_31.csv" -> ("D-13", "16.5")
      "D-6 Y1 - 16.5-2026-06-01 18_25_54.csv" -> ("D-6 Y1", "16.5")
    """
    # Remove extension
    name = os.path.splitext(filename)[0]
    
    # Pattern: "Well Name - Section-Date Time"
    # Look for section size (12.25, 16.5, 17.5, etc.)
    section_match = re.search(r'(\d+\.?\d*)\s*[-_]?\s*\d{2,4}[-_]', name)
    
    if section_match:
        section = section_match.group(1)
        # Everything before the section is the well name
        well_part = name[:section_match.start()].strip()
        # Remove trailing dash/space
        well_name = re.sub(r'[\s\-_]+$', '', well_part)
    else:
        # Fallback: try to find section size anywhere
        section_match2 = re.search(r'(12\.25|16\.5|17\.5|8\.5)', name)
        if section_match2:
            section = section_match2.group(1)
            well_name = name.split('-')[0].strip()
        else:
            section = 'Unknown'
            well_name = name.split('-')[0].strip()
    
    return well_name, section


def clean_well_data(filepath, encoding, separator):
    """
    Clean inclination data for a single well.
    """
    df = pd.read_csv(filepath, encoding=encoding, sep=separator)
    
    depth_col = find_column(df, ['hole depth', 'depth'])
    inc_col = find_column(df, ['inclination', 'inc'])
    
    if depth_col is None:
        raise ValueError(f"Could not find Hole Depth column. Available: {list(df.columns)}")
    if inc_col is None:
        raise ValueError(f"Could not find Inclination column. Available: {list(df.columns)}")
    
    stats = {
        'raw_rows': len(df),
        'depth_col': depth_col,
        'inc_col': inc_col,
    }
    
    df_two = df[[depth_col, inc_col]].copy()
    df_two.columns = ['Hole Depth (m)', 'Inclination (degrees)']
    
    # Convert to numeric (in case of string values)
    df_two['Hole Depth (m)'] = pd.to_numeric(df_two['Hole Depth (m)'], errors='coerce')
    df_two['Inclination (degrees)'] = pd.to_numeric(df_two['Inclination (degrees)'], errors='coerce')
    
    df_no_nan = df_two.dropna()
    stats['after_nan_removal'] = len(df_no_nan)
    stats['nan_removed'] = stats['raw_rows'] - stats['after_nan_removal']
    
    df_valid = df_no_nan[df_no_nan['Hole Depth (m)'] > 0]
    df_valid = df_valid[df_valid['Inclination (degrees)'] >= 0]
    df_valid = df_valid[df_valid['Inclination (degrees)'] <= 90]
    
    # Remove outlier depths (> 5000m is clearly wrong)
    df_valid = df_valid[df_valid['Hole Depth (m)'] < 5000]
    
    stats['after_invalid_removal'] = len(df_valid)
    stats['invalid_removed'] = stats['after_nan_removal'] - stats['after_invalid_removal']
    
    if len(df_valid) == 0:
        raise ValueError("No valid data after cleaning")
    
    df_by_depth = df_valid.groupby('Hole Depth (m)').apply(get_consistent_inclination)
    df_by_depth = df_by_depth.reset_index()
    df_by_depth.columns = ['Hole Depth (m)', 'Inclination (degrees)']
    df_by_depth = df_by_depth.sort_values('Hole Depth (m)').reset_index(drop=True)
    
    stats['unique_depths'] = len(df_by_depth)
    stats['min_depth'] = df_by_depth['Hole Depth (m)'].min()
    stats['max_depth'] = df_by_depth['Hole Depth (m)'].max()
    stats['min_inc'] = df_by_depth['Inclination (degrees)'].min()
    stats['max_inc'] = df_by_depth['Inclination (degrees)'].max()
    
    return df_by_depth, stats


def calculate_zones(df_clean):
    """
    Calculate zone percentages from cleaned inclination profile.
    """
    depths = df_clean['Hole Depth (m)'].values
    incs = df_clean['Inclination (degrees)'].values
    
    total_length = 0
    zone_0_30 = 0
    zone_30_60 = 0
    zone_60_plus = 0
    
    intervals = []
    
    for i in range(1, len(depths)):
        length = depths[i] - depths[i-1]
        if length <= 0:
            continue
        
        avg_inc = (incs[i-1] + incs[i]) / 2
        total_length += length
        
        if avg_inc < 30:
            zone_0_30 += length
            zone = '0-30°'
        elif avg_inc < 60:
            zone_30_60 += length
            zone = '30-60°'
        else:
            zone_60_plus += length
            zone = '60°+'
        
        intervals.append({
            'From Depth (m)': depths[i-1],
            'To Depth (m)': depths[i],
            'Interval (m)': length,
            'Inc Start (°)': round(incs[i-1], 2),
            'Inc End (°)': round(incs[i], 2),
            'Avg Inc (°)': round(avg_inc, 2),
            'Zone': zone
        })
    
    df_intervals = pd.DataFrame(intervals)
    
    zones = {
        'total_length': total_length,
        'zone_0_30_m': zone_0_30,
        'zone_30_60_m': zone_30_60,
        'zone_60_plus_m': zone_60_plus,
        'pct_0_30': (zone_0_30 / total_length * 100) if total_length > 0 else 0,
        'pct_30_60': (zone_30_60 / total_length * 100) if total_length > 0 else 0,
        'pct_60_plus': (zone_60_plus / total_length * 100) if total_length > 0 else 0,
    }
    
    return zones, df_intervals


#######################################################################
# MAIN SCRIPT
#######################################################################

def main():
    print("="*70)
    print("CLEANING INCLINATION DATA - AUTOMATIC WELL DETECTION")
    print("="*70)
    
    # Check input folder exists
    if not os.path.exists(INPUT_FOLDER):
        print(f"\n❌ ERROR: Input folder not found: {INPUT_FOLDER}")
        print("Please update INPUT_FOLDER at the top of this script.")
        return
    
    # Create output folder if needed
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"\nCreated output folder: {OUTPUT_FOLDER}")
    
    # Find all CSV files
    csv_files = glob.glob(os.path.join(INPUT_FOLDER, '*.csv'))
    
    if not csv_files:
        print(f"\n❌ No CSV files found in: {INPUT_FOLDER}")
        return
    
    print(f"\nFound {len(csv_files)} CSV files")
    
    all_results = []
    
    for filepath in csv_files:
        filename = os.path.basename(filepath)
        well_name, section = parse_filename(filename)
        
        print(f"\n{'─'*70}")
        print(f"File: {filename}")
        print(f"Well: {well_name} | Section: {section}\"")
        print(f"{'─'*70}")
        
        try:
            # Detect encoding
            encoding, separator = detect_encoding_and_separator(filepath)
            
            if encoding is None:
                print(f"  ❌ Could not detect file encoding/format")
                continue
            
            print(f"  Format: encoding={encoding}, separator={'TAB' if separator == chr(9) else separator}")
            
            # Clean the data
            df_clean, stats = clean_well_data(filepath, encoding, separator)
            
            # Calculate zones
            zones, df_intervals = calculate_zones(df_clean)
            
            # Print summary
            print(f"  Raw rows:        {stats['raw_rows']:,}")
            print(f"  NaN removed:     {stats['nan_removed']:,}")
            print(f"  Invalid removed: {stats['invalid_removed']:,}")
            print(f"  Unique depths:   {stats['unique_depths']:,}")
            print(f"  Depth range:     {stats['min_depth']:.0f}m - {stats['max_depth']:.0f}m")
            print(f"  Inc range:       {stats['min_inc']:.1f}° - {stats['max_inc']:.1f}°")
            print(f"  Zones:")
            print(f"    0-30°:  {zones['zone_0_30_m']:.0f}m ({zones['pct_0_30']:.1f}%)")
            print(f"    30-60°: {zones['zone_30_60_m']:.0f}m ({zones['pct_30_60']:.1f}%)")
            print(f"    60°+:   {zones['zone_60_plus_m']:.0f}m ({zones['pct_60_plus']:.1f}%)")
            
            # Save individual Excel file
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', f"{well_name}_{section}")
            output_file = os.path.join(OUTPUT_FOLDER, f'{safe_name}_CLEANED.xlsx')
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df_clean.to_excel(writer, sheet_name='Inclination Profile', index=False)
                df_intervals.to_excel(writer, sheet_name='Interval Calculations', index=False)
                
                summary = pd.DataFrame({
                    'Metric': [
                        'Well Name',
                        'Section',
                        'Source File',
                        'Raw Rows',
                        'NaN Removed',
                        'Invalid Removed',
                        'Unique Depths',
                        'Min Depth (m)',
                        'Max Depth (m)',
                        'Min Inclination (°)',
                        'Max Inclination (°)',
                        'Total Length (m)',
                        '0-30° Zone (m)',
                        '0-30° Zone (%)',
                        '30-60° Zone (m)',
                        '30-60° Zone (%)',
                        '60°+ Zone (m)',
                        '60°+ Zone (%)',
                    ],
                    'Value': [
                        well_name,
                        section,
                        filename,
                        stats['raw_rows'],
                        stats['nan_removed'],
                        stats['invalid_removed'],
                        stats['unique_depths'],
                        stats['min_depth'],
                        stats['max_depth'],
                        round(stats['min_inc'], 2),
                        round(stats['max_inc'], 2),
                        round(zones['total_length'], 1),
                        round(zones['zone_0_30_m'], 1),
                        round(zones['pct_0_30'], 1),
                        round(zones['zone_30_60_m'], 1),
                        round(zones['pct_30_60'], 1),
                        round(zones['zone_60_plus_m'], 1),
                        round(zones['pct_60_plus'], 1),
                    ]
                })
                summary.to_excel(writer, sheet_name='Summary', index=False)
            
            print(f"  ✓ Saved: {output_file}")
            
            all_results.append({
                'Well': well_name,
                'Section': section,
                'Source File': filename,
                'Raw Rows': stats['raw_rows'],
                'Unique Depths': stats['unique_depths'],
                'Min Depth (m)': round(stats['min_depth'], 0),
                'Max Depth (m)': round(stats['max_depth'], 0),
                'Max Inc (°)': round(stats['max_inc'], 1),
                'Total Length (m)': round(zones['total_length'], 0),
                '% 0-30°': round(zones['pct_0_30'], 1),
                '% 30-60°': round(zones['pct_30_60'], 1),
                '% 60°+': round(zones['pct_60_plus'], 1),
            })
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            continue
    
    # Save summary
    if all_results:
        df_all = pd.DataFrame(all_results)
        summary_file = os.path.join(OUTPUT_FOLDER, 'ALL_WELLS_SUMMARY.xlsx')
        df_all.to_excel(summary_file, index=False)
        
        print(f"\n{'='*70}")
        print(f"✓ SUMMARY SAVED: {summary_file}")
        print(f"{'='*70}")
        
        print("\nAll Wells Summary:")
        print(df_all.to_string(index=False))
    
    print("\n" + "="*70)
    print("DONE! Check the output folder for Excel files to verify.")
    print("="*70)


if __name__ == '__main__':
    main()
