"""
TCBU FACTOR DERIVATION SCRIPT - AKERBP 15 WELLS
================================================

This script:
1. Reads cleaned Excel files (output from clean_all_wells_v2.py)
2. Combines zone percentages with BU Cycle data
3. Derives optimal TCBU factors using optimization
4. Outputs comparison and validation results

Requirements:
  pip install pandas numpy scipy openpyxl

Author: DrillDocs / CleanSight
Date: June 2026
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
import os
import glob


#######################################################################
# CONFIGURATION
#######################################################################

# Folder where your cleaned Excel files are (from clean_all_wells_v2.py)
CLEANED_DATA_FOLDER = r'C:\Users\siyar\OneDrive\Documents\NextEnergie\Consultant work\DrillDocs\Analysis\AkerBP\Raw Well Data\16.5\Internal\output'

# Output folder for results
OUTPUT_FOLDER = r'C:\Users\siyar\OneDrive\Documents\NextEnergie\Consultant work\DrillDocs\Analysis\AkerBP\Raw Well Data\16.5\Internal\output'

# BU Cycle data - EXACT well names matching your cleaned files
# Format: 'WellName_Section' : BU_Cycles
BU_CYCLES = {
    # 16.5" Section (5 wells)
    'D-3 Y1_16.5': 2.39,
    'D-6 Y1_16.5': 1.61,
    'D-11_16.5': 3.26,
    'D-12_16.5': 2.40,
    'D-13_16.5': 1.30,
    
    # 12.25" Section (10 wells)
    'D-11_12.25': 1.93,
    'D-11 T2_12.25': 3.15,
    'D-11 T3_12.25': 4.08,
    'D-11 T4_12.25': 2.44,
    'D-11 T5_12.25': 4.77,
    'D-12_12.25': 1.66,
    'D-12 T2_12.25': 4.08,
    'D-12 T3_12.25': 1.00,
    'D-12 T4_12.25': 3.23,
    'D-12 T5_12.25': 1.65,
}


#######################################################################
# FUNCTIONS
#######################################################################

def load_cleaned_data(folder):
    """
    Load zone percentages from cleaned Excel files.
    Looks for files ending in '_CLEANED.xlsx'
    """
    pattern = os.path.join(folder, '*_CLEANED.xlsx')
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No cleaned Excel files found in {folder}")
    
    print(f"   Found {len(files)} cleaned Excel files")
    
    data = []
    
    for filepath in files:
        filename = os.path.basename(filepath)
        
        try:
            # Read the Summary sheet
            df_summary = pd.read_excel(filepath, sheet_name='Summary')
            
            # Extract values
            summary_dict = dict(zip(df_summary['Metric'], df_summary['Value']))
            
            # Get well name and section from filename
            # Format: "D-11 T2_12.25_CLEANED.xlsx"
            base_name = filename.replace('_CLEANED.xlsx', '')  # "D-11 T2_12.25"
            
            # Split by last underscore to get section
            parts = base_name.rsplit('_', 1)
            if len(parts) == 2:
                well_name = parts[0]  # "D-11 T2"
                section = parts[1]     # "12.25"
            else:
                well_name = base_name
                section = str(summary_dict.get('Section', 'Unknown'))
            
            # Key for matching BU Cycles
            key = f"{well_name}_{section}"
            
            data.append({
                'Well': well_name,
                'Section': section,
                'Key': key,
                'pct_0_30': float(summary_dict.get('0-30° Zone (%)', 0)),
                'pct_30_60': float(summary_dict.get('30-60° Zone (%)', 0)),
                'pct_60_plus': float(summary_dict.get('60°+ Zone (%)', 0)),
                'file': filename,
            })
            
            print(f"   ✓ Loaded: {key}")
            
        except Exception as e:
            print(f"   ✗ Error loading {filename}: {e}")
    
    return pd.DataFrame(data)


def match_bu_cycles(df, bu_cycles_dict):
    """
    Match BU Cycle values to wells using the Key column.
    """
    matched = []
    unmatched = []
    
    for _, row in df.iterrows():
        key = row['Key']
        
        # Try exact match
        bu = bu_cycles_dict.get(key)
        
        if bu is not None:
            row_data = row.to_dict()
            row_data['bu_cycles'] = bu
            matched.append(row_data)
            print(f"   ✓ Matched: {key} → BU = {bu}")
        else:
            unmatched.append(key)
            print(f"   ✗ No match: {key}")
    
    if unmatched:
        print(f"\n   ⚠️  Could not match BU Cycles for {len(unmatched)} wells:")
        for u in unmatched:
            print(f"      - {u}")
        print("\n   Please check the BU_CYCLES dictionary keys match your file names.")
    
    return pd.DataFrame(matched)


def predict_bu(pct_0_30, pct_30_60, pct_60_plus, f1, f2, f3):
    """Calculate predicted BU cycles from zone percentages and factors"""
    return (pct_0_30/100 * f1) + (pct_30_60/100 * f2) + (pct_60_plus/100 * f3)


def optimize_factors(df):
    """
    Find optimal TCBU factors that minimize prediction error.
    Uses L-BFGS-B optimization with bounds [1.0, 5.0]
    """
    def total_squared_error(factors):
        f1, f2, f3 = factors
        total = 0
        for _, row in df.iterrows():
            predicted = predict_bu(row['pct_0_30'], row['pct_30_60'], row['pct_60_plus'], f1, f2, f3)
            total += (predicted - row['bu_cycles']) ** 2
        return total
    
    # Starting guess
    initial = [1.5, 2.0, 3.0]
    
    # Bounds
    bounds = [(1.0, 5.0), (1.0, 5.0), (1.0, 5.0)]
    
    # Optimize
    result = minimize(total_squared_error, x0=initial, bounds=bounds, method='L-BFGS-B')
    
    return result.x, result.success, result.nit


def calculate_mae(df, factors):
    """Calculate Mean Absolute Error for a set of factors"""
    f1, f2, f3 = factors
    errors = []
    for _, row in df.iterrows():
        predicted = predict_bu(row['pct_0_30'], row['pct_30_60'], row['pct_60_plus'], f1, f2, f3)
        errors.append(abs(predicted - row['bu_cycles']))
    return np.mean(errors)


#######################################################################
# MAIN
#######################################################################

def main():
    print("="*70)
    print("TCBU FACTOR DERIVATION - AKERBP 15 WELLS")
    print("="*70)
    
    # Check folders
    if not os.path.exists(CLEANED_DATA_FOLDER):
        print(f"\n❌ Cleaned data folder not found: {CLEANED_DATA_FOLDER}")
        print("Please update CLEANED_DATA_FOLDER at the top of this script.")
        return
    
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    
    # Load cleaned data
    print("\n1. Loading cleaned data...")
    df_zones = load_cleaned_data(CLEANED_DATA_FOLDER)
    print(f"\n   Loaded {len(df_zones)} wells")
    
    # Match with BU Cycles
    print("\n2. Matching BU Cycle data...")
    df = match_bu_cycles(df_zones, BU_CYCLES)
    print(f"\n   Matched {len(df)} wells with BU Cycle data")
    
    if len(df) == 0:
        print("\n❌ No wells matched. Please check your BU_CYCLES dictionary.")
        return
    
    if len(df) < 15:
        print(f"\n⚠️  Warning: Only {len(df)} of 15 wells matched!")
    
    # Show input data
    print("\n" + "="*70)
    print("INPUT DATA")
    print("="*70)
    print(f"\n{'Well':<15} {'Section':<8} {'% 0-30':<10} {'% 30-60':<10} {'% 60+':<10} {'BU Cyc':<8}")
    print("-"*66)
    for _, row in df.iterrows():
        print(f"{row['Well']:<15} {row['Section']:<8} {row['pct_0_30']:<10.1f} {row['pct_30_60']:<10.1f} {row['pct_60_plus']:<10.1f} {row['bu_cycles']:<8.2f}")
    
    # Optimize factors
    print("\n" + "="*70)
    print("3. OPTIMIZING FACTORS")
    print("="*70)
    
    factors, converged, iterations = optimize_factors(df)
    f1, f2, f3 = factors
    
    print(f"\n   Converged: {converged}")
    print(f"   Iterations: {iterations}")
    
    print(f"\n   ┌─────────────────────────────────────────┐")
    print(f"   │  EMPIRICAL TCBU FACTORS (AkerBP)        │")
    print(f"   ├─────────────────────────────────────────┤")
    print(f"   │  0-30° Zone:   {f1:.2f}x                    │")
    print(f"   │  30-60° Zone:  {f2:.2f}x                    │")
    print(f"   │  60°+ Zone:    {f3:.2f}x                    │")
    print(f"   └─────────────────────────────────────────┘")
    
    # Validation
    print("\n" + "="*70)
    print("4. VALIDATION: PREDICTED vs ACTUAL")
    print("="*70)
    
    print(f"\n{'Well':<15} {'Section':<8} {'Actual':<10} {'Predicted':<10} {'Error':<10} {'% Error':<10}")
    print("-"*68)
    
    results = []
    for _, row in df.iterrows():
        predicted = predict_bu(row['pct_0_30'], row['pct_30_60'], row['pct_60_plus'], f1, f2, f3)
        error = predicted - row['bu_cycles']
        pct_error = (error / row['bu_cycles']) * 100
        
        print(f"{row['Well']:<15} {row['Section']:<8} {row['bu_cycles']:<10.2f} {predicted:<10.2f} {error:<+10.2f} {pct_error:<+10.1f}%")
        
        results.append({
            'Well': row['Well'],
            'Section': row['Section'],
            'pct_0_30': row['pct_0_30'],
            'pct_30_60': row['pct_30_60'],
            'pct_60_plus': row['pct_60_plus'],
            'bu_cycles': row['bu_cycles'],
            'predicted': round(predicted, 2),
            'error': round(error, 2),
            'pct_error': round(pct_error, 1),
            'file': row['file'],
        })
    
    mae = calculate_mae(df, factors)
    print("-"*68)
    print(f"Mean Absolute Error (MAE): {mae:.2f} BU cycles")
    
    # Compare with other factor sets
    print("\n" + "="*70)
    print("5. COMPARISON WITH OTHER FACTOR SETS")
    print("="*70)
    
    factor_sets = {
        'Literature': [1.50, 2.50, 2.00],
        'BP (Calvin)': [1.60, 2.50, 3.00],
        'Empirical (AkerBP)': [f1, f2, f3],
    }
    
    print(f"\n{'Factor Set':<25} {'0-30°':<10} {'30-60°':<10} {'60°+':<10} {'MAE':<10}")
    print("-"*65)
    
    comparison = []
    for name, fset in factor_sets.items():
        mae_val = calculate_mae(df, fset)
        print(f"{name:<25} {fset[0]:<10.2f} {fset[1]:<10.2f} {fset[2]:<10.2f} {mae_val:<10.2f}")
        comparison.append({
            'Factor Set': name,
            '0-30° Factor': round(fset[0], 2),
            '30-60° Factor': round(fset[1], 2),
            '60°+ Factor': round(fset[2], 2),
            'MAE': round(mae_val, 2),
        })
    
    # Save results to Excel
    print("\n" + "="*70)
    print("6. SAVING RESULTS")
    print("="*70)
    
    output_file = os.path.join(OUTPUT_FOLDER, 'TCBU_Factor_Analysis_15_Wells.xlsx')
    
    df_results = pd.DataFrame(results)
    df_comparison = pd.DataFrame(comparison)
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet 1: Well Analysis
        df_results.to_excel(writer, sheet_name='Well Analysis', index=False)
        
        # Sheet 2: Factor Comparison
        df_comparison.to_excel(writer, sheet_name='Factor Comparison', index=False)
        
        # Sheet 3: Summary
        summary = pd.DataFrame({
            'Item': [
                'TCBU Formula',
                '',
                'Empirical Factors (AkerBP)',
                '  0-30° Zone Factor',
                '  30-60° Zone Factor',
                '  60°+ Zone Factor',
                '',
                'Model Performance',
                '  Mean Absolute Error',
                '  Number of Wells',
                '  16.5" Wells',
                '  12.25" Wells',
            ],
            'Value': [
                f'TCBU = ({f1:.2f} × % 0-30°) + ({f2:.2f} × % 30-60°) + ({f3:.2f} × % 60°+)',
                '',
                '',
                f'{f1:.2f}x',
                f'{f2:.2f}x',
                f'{f3:.2f}x',
                '',
                '',
                f'{mae:.2f} BU cycles',
                str(len(df)),
                str(len(df[df['Section'] == '16.5'])),
                str(len(df[df['Section'] == '12.25'])),
            ]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)
    
    print(f"\n   ✓ Saved: {output_file}")
    
    print("\n" + "="*70)
    print("DONE!")
    print("="*70)
    print(f"""
TCBU Formula:

  TCBU = ({f1:.2f} × % in 0-30°) + ({f2:.2f} × % in 30-60°) + ({f3:.2f} × % in 60°+)

This means:
  - Vertical/low-angle sections (0-30°) need {f1:.2f}x the theoretical BU time
  - Deviated sections (30-60°) need {f2:.2f}x the theoretical BU time  
  - High-angle/horizontal sections (60°+) need {f3:.2f}x the theoretical BU time

Model accuracy: MAE = {mae:.2f} BU cycles across {len(df)} wells
""")


if __name__ == '__main__':
    main()
