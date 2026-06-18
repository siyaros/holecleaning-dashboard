"""
CLEAN INCLINATION DATA FROM CLEANSIGHT CSV EXPORTS
===================================================

This script extracts and cleans the Hole Depth and Inclination data
from CleanSight CSV exports.

Problem solved:
  - Raw data has multiple readings at the same depth (recorded over time)
  - Some readings are garbage (sensor errors during circulation at TD)
  - Example: At depth 1823m, there might be 460 readings at ~0° (garbage)
    and 690 readings at ~47° (valid)

Solution:
  - For each depth, find the "dominant" inclination value (most common)
  - Keep only values within ±5° of the dominant value
  - Take the median of those filtered values

Usage:
  1. Change the 'filepath' variable to your CSV file
  2. Change 'encoding' if needed (utf-8 for 16.5" files, utf-16-le for 12.25")
  3. Run the script
  4. The clean data is in 'df_by_depth' DataFrame
"""

import pandas as pd
import numpy as np


#######################################################################
# CONFIGURATION - CHANGE THESE FOR YOUR FILE
#######################################################################

# Your CSV file path
filepath = '/mnt/project/Data_Export__Rig_Data___25_2D11__16_5_dataasjoinbyfield20260601_18_25_17.csv'

# Encoding settings:
#   - For 16.5" section files: encoding='utf-8', separator=','
#   - For 12.25" section files: encoding='utf-16-le', separator='\t'
encoding = 'utf-8'
separator = ','


#######################################################################
# STEP 1: READ THE CSV FILE
#######################################################################

print("Step 1: Reading CSV file...")
df = pd.read_csv(filepath, encoding=encoding, sep=separator)
print(f"  Loaded {len(df)} rows")


#######################################################################
# STEP 2: EXTRACT ONLY THE 2 COLUMNS WE NEED
#######################################################################

print("\nStep 2: Extracting Hole Depth and Inclination columns...")
df_two_columns = df[['Hole Depth (m)', 'Inclination (degrees)']]
print(f"  Extracted 2 columns")


#######################################################################
# STEP 3: REMOVE ROWS WITH MISSING DATA (NaN)
#######################################################################

print("\nStep 3: Removing rows with missing data...")
before = len(df_two_columns)
df_no_nan = df_two_columns.dropna()
after = len(df_no_nan)
print(f"  Removed {before - after} rows with NaN")
print(f"  Remaining: {after} rows")


#######################################################################
# STEP 4: REMOVE INVALID DATA
#######################################################################

print("\nStep 4: Removing invalid data...")
before = len(df_no_nan)

# Keep only rows where depth > 0
df_clean = df_no_nan[df_no_nan['Hole Depth (m)'] > 0]

# Keep only rows where inclination is between 0 and 90
df_clean = df_clean[df_clean['Inclination (degrees)'] >= 0]
df_clean = df_clean[df_clean['Inclination (degrees)'] <= 90]

after = len(df_clean)
print(f"  Removed {before - after} rows with invalid depth or inclination")
print(f"  Remaining: {after} rows")


#######################################################################
# STEP 5: FOR EACH DEPTH, GET THE MOST CONSISTENT INCLINATION VALUE
#######################################################################

print("\nStep 5: Getting consistent inclination for each depth...")

def get_consistent_inclination(group):
    """
    For a group of readings at the same depth, return the most consistent value.
    
    Method:
    1. Round all values to nearest degree
    2. Find the most common rounded value (the "dominant" cluster)
    3. Keep only values within ±5° of the dominant value
    4. Return the median of those filtered values
    """
    values = group['Inclination (degrees)']
    
    # If only 1 reading, just return it
    if len(values) == 1:
        return values.iloc[0]
    
    # Round all values to nearest degree to find clusters
    rounded = values.round(0)
    
    # Find the most common rounded value (the "dominant" cluster)
    mode_rounded = rounded.mode()
    if len(mode_rounded) == 0:
        return values.median()
    
    dominant = mode_rounded.iloc[0]
    
    # Keep only values within ±5° of the dominant value
    mask = (values >= dominant - 5) & (values <= dominant + 5)
    filtered = values[mask]
    
    # If nothing left after filtering, fall back to median
    if len(filtered) == 0:
        return values.median()
    
    # Return the median of the filtered values
    return filtered.median()


# Apply the function to each depth group
df_by_depth = df_clean.groupby('Hole Depth (m)').apply(get_consistent_inclination)

# Convert back to a DataFrame
df_by_depth = df_by_depth.reset_index()
df_by_depth.columns = ['Hole Depth (m)', 'Inclination (degrees)']

print(f"  Condensed to {len(df_by_depth)} unique depths")


#######################################################################
# STEP 6: SORT BY DEPTH (SHALLOWEST TO DEEPEST)
#######################################################################

print("\nStep 6: Sorting by depth...")
df_by_depth = df_by_depth.sort_values('Hole Depth (m)').reset_index(drop=True)


#######################################################################
# RESULT
#######################################################################

print("\n" + "="*60)
print("CLEAN INCLINATION PROFILE")
print("="*60)
print(f"Total unique depths: {len(df_by_depth)}")
print(f"Depth range: {df_by_depth['Hole Depth (m)'].min():.0f}m to {df_by_depth['Hole Depth (m)'].max():.0f}m")
print(f"Inclination range: {df_by_depth['Inclination (degrees)'].min():.1f}° to {df_by_depth['Inclination (degrees)'].max():.1f}°")

print("\nFirst 10 rows:")
print(df_by_depth.head(10).to_string(index=False))

print("\nLast 10 rows:")
print(df_by_depth.tail(10).to_string(index=False))


#######################################################################
# OPTIONAL: SAVE TO CSV OR EXCEL
#######################################################################

# Uncomment to save:
# df_by_depth.to_csv('clean_inclination_profile.csv', index=False)
# df_by_depth.to_excel('clean_inclination_profile.xlsx', index=False)

print("\n" + "="*60)
print("The clean data is stored in: df_by_depth")
print("="*60)
