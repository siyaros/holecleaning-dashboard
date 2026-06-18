#!/usr/bin/env python3
"""
CleanSight Multi-Well Analysis Processor
Processes multiple well CSV files and generates comprehensive analysis

Usage: python cleansight_multi_well_processor.py /path/to/data/folder
"""

import os
import sys
import re
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Well issues mapping (from documented problems)
WELL_ISSUES = {
    'HH_1i01': {
        'severity': 3, 
        '17.5': ['pack-off at DPPT', 'backream OOH', 'pressurized shale cavings'],
        '12.25': ['cavings large volumes', 'target circulations', 'pack-off', 'backream OOH']
    },
    'LIZ_3i11': {
        'severity': 1, 
        '17.5': [],
        '12.25': ['target circulations at base cretaceous', 'target circulations below base MTC']
    },
    'LIZ_3P13': {
        'severity': 0,  # BENCHMARK - CLEAN
        '17.5': [],
        '12.25': []
    },
    'PY_1P4': {
        'severity': 1, 
        '17.5': ['increased circulations at TD'],
        '12.25': ['circulation at base tangent', 'circulation at TD']
    },
    'UA_2i02': {
        'severity': 2, 
        '17.5': ['drag in riser', 'pack-off around WB'],
        '12.25': ['drag at Base MTCs', 'additional circulations']
    },
    'UA_3P06': {
        'severity': 1, 
        '17.5': [],
        '12.25': []
    },
    'WT_1P05': {
        'severity': 2, 
        '17.5': ['drag in riser', 'pack-off around WB'],
        '12.25': []
    },
    'WT_1P06': {
        'severity': 2, 
        '17.5': ['drag in riser', 'pack-off around WB'],
        '12.25': ['pack-off below base MTC']
    },
    'WT_1P11': {
        'severity': 1, 
        '17.5': [],
        '12.25': []
    },
    'WT_5P02': {
        'severity': 3, 
        '17.5': [],
        '12.25': ['restrictions', 'pack-off', 'additional circulations', 'cavings', 'Base MTC circulation']
    },
    'YT_1i10': {
        'severity': 3, 
        '17.5': [],
        '12.25': ['cuttings beds', 'additional circulations', 'pack-off', 'Base MTC circulation', 'cavings pumping OOH', 'casing drag', 'pack-offs RIH']
    },
    'YT_1P10': {
        'severity': 3,  # MOST SEVERE
        '17.5': [],
        '12.25': ['80k drag POOH', 'Type II cavings', 'Type III cavings', 'activated WC during circulations', 'casing drag']
    },
    'YT_3P01A': {
        'severity': 3, 
        '17.5': ['drag in riser', 'swabbing POOH'],
        '12.25': ['WC opened at TD', 'additional MTC circulations', '200k drag RIH casing']
    },
    'YT_3P06': {
        'severity': 0,  # IMPROVED - Target circulations worked
        '17.5': [],
        '12.25': ['target circulations implemented', 'no cavings seen']
    },
    'YT_3P12ST': {
        'severity': 2,
        '17.5': ['drag swabbing in riser', 'BHA WB pack-off'],
        '12.25': ['drag RIH casing']
    }
}


def parse_filename(filename):
    """Extract well name and section size from filename."""
    # Pattern: {Well}_{Section}_Data Export...
    # Examples: 
    #   HH_1i01 PH_12.25_Data Export-data-as-joinbyfield-2026-04-23 15_48_19.csv
    #   YT_1P10_17.5_Data Export-data-as-joinbyfield-2026-04-23 15_28_30.csv
    
    name = filename.replace('.csv', '').replace('.CSV', '')
    
    # Try to extract section size
    section_match = re.search(r'[_\s](12\.25|17\.5)[_\s]', name)
    section = section_match.group(1) if section_match else 'Unknown'
    
    # Extract well name (everything before the section)
    if section_match:
        well_part = name[:section_match.start()]
    else:
        well_part = name.split('_Data')[0]
    
    # Clean up well name
    well_name = well_part.strip().replace('_', ' ').strip()
    well_name = re.sub(r'\s+', '_', well_name)
    
    # Normalize common patterns
    well_name = well_name.replace(' PH', '_PH').replace('PH_', 'PH ')
    
    return well_name, section


def read_cleansight_csv(filepath):
    """Read CleanSight CSV file with proper encoding handling."""
    encodings = ['utf-16-le', 'utf-16', 'utf-8', 'cp1252', 'latin1']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(filepath, encoding=encoding, sep='\t', on_bad_lines='skip')
            if len(df.columns) > 5:  # Looks like valid data
                return df
        except:
            continue
    
    # Try comma separator
    for encoding in encodings:
        try:
            df = pd.read_csv(filepath, encoding=encoding, sep=',', on_bad_lines='skip')
            if len(df.columns) > 5:
                return df
        except:
            continue
    
    return None


def clean_column_names(df):
    """Standardize column names."""
    # Remove BOM and special characters
    df.columns = df.columns.str.replace('\ufeff', '').str.replace('"', '').str.strip()
    
    # Standardize common column names
    rename_map = {
        'time': 'Time',
        'CRR (bbl/min)': 'CRR_bbl_min',
        'CRR (lbm/min)': 'CRR_lbm_min',
        'Hole Depth (m)': 'Hole_Depth_m',
        'Bit Depth (m)': 'Bit_Depth_m',
        'Flow In (gpm)': 'Flow_In_gpm',
        'ROP (ft/h)': 'ROP_ft_h',
        'Lag Depth (m)': 'Lag_Depth_m',
        'Lag Time (min)': 'Lag_Time_min',
        'Pump Pressure (psi)': 'Pump_Pressure_psi',
        'ECD (ppg)': 'ECD_ppg',
        'Inclination (degrees)': 'Inclination_deg',
        'RPM': 'RPM',
        'Pit Volume (bbl)': 'Pit_Volume_bbl',
        'GAS': 'Gas',
        'Hook Load (klbf)': 'Hook_Load_klbf',
        'Block Height (m)': 'Block_Height_m',
        'CSD P50 (mm)': 'CSD_P50_mm',
        'UFO Count': 'UFO_Count',
        'Rig Message': 'Rig_Message',
        'Lagged ROP (m/hr)': 'Lagged_ROP_m_hr',
        'Measured TCR (bbl)': 'Measured_TCR_bbl',
        'Theoretical TCR (bbl)': 'Theoretical_TCR_bbl',
        'Theoretical Lag Depth TCR (bbl)': 'Theoretical_Lag_TCR_bbl',
        'Measured TCR (lbm)': 'Measured_TCR_lbm',
        'Theoretical TCR (lbm)': 'Theoretical_TCR_lbm',
        'Theoretical Lag Depth TCR (lbm)': 'Theoretical_Lag_TCR_lbm',
    }
    
    for old, new in rename_map.items():
        if old in df.columns:
            df = df.rename(columns={old: new})
    
    return df


def calculate_well_statistics(df, well_name, section):
    """Calculate summary statistics for a well/section."""
    stats = {
        'Well': well_name,
        'Section': section,
        'Records': len(df),
    }
    
    # Time range
    if 'Time' in df.columns:
        try:
            df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
            stats['Start_Time'] = df['Time'].min()
            stats['End_Time'] = df['Time'].max()
            duration = (df['Time'].max() - df['Time'].min()).total_seconds() / 3600
            stats['Duration_Hours'] = round(duration, 1)
        except:
            stats['Duration_Hours'] = len(df) * 10 / 3600  # Assume 10s intervals
    
    # Depth
    depth_col = 'Hole_Depth_m' if 'Hole_Depth_m' in df.columns else 'Bit_Depth_m'
    if depth_col in df.columns:
        stats['Min_Depth_m'] = df[depth_col].min()
        stats['Max_Depth_m'] = df[depth_col].max()
        stats['Depth_Drilled_m'] = stats['Max_Depth_m'] - stats['Min_Depth_m']
    
    # TCR Analysis
    if 'Measured_TCR_bbl' in df.columns and 'Theoretical_TCR_bbl' in df.columns:
        measured = df['Measured_TCR_bbl'].dropna()
        theoretical = df['Theoretical_TCR_bbl'].dropna()
        
        if len(measured) > 0 and len(theoretical) > 0:
            final_measured = measured.iloc[-1] if len(measured) > 0 else 0
            final_theoretical = theoretical.iloc[-1] if len(theoretical) > 0 else 1
            
            stats['Final_Measured_TCR_bbl'] = round(final_measured, 2)
            stats['Final_Theoretical_TCR_bbl'] = round(final_theoretical, 2)
            stats['TCR_Ratio'] = round(final_measured / final_theoretical, 3) if final_theoretical > 0 else None
            stats['Excess_Volume_bbl'] = round(final_measured - final_theoretical, 2)
            stats['Excess_Percent'] = round((final_measured / final_theoretical - 1) * 100, 1) if final_theoretical > 0 else None
    
    # UFO Analysis
    if 'UFO_Count' in df.columns:
        ufo = df['UFO_Count'].dropna()
        stats['UFO_Total'] = int(ufo.sum())
        stats['UFO_Max_Single'] = int(ufo.max()) if len(ufo) > 0 else 0
        duration_hrs = stats.get('Duration_Hours', 1)
        stats['UFO_Rate_per_hr'] = round(stats['UFO_Total'] / duration_hrs, 2) if duration_hrs > 0 else 0
    
    # CSD Analysis
    if 'CSD_P50_mm' in df.columns:
        csd = df['CSD_P50_mm'].dropna()
        if len(csd) > 0:
            stats['CSD_P50_Mean_mm'] = round(csd.mean(), 1)
            stats['CSD_P50_Max_mm'] = round(csd.max(), 1)
            stats['CSD_P50_Min_mm'] = round(csd.min(), 1)
            stats['CSD_P50_Std_mm'] = round(csd.std(), 2)
    
    # CRR Analysis
    if 'CRR_bbl_min' in df.columns:
        crr = df['CRR_bbl_min'].dropna()
        if len(crr) > 0:
            stats['CRR_Mean_bbl_min'] = round(crr.mean(), 4)
            stats['CRR_Max_bbl_min'] = round(crr.max(), 4)
    
    # ROP Analysis
    rop_col = 'ROP_ft_h' if 'ROP_ft_h' in df.columns else 'Lagged_ROP_m_hr'
    if rop_col in df.columns:
        rop = df[rop_col].dropna()
        if len(rop) > 0:
            stats['ROP_Mean'] = round(rop.mean(), 1)
            stats['ROP_Max'] = round(rop.max(), 1)
            # Drilling efficiency (time with ROP > 0)
            drilling_records = (rop > 5).sum()  # ROP > 5 = actively drilling
            stats['Drilling_Efficiency_Pct'] = round(drilling_records / len(rop) * 100, 1)
    
    # Add issue data
    well_base = well_name.replace('_PH', '').replace(' PH', '').split('_')[0] + '_' + well_name.replace('_PH', '').replace(' PH', '').split('_')[1] if '_' in well_name else well_name
    
    # Try to match well name
    matched_well = None
    for known_well in WELL_ISSUES.keys():
        if known_well.replace('_', '').lower() in well_name.replace('_', '').lower():
            matched_well = known_well
            break
    
    if matched_well:
        stats['Issue_Severity'] = WELL_ISSUES[matched_well]['severity']
        section_key = '12.25' if '12' in section else '17.5'
        stats['Documented_Issues'] = '; '.join(WELL_ISSUES[matched_well].get(section_key, []))
    else:
        stats['Issue_Severity'] = None
        stats['Documented_Issues'] = ''
    
    return stats


def process_all_files(data_folder, output_folder):
    """Process all CSV files in the data folder."""
    
    data_path = Path(data_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all CSV files
    csv_files = list(data_path.glob('*.csv')) + list(data_path.glob('*.CSV'))
    print(f"Found {len(csv_files)} CSV files")
    
    all_data = []
    well_stats = []
    
    for filepath in csv_files:
        print(f"\nProcessing: {filepath.name}")
        
        # Parse filename
        well_name, section = parse_filename(filepath.name)
        print(f"  Well: {well_name}, Section: {section}")
        
        # Read file
        df = read_cleansight_csv(filepath)
        if df is None:
            print(f"  ERROR: Could not read file")
            continue
        
        print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
        
        # Clean columns
        df = clean_column_names(df)
        
        # Add metadata columns
        df['Well'] = well_name
        df['Section'] = section
        df['Source_File'] = filepath.name
        
        # Calculate statistics
        stats = calculate_well_statistics(df, well_name, section)
        well_stats.append(stats)
        
        # Add to master dataset
        all_data.append(df)
        
        print(f"  TCR Ratio: {stats.get('TCR_Ratio', 'N/A')}")
        print(f"  UFO Total: {stats.get('UFO_Total', 'N/A')}")
    
    # Combine all data
    print("\n" + "="*50)
    print("Creating master dataset...")
    
    if all_data:
        master_df = pd.concat(all_data, ignore_index=True)
        master_path = output_path / 'master_cleansight_all_wells.csv'
        master_df.to_csv(master_path, index=False)
        print(f"Master dataset saved: {master_path}")
        print(f"  Total rows: {len(master_df)}")
    
    # Save well statistics
    if well_stats:
        stats_df = pd.DataFrame(well_stats)
        stats_path = output_path / 'well_summary_statistics.csv'
        stats_df.to_csv(stats_path, index=False)
        print(f"Well statistics saved: {stats_path}")
        
        # Create section benchmarks
        create_benchmarks(stats_df, output_path)
    
    return master_df if all_data else None, pd.DataFrame(well_stats) if well_stats else None


def create_benchmarks(stats_df, output_path):
    """Create benchmark statistics by section."""
    
    benchmarks = []
    
    for section in ['12.25', '17.5']:
        section_data = stats_df[stats_df['Section'].str.contains(section, na=False)]
        
        if len(section_data) == 0:
            continue
        
        # Clean wells (severity 0)
        clean_wells = section_data[section_data['Issue_Severity'] == 0]
        
        # All wells
        benchmark = {
            'Section': section,
            'Well_Count': len(section_data),
            'Clean_Well_Count': len(clean_wells),
        }
        
        # TCR benchmarks
        if 'TCR_Ratio' in section_data.columns:
            benchmark['TCR_Ratio_Mean_All'] = round(section_data['TCR_Ratio'].mean(), 3)
            benchmark['TCR_Ratio_Std_All'] = round(section_data['TCR_Ratio'].std(), 3)
            if len(clean_wells) > 0:
                benchmark['TCR_Ratio_Mean_Clean'] = round(clean_wells['TCR_Ratio'].mean(), 3)
        
        # UFO benchmarks
        if 'UFO_Rate_per_hr' in section_data.columns:
            benchmark['UFO_Rate_Mean_All'] = round(section_data['UFO_Rate_per_hr'].mean(), 2)
            if len(clean_wells) > 0:
                benchmark['UFO_Rate_Mean_Clean'] = round(clean_wells['UFO_Rate_per_hr'].mean(), 2)
        
        # CSD benchmarks
        if 'CSD_P50_Mean_mm' in section_data.columns:
            benchmark['CSD_P50_Mean_All'] = round(section_data['CSD_P50_Mean_mm'].mean(), 1)
            if len(clean_wells) > 0:
                benchmark['CSD_P50_Mean_Clean'] = round(clean_wells['CSD_P50_Mean_mm'].mean(), 1)
        
        benchmarks.append(benchmark)
    
    if benchmarks:
        bench_df = pd.DataFrame(benchmarks)
        bench_path = output_path / 'section_benchmarks.csv'
        bench_df.to_csv(bench_path, index=False)
        print(f"Section benchmarks saved: {bench_path}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python cleansight_multi_well_processor.py /path/to/data/folder")
        print("       Output will be saved to /mnt/user-data/outputs/")
        sys.exit(1)
    
    data_folder = sys.argv[1]
    output_folder = '/mnt/user-data/outputs'
    
    if not os.path.exists(data_folder):
        print(f"ERROR: Data folder not found: {data_folder}")
        sys.exit(1)
    
    print("="*50)
    print("CleanSight Multi-Well Analysis Processor")
    print("="*50)
    print(f"Data folder: {data_folder}")
    print(f"Output folder: {output_folder}")
    print("="*50)
    
    master_df, stats_df = process_all_files(data_folder, output_folder)
    
    print("\n" + "="*50)
    print("Processing complete!")
    print("="*50)
    
    if stats_df is not None:
        print("\nWell Summary:")
        print(stats_df[['Well', 'Section', 'TCR_Ratio', 'UFO_Total', 'Issue_Severity']].to_string())


if __name__ == '__main__':
    main()
