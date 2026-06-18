#!/usr/bin/env python3
"""
CleanSight Data Explorer v3.0
=============================
Professional Local Engineering Analytics Platform

Version: 3.0.0
Date: May 2026

PHASE 1 - Tab Structure:
- Main tab: Existing dashboard with flexible charting
- Hole Cleaning tab: Placeholder (Phase 2)
- Tripping tab: Placeholder (Phase 3)
- Compare Wells tab: Multi-select dataset control (Phase 4)

KEY CHANGES FROM v2.2:
- Tab navigation (Main, Hole Cleaning, Tripping, Compare Wells)
- Dataset selector across all tabs (switch between loaded wells)
- Multi-select dataset control for Compare Wells
- Preserved all existing functionality in Main tab
"""

import os
import io
import json
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import traceback

import dash
from dash import dcc, html, dash_table, callback_context, no_update, ALL, MATCH
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================

APP_TITLE = "CleanSight Data Explorer"
APP_VERSION = "3.3.6"

APP_DIR = Path(__file__).parent
CACHE_DIR = APP_DIR / ".cache"
AUTOSAVE_FILE = APP_DIR / ".autosave.json"

CACHE_DIR.mkdir(exist_ok=True)

# LAS File Configuration
LAS_NULL_VALUE = -999.25

# Friendly names for LAS channels (abbreviation -> display name)
LAS_FRIENDLY_NAMES = {
    # PWD channels
    'TIME': 'Time (raw)',
    'Timestamp': 'Timestamp',
    'Elapsed_Hours': 'Elapsed Time',
    'Elapsed_Minutes': 'Elapsed Time',
    'Time_Index': 'Sample Index',
    'PWDEPTH': 'PWD Depth',
    'PWTVD': 'True Vertical Depth',
    'PANTM': 'Annulus Temperature',
    'PWPA': 'Annular Pressure',
    'PWEA': 'Annular EMW (ECD)',
    'PWEAAF': 'Avg Pumps-Off EMW',
    'PWEANF': 'Min Pumps-Off EMW',
    'PWEAXF': 'Max Pumps-Off EMW',
    'PWPD': 'Differential Pressure',
    'PWPI': 'Internal Pressure',
    'PBRTM': 'Bore Temperature',
    # Caliper channels
    'DEPT': 'Depth',
    'BCHDF': 'Avg Hole Diameter',
    'BCHDF_DR': 'Avg Hole Diameter (Drilling)',
    'BCEXF': 'Max Hole Diameter',
    'BCEXF_DR': 'Max Hole Diameter (Drilling)',
    'BCENF': 'Min Hole Diameter',
    'BCENF_DR': 'Min Hole Diameter (Drilling)',
    'BACGC': 'Gamma Ray',
    'BACGC_DR': 'Gamma Ray (Drilling)',
    'BACGC_TO': 'Gamma Ray (POOH)',
    'BCXFH': 'Center X Final',
    'BCXFH_DR': 'Center X Final (Drilling)',
    'BCYFH': 'Center Y Final',
    'BCYFH_DR': 'Center Y Final (Drilling)',
    'BCEOFH': 'Major Axis Orientation',
    'BCEOFH_DR': 'Major Axis Orient (Drilling)',
    'BCEO8FH': 'Major Axis 180°',
    'BCEO8FH_DR': 'Major Axis 180° (Drilling)',
    'BCHDS_TO': 'Simple Avg Hole Size (POOH)',
    'BCDXS_TO': 'Simple Max Diam (POOH)',
    'BCDNS_TO': 'Simple Min Diam (POOH)',
    'BCRAS_TO': 'Radius A (POOH)',
    'BCRBS_TO': 'Radius B (POOH)',
    'BCRCS_TO': 'Radius C (POOH)',
    'BCRDS_TO': 'Radius D (POOH)',
    'BCELLF': 'Ellipticity',
    'BCQCSGH': 'QC Shape Geo',
    'ROPA': 'ROP Average',
}

# Default units for channels (when not specified in file)
LAS_DEFAULT_UNITS = {
    'TIME': '',
    'PWDEPTH': 'm',
    'PWTVD': 'm',
    'DEPT': 'm',
    'PANTM': '°C',
    'PBRTM': '°C',
    'PWPA': 'bar',
    'PWPD': 'bar',
    'PWPI': 'bar',
    'PWEA': 'sg',
    'PWEAAF': 'sg',
    'PWEANF': 'sg',
    'PWEAXF': 'sg',
    'BCHDF': 'in',
    'BCHDF_DR': 'in',
    'BCEXF': 'in',
    'BCEXF_DR': 'in',
    'BCENF': 'in',
    'BCENF_DR': 'in',
    'BCHDS_TO': 'in',
    'BCDXS_TO': 'in',
    'BCDNS_TO': 'in',
    'BCRAS_TO': 'in',
    'BCRBS_TO': 'in',
    'BCRCS_TO': 'in',
    'BCRDS_TO': 'in',
    'BACGC': 'API',
    'BACGC_DR': 'API',
    'BACGC_TO': 'API',
    'ROPA': 'm/hr',
}

# Theme definitions
THEMES = {
    'dark': {
        'bg': '#0A0E14',
        'card': '#111820',
        'border': '#1E3A5F',
        'text': '#FFFFFF',
        'dim': '#A0AEC0',
        'muted': '#6B7280',
        'orange': '#F26522',
        'blue': '#3B82F6',
        'green': '#10B981',
        'yellow': '#F59E0B',
        'red': '#EF4444',
        'purple': '#8B5CF6',
        'cyan': '#06B6D4',
        'pink': '#EC4899',
        'grid': 'rgba(255,255,255,0.05)',
        'hover': 'rgba(255,255,255,0.1)',
    },
    'light': {
        'bg': '#F8FAFC',
        'card': '#FFFFFF',
        'border': '#E2E8F0',
        'text': '#1E293B',
        'dim': '#475569',
        'muted': '#94A3B8',
        'orange': '#EA580C',
        'blue': '#2563EB',
        'green': '#059669',
        'yellow': '#D97706',
        'red': '#DC2626',
        'purple': '#7C3AED',
        'cyan': '#0891B2',
        'pink': '#DB2777',
        'grid': 'rgba(0,0,0,0.08)',
        'hover': 'rgba(0,0,0,0.05)',
    }
}

# Current theme (mutable - will be updated by callback)
COLORS = THEMES['dark'].copy()

def get_theme_colors(theme_name: str) -> dict:
    """Get colors for a specific theme."""
    return THEMES.get(theme_name, THEMES['dark'])

TRACE_COLORS = [
    '#F26522', '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
    '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316',
]

# Consistent colors for common parameters - same parameter = same color everywhere
PARAMETER_COLORS = {
    # Drilling parameters
    'CRR': '#F26522',           # Orange - primary DrillDocs color
    'CRR (m3/min)': '#F26522',
    'Hole Depth': '#3B82F6',    # Blue
    'Hole Depth (m)': '#3B82F6',
    'Bit Depth': '#06B6D4',     # Cyan
    'Bit Depth (m)': '#06B6D4',
    'ECD': '#10B981',           # Green
    'ECD (kg/gal)': '#10B981',
    'Flow In': '#8B5CF6',       # Purple
    'Flow In (L/m3)': '#8B5CF6',
    'ROP': '#F59E0B',           # Amber
    'ROP (m/h)': '#F59E0B',
    'ROP (ft/h)': '#F59E0B',
    'Lagged ROP': '#06B6D4',    # Cyan - very distinct from amber ROP
    'Lagged ROP (m/hr)': '#06B6D4',
    'Lagged ROP (ft/hr)': '#06B6D4',
    'RPM': '#EC4899',           # Pink
    'Pump Pressure': '#EF4444', # Red
    'Pump Pressure (psi)': '#EF4444',
    'Hook Load': '#84CC16',     # Lime
    'Hook Load (klbf)': '#84CC16',
    'Block Height': '#14B8A6',  # Teal
    'Block Height (m)': '#14B8A6',
    'Inclination': '#A855F7',   # Violet
    'Inclination (degrees)': '#A855F7',
    'Lag Depth': '#0EA5E9',     # Sky
    'Lag Depth (m)': '#0EA5E9',
    'Pit Volume': '#22C55E',    # Green
    'Pit Volume (m3)': '#22C55E',
    'GAS': '#FACC15',           # Yellow
    'Theoretical TCR': '#FB923C', # Orange light
    'Theoretical TCR (m3)': '#FB923C',
    'Measured TCR': '#F97316',  # Orange
    'Measured TCR (m3)': '#F97316',
    'Theoretical Lag TCR': '#FDBA74',
    'Theoretical Lag TCR (m3)': '#FDBA74',
    # LWD/PWD parameters
    'Annular Pressure': '#3B82F6',
    'Annular EMW (ECD)': '#10B981',
    'Pipe Pressure': '#EF4444',
    'Differential Pressure': '#F59E0B',
    'Annular Temperature': '#EC4899',
    'Bore Temperature': '#F472B6',
    'PWD Depth': '#06B6D4',
    # Caliper parameters
    'Avg Hole Size': '#8B5CF6',
    'Max Hole Size': '#A855F7',
    'Min Hole Size': '#7C3AED',
    'Gamma Ray': '#22C55E',
}

def get_parameter_color(param_name: str, fallback_idx: int = 0) -> str:
    """Get consistent color for a parameter name.
    
    Uses predefined colors for common parameters, or generates
    a consistent color from the parameter name hash for unknown ones.
    """
    # Clean the parameter name for matching
    clean_name = param_name.strip()
    
    # Direct match
    if clean_name in PARAMETER_COLORS:
        return PARAMETER_COLORS[clean_name]
    
    # Try matching without units (e.g., "CRR (m3/min)" -> "CRR")
    base_name = clean_name.split('(')[0].strip()
    if base_name in PARAMETER_COLORS:
        return PARAMETER_COLORS[base_name]
    
    # Try matching key parts
    name_lower = clean_name.lower()
    for key, color in PARAMETER_COLORS.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return color
    
    # Generate consistent color from hash
    hash_val = hash(clean_name) % len(TRACE_COLORS)
    return TRACE_COLORS[hash_val]

KPI_CALC_TYPES = {
    'delta': 'Delta (Last - First)',
    'range': 'Range (Max - Min)',
    'last': 'Last Value',
    'first': 'First Value',
    'max': 'Maximum',
    'min': 'Minimum',
    'mean': 'Average',
    'sum': 'Sum Total',
    'delta_pct': 'Delta %',
}

# Bottoms-Up and Trip Readiness Configuration
BU_CONFIG = {
    'bu_target': 1.1,                    # Minimum BU cycles for readiness (configurable)
    'crr_reduction_pct': 0.15,           # Clean = CRR drops to 15% of CRR at TD (85% reduction)
    'crr_sustain_minutes': 5,            # Must stay below threshold for this many minutes
    'crr_fallback_threshold': 0.006,     # Fallback if CRR at TD not available
    'flow_min_threshold': 100,           # L/min - minimum flow to consider pumps on
    'bit_td_tolerance': 30,              # m - bit within this distance of TD = "at TD"
    'rop_drilling_threshold': 0.5,       # m/h - ROP above this = drilling
    'spp_min_threshold': 100,            # psi - minimum SPP to confirm pumps on
}

# CRR Load Level Descriptors (for reference lines on charts)
CRR_LOAD_LEVELS = {
    'shaker_clean': 0.006,  # m³/min - fallback reference
    'low': 0.02,
    'medium': 0.1,
    'large': 0.25,
}

TAB_STYLES = {
    'tab': {
        'backgroundColor': COLORS['bg'],
        'color': COLORS['muted'],
        'border': 'none',
        'borderBottom': f'2px solid transparent',
        'padding': '10px 20px',
        'fontWeight': '500',
        'fontSize': '12px',
        'cursor': 'pointer',
    },
    'tab_selected': {
        'backgroundColor': COLORS['bg'],
        'color': COLORS['orange'],
        'border': 'none',
        'borderBottom': f'2px solid {COLORS["orange"]}',
        'padding': '10px 20px',
        'fontWeight': '600',
        'fontSize': '12px',
    }
}


# ============================================================
# LAS FILE PARSER
# ============================================================

class LASParser:
    """
    Parser for LAS (Log ASCII Standard) 2.0 files.
    Handles both time-indexed (PWD) and depth-indexed (Caliper) files.
    """
    
    def __init__(self):
        self.version = None
        self.well_info = {}
        self.curves = []
        self.curve_units = {}
        self.curve_descriptions = {}
        self.parameters = {}
        self.data = None
        self.null_value = LAS_NULL_VALUE
        self.index_type = None  # 'time' or 'depth'
        self.file_name = None
    
    def parse(self, content: str, file_name: str = None) -> 'LASParser':
        """Parse LAS file content and return self for chaining."""
        self.file_name = file_name
        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        
        current_section = None
        data_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Section headers
            if line.startswith('~'):
                section_char = line[1].upper() if len(line) > 1 else ''
                if section_char == 'V':
                    current_section = 'version'
                elif section_char == 'W':
                    current_section = 'well'
                elif section_char == 'C':
                    current_section = 'curves'
                elif section_char == 'P':
                    current_section = 'parameters'
                elif section_char == 'A':
                    current_section = 'data'
                    # Parse the header line for column names
                    header_part = line[2:].strip() if len(line) > 2 else ''
                    if header_part:
                        self.curves = header_part.split()
                continue
            
            # Parse based on current section
            if current_section == 'version':
                self._parse_header_line(line, 'version')
            elif current_section == 'well':
                self._parse_header_line(line, 'well')
            elif current_section == 'curves':
                self._parse_curve_line(line)
            elif current_section == 'parameters':
                self._parse_header_line(line, 'parameters')
            elif current_section == 'data':
                data_lines.append(line)
        
        # Parse data section
        if data_lines:
            self._parse_data(data_lines)
        
        # Determine index type
        self._determine_index_type()
        
        return self
    
    def _parse_header_line(self, line: str, section: str):
        """Parse a header line in format: MNEM.UNIT VALUE: DESCRIPTION"""
        try:
            # Split by colon to separate value from description
            if ':' in line:
                left, description = line.split(':', 1)
                description = description.strip()
            else:
                left = line
                description = ''
            
            # Parse mnemonic and unit
            if '.' in left:
                mnem_unit, value = left.split(None, 1) if ' ' in left.strip() else (left, '')
                if '.' in mnem_unit:
                    mnem, unit = mnem_unit.split('.', 1)
                else:
                    mnem = mnem_unit
                    unit = ''
            else:
                parts = left.split()
                mnem = parts[0] if parts else ''
                unit = ''
                value = ' '.join(parts[1:]) if len(parts) > 1 else ''
            
            mnem = mnem.strip()
            value = value.strip()
            
            if section == 'version':
                if mnem == 'VERS':
                    self.version = value
                elif mnem == 'NULL':
                    try:
                        self.null_value = float(value)
                    except:
                        pass
            elif section == 'well':
                self.well_info[mnem] = {'value': value, 'unit': unit.strip(), 'desc': description}
                # Also extract NULL from well section
                if mnem == 'NULL':
                    try:
                        self.null_value = float(value)
                    except:
                        pass
            elif section == 'parameters':
                self.parameters[mnem] = {'value': value, 'unit': unit.strip(), 'desc': description}
        except Exception as e:
            pass  # Skip malformed lines
    
    def _parse_curve_line(self, line: str):
        """Parse a curve definition line."""
        try:
            if ':' in line:
                left, description = line.split(':', 1)
            else:
                left = line
                description = ''
            
            parts = left.split()
            if parts:
                mnem_unit = parts[0]
                if '.' in mnem_unit:
                    mnem, unit = mnem_unit.split('.', 1)
                else:
                    mnem = mnem_unit
                    unit = ''
                
                mnem = mnem.strip()
                if mnem and mnem not in self.curves:
                    self.curves.append(mnem)
                self.curve_units[mnem] = unit.strip()
                self.curve_descriptions[mnem] = description.strip()
        except:
            pass
    
    def _parse_data(self, data_lines: List[str]):
        """Parse the data section into a DataFrame."""
        rows = []
        for line in data_lines:
            # Handle time format like "00:10:00.23-12-25"
            values = line.split()
            if values:
                rows.append(values)
        
        if rows and self.curves:
            # Ensure we have the right number of columns
            n_cols = len(self.curves)
            processed_rows = []
            for row in rows:
                if len(row) >= n_cols:
                    processed_rows.append(row[:n_cols])
                elif len(row) > 0:
                    # Pad with NaN if needed
                    processed_rows.append(row + [np.nan] * (n_cols - len(row)))
            
            if processed_rows:
                self.data = pd.DataFrame(processed_rows, columns=self.curves)
                
                # Convert numeric columns
                for col in self.data.columns:
                    if col.upper() not in ['TIME', 'DATE', 'DATETIME']:
                        try:
                            self.data[col] = pd.to_numeric(self.data[col], errors='coerce')
                        except:
                            pass
                
                # Replace null values with NaN
                self.data = self.data.replace(self.null_value, np.nan)
                
                # Parse TIME column and create elapsed time
                self._parse_time_column()
    
    def _parse_time_column(self):
        """Parse TIME column and create numeric elapsed time and datetime."""
        if self.data is None:
            return
        
        time_col = None
        for col in self.data.columns:
            if col.upper() in ['TIME', 'DATETIME', 'DATE']:
                time_col = col
                break
        
        if time_col is None:
            return
        
        try:
            # Parse time strings like "00:10:00.23-12-25" (HH:MM:SS.DD-MM-YY)
            elapsed_seconds = []
            datetime_values = []
            first_time = None
            
            for time_str in self.data[time_col]:
                if pd.isna(time_str) or time_str == '':
                    elapsed_seconds.append(np.nan)
                    datetime_values.append(pd.NaT)
                    continue
                
                try:
                    # Format: HH:MM:SS.DD-MM-YY
                    time_str = str(time_str)
                    
                    # Split time and date parts
                    if '.' in time_str:
                        time_part, date_part = time_str.rsplit('.', 1)
                    else:
                        time_part = time_str
                        date_part = '01-01-26'
                    
                    # Parse time
                    h, m, s = map(int, time_part.split(':'))
                    
                    # Parse date
                    date_parts = date_part.split('-')
                    if len(date_parts) == 3:
                        day, month, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                        # Assume 20xx for 2-digit years
                        if year < 100:
                            year += 2000
                    else:
                        day, month, year = 1, 1, 2026
                    
                    # Create proper datetime
                    try:
                        dt = datetime(year, month, day, h, m, s)
                        datetime_values.append(dt)
                    except:
                        datetime_values.append(pd.NaT)
                    
                    # Convert to total seconds from epoch-like reference
                    total_secs = (year * 365 * 24 * 3600) + (month * 30 * 24 * 3600) + (day * 24 * 3600) + (h * 3600) + (m * 60) + s
                    
                    if first_time is None:
                        first_time = total_secs
                    
                    elapsed_seconds.append(total_secs - first_time)
                except:
                    elapsed_seconds.append(np.nan)
                    datetime_values.append(pd.NaT)
            
            # Add columns
            if elapsed_seconds and any(not np.isnan(x) if isinstance(x, float) else True for x in elapsed_seconds):
                self.data['Elapsed_Hours'] = [s / 3600 if not np.isnan(s) else np.nan for s in elapsed_seconds]
                self.data['Elapsed_Minutes'] = [s / 60 if not np.isnan(s) else np.nan for s in elapsed_seconds]
                self.data['Time_Index'] = range(len(self.data))
                
                # Add datetime column for proper time-axis plotting
                self.data['Timestamp'] = datetime_values
                
                # Update curve units
                self.curve_units['Elapsed_Hours'] = 'hrs'
                self.curve_units['Elapsed_Minutes'] = 'min'
                self.curve_units['Time_Index'] = ''
                self.curve_units['Timestamp'] = ''
                
                # Add to curves list
                self.curves.extend(['Elapsed_Hours', 'Elapsed_Minutes', 'Time_Index', 'Timestamp'])
        except Exception as e:
            pass  # Keep original TIME column if parsing fails
    
    def _determine_index_type(self):
        """Determine if this is time-indexed or depth-indexed data."""
        if self.curves:
            first_col = self.curves[0].upper()
            if 'TIME' in first_col or 'DATE' in first_col:
                self.index_type = 'time'
            else:
                self.index_type = 'depth'
        
        # Also check well info for clues
        strt = self.well_info.get('STRT', {})
        if strt.get('unit', '').upper() in ['S', 'SEC', 'MIN', 'HR']:
            self.index_type = 'time'
        elif strt.get('unit', '').upper() in ['M', 'FT', 'F']:
            self.index_type = 'depth'
    
    def get_well_name(self) -> str:
        """Get well name from header."""
        well = self.well_info.get('WELL', {}).get('value', '')
        if not well and self.file_name:
            # Extract from filename
            well = self.file_name.replace('.las', '').replace('.LAS', '').replace('.txt', '')
        return well or 'Unknown'
    
    def get_index_column(self) -> str:
        """Get the index column name."""
        if self.curves:
            return self.curves[0]
        return None
    
    def get_data_channels(self) -> List[str]:
        """Get list of data channels (excluding index)."""
        if self.curves:
            return self.curves[1:]
        return []
    
    def to_dataframe(self) -> pd.DataFrame:
        """Return the data as a DataFrame."""
        return self.data if self.data is not None else pd.DataFrame()
    
    def get_summary(self) -> Dict:
        """Get a summary of the LAS file."""
        return {
            'file_name': self.file_name,
            'well_name': self.get_well_name(),
            'index_type': self.index_type,
            'index_column': self.get_index_column(),
            'channels': self.get_data_channels(),
            'n_rows': len(self.data) if self.data is not None else 0,
            'depth_range': self._get_range(self.get_index_column()) if self.index_type == 'depth' else None,
            'curve_units': self.curve_units,
        }
    
    def _get_range(self, col: str) -> tuple:
        """Get min/max range for a column."""
        if self.data is not None and col in self.data.columns:
            numeric_col = pd.to_numeric(self.data[col], errors='coerce')
            return (numeric_col.min(), numeric_col.max())
        return (None, None)
    
    def get_friendly_name(self, channel: str) -> str:
        """Get friendly display name for a channel."""
        # Check friendly names dictionary
        if channel in LAS_FRIENDLY_NAMES:
            return LAS_FRIENDLY_NAMES[channel]
        
        # Check curve descriptions from file
        if channel in self.curve_descriptions and self.curve_descriptions[channel]:
            return self.curve_descriptions[channel]
        
        # Return as-is
        return channel
    
    def get_unit(self, channel: str) -> str:
        """Get unit for a channel."""
        # Check curve units from file first
        if channel in self.curve_units and self.curve_units[channel]:
            return self.curve_units[channel]
        
        # Fall back to default units
        if channel in LAS_DEFAULT_UNITS:
            return LAS_DEFAULT_UNITS[channel]
        
        return ''
    
    def get_channel_label(self, channel: str) -> str:
        """Get full label with friendly name and unit."""
        name = self.get_friendly_name(channel)
        unit = self.get_unit(channel)
        if unit:
            return f"{name} ({unit})"
        return name


def parse_las_file(content: str, file_name: str = None) -> LASParser:
    """Convenience function to parse a LAS file."""
    parser = LASParser()
    return parser.parse(content, file_name)


# ============================================================
# SESSION MANAGER
# ============================================================

class Session:
    def __init__(self):
        self.datasets: Dict[str, Dict] = {}
        self.active_dataset: Optional[str] = None
        self.compare_datasets: List[str] = []  # Multi-select for Compare Wells
        self.main_config = {'x': None, 'y1': [], 'y2': [], 'type': 'line'}
        self.subplots: List[Dict] = []
        self.kpis: List[Dict] = []
        self.active_tab = 'main'
        # LAS data storage
        self.las_files: Dict[str, Dict] = {}  # {name: {'parser': LASParser, 'path': Path}}
        self.active_las: Optional[str] = None
        self.compare_las: List[str] = []  # Multi-select for LWD/PWD comparison
        # Theme
        self.theme: str = 'dark'
        self._load()
    
    def _load(self):
        try:
            if AUTOSAVE_FILE.exists():
                with open(AUTOSAVE_FILE) as f:
                    data = json.load(f)
                self.active_dataset = data.get('active')
                self.compare_datasets = data.get('compare_datasets', [])
                self.main_config = data.get('main_config', self.main_config)
                self.subplots = data.get('subplots', [])
                self.kpis = data.get('kpis', [])
                self.active_tab = data.get('active_tab', 'main')
                self.active_las = data.get('active_las')
                self.compare_las = data.get('compare_las', [])
                self.theme = data.get('theme', 'dark')
                
                # Update global COLORS based on saved theme
                global COLORS
                COLORS.update(get_theme_colors(self.theme))
                
                for name, info in data.get('datasets', {}).items():
                    path = Path(info.get('path', ''))
                    if path.exists():
                        try:
                            df = pd.read_parquet(path)
                            self.datasets[name] = {'df': df, 'path': path}
                            print(f"  ✓ Restored: {name}")
                        except:
                            pass
                
                # Restore LAS files
                for name, info in data.get('las_files', {}).items():
                    path = Path(info.get('path', ''))
                    if path.exists():
                        try:
                            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read()
                            parser = parse_las_file(content, name)
                            self.las_files[name] = {'parser': parser, 'path': path}
                            print(f"  ✓ Restored LAS: {name}")
                        except:
                            pass
        except Exception as e:
            print(f"  Load error: {e}")
    
    def save(self):
        try:
            data = {
                'active': self.active_dataset,
                'compare_datasets': self.compare_datasets,
                'main_config': self.main_config,
                'subplots': self.subplots,
                'kpis': self.kpis,
                'active_tab': self.active_tab,
                'datasets': {n: {'path': str(i.get('path', ''))} for n, i in self.datasets.items()},
                'active_las': self.active_las,
                'compare_las': self.compare_las,
                'las_files': {n: {'path': str(i.get('path', ''))} for n, i in self.las_files.items()},
                'theme': self.theme,
                'saved': datetime.now().isoformat(),
            }
            with open(AUTOSAVE_FILE, 'w') as f:
                json.dump(data, f)
        except:
            pass
    
    def add_dataset(self, name: str, df: pd.DataFrame):
        h = hashlib.md5(name.encode()).hexdigest()[:10]
        path = CACHE_DIR / f"{h}.parquet"
        try:
            df.to_parquet(path)
        except:
            path = None
        self.datasets[name] = {'df': df, 'path': path}
        self.active_dataset = name
        
        # Auto-create KPIs on first data load
        if not self.kpis:
            self._auto_create_kpis(df)
        
        self.save()
    
    def _auto_create_kpis(self, df):
        """Auto-create engineering-relevant KPIs."""
        cols_lower = {c.lower(): c for c in df.columns}
        
        # Depth Drilled
        depth_col = None
        for pattern in ['hole depth', 'holedepth', 'well depth', 'md']:
            for cl, c in cols_lower.items():
                if pattern in cl:
                    depth_col = c
                    break
            if depth_col:
                break
        
        if depth_col and pd.api.types.is_numeric_dtype(df[depth_col]):
            self.kpis.append({
                'id': 'auto_depth',
                'title': 'Depth Drilled',
                'column': depth_col,
                'calc': 'range',
                'unit': 'm',
                'color': 'orange'
            })
        
        # TCR
        for cl, c in cols_lower.items():
            if 'tcr' in cl and 'measured' in cl:
                if pd.api.types.is_numeric_dtype(df[c]):
                    self.kpis.append({
                        'id': 'auto_tcr',
                        'title': 'Total TCR',
                        'column': c,
                        'calc': 'last',
                        'unit': 'm³',
                        'color': 'blue'
                    })
                break
        
        # Max ROP
        for cl, c in cols_lower.items():
            if 'rop' in cl:
                if pd.api.types.is_numeric_dtype(df[c]):
                    self.kpis.append({
                        'id': 'auto_rop',
                        'title': 'Max ROP',
                        'column': c,
                        'calc': 'max',
                        'unit': 'ft/h',
                        'color': 'green'
                    })
                break
    
    def get_df(self, dataset_name: str = None) -> Optional[pd.DataFrame]:
        name = dataset_name or self.active_dataset
        if name and name in self.datasets:
            return self.datasets[name].get('df')
        return None
    
    def get_dataset_list(self) -> List[str]:
        return list(self.datasets.keys())
    
    def remove_dataset(self, name: str):
        if name in self.datasets:
            # Remove cache file
            path = self.datasets[name].get('path')
            if path and Path(path).exists():
                try:
                    Path(path).unlink()
                except:
                    pass
            del self.datasets[name]
            
            # Update active if needed
            if self.active_dataset == name:
                self.active_dataset = next(iter(self.datasets.keys()), None)
            
            # Update compare list
            self.compare_datasets = [d for d in self.compare_datasets if d != name]
            
            self.save()
    
    def add_subplot(self):
        self.subplots.append({'x': '__index__', 'y1': [], 'y2': []})
        self.save()
    
    def remove_subplot(self, idx: int):
        if 0 <= idx < len(self.subplots):
            self.subplots.pop(idx)
            self.save()
    
    def add_kpi(self, kpi: Dict):
        kpi['id'] = f"kpi_{datetime.now().strftime('%H%M%S%f')}"
        self.kpis.append(kpi)
        self.save()
    
    def remove_kpi(self, kpi_id: str):
        self.kpis = [k for k in self.kpis if k.get('id') != kpi_id]
        self.save()
    
    def rename_dataset(self, old_name: str, new_name: str) -> bool:
        """Rename a dataset. Returns True on success."""
        if old_name not in self.datasets:
            return False
        if new_name in self.datasets:
            return False  # Name already exists
        if not new_name.strip():
            return False
        
        new_name = new_name.strip()
        
        # Move the dataset to new key
        self.datasets[new_name] = self.datasets.pop(old_name)
        
        # Update active dataset if needed
        if self.active_dataset == old_name:
            self.active_dataset = new_name
        
        # Update compare list
        self.compare_datasets = [new_name if d == old_name else d for d in self.compare_datasets]
        
        self.save()
        return True
    
    # LAS File Methods
    def add_las_file(self, name: str, parser: 'LASParser', content: str):
        """Add a parsed LAS file to session."""
        # Save content to cache for persistence
        h = hashlib.md5(name.encode()).hexdigest()[:10]
        path = CACHE_DIR / f"las_{h}.txt"
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except:
            path = None
        
        self.las_files[name] = {'parser': parser, 'path': path}
        self.active_las = name
        self.save()
    
    def get_las_parser(self, name: str = None) -> Optional['LASParser']:
        """Get LAS parser for a file."""
        name = name or self.active_las
        if name and name in self.las_files:
            return self.las_files[name].get('parser')
        return None
    
    def get_las_df(self, name: str = None) -> Optional[pd.DataFrame]:
        """Get DataFrame from LAS file."""
        parser = self.get_las_parser(name)
        if parser:
            return parser.to_dataframe()
        return None
    
    def get_las_list(self) -> List[str]:
        """Get list of loaded LAS files."""
        return list(self.las_files.keys())
    
    def remove_las_file(self, name: str):
        """Remove a LAS file from session."""
        if name in self.las_files:
            # Remove cache file
            path = self.las_files[name].get('path')
            if path and Path(path).exists():
                try:
                    Path(path).unlink()
                except:
                    pass
            del self.las_files[name]
            
            # Update active if needed
            if self.active_las == name:
                self.active_las = next(iter(self.las_files.keys()), None)
            
            # Update compare list
            self.compare_las = [f for f in self.compare_las if f != name]
            
            self.save()
    
    def get_las_channels_for_main(self) -> List[str]:
        """Get all LAS channels available for Main tab plotting."""
        channels = []
        for name, info in self.las_files.items():
            parser = info.get('parser')
            if parser:
                prefix = f"[LAS:{name}] "
                for ch in parser.get_data_channels():
                    channels.append(prefix + ch)
        return channels


SESSION = Session()


# ============================================================
# DATA FUNCTIONS
# ============================================================

def parse_file(contents: str, filename: str) -> tuple:
    """Parse uploaded CSV/XLSX file."""
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        if filename.lower().endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            # Try different encodings
            for enc in ['utf-8', 'utf-16-le', 'utf-16', 'latin-1', 'cp1252']:
                try:
                    text = decoded.decode(enc)
                    # Detect delimiter
                    first_line = text.split('\n')[0]
                    if '\t' in first_line:
                        df = pd.read_csv(io.StringIO(text), sep='\t')
                    else:
                        df = pd.read_csv(io.StringIO(text))
                    break
                except:
                    continue
            else:
                return None, "Could not parse file"
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Parse dates
        for col in df.columns:
            if 'time' in col.lower() or 'date' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col])
                except:
                    pass
        
        return df, None
    except Exception as e:
        return None, str(e)


def get_columns_info(df: pd.DataFrame):
    """Get column type info."""
    all_cols = list(df.columns)
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    dt_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    return all_cols, num_cols, dt_cols


def calculate_kpi(df: pd.DataFrame, kpi: Dict) -> str:
    """Calculate KPI value."""
    if df is None:
        return "—"
    
    col = kpi.get('column')
    calc = kpi.get('calc', 'last')
    unit = kpi.get('unit', '')
    
    if col not in df.columns:
        return "—"
    
    try:
        series = df[col].dropna()
        if len(series) == 0:
            return "—"
        
        if calc == 'last':
            val = series.iloc[-1]
        elif calc == 'first':
            val = series.iloc[0]
        elif calc == 'max':
            val = series.max()
        elif calc == 'min':
            val = series.min()
        elif calc == 'mean':
            val = series.mean()
        elif calc == 'sum':
            val = series.sum()
        elif calc == 'delta':
            val = series.iloc[-1] - series.iloc[0]
        elif calc == 'delta_pct':
            first = series.iloc[0]
            if first != 0:
                val = ((series.iloc[-1] - first) / first) * 100
                return f"{val:.1f}%"
            return "—"
        elif calc == 'range':
            val = series.max() - series.min()
        else:
            val = series.iloc[-1]
        
        # Format
        if abs(val) >= 1000:
            return f"{val:,.0f} {unit}".strip()
        elif abs(val) >= 1:
            return f"{val:.1f} {unit}".strip()
        else:
            return f"{val:.3f} {unit}".strip()
    except:
        return "—"


def get_column_data(col_name: str, df: pd.DataFrame = None):
    """
    Get column data - handles both regular CSV columns and LAS columns.
    LAS columns are prefixed with 'LAS:filename:channel'.
    Returns (data_series, display_name, is_from_las).
    """
    if col_name is None:
        return None, None, False
    
    # Check if it's a LAS column
    if col_name.startswith('LAS:'):
        parts = col_name.split(':', 2)
        if len(parts) >= 3:
            las_name = parts[1]
            channel = parts[2]
            
            parser = SESSION.get_las_parser(las_name)
            if parser:
                las_df = parser.to_dataframe()
                if las_df is not None and channel in las_df.columns:
                    data = las_df[channel]
                    # Don't convert Timestamp to numeric - keep as datetime
                    if channel != 'Timestamp' and not pd.api.types.is_numeric_dtype(data) and not pd.api.types.is_datetime64_any_dtype(data):
                        data = pd.to_numeric(data, errors='coerce')
                    friendly_name = parser.get_channel_label(channel)
                    return data, f"[{las_name}] {friendly_name}", True
        return None, col_name, True
    
    # Regular CSV column
    if df is not None and col_name in df.columns:
        return df[col_name], col_name, False
    elif col_name == '__index__' and df is not None:
        return df.index, 'Index', False
    
    return None, col_name, False


def create_chart(df: pd.DataFrame, main_config: Dict, subplots_config: List[Dict]) -> go.Figure:
    """Create the main chart with subplots."""
    # Check if we have any data (CSV or LAS)
    has_csv = df is not None and not df.empty
    has_las = len(SESSION.get_las_list()) > 0
    
    if not has_csv and not has_las:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['card'],
            font=dict(color=COLORS['text']),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False),
            annotations=[dict(
                text="Upload data to begin",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=16, color=COLORS['muted'])
            )]
        )
        return fig
    
    x_main = main_config.get('x') or '__index__'
    y1 = main_config.get('y1', []) or []
    y2 = main_config.get('y2', []) or []
    chart_type = main_config.get('type', 'line')
    
    n_rows = 1 + len(subplots_config)
    
    # Create figure with subplots
    specs = [[{"secondary_y": True}] for _ in range(n_rows)]
    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,  # Share x-axes so zoom/pan syncs across all plots
        vertical_spacing=0.08,
        specs=specs,
    )
    
    # Get X data for main plot
    x_data_main, x_label, x_is_las = get_column_data(x_main, df)
    if x_data_main is None and df is not None:
        x_data_main = df.index
        x_label = 'Index'
    
    # Primary Y
    for col in y1:
        y_data, y_label, is_las = get_column_data(col, df)
        if y_data is not None:
            color = get_parameter_color(y_label)  # Consistent color based on parameter name
            mode = 'lines' if chart_type == 'line' else 'markers'
            
            # For LAS data, we may need to use its own index
            if is_las and not x_is_las:
                # If X is CSV and Y is LAS, use Time_Index or range
                parser_name = col.split(':')[1] if col.startswith('LAS:') else None
                if parser_name:
                    parser = SESSION.get_las_parser(parser_name)
                    if parser:
                        las_df = parser.to_dataframe()
                        if 'Elapsed_Hours' in las_df.columns:
                            x_for_trace = las_df['Elapsed_Hours']
                        else:
                            x_for_trace = range(len(y_data))
                    else:
                        x_for_trace = range(len(y_data))
                else:
                    x_for_trace = range(len(y_data))
            else:
                x_for_trace = x_data_main
            
            fig.add_trace(
                go.Scatter(x=x_for_trace, y=y_data, name=y_label, mode=mode,
                          line=dict(color=color, width=1.5, dash='solid'),
                          hovertemplate=f'{y_label}: %{{y:.3f}}<extra></extra>'),
                row=1, col=1, secondary_y=False
            )
    
    # Secondary Y
    for col in y2:
        y_data, y_label, is_las = get_column_data(col, df)
        if y_data is not None:
            color = get_parameter_color(y_label)  # Consistent color based on parameter name
            
            # Handle LAS data index
            if is_las and not x_is_las:
                parser_name = col.split(':')[1] if col.startswith('LAS:') else None
                if parser_name:
                    parser = SESSION.get_las_parser(parser_name)
                    if parser:
                        las_df = parser.to_dataframe()
                        if 'Elapsed_Hours' in las_df.columns:
                            x_for_trace = las_df['Elapsed_Hours']
                        else:
                            x_for_trace = range(len(y_data))
                    else:
                        x_for_trace = range(len(y_data))
                else:
                    x_for_trace = range(len(y_data))
            else:
                x_for_trace = x_data_main
            
            fig.add_trace(
                go.Scatter(x=x_for_trace, y=y_data, name=f"{y_label} (R)", mode='lines',
                          line=dict(color=color, width=1.5, dash='solid'),
                          hovertemplate=f'{y_label}: %{{y:.3f}}<extra></extra>'),
                row=1, col=1, secondary_y=True
            )
    
    # Axis labels
    fig.update_xaxes(title_text=x_label, row=1, col=1)
    
    # Y-axis labels with smaller font
    if y1:
        y1_labels = [get_column_data(c, df)[1] for c in y1]
        fig.update_yaxes(
            title_text=_format_axis_label(y1_labels),
            title_font=dict(size=8),
            title_standoff=2,
            row=1, col=1, secondary_y=False
        )
    if y2:
        y2_labels = [get_column_data(c, df)[1] for c in y2]
        fig.update_yaxes(
            title_text=_format_axis_label(y2_labels),
            title_font=dict(size=8),
            title_standoff=2,
            row=1, col=1, secondary_y=True
        )
    
    # --- SUBPLOTS ---
    for i, sp in enumerate(subplots_config):
        row = i + 2
        x_sp = sp.get('x', '__index__')
        x_data_sp, x_label_sp, x_sp_is_las = get_column_data(x_sp, df)
        if x_data_sp is None and df is not None:
            x_data_sp = df.index
            x_label_sp = 'Index'
        
        sp_y1 = sp.get('y1', [])
        sp_y2 = sp.get('y2', [])
        
        for col in sp_y1:
            y_data, y_label, is_las = get_column_data(col, df)
            if y_data is not None:
                color = get_parameter_color(y_label)  # Consistent color based on parameter name
                
                # Handle LAS data index
                if is_las and not x_sp_is_las:
                    parser_name = col.split(':')[1] if col.startswith('LAS:') else None
                    if parser_name:
                        parser = SESSION.get_las_parser(parser_name)
                        if parser:
                            las_df = parser.to_dataframe()
                            if 'Elapsed_Hours' in las_df.columns:
                                x_for_trace = las_df['Elapsed_Hours']
                            else:
                                x_for_trace = range(len(y_data))
                        else:
                            x_for_trace = range(len(y_data))
                    else:
                        x_for_trace = range(len(y_data))
                else:
                    x_for_trace = x_data_sp
                
                fig.add_trace(
                    go.Scatter(x=x_for_trace, y=y_data, name=y_label, mode='lines',
                              line=dict(color=color, width=1.5, dash='solid'),
                              hovertemplate=f'{y_label}: %{{y:.3f}}<extra></extra>'),
                    row=row, col=1, secondary_y=False
                )
        
        for col in sp_y2:
            y_data, y_label, is_las = get_column_data(col, df)
            if y_data is not None:
                color = get_parameter_color(y_label)  # Consistent color based on parameter name
                
                # Handle LAS data index
                if is_las and not x_sp_is_las:
                    parser_name = col.split(':')[1] if col.startswith('LAS:') else None
                    if parser_name:
                        parser = SESSION.get_las_parser(parser_name)
                        if parser:
                            las_df = parser.to_dataframe()
                            if 'Elapsed_Hours' in las_df.columns:
                                x_for_trace = las_df['Elapsed_Hours']
                            else:
                                x_for_trace = range(len(y_data))
                        else:
                            x_for_trace = range(len(y_data))
                    else:
                        x_for_trace = range(len(y_data))
                else:
                    x_for_trace = x_data_sp
                
                fig.add_trace(
                    go.Scatter(x=x_for_trace, y=y_data, name=f"{y_label} (R)", mode='lines',
                              line=dict(color=color, width=1.5, dash='solid'),
                              hovertemplate=f'{y_label}: %{{y:.3f}}<extra></extra>'),
                    row=row, col=1, secondary_y=True
                )
        
        # X-axis label
        fig.update_xaxes(title_text=x_label_sp, row=row, col=1)
        
        # Y-axis labels for subplots
        if sp_y1:
            sp_y1_labels = [get_column_data(c, df)[1] for c in sp_y1]
            fig.update_yaxes(
                title_text=_format_axis_label(sp_y1_labels),
                title_font=dict(size=8),
                title_standoff=2,
                row=row, col=1, secondary_y=False
            )
        if sp_y2:
            sp_y2_labels = [get_column_data(c, df)[1] for c in sp_y2]
            fig.update_yaxes(
                title_text=_format_axis_label(sp_y2_labels),
                title_font=dict(size=8),
                title_standoff=2,
                row=row, col=1, secondary_y=True
            )
    
    # Layout
    height_per_plot = 280
    total_height = height_per_plot * n_rows + 60
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono, monospace', size=10),
        legend=dict(
            bgcolor='rgba(17,24,32,0.95)', bordercolor=COLORS['border'], borderwidth=1,
            orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
            font=dict(size=9),
        ),
        margin=dict(l=80, r=80, t=40, b=40),
        height=total_height,
        hovermode='x unified',
        dragmode='zoom',
        uirevision='constant',
    )
    
    fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)', zerolinecolor='rgba(255,255,255,0.1)', fixedrange=False)
    
    # Explicitly link all x-axes to the first one for synchronized zoom/pan
    # Also show tick labels on ALL plots (not just the bottom one)
    # The first x-axis is 'xaxis', subsequent ones are 'xaxis2', 'xaxis3', etc.
    if n_rows > 1:
        for i in range(2, n_rows + 1):
            fig.update_layout(**{f'xaxis{i}': dict(matches='x', showticklabels=True)})
    
    return fig


def _format_axis_label(columns: List[str]) -> str:
    """Format column names for Y-axis label - stack vertically if multiple."""
    if not columns:
        return ''
    
    if len(columns) == 1:
        return columns[0]
    else:
        return '<br>'.join(columns)


# ============================================================
# DASH APP
# ============================================================

app = dash.Dash(__name__, title=APP_TITLE, suppress_callback_exceptions=True)

app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; }
        .Select-control { background-color: #111820 !important; border-color: #1E3A5F !important; }
        .Select-menu-outer { background-color: #111820 !important; border-color: #1E3A5F !important; max-height: 300px !important; }
        .Select-option { background-color: #111820 !important; color: #FFF !important; }
        .Select-option:hover { background-color: #1E3A5F !important; }
        .Select-value-label, .Select-placeholder { color: #A0AEC0 !important; }
        .Select-input > input { color: #FFF !important; }
        .Select-multi-value-wrapper .Select-value { background: #1E3A5F !important; border-color: #3B82F6 !important; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0A0E14; }
        ::-webkit-scrollbar-thumb { background: #1E3A5F; border-radius: 3px; }
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 10000; }
        .modal-overlay.show { display: flex; align-items: center; justify-content: center; }
        .tab-disabled { opacity: 0.5; cursor: not-allowed !important; }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
'''


# ============================================================
# LAYOUT COMPONENTS
# ============================================================

def create_header():
    """Create the app header with branding and controls."""
    return html.Div([
        # Logo and title
        html.Div([
            html.Div([
                html.Span("Drill", style={'color': '#FFF'}),
                html.Span("Docs", style={'color': COLORS['orange']}),
            ], style={'fontSize': '20px', 'fontWeight': '600', 'fontFamily': 'JetBrains Mono'}),
            html.Span(f"CleanSight® v{APP_VERSION}", style={'color': COLORS['dim'], 'fontSize': '12px', 'marginLeft': '12px'}),
        ], style={'display': 'flex', 'alignItems': 'center'}),
        
        # Active dataset indicator
        html.Div(id='header-dataset-indicator', style={
            'fontSize': '12px', 'color': COLORS['text'], 'fontFamily': 'JetBrains Mono',
            'background': COLORS['card'], 'padding': '4px 12px', 'borderRadius': '4px',
            'border': f'1px solid {COLORS["border"]}'
        }),
        
        # Right side controls
        html.Div([
            # Theme toggle
            html.Button("☀", id='theme-toggle', title='Toggle Light/Dark Theme', style={
                'background': 'transparent', 'color': COLORS['dim'], 'border': f'1px solid {COLORS["border"]}',
                'padding': '6px 10px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '14px',
                'marginRight': '10px'
            }),
            # Save button
            html.Button("💾 Save", id='btn-save', style={
                'background': COLORS['border'], 'color': '#FFF', 'border': 'none',
                'padding': '6px 14px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '11px'
            }),
        ], style={'display': 'flex', 'alignItems': 'center'}),
    ], style={
        'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
        'padding': '10px 16px', 'background': COLORS['card'], 'borderBottom': f'1px solid {COLORS["border"]}'
    })


def create_tab_bar():
    """Create the tab navigation bar."""
    return html.Div([
        dcc.Tabs(id='main-tabs', value='main', children=[
            dcc.Tab(label='▦ Main', value='main', style=TAB_STYLES['tab'], selected_style=TAB_STYLES['tab_selected']),
            dcc.Tab(label='◎ Hole Cleaning', value='hole-cleaning', style=TAB_STYLES['tab'], selected_style=TAB_STYLES['tab_selected']),
            dcc.Tab(label='↻ Tripping', value='tripping', style=TAB_STYLES['tab'], selected_style=TAB_STYLES['tab_selected']),
            dcc.Tab(label='⇌ Compare Wells', value='compare', style=TAB_STYLES['tab'], selected_style=TAB_STYLES['tab_selected']),
            dcc.Tab(label='≋ LWD/PWD', value='lwd-pwd', style=TAB_STYLES['tab'], selected_style=TAB_STYLES['tab_selected']),
        ], style={'borderBottom': f'1px solid {COLORS["border"]}'}),
    ], style={'background': COLORS['bg']})


def create_data_sidebar():
    """Create the data upload and dataset selector sidebar."""
    return html.Div([
        # Upload section
        html.Div([
            html.Div("▦ DATA", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'marginBottom': '8px', 'letterSpacing': '1px'}),
            dcc.Upload(id='upload-visible', children=html.Div([
                "Drop CSV/XLSX or ", html.Span("browse", style={'color': COLORS['orange']})
            ], style={'textAlign': 'center', 'fontSize': '11px'}),
            style={'padding': '14px', 'border': f'2px dashed {COLORS["border"]}', 'borderRadius': '6px', 'cursor': 'pointer'}),
            html.Div(id='upload-status', style={'marginTop': '6px', 'fontSize': '10px'}),
        ], style={'marginBottom': '12px'}),
        
        # Quick Load from project files
        html.Div([
            html.Div("◈ QUICK LOAD", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'marginBottom': '8px', 'letterSpacing': '1px'}),
            dcc.Dropdown(
                id='quick-load-selector',
                options=[],
                value=None,
                placeholder='Load from project...',
                style={'fontSize': '11px'}
            ),
            html.Div(id='quick-load-status', style={'marginTop': '4px', 'fontSize': '10px'}),
        ], style={'marginBottom': '12px'}),
        
        # Dataset selector with rename button
        html.Div([
            html.Div("◇ DATASETS", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'marginBottom': '8px', 'letterSpacing': '1px'}),
            html.Div([
                dcc.Dropdown(
                    id='dataset-selector',
                    options=[],
                    value=None,
                    placeholder='Select dataset...',
                    style={'flex': '1'}
                ),
                html.Button("✏", id='btn-rename-dataset', title='Rename dataset', style={
                    'background': COLORS['card'], 'color': COLORS['text'], 'border': f'1px solid {COLORS["border"]}',
                    'padding': '6px 10px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px',
                    'marginLeft': '6px'
                }),
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '8px'}),
            html.Div(id='dataset-list', style={'maxHeight': '150px', 'overflowY': 'auto'}),
        ], style={'marginBottom': '16px'}),
    ])


def create_main_tab_sidebar():
    """Create the sidebar controls for Main tab."""
    return html.Div([
        # Axis Config
        html.Div([
            html.Div("MAIN PLOT", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'marginBottom': '8px', 'letterSpacing': '1px'}),
            html.Label("X-Axis", style={'fontSize': '9px', 'color': COLORS['muted']}),
            dcc.Dropdown(id='main-x', placeholder='X-axis...'),
            html.Label("Y-Axis (Left)", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginTop': '8px', 'display': 'block'}),
            dcc.Dropdown(id='main-y1', multi=True, placeholder='Primary Y...'),
            html.Label("Y-Axis (Right)", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginTop': '8px', 'display': 'block'}),
            dcc.Dropdown(id='main-y2', multi=True, placeholder='Secondary Y...'),
            html.Label("Chart Type", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginTop': '8px', 'display': 'block'}),
            dcc.RadioItems(id='chart-type', options=[
                {'label': ' Line', 'value': 'line'},
                {'label': ' Scatter', 'value': 'scatter'},
            ], value='line', inline=True, style={'fontSize': '10px'}, labelStyle={'marginRight': '10px', 'color': COLORS['text']}),
        ], style={'marginBottom': '16px'}),
        
        # Subplots
        html.Div([
            html.Div([
                html.Span("▤ SUBPLOTS", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'letterSpacing': '1px'}),
                html.Button("+ Add", id='btn-add-subplot', style={
                    'background': COLORS['blue'], 'color': '#FFF', 'border': 'none',
                    'padding': '3px 10px', 'borderRadius': '3px', 'cursor': 'pointer', 'fontSize': '9px'
                }),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '8px'}),
            html.Div(id='subplot-list'),
        ]),
    ])


def create_main_tab_content():
    """Create the main tab content (chart and KPIs)."""
    return html.Div([
        # KPI Section
        html.Div([
            html.Div([
                html.Span("KEY METRICS", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'letterSpacing': '1px'}),
                html.Button("+ Add KPI", id='btn-add-kpi', style={
                    'background': COLORS['border'], 'color': '#FFF', 'border': 'none',
                    'padding': '3px 10px', 'borderRadius': '3px', 'cursor': 'pointer', 'fontSize': '9px'
                }),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
            html.Div(id='kpi-list', style={'display': 'flex', 'gap': '10px', 'flexWrap': 'wrap'}),
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '12px', 'marginBottom': '12px'
        }),
        
        # Chart
        html.Div([
            dcc.Graph(id='chart', config={
                'displayModeBar': True, 'displaylogo': False,
                'toImageButtonOptions': {'format': 'png', 'filename': 'chart', 'scale': 2}
            }, style={'height': '100%'}),
        ], style={
            'flex': '1', 'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '6px', 'minHeight': '300px'
        }),
    ], style={'flex': '1', 'padding': '12px', 'display': 'flex', 'flexDirection': 'column', 'overflowY': 'auto'})


def create_column_browser():
    """Create the column browser panel."""
    return html.Div([
        html.Div("▥ COLUMNS", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'marginBottom': '8px', 'letterSpacing': '1px'}),
        dcc.Input(id='col-search', type='text', placeholder='◌ Search...', style={
            'width': '100%', 'padding': '6px 8px', 'background': COLORS['bg'],
            'border': f'1px solid {COLORS["border"]}', 'borderRadius': '4px',
            'color': COLORS['text'], 'fontSize': '11px', 'marginBottom': '8px'
        }),
        html.Div(id='col-list', style={
            'maxHeight': '60vh', 'overflowY': 'auto', 'border': f'1px solid {COLORS["border"]}', 'borderRadius': '4px'
        }),
        html.Div(id='data-stats', style={'marginTop': '10px', 'fontSize': '10px', 'color': COLORS['dim']}),
    ])


def create_hole_cleaning_tab():
    """Create the Hole Cleaning tab content - Phase 2 Implementation."""
    return html.Div([
        # Top Row - KPI Cards
        html.Div([
            # TCR Ratio Card
            html.Div([
                html.Div("TCR RATIO", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='hc-tcr-ratio', children="—", style={
                    'fontSize': '26px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['orange']
                }),
                html.Div("Measured / Theoretical", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["orange"]}', 'borderRadius': '4px',
                'padding': '12px 16px', 'minWidth': '150px', 'flex': '1'
            }),
            
            # Measured TCR Card
            html.Div([
                html.Div("MEASURED TCR", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='hc-measured-tcr', children="—", style={
                    'fontSize': '26px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['blue']
                }),
                html.Div("Cumulative (m³)", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["blue"]}', 'borderRadius': '4px',
                'padding': '12px 16px', 'minWidth': '150px', 'flex': '1'
            }),
            
            # Theoretical TCR Card
            html.Div([
                html.Div("THEORETICAL TCR", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='hc-theoretical-tcr', children="—", style={
                    'fontSize': '26px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['cyan']
                }),
                html.Div("Lag Adjusted (m³)", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["cyan"]}', 'borderRadius': '4px',
                'padding': '12px 16px', 'minWidth': '150px', 'flex': '1'
            }),
            
            # Excess/Deficit Card
            html.Div([
                html.Div("EXCESS / DEFICIT", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='hc-excess-deficit', children="—", style={
                    'fontSize': '26px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['green']
                }),
                html.Div(id='hc-excess-pct', children="", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["green"]}', 'borderRadius': '4px',
                'padding': '12px 16px', 'minWidth': '150px', 'flex': '1'
            }),
            
            # CSD P50 Card
            html.Div([
                html.Div("CSD P50", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='hc-csd-p50', children="—", style={
                    'fontSize': '26px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['purple']
                }),
                html.Div("Median Size (mm)", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["purple"]}', 'borderRadius': '4px',
                'padding': '12px 16px', 'minWidth': '150px', 'flex': '1'
            }),
            
            # UFO Card
            html.Div([
                html.Div("UFO EVENTS", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='hc-ufo-count', children="—", style={
                    'fontSize': '26px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['red']
                }),
                html.Div(id='hc-ufo-rate', children="", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["red"]}', 'borderRadius': '4px',
                'padding': '12px 16px', 'minWidth': '150px', 'flex': '1'
            }),
        ], style={
            'display': 'flex', 'gap': '12px', 'marginBottom': '16px', 'flexWrap': 'wrap'
        }),
        
        # Row 1 - TCR Analysis (full width)
        html.Div([
            html.Div([
                html.Span("TCR Analysis", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                html.Span(" — Measured vs Theoretical over Time", style={'fontSize': '11px', 'color': COLORS['dim']}),
            ], style={'marginBottom': '10px'}),
            dcc.Graph(id='hc-tcr-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                     style={'height': '300px'}),
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '16px', 'marginBottom': '16px'
        }),
        
        # Row 2 - TCR by Depth + CSD Distribution (side by side, equal 50%)
        html.Div([
            # Left - TCR by Depth
            html.Div([
                html.Div([
                    html.Span("TCR by Depth", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                    html.Span(" — 100m Intervals", style={'fontSize': '11px', 'color': COLORS['dim']}),
                ], style={'marginBottom': '10px'}),
                dcc.Graph(id='hc-tcr-depth-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                         style={'height': '320px'}),
            ], style={
                'flex': '1', 'minWidth': '400px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px'
            }),
            
            # Right - CSD Distribution
            html.Div([
                html.Div([
                    html.Span("Cuttings Size Distribution", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                ], style={'marginBottom': '10px'}),
                dcc.Graph(id='hc-csd-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                         style={'height': '320px'}),
            ], style={
                'flex': '1', 'minWidth': '400px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px'
            }),
        ], style={'display': 'flex', 'gap': '16px', 'marginBottom': '16px', 'flexWrap': 'wrap'}),
        
        # Row 3 - CRR + UFO Events (side by side, equal 50%)
        html.Div([
            # Left - CRR Trend
            html.Div([
                html.Div([
                    html.Span("Cuttings Return Rate", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                    html.Span(" — Load over Time", style={'fontSize': '11px', 'color': COLORS['dim']}),
                ], style={'marginBottom': '10px'}),
                dcc.Graph(id='hc-crr-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                         style={'height': '320px'}),
            ], style={
                'flex': '1', 'minWidth': '400px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px'
            }),
            
            # Right - UFO Events by Depth
            html.Div([
                html.Div([
                    html.Span("UFO Events by Depth", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                    html.Span(" — Per 100m Interval", style={'fontSize': '11px', 'color': COLORS['dim']}),
                ], style={'marginBottom': '10px'}),
                dcc.Graph(id='hc-ufo-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                         style={'height': '320px'}),
            ], style={
                'flex': '1', 'minWidth': '400px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px'
            }),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'}),
        
    ], style={
        'flex': '1', 'padding': '16px', 'overflowY': 'auto', 'overflowX': 'hidden',
        'background': COLORS['bg'], 'width': '100%', 'boxSizing': 'border-box'
    })


def create_tripping_tab():
    """Create the Tripping tab content - Revised with proper BU logic."""
    return html.Div([
        # Top Row - Primary Status Cards (BU-focused)
        html.Div([
            # Trip Readiness Card (large, prominent)
            html.Div([
                html.Div("TRIP READINESS", style={'fontSize': '11px', 'color': COLORS['muted'], 'marginBottom': '6px', 'letterSpacing': '0.5px', 'textAlign': 'center'}),
                html.Div(id='trip-readiness-value', children="—", style={
                    'fontSize': '42px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 
                    'color': COLORS['green'], 'textAlign': 'center', 'lineHeight': '1'
                }),
                html.Div(id='trip-readiness-status', children="Calculating...", style={
                    'fontSize': '12px', 'color': COLORS['dim'], 'textAlign': 'center', 'marginTop': '6px'
                }),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '8px', 'padding': '16px 24px', 'minWidth': '160px'
            }),
            
            # BU Cycles Completed
            html.Div([
                html.Div("BU CYCLES", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='trip-bu-cycles', children="—", style={
                    'fontSize': '32px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['blue']
                }),
                html.Div(id='trip-bu-target', children="Target: ≥1.1", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["blue"]}', 'borderRadius': '4px',
                'padding': '14px 18px', 'minWidth': '120px', 'flex': '1'
            }),
            
            # BU Completion %
            html.Div([
                html.Div("CURRENT BU", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='trip-bu-completion', children="—%", style={
                    'fontSize': '32px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['cyan']
                }),
                html.Div(id='trip-bu-time', children="", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["cyan"]}', 'borderRadius': '4px',
                'padding': '14px 18px', 'minWidth': '120px', 'flex': '1'
            }),
            
            # Reference BU Time
            html.Div([
                html.Div("REF BU TIME", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='trip-ref-bu-time', children="—", style={
                    'fontSize': '32px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['purple']
                }),
                html.Div("minutes", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["purple"]}', 'borderRadius': '4px',
                'padding': '14px 18px', 'minWidth': '120px', 'flex': '1'
            }),
            
            # CRR Status (Clean Hole Indicator)
            html.Div([
                html.Div("CRR STATUS", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='trip-crr-status', children="—", style={
                    'fontSize': '26px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['green']
                }),
                html.Div(id='trip-crr-value', children="", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["green"]}', 'borderRadius': '4px',
                'padding': '14px 18px', 'minWidth': '120px', 'flex': '1'
            }),
            
            # Time at TD
            html.Div([
                html.Div("TIME AT TD", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'letterSpacing': '0.5px'}),
                html.Div(id='trip-time-td', children="—", style={
                    'fontSize': '32px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['orange']
                }),
                html.Div("hours", style={'fontSize': '9px', 'color': COLORS['dim']}),
            ], style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderLeft': f'3px solid {COLORS["orange"]}', 'borderRadius': '4px',
                'padding': '14px 18px', 'minWidth': '120px', 'flex': '1'
            }),
        ], style={
            'display': 'flex', 'gap': '10px', 'marginBottom': '16px', 'flexWrap': 'wrap', 'alignItems': 'stretch'
        }),
        
        # Row 2 - BU Gauge + CRR Trend Chart
        html.Div([
            # Left - BU Completion Gauge
            html.Div([
                html.Div([
                    html.Span("BU completion gauge", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                ], style={'marginBottom': '10px'}),
                dcc.Graph(id='trip-bu-gauge', config={'displayModeBar': False}, 
                         style={'height': '300px'}),
            ], style={
                'flex': '1', 'minWidth': '320px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px'
            }),
            
            # Right - CRR Trend with Clean Threshold
            html.Div([
                html.Div([
                    html.Span("CRR trend", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                    html.Span(" — cuttings return rate with clean-hole threshold", style={'fontSize': '11px', 'color': COLORS['dim']}),
                ], style={'marginBottom': '10px'}),
                dcc.Graph(id='trip-crr-trend', config={'displayModeBar': True, 'displaylogo': False}, 
                         style={'height': '300px'}),
            ], style={
                'flex': '2', 'minWidth': '450px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px'
            }),
        ], style={'display': 'flex', 'gap': '16px', 'marginBottom': '16px', 'flexWrap': 'wrap'}),
        
        # Row 3 - BU Analysis + Secondary Indicators
        html.Div([
            # Left - BU Mode Analysis
            html.Div([
                html.Div([
                    html.Span("BU mode analysis", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                ], style={'marginBottom': '12px'}),
                
                html.Div(id='trip-bu-analysis', children=[
                    html.Div("Analyzing BU sequences...", style={'color': COLORS['muted'], 'fontSize': '12px'})
                ]),
            ], style={
                'flex': '1', 'minWidth': '350px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px', 'minHeight': '260px'
            }),
            
            # Right - Secondary Indicators Panel
            html.Div([
                html.Div([
                    html.Span("Secondary indicators", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                    html.Span(" — warnings and supporting data", style={'fontSize': '11px', 'color': COLORS['dim']}),
                ], style={'marginBottom': '12px'}),
                
                # Secondary indicator badges
                html.Div([
                    # TCR Ratio Badge
                    html.Div([
                        html.Div("TCR RATIO", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginBottom': '2px'}),
                        html.Div(id='trip-tcr-ratio', children="—", style={
                            'fontSize': '20px', 'fontWeight': '600', 'fontFamily': 'JetBrains Mono', 'color': COLORS['orange']
                        }),
                        html.Div(id='trip-tcr-status', children="", style={'fontSize': '8px', 'color': COLORS['dim']}),
                    ], style={
                        'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                        'borderRadius': '4px', 'padding': '10px 14px', 'textAlign': 'center', 'flex': '1'
                    }),
                    
                    # UFO Badge
                    html.Div([
                        html.Div("UFO EVENTS", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginBottom': '2px'}),
                        html.Div(id='trip-ufo-total', children="—", style={
                            'fontSize': '20px', 'fontWeight': '600', 'fontFamily': 'JetBrains Mono', 'color': COLORS['red']
                        }),
                        html.Div(id='trip-ufo-status', children="", style={'fontSize': '8px', 'color': COLORS['dim']}),
                    ], style={
                        'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                        'borderRadius': '4px', 'padding': '10px 14px', 'textAlign': 'center', 'flex': '1'
                    }),
                    
                    # CSD Badge
                    html.Div([
                        html.Div("CSD P50", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginBottom': '2px'}),
                        html.Div(id='trip-csd-value', children="—", style={
                            'fontSize': '20px', 'fontWeight': '600', 'fontFamily': 'JetBrains Mono', 'color': COLORS['purple']
                        }),
                        html.Div(id='trip-csd-trend', children="", style={'fontSize': '8px', 'color': COLORS['dim']}),
                    ], style={
                        'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                        'borderRadius': '4px', 'padding': '10px 14px', 'textAlign': 'center', 'flex': '1'
                    }),
                    
                    # Lag Depth Badge
                    html.Div([
                        html.Div("LAG DEPTH", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginBottom': '2px'}),
                        html.Div(id='trip-lag-depth', children="—", style={
                            'fontSize': '20px', 'fontWeight': '600', 'fontFamily': 'JetBrains Mono', 'color': COLORS['cyan']
                        }),
                        html.Div(id='trip-lag-status', children="", style={'fontSize': '8px', 'color': COLORS['dim']}),
                    ], style={
                        'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                        'borderRadius': '4px', 'padding': '10px 14px', 'textAlign': 'center', 'flex': '1'
                    }),
                ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '16px', 'flexWrap': 'wrap'}),
                
                # Lag Depth Progress Chart
                dcc.Graph(id='trip-lag-progress', config={'displayModeBar': False}, 
                         style={'height': '140px'}),
                         
            ], style={
                'flex': '2', 'minWidth': '450px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px'
            }),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap', 'marginBottom': '16px'}),
        
        # ================================================================
        # ROW 4 - MULTI-WELL CUC COMPARISON (NEW in v3.3.0)
        # ================================================================
        html.Div([
            # Section Header with Expand/Collapse
            html.Div([
                html.Div([
                    html.Span("▼ ", id='multiwell-toggle-icon', style={'fontSize': '10px', 'cursor': 'pointer'}),
                    html.Span("Multi-well CUC comparison", style={'fontSize': '14px', 'fontWeight': '600', 'color': COLORS['text']}),
                    html.Span(" — compare cleanup cycles across multiple wells", style={'fontSize': '11px', 'color': COLORS['dim']}),
                ], style={'display': 'flex', 'alignItems': 'center', 'cursor': 'pointer'}, id='multiwell-header'),
                html.Button("Process All Loaded Wells", id='btn-process-multiwell', n_clicks=0, style={
                    'background': COLORS['orange'], 'color': 'white', 'border': 'none',
                    'borderRadius': '4px', 'padding': '8px 16px', 'fontSize': '11px',
                    'cursor': 'pointer', 'fontWeight': '500'
                }),
            ], style={
                'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
                'marginBottom': '12px', 'paddingBottom': '10px', 'borderBottom': f'1px solid {COLORS["border"]}'
            }),
            
            # Multi-well content (collapsible)
            html.Div([
                # File Upload for Batch Processing
                html.Div([
                    html.Div([
                        html.Div("BATCH UPLOAD", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '6px', 'letterSpacing': '0.5px'}),
                        dcc.Upload(
                            id='upload-multiwell-batch',
                            children=html.Div([
                                "Drop multiple CSV files here or ",
                                html.Span("browse", style={'color': COLORS['orange'], 'textDecoration': 'underline'})
                            ]),
                            style={
                                'padding': '20px', 'border': f'2px dashed {COLORS["border"]}',
                                'borderRadius': '6px', 'textAlign': 'center', 'cursor': 'pointer',
                                'fontSize': '12px', 'color': COLORS['muted']
                            },
                            multiple=True
                        ),
                    ], style={'flex': '1', 'minWidth': '250px'}),
                    
                    # Status and Well Count
                    html.Div([
                        html.Div("WELLS LOADED", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '6px', 'letterSpacing': '0.5px'}),
                        html.Div(id='multiwell-count', children="0", style={
                            'fontSize': '36px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono',
                            'color': COLORS['blue'], 'textAlign': 'center'
                        }),
                        html.Div(id='multiwell-status', children="No wells processed", style={
                            'fontSize': '10px', 'color': COLORS['dim'], 'textAlign': 'center'
                        }),
                    ], style={
                        'flex': '0 0 120px', 'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                        'borderRadius': '6px', 'padding': '12px', 'textAlign': 'center'
                    }),
                    
                    # Export Button
                    html.Div([
                        html.Div("EXPORT", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '6px', 'letterSpacing': '0.5px'}),
                        html.Button("📥 Download Excel", id='btn-export-multiwell', n_clicks=0, style={
                            'background': COLORS['green'], 'color': 'white', 'border': 'none',
                            'borderRadius': '4px', 'padding': '10px 16px', 'fontSize': '11px',
                            'cursor': 'pointer', 'fontWeight': '500', 'width': '100%'
                        }),
                        dcc.Download(id='download-multiwell-excel'),
                    ], style={'flex': '0 0 140px'}),
                ], style={'display': 'flex', 'gap': '12px', 'marginBottom': '16px', 'flexWrap': 'wrap', 'alignItems': 'flex-start'}),
                
                # CUC Comparison Summary Table
                html.Div([
                    html.Div([
                        html.Span("CUC summary table", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                        html.Span(" — key metrics for threshold validation", style={'fontSize': '11px', 'color': COLORS['dim']}),
                    ], style={'marginBottom': '10px'}),
                    html.Div(id='multiwell-cuc-table', children=[
                        html.Div("Process wells to see comparison table", style={
                            'color': COLORS['muted'], 'fontSize': '12px', 'padding': '30px', 'textAlign': 'center'
                        })
                    ], style={'overflowX': 'auto'}),
                ], style={'marginBottom': '16px'}),
                
                # CRR Decay Overlay Chart
                html.Div([
                    html.Div([
                        html.Span("CRR decay comparison", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                        html.Span(" — all wells overlaid from TD", style={'fontSize': '11px', 'color': COLORS['dim']}),
                    ], style={'marginBottom': '10px'}),
                    dcc.Graph(id='multiwell-crr-overlay', config={
                        'displayModeBar': True, 'displaylogo': False,
                        'toImageButtonOptions': {'format': 'png', 'filename': 'crr_overlay', 'scale': 2, 'bgcolor': '#1a1a2e'}
                    }, style={'height': '350px'}),
                ], style={'marginBottom': '16px'}),
                
                # NEW: Normalized CRR vs BU Cycles Chart
                html.Div([
                    html.Div([
                        html.Span("Normalized CRR vs BU cycles", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                        html.Span(" — X-axis normalized by Ref BU time, Y-axis by CRR at TD", style={'fontSize': '11px', 'color': COLORS['dim']}),
                    ], style={'marginBottom': '10px'}),
                    dcc.Graph(id='multiwell-normalized-bu', config={
                        'displayModeBar': True, 'displaylogo': False,
                        'toImageButtonOptions': {'format': 'png', 'filename': 'normalized_bu_cycles', 'scale': 2, 'bgcolor': '#1a1a2e'}
                    }, style={'height': '380px'}),
                ], style={'marginBottom': '16px'}),
                
                # NEW: BU Cycles Bar Chart (like XOM chart)
                html.Div([
                    html.Div([
                        html.Span("BU Cycles to Clean by Well", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                        html.Span(" — bar chart comparing cleanup efficiency across wells", style={'fontSize': '11px', 'color': COLORS['dim']}),
                    ], style={'marginBottom': '10px'}),
                    dcc.Graph(id='multiwell-bu-bar-chart', config={
                        'displayModeBar': True, 'displaylogo': False,
                        'toImageButtonOptions': {'format': 'png', 'filename': 'bu_cycles_bar', 'scale': 2, 'bgcolor': '#1a1a2e'}
                    }, style={'height': '320px'}),
                ], style={'marginBottom': '16px'}),
                
                # Threshold Validation Summary
                html.Div([
                    html.Div([
                        html.Span("Threshold validation", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                        html.Span(" — normalized metrics across wells", style={'fontSize': '11px', 'color': COLORS['dim']}),
                    ], style={'marginBottom': '10px'}),
                    html.Div(id='multiwell-threshold-summary', children=[
                        html.Div([
                            html.Div([
                                html.Div("WELLS REACHING THRESHOLD", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginBottom': '4px'}),
                                html.Div(id='threshold-reached-count', children="—", style={
                                    'fontSize': '28px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['green']
                                }),
                                html.Div(id='threshold-reached-pct', children="", style={'fontSize': '10px', 'color': COLORS['dim']}),
                            ], style={
                                'flex': '1', 'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                                'borderLeft': f'3px solid {COLORS["green"]}', 'borderRadius': '4px',
                                'padding': '12px', 'textAlign': 'center'
                            }),
                            html.Div([
                                html.Div("AVG BU TO CLEAN", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginBottom': '4px'}),
                                html.Div(id='avg-bu-cycles', children="—", style={
                                    'fontSize': '28px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['cyan']
                                }),
                                html.Div("BU cycles", style={'fontSize': '10px', 'color': COLORS['dim']}),
                            ], style={
                                'flex': '1', 'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                                'borderLeft': f'3px solid {COLORS["cyan"]}', 'borderRadius': '4px',
                                'padding': '12px', 'textAlign': 'center'
                            }),
                            html.Div([
                                html.Div("AVG REF BU TIME", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginBottom': '4px'}),
                                html.Div(id='avg-ref-bu-time', children="—", style={
                                    'fontSize': '28px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['blue']
                                }),
                                html.Div("minutes", style={'fontSize': '10px', 'color': COLORS['dim']}),
                            ], style={
                                'flex': '1', 'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                                'borderLeft': f'3px solid {COLORS["blue"]}', 'borderRadius': '4px',
                                'padding': '12px', 'textAlign': 'center'
                            }),
                            html.Div([
                                html.Div("AVG TIME TO CLEAN", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginBottom': '4px'}),
                                html.Div(id='avg-time-to-clean', children="—", style={
                                    'fontSize': '28px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['purple']
                                }),
                                html.Div("minutes", style={'fontSize': '10px', 'color': COLORS['dim']}),
                            ], style={
                                'flex': '1', 'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                                'borderLeft': f'3px solid {COLORS["purple"]}', 'borderRadius': '4px',
                                'padding': '12px', 'textAlign': 'center'
                            }),
                            html.Div([
                                html.Div("AVG EXCESS CIRC", style={'fontSize': '9px', 'color': COLORS['muted'], 'marginBottom': '4px'}),
                                html.Div(id='avg-excess-circ', children="—", style={
                                    'fontSize': '28px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['red']
                                }),
                                html.Div("minutes wasted", style={'fontSize': '10px', 'color': COLORS['dim']}),
                            ], style={
                                'flex': '1', 'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
                                'borderLeft': f'3px solid {COLORS["red"]}', 'borderRadius': '4px',
                                'padding': '12px', 'textAlign': 'center'
                            }),
                        ], style={'display': 'flex', 'gap': '10px', 'flexWrap': 'wrap'}),
                    ]),
                ]),
                
            ], id='multiwell-content', style={'display': 'block'}),  # Visible by default
            
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '16px'
        }),
        
        # Store for multi-well data
        dcc.Store(id='store-multiwell-data', data=[]),
        
    ], style={
        'flex': '1', 'padding': '16px', 'overflowY': 'auto', 'overflowX': 'hidden',
        'background': COLORS['bg'], 'width': '100%', 'boxSizing': 'border-box'
    })


def create_compare_wells_tab():
    """Create the Compare Wells tab content - Phase 4 Implementation."""
    return html.Div([
        # Top Row - Controls and Summary
        html.Div([
            # Left - Well Selector
            html.Div([
                html.Div("SELECT WELLS", style={'fontSize': '11px', 'color': COLORS['muted'], 'marginBottom': '8px', 'letterSpacing': '0.5px'}),
                dcc.Dropdown(
                    id='compare-dataset-selector',
                    options=[],
                    value=[],
                    multi=True,
                    placeholder='Select 2+ datasets to compare...',
                    style={'marginBottom': '8px'}
                ),
                html.Div(id='compare-status', style={'fontSize': '10px', 'color': COLORS['dim']}),
            ], style={
                'flex': '2', 'minWidth': '300px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '14px'
            }),
            
            # Middle - Normalization Mode
            html.Div([
                html.Div("NORMALIZE BY", style={'fontSize': '11px', 'color': COLORS['muted'], 'marginBottom': '8px', 'letterSpacing': '0.5px'}),
                dcc.RadioItems(
                    id='compare-normalization',
                    options=[
                        {'label': ' Depth (m)', 'value': 'depth'},
                        {'label': ' Elapsed Time (hrs)', 'value': 'elapsed'},
                        {'label': ' % Section', 'value': 'percent'},
                    ],
                    value='depth',
                    inline=True,
                    style={'fontSize': '11px'},
                    labelStyle={'marginRight': '16px', 'color': COLORS['text']},
                ),
            ], style={
                'flex': '1', 'minWidth': '280px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '14px'
            }),
            
            # Right - Chart Type
            html.Div([
                html.Div("CHART MODE", style={'fontSize': '11px', 'color': COLORS['muted'], 'marginBottom': '8px', 'letterSpacing': '0.5px'}),
                dcc.RadioItems(
                    id='compare-chart-mode',
                    options=[
                        {'label': ' Overlay', 'value': 'overlay'},
                        {'label': ' Side-by-Side', 'value': 'sidebyside'},
                    ],
                    value='overlay',
                    inline=True,
                    style={'fontSize': '11px'},
                    labelStyle={'marginRight': '16px', 'color': COLORS['text']},
                ),
            ], style={
                'flex': '1', 'minWidth': '200px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '14px'
            }),
        ], style={'display': 'flex', 'gap': '12px', 'marginBottom': '16px', 'flexWrap': 'wrap'}),
        
        # Row 2 - KPI Comparison Table
        html.Div([
            html.Div([
                html.Span("KPI Comparison", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                html.Span(" — Key Metrics by Well", style={'fontSize': '11px', 'color': COLORS['dim']}),
            ], style={'marginBottom': '12px'}),
            html.Div(id='compare-kpi-table', children=[
                html.Div("Select 2 or more wells to compare", style={'color': COLORS['muted'], 'fontSize': '12px', 'padding': '20px', 'textAlign': 'center'})
            ]),
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '16px', 'marginBottom': '16px'
        }),
        
        # Row 3 - TCR Comparison Chart
        html.Div([
            html.Div([
                html.Span("TCR Comparison", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                html.Span(id='compare-tcr-subtitle', children=" — Measured TCR", style={'fontSize': '11px', 'color': COLORS['dim']}),
            ], style={'marginBottom': '10px'}),
            dcc.Graph(id='compare-tcr-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                     style={'height': '320px'}),
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '16px', 'marginBottom': '16px'
        }),
        
        # Row 4 - CRR and CSD Comparison (side by side)
        html.Div([
            # Left - CRR Comparison
            html.Div([
                html.Div([
                    html.Span("CRR Comparison", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                ], style={'marginBottom': '10px'}),
                dcc.Graph(id='compare-crr-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                         style={'height': '280px'}),
            ], style={
                'flex': '1', 'minWidth': '400px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px'
            }),
            
            # Right - UFO Comparison
            html.Div([
                html.Div([
                    html.Span("UFO Events Comparison", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                ], style={'marginBottom': '10px'}),
                dcc.Graph(id='compare-ufo-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                         style={'height': '280px'}),
            ], style={
                'flex': '1', 'minWidth': '400px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '16px'
            }),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap', 'marginBottom': '16px'}),
        
        # Row 5 - Flexible Comparison Chart
        html.Div([
            html.Div([
                html.Span("◇ Flexible Comparison", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                html.Span(" — Compare any parameter across wells", style={'fontSize': '11px', 'color': COLORS['dim']}),
            ], style={'marginBottom': '12px'}),
            
            # Controls row
            html.Div([
                # X-Axis selector
                html.Div([
                    html.Label("X-Axis", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'display': 'block'}),
                    dcc.Dropdown(
                        id='compare-flex-x',
                        placeholder="Select X...",
                        style={'fontSize': '11px'},
                        className='dark-dropdown'
                    ),
                ], style={'flex': '1', 'minWidth': '150px'}),
                
                # Y1 Axis selector
                html.Div([
                    html.Label("Y-Axis (Left)", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'display': 'block'}),
                    dcc.Dropdown(
                        id='compare-flex-y1',
                        placeholder="Select Y1...",
                        multi=True,
                        style={'fontSize': '11px'},
                        className='dark-dropdown'
                    ),
                ], style={'flex': '2', 'minWidth': '200px'}),
                
                # Y2 Axis selector
                html.Div([
                    html.Label("Y-Axis (Right)", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'display': 'block'}),
                    dcc.Dropdown(
                        id='compare-flex-y2',
                        placeholder="Select Y2...",
                        multi=True,
                        style={'fontSize': '11px'},
                        className='dark-dropdown'
                    ),
                ], style={'flex': '2', 'minWidth': '200px'}),
                
                # Normalize toggle
                html.Div([
                    html.Label("Options", style={'fontSize': '10px', 'color': COLORS['muted'], 'marginBottom': '4px', 'display': 'block'}),
                    dcc.Checklist(
                        id='compare-flex-options',
                        options=[
                            {'label': ' Normalize X (start at 0)', 'value': 'normalize_x'},
                        ],
                        value=[],
                        style={'fontSize': '11px'},
                        labelStyle={'color': COLORS['text']},
                    ),
                ], style={'flex': '1', 'minWidth': '150px'}),
            ], style={'display': 'flex', 'gap': '12px', 'marginBottom': '12px', 'flexWrap': 'wrap'}),
            
            # Chart
            dcc.Graph(id='compare-flex-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                     style={'height': '350px'}),
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '16px'
        }),
        
    ], style={
        'flex': '1', 'padding': '16px', 'overflowY': 'auto', 'overflowX': 'hidden',
        'background': COLORS['bg'], 'width': '100%', 'boxSizing': 'border-box'
    })


def create_kpi_modal():
    """Create the KPI add/edit modal."""
    return html.Div([
        html.Div([
            html.Div("Add KPI", style={'fontSize': '16px', 'fontWeight': '600', 'marginBottom': '16px', 'color': COLORS['orange']}),
            
            html.Label("Title", style={'fontSize': '11px', 'color': COLORS['dim']}),
            dcc.Input(id='kpi-title', type='text', placeholder='e.g., Depth Drilled', value='', style={
                'width': '100%', 'padding': '8px', 'background': COLORS['bg'],
                'border': f'1px solid {COLORS["border"]}', 'borderRadius': '4px', 'color': COLORS['text'], 'marginBottom': '12px'
            }),
            
            html.Label("Column", style={'fontSize': '11px', 'color': COLORS['dim']}),
            dcc.Dropdown(id='kpi-col', options=[], placeholder='Select column...', style={'marginBottom': '12px'}),
            
            html.Label("Calculation", style={'fontSize': '11px', 'color': COLORS['dim']}),
            dcc.Dropdown(id='kpi-calc', options=[{'label': v, 'value': k} for k, v in KPI_CALC_TYPES.items()], value='delta', style={'marginBottom': '12px'}),
            
            html.Label("Unit", style={'fontSize': '11px', 'color': COLORS['dim']}),
            dcc.Input(id='kpi-unit', type='text', placeholder='e.g., m, m³, %', value='', style={
                'width': '100%', 'padding': '8px', 'background': COLORS['bg'],
                'border': f'1px solid {COLORS["border"]}', 'borderRadius': '4px', 'color': COLORS['text'], 'marginBottom': '12px'
            }),
            
            html.Label("Color", style={'fontSize': '11px', 'color': COLORS['dim']}),
            dcc.Dropdown(id='kpi-color', options=[
                {'label': '🟠 Orange', 'value': 'orange'},
                {'label': '🔵 Blue', 'value': 'blue'},
                {'label': '🟢 Green', 'value': 'green'},
                {'label': '🟡 Yellow', 'value': 'yellow'},
                {'label': '🟣 Purple', 'value': 'purple'},
                {'label': '🔴 Red', 'value': 'red'},
            ], value='orange', style={'marginBottom': '16px'}),
            
            html.Div([
                html.Button("Cancel", id='kpi-cancel', style={
                    'background': COLORS['border'], 'color': COLORS['text'], 'border': 'none',
                    'padding': '8px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 'marginRight': '10px'
                }),
                html.Button("Add KPI", id='kpi-save', style={
                    'background': COLORS['orange'], 'color': '#FFF', 'border': 'none',
                    'padding': '8px 20px', 'borderRadius': '4px', 'cursor': 'pointer'
                }),
            ], style={'display': 'flex', 'justifyContent': 'flex-end'}),
        ], style={
            'background': COLORS['card'], 'borderRadius': '8px', 'padding': '20px',
            'width': '380px', 'border': f'1px solid {COLORS["border"]}'
        }),
    ], id='kpi-modal', className='modal-overlay')


def create_rename_modal():
    """Create the dataset rename modal."""
    return html.Div([
        html.Div([
            html.Div("✎ Rename Dataset", style={'fontSize': '16px', 'fontWeight': '600', 'marginBottom': '16px', 'color': COLORS['orange']}),
            
            html.Label("Current Name", style={'fontSize': '11px', 'color': COLORS['dim']}),
            html.Div(id='rename-current-name', children="—", style={
                'padding': '8px', 'background': COLORS['bg'], 'borderRadius': '4px',
                'marginBottom': '12px', 'fontSize': '11px', 'fontFamily': 'JetBrains Mono',
                'color': COLORS['muted'], 'wordBreak': 'break-all'
            }),
            
            html.Label("New Name", style={'fontSize': '11px', 'color': COLORS['dim']}),
            dcc.Input(id='rename-new-name', type='text', placeholder='Enter new name...', value='', style={
                'width': '100%', 'padding': '8px', 'background': COLORS['bg'],
                'border': f'1px solid {COLORS["border"]}', 'borderRadius': '4px', 
                'color': COLORS['text'], 'marginBottom': '16px'
            }),
            
            html.Div([
                html.Button("Cancel", id='rename-cancel', style={
                    'background': COLORS['border'], 'color': COLORS['text'], 'border': 'none',
                    'padding': '8px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 'marginRight': '10px'
                }),
                html.Button("Rename", id='rename-save', style={
                    'background': COLORS['orange'], 'color': '#FFF', 'border': 'none',
                    'padding': '8px 20px', 'borderRadius': '4px', 'cursor': 'pointer'
                }),
            ], style={'display': 'flex', 'justifyContent': 'flex-end'}),
        ], style={
            'background': COLORS['card'], 'borderRadius': '8px', 'padding': '20px',
            'width': '400px', 'border': f'1px solid {COLORS["border"]}'
        }),
    ], id='rename-modal', className='modal-overlay')


def create_las_rename_modal():
    """Create the LAS file rename modal."""
    return html.Div([
        html.Div([
            html.Div("✎ Rename LAS File", style={'fontSize': '16px', 'fontWeight': '600', 'marginBottom': '16px', 'color': COLORS['orange']}),
            
            html.Label("Current Name", style={'fontSize': '11px', 'color': COLORS['dim']}),
            html.Div(id='las-rename-current-name', children="—", style={
                'padding': '8px', 'background': COLORS['bg'], 'borderRadius': '4px',
                'marginBottom': '12px', 'fontSize': '11px', 'fontFamily': 'JetBrains Mono',
                'color': COLORS['muted'], 'wordBreak': 'break-all'
            }),
            
            html.Label("New Name", style={'fontSize': '11px', 'color': COLORS['dim']}),
            dcc.Input(id='las-rename-new-name', type='text', placeholder='Enter new name...', value='', style={
                'width': '100%', 'padding': '8px', 'background': COLORS['bg'],
                'border': f'1px solid {COLORS["border"]}', 'borderRadius': '4px', 
                'color': COLORS['text'], 'marginBottom': '16px'
            }),
            
            # Store the original name for the callback
            dcc.Store(id='las-rename-original-name', data=None),
            
            html.Div([
                html.Button("Cancel", id='las-rename-cancel', style={
                    'background': COLORS['border'], 'color': COLORS['text'], 'border': 'none',
                    'padding': '8px 20px', 'borderRadius': '4px', 'cursor': 'pointer', 'marginRight': '10px'
                }),
                html.Button("Rename", id='las-rename-save', style={
                    'background': COLORS['orange'], 'color': '#FFF', 'border': 'none',
                    'padding': '8px 20px', 'borderRadius': '4px', 'cursor': 'pointer'
                }),
            ], style={'display': 'flex', 'justifyContent': 'flex-end'}),
        ], style={
            'background': COLORS['card'], 'borderRadius': '8px', 'padding': '20px',
            'width': '400px', 'border': f'1px solid {COLORS["border"]}'
        }),
    ], id='las-rename-modal', className='modal-overlay')


def create_lwd_pwd_tab():
    """Create the LWD/PWD tab content - Downhole data analysis."""
    return html.Div([
        # Top Row - Upload and File Selector
        html.Div([
            # Left - LAS Upload
            html.Div([
                html.Div("UPLOAD LAS FILES", style={'fontSize': '11px', 'color': COLORS['muted'], 'marginBottom': '8px', 'letterSpacing': '0.5px'}),
                dcc.Upload(id='las-upload', children=html.Div([
                    "Drop LAS files or ", html.Span("browse", style={'color': COLORS['cyan']})
                ], style={'textAlign': 'center', 'fontSize': '11px'}),
                style={'padding': '14px', 'border': f'2px dashed {COLORS["cyan"]}', 'borderRadius': '6px', 'cursor': 'pointer'},
                multiple=True),
                html.Div(id='las-upload-status', style={'marginTop': '6px', 'fontSize': '10px'}),
            ], style={
                'flex': '1', 'minWidth': '250px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '14px'
            }),
            
            # Middle - File Selector
            html.Div([
                html.Div("SELECT LAS FILE", style={'fontSize': '11px', 'color': COLORS['muted'], 'marginBottom': '8px', 'letterSpacing': '0.5px'}),
                dcc.Dropdown(
                    id='las-file-selector',
                    options=[],
                    value=None,
                    placeholder='Select LAS file...',
                    style={'marginBottom': '8px'}
                ),
                html.Div(id='las-file-info', style={'fontSize': '10px', 'color': COLORS['dim']}),
            ], style={
                'flex': '2', 'minWidth': '300px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '14px'
            }),
            
            # Right - View Mode
            html.Div([
                html.Div("VIEW MODE", style={'fontSize': '11px', 'color': COLORS['muted'], 'marginBottom': '8px', 'letterSpacing': '0.5px'}),
                dcc.RadioItems(
                    id='las-view-mode',
                    options=[
                        {'label': ' Single File', 'value': 'single'},
                        {'label': ' Compare Files', 'value': 'compare'},
                    ],
                    value='single',
                    inline=True,
                    style={'fontSize': '11px'},
                    labelStyle={'marginRight': '16px', 'color': COLORS['text']},
                ),
                html.Div([
                    html.Div("Compare Files:", style={'fontSize': '10px', 'color': COLORS['dim'], 'marginTop': '8px'}),
                    dcc.Dropdown(
                        id='las-compare-selector',
                        options=[],
                        value=[],
                        multi=True,
                        placeholder='Select files to compare...',
                    ),
                ], id='las-compare-container', style={'display': 'none'}),
            ], style={
                'flex': '1.5', 'minWidth': '280px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '14px'
            }),
        ], style={'display': 'flex', 'gap': '12px', 'marginBottom': '16px', 'flexWrap': 'wrap'}),
        
        # Row 2 - Channel Selection
        html.Div([
            html.Div([
                html.Span("Channel Selection", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                html.Span(" — Select channels to display", style={'fontSize': '11px', 'color': COLORS['dim']}),
            ], style={'marginBottom': '12px'}),
            html.Div([
                html.Div([
                    html.Label("Index (X-Axis)", style={'fontSize': '10px', 'color': COLORS['muted']}),
                    dcc.Dropdown(id='las-x-axis', placeholder='Select index...', style={'marginBottom': '8px'}),
                ], style={'flex': '1', 'minWidth': '150px'}),
                html.Div([
                    html.Label("Primary Channels (Left Y)", style={'fontSize': '10px', 'color': COLORS['muted']}),
                    dcc.Dropdown(id='las-y1-channels', multi=True, placeholder='Select channels...'),
                ], style={'flex': '2', 'minWidth': '200px'}),
                html.Div([
                    html.Label("Secondary Channels (Right Y)", style={'fontSize': '10px', 'color': COLORS['muted']}),
                    dcc.Dropdown(id='las-y2-channels', multi=True, placeholder='Select channels...'),
                ], style={'flex': '2', 'minWidth': '200px'}),
            ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'}),
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '16px', 'marginBottom': '16px'
        }),
        
        # Row 3 - Main Chart
        html.Div([
            html.Div([
                html.Span("PWD / Caliper Data", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                html.Span(id='las-chart-subtitle', children="", style={'fontSize': '11px', 'color': COLORS['dim'], 'marginLeft': '8px'}),
            ], style={'marginBottom': '10px'}),
            dcc.Graph(id='las-main-chart', config={'displayModeBar': True, 'displaylogo': False}, 
                     style={'height': '400px'}),
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '16px', 'marginBottom': '16px'
        }),
        
        # Row 4 - Secondary Charts (Temperature and ECD)
        html.Div([
            # Temperature Chart
            html.Div([
                html.Div([
                    html.Span("Temperature Profile", style={'fontSize': '12px', 'fontWeight': '600', 'color': COLORS['text']}),
                ], style={'marginBottom': '8px'}),
                dcc.Graph(id='las-temp-chart', config={'displayModeBar': False, 'displaylogo': False}, 
                         style={'height': '280px'}),
            ], style={
                'flex': '1', 'minWidth': '300px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '14px'
            }),
            
            # ECD/Pressure Chart
            html.Div([
                html.Div([
                    html.Span("ECD / Pressure", style={'fontSize': '12px', 'fontWeight': '600', 'color': COLORS['text']}),
                ], style={'marginBottom': '8px'}),
                dcc.Graph(id='las-ecd-chart', config={'displayModeBar': False, 'displaylogo': False}, 
                         style={'height': '280px'}),
            ], style={
                'flex': '1', 'minWidth': '300px',
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '6px', 'padding': '14px'
            }),
        ], style={'display': 'flex', 'gap': '12px', 'marginBottom': '16px', 'flexWrap': 'wrap'}),
        
        # Row 5 - File Summary Table
        html.Div([
            html.Div([
                html.Span("Loaded LAS Files", style={'fontSize': '13px', 'fontWeight': '600', 'color': COLORS['text']}),
                html.Span(" — Summary", style={'fontSize': '11px', 'color': COLORS['dim']}),
                html.Button("⬇ Export All to CSV", id='las-export-all-btn', style={
                    'marginLeft': 'auto', 'background': COLORS['cyan'], 'border': 'none',
                    'color': '#000', 'padding': '6px 12px', 'borderRadius': '4px',
                    'cursor': 'pointer', 'fontSize': '11px', 'fontWeight': '600',
                }),
            ], style={'marginBottom': '12px', 'display': 'flex', 'alignItems': 'center'}),
            html.Div(id='las-files-table', children=[
                html.Div("No LAS files loaded. Upload LAS files above.", 
                        style={'color': COLORS['muted'], 'fontSize': '12px', 'padding': '20px', 'textAlign': 'center'})
            ]),
            # Download components for CSV export
            dcc.Download(id='las-csv-download'),
            dcc.Download(id='las-csv-download-single'),
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '6px', 'padding': '16px'
        }),
        
    ], style={'flex': '1', 'padding': '16px', 'overflowY': 'auto', 'height': 'calc(100vh - 95px)'})


def create_lwd_pwd_tab_full():
    """Create the full LWD/PWD tab layout."""
    return html.Div([
        # Main content (no sidebar needed - all controls inline)
        create_lwd_pwd_tab(),
    ], id='tab-lwd-pwd', style={'display': 'none', 'flex': '1'})


# ============================================================
# MAIN LAYOUT - All tabs in DOM, visibility toggled
# ============================================================

def create_main_tab_full():
    """Create the full Main tab layout."""
    return html.Div([
        # Left Panel - Data & Config
        html.Div([
            create_data_sidebar(),
            create_main_tab_sidebar(),
        ], style={
            'width': '240px', 'padding': '12px', 'background': COLORS['bg'],
            'borderRight': f'1px solid {COLORS["border"]}', 'overflowY': 'auto', 'height': 'calc(100vh - 95px)'
        }),
        
        # Center Panel - Chart
        create_main_tab_content(),
        
        # Right Panel - Columns
        html.Div([
            create_column_browser(),
        ], style={
            'width': '220px', 'padding': '12px', 'background': COLORS['bg'],
            'borderLeft': f'1px solid {COLORS["border"]}', 'overflowY': 'auto', 'height': 'calc(100vh - 95px)'
        }),
    ], id='tab-main', style={'display': 'flex', 'flex': '1'})


def create_hole_cleaning_tab_full():
    """Create the full Hole Cleaning tab layout."""
    return html.Div([
        # Left Panel - Data selector
        html.Div([
            # Duplicate upload for this tab
            html.Div([
                html.Div("▦ DATA", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'marginBottom': '8px', 'letterSpacing': '1px'}),
                dcc.Upload(id='upload-hc', children=html.Div([
                    "Drop CSV/XLSX or ", html.Span("browse", style={'color': COLORS['orange']})
                ], style={'textAlign': 'center', 'fontSize': '11px'}),
                style={'padding': '14px', 'border': f'2px dashed {COLORS["border"]}', 'borderRadius': '6px', 'cursor': 'pointer'}),
                html.Div(id='upload-status-hc', style={'marginTop': '6px', 'fontSize': '10px'}),
            ], style={'marginBottom': '16px'}),
            
            html.Div([
                html.Div("◇ DATASETS", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'marginBottom': '8px', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='dataset-selector-hc', options=[], value=None, placeholder='Select dataset...'),
            ], style={'marginBottom': '16px'}),
        ], style={
            'width': '240px', 'padding': '12px', 'background': COLORS['bg'],
            'borderRight': f'1px solid {COLORS["border"]}', 'overflowY': 'auto', 'height': 'calc(100vh - 95px)'
        }),
        
        # Main content placeholder
        create_hole_cleaning_tab(),
    ], id='tab-hole-cleaning', style={'display': 'none', 'flex': '1'})


def create_tripping_tab_full():
    """Create the full Tripping tab layout."""
    return html.Div([
        # Left Panel - Data selector
        html.Div([
            html.Div([
                html.Div("▦ DATA", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'marginBottom': '8px', 'letterSpacing': '1px'}),
                dcc.Upload(id='upload-trip', children=html.Div([
                    "Drop CSV/XLSX or ", html.Span("browse", style={'color': COLORS['orange']})
                ], style={'textAlign': 'center', 'fontSize': '11px'}),
                style={'padding': '14px', 'border': f'2px dashed {COLORS["border"]}', 'borderRadius': '6px', 'cursor': 'pointer'}),
                html.Div(id='upload-status-trip', style={'marginTop': '6px', 'fontSize': '10px'}),
            ], style={'marginBottom': '16px'}),
            
            html.Div([
                html.Div("◇ DATASETS", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['dim'], 'marginBottom': '8px', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='dataset-selector-trip', options=[], value=None, placeholder='Select dataset...'),
            ], style={'marginBottom': '16px'}),
        ], style={
            'width': '240px', 'padding': '12px', 'background': COLORS['bg'],
            'borderRight': f'1px solid {COLORS["border"]}', 'overflowY': 'auto', 'height': 'calc(100vh - 95px)'
        }),
        
        # Main content placeholder
        create_tripping_tab(),
    ], id='tab-tripping', style={'display': 'none', 'flex': '1'})


app.layout = html.Div([
    # Header
    create_header(),
    
    # Tab Bar
    create_tab_bar(),
    
    # All Tab Contents - always in DOM, visibility toggled
    html.Div([
        create_main_tab_full(),
        create_hole_cleaning_tab_full(),
        create_tripping_tab_full(),
        html.Div(id='tab-compare', children=[create_compare_wells_tab()], style={'display': 'none', 'flex': '1'}),
        create_lwd_pwd_tab_full(),
    ], id='tab-container', style={'flex': '1', 'display': 'flex', 'overflow': 'hidden'}),
    
    # KPI Modal
    create_kpi_modal(),
    
    # Rename Modal
    create_rename_modal(),
    
    # LAS Rename Modal
    create_las_rename_modal(),
    
    # Stores
    dcc.Store(id='store-subplots', data=[]),
    dcc.Store(id='store-kpis', data=[]),
    dcc.Store(id='store-datasets', data=[]),
    dcc.Store(id='store-active-dataset', data=None),
    dcc.Store(id='store-compare-datasets', data=[]),
    dcc.Store(id='store-las-files', data=[]),
    dcc.Store(id='store-refresh', data=0),
    dcc.Store(id='store-initialized', data=False),
    dcc.Store(id='store-theme', data=SESSION.theme),  # Theme storage
    dcc.Interval(id='autosave', interval=30000),
    dcc.Interval(id='init-interval', interval=500, max_intervals=1),  # Fires once on page load
    
    # Notification
    html.Div(id='notif', style={'position': 'fixed', 'top': '60px', 'right': '16px', 'zIndex': 9999}),
    
], style={
    'fontFamily': 'Inter, sans-serif', 
    'background': COLORS['bg'], 
    'color': COLORS['text'], 
    'minHeight': '100vh', 
    'display': 'flex', 
    'flexDirection': 'column'
}, id='app-container')


# ============================================================
# CALLBACKS
# ============================================================

# ============================================================
# INITIALIZATION CALLBACK - Populates dropdowns on page load
# ============================================================

@app.callback(
    [Output('las-file-selector', 'options', allow_duplicate=True),
     Output('las-file-selector', 'value', allow_duplicate=True),
     Output('las-compare-selector', 'options', allow_duplicate=True),
     Output('dataset-selector', 'options', allow_duplicate=True),
     Output('dataset-selector', 'value', allow_duplicate=True),
     Output('dataset-selector-hc', 'options', allow_duplicate=True),
     Output('dataset-selector-trip', 'options', allow_duplicate=True),
     Output('quick-load-selector', 'options')],
    [Input('init-interval', 'n_intervals')],
    prevent_initial_call=True
)
def initialize_dropdowns(n_intervals):
    """Initialize all dropdowns on page load from session data."""
    # LAS file options
    las_list = SESSION.get_las_list()
    las_options = [{'label': name, 'value': name} for name in las_list]
    active_las = SESSION.active_las if SESSION.active_las in las_list else (las_list[0] if las_list else None)
    
    # Dataset options
    dataset_names = list(SESSION.datasets.keys())
    dataset_options = [{'label': name, 'value': name} for name in dataset_names]
    active_dataset = SESSION.active_dataset if SESSION.active_dataset in dataset_names else (dataset_names[0] if dataset_names else None)
    
    # Quick Load options - scan for CSV files in current directory and common locations
    quick_load_options = []
    try:
        import os
        # Try multiple possible locations
        possible_paths = [
            os.getcwd(),  # Current directory
            os.path.dirname(os.path.abspath(__file__)),  # Script directory
            os.path.join(os.getcwd(), 'data'),  # data subfolder
        ]
        
        csv_files_found = set()
        for project_path in possible_paths:
            if os.path.exists(project_path):
                for f in os.listdir(project_path):
                    if f.endswith('.csv') and 'Data_Export' in f and f not in csv_files_found:
                        csv_files_found.add(f)
                        # Extract well name from filename
                        label = f.replace('Data_Export__Rig_Data___', '').replace('_dataasjoinbyfield', ' ').replace('.csv', '')
                        # Clean up the label
                        parts = label.split('_')
                        if len(parts) >= 2:
                            well = parts[0].replace('2D', '2-D-')
                            section = parts[1].replace('_', ' ').strip()
                            label = f"{well} ({section})"
                        quick_load_options.append({'label': label, 'value': os.path.join(project_path, f)})
        
        quick_load_options = sorted(quick_load_options, key=lambda x: x['label'])
    except Exception as e:
        print(f"Error scanning for CSV files: {e}")
    
    return (
        las_options, active_las, las_options,  # LAS dropdowns
        dataset_options, active_dataset,  # Main dataset selector
        dataset_options, dataset_options,  # HC and Trip selectors
        quick_load_options  # Quick Load selector
    )


# ============================================================
# QUICK LOAD CALLBACK - Load CSV from project folder
# ============================================================

@app.callback(
    [Output('store-datasets', 'data', allow_duplicate=True),
     Output('store-active-dataset', 'data', allow_duplicate=True),
     Output('store-refresh', 'data', allow_duplicate=True),
     Output('quick-load-status', 'children')],
    [Input('quick-load-selector', 'value')],
    [State('store-refresh', 'data')],
    prevent_initial_call=True
)
def handle_quick_load(filepath, refresh_count):
    """Load a CSV file directly from the selected path."""
    if not filepath:
        raise PreventUpdate
    
    import os
    
    if not os.path.exists(filepath):
        return no_update, no_update, no_update, html.Span(f"✗ File not found", style={'color': COLORS['red']})
    
    try:
        # Read the file with proper encoding (UTF-16-LE for these files)
        df = None
        for encoding in ['utf-16-le', 'utf-16', 'utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(filepath, encoding=encoding, sep='\t')
                if len(df.columns) > 1:
                    break
                # Try comma separator
                df = pd.read_csv(filepath, encoding=encoding, sep=',')
                if len(df.columns) > 1:
                    break
            except:
                continue
        
        if df is None or df.empty:
            return no_update, no_update, no_update, html.Span(f"✗ Could not parse file", style={'color': COLORS['red']})
        
        # Clean column names
        df.columns = [c.strip().strip('"').strip() for c in df.columns]
        
        # Generate a clean name from filename
        filename = os.path.basename(filepath)
        name = filename.replace('Data_Export__Rig_Data___', '').replace('_dataasjoinbyfield', '').replace('.csv', '')
        name = name.replace('_', ' ').replace('2D', '2-D-').strip()
        
        # Clean up timestamp
        parts = name.split(' ')
        if len(parts) > 2:
            name = ' '.join(parts[:2])  # Just well and section
        
        # Avoid duplicates
        base_name = name
        counter = 1
        while name in SESSION.datasets:
            name = f"{base_name} ({counter})"
            counter += 1
        
        # Store the dataset
        SESSION.add_dataset(name, df)
        
        # Return updated state
        dataset_names = list(SESSION.datasets.keys())
        new_refresh = (refresh_count or 0) + 1
        
        status = html.Span(f"✓ Loaded: {name}", style={'color': COLORS['green']})
        return dataset_names, name, new_refresh, status
        
    except Exception as e:
        return no_update, no_update, no_update, html.Span(f"✗ Error: {str(e)[:40]}", style={'color': COLORS['red']})


@app.callback(
    [Output('tab-main', 'style'),
     Output('tab-hole-cleaning', 'style'),
     Output('tab-tripping', 'style'),
     Output('tab-compare', 'style'),
     Output('tab-lwd-pwd', 'style')],
    [Input('main-tabs', 'value')]
)
def toggle_tab_visibility(tab):
    """Toggle tab visibility instead of recreating content."""
    SESSION.active_tab = tab
    SESSION.save()
    
    # Base styles
    visible = {'display': 'flex', 'flex': '1'}
    hidden = {'display': 'none', 'flex': '1'}
    
    return (
        visible if tab == 'main' else hidden,
        visible if tab == 'hole-cleaning' else hidden,
        visible if tab == 'tripping' else hidden,
        visible if tab == 'compare' else hidden,
        visible if tab == 'lwd-pwd' else hidden,
    )


@app.callback(
    Output('header-dataset-indicator', 'children'),
    [Input('store-active-dataset', 'data'), Input('main-tabs', 'value')]
)
def update_header_indicator(active, tab):
    """Update the header dataset indicator."""
    if not active:
        return "No dataset loaded"
    return f"{active}"


@app.callback(
    [Output('store-datasets', 'data'),
     Output('store-active-dataset', 'data'),
     Output('store-refresh', 'data')],
    [Input('upload-visible', 'contents'),
     Input('upload-hc', 'contents'),
     Input('upload-trip', 'contents')],
    [State('upload-visible', 'filename'),
     State('upload-hc', 'filename'),
     State('upload-trip', 'filename'),
     State('store-refresh', 'data')]
)
def handle_upload(contents_main, contents_hc, contents_trip, 
                  filename_main, filename_hc, filename_trip, refresh_count):
    """Handle file upload from any tab."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Determine which upload was triggered
    if trigger == 'upload-visible' and contents_main:
        contents, filename = contents_main, filename_main
    elif trigger == 'upload-hc' and contents_hc:
        contents, filename = contents_hc, filename_hc
    elif trigger == 'upload-trip' and contents_trip:
        contents, filename = contents_trip, filename_trip
    else:
        raise PreventUpdate
    
    df, err = parse_file(contents, filename)
    if err:
        print(f"Upload error: {err}")
        raise PreventUpdate
    
    SESSION.add_dataset(filename, df)
    
    return SESSION.get_dataset_list(), SESSION.active_dataset, (refresh_count or 0) + 1


@app.callback(
    [Output('upload-status', 'children'),
     Output('dataset-selector', 'options'),
     Output('dataset-selector', 'value'),
     Output('upload-status-hc', 'children'),
     Output('dataset-selector-hc', 'options'),
     Output('dataset-selector-hc', 'value'),
     Output('upload-status-trip', 'children'),
     Output('dataset-selector-trip', 'options'),
     Output('dataset-selector-trip', 'value'),
     Output('compare-dataset-selector', 'options'),
     Output('store-active-dataset', 'data', allow_duplicate=True)],
    [Input('store-refresh', 'data'), 
     Input('dataset-selector', 'value'),
     Input('dataset-selector-hc', 'value'),
     Input('dataset-selector-trip', 'value')],
    [State('store-datasets', 'data'), State('store-active-dataset', 'data')],
    prevent_initial_call=True
)
def update_dataset_ui(refresh, selected_main, selected_hc, selected_trip, datasets_store, active_store):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # Handle dataset selection from any tab
    new_active = SESSION.active_dataset
    if trigger == 'dataset-selector' and selected_main:
        SESSION.active_dataset = selected_main
        new_active = selected_main
        SESSION.save()
    elif trigger == 'dataset-selector-hc' and selected_hc:
        SESSION.active_dataset = selected_hc
        new_active = selected_hc
        SESSION.save()
    elif trigger == 'dataset-selector-trip' and selected_trip:
        SESSION.active_dataset = selected_trip
        new_active = selected_trip
        SESSION.save()
    
    # Build options
    dataset_names = SESSION.get_dataset_list()
    options = [{'label': f"📄 {name}", 'value': name} for name in dataset_names]
    
    active = SESSION.active_dataset
    
    if dataset_names:
        status = html.Span(f"{len(dataset_names)} dataset(s) loaded", style={'color': COLORS['green']})
    else:
        status = html.Span("No data", style={'color': COLORS['muted']})
    
    # Return same status/options/value for all tabs to keep them in sync
    # Also update store-active-dataset to trigger chart refresh
    return (status, options, active,    # Main tab
            status, options, active,    # Hole Cleaning tab
            status, options, active,    # Tripping tab
            options,                     # Compare tab
            new_active)                  # Update store to trigger chart refresh


@app.callback(
    [Output('main-x', 'options'), Output('main-y1', 'options'), Output('main-y2', 'options'),
     Output('col-list', 'children'), Output('data-stats', 'children'),
     Output('main-x', 'value'), Output('main-y1', 'value'), Output('main-y2', 'value'),
     Output('store-subplots', 'data'), Output('store-kpis', 'data'),
     Output('kpi-col', 'options')],
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data'), Input('col-search', 'value')]
)
def update_column_options(active_dataset, refresh, search):
    df = SESSION.get_df()
    
    if df is None:
        return (
            [], [], [], 
            html.Div("Upload a file", style={'padding': '12px', 'color': COLORS['muted'], 'textAlign': 'center'}),
            [], None, [], [], [], [], []
        )
    
    all_cols, num_cols, dt_cols = get_columns_info(df)
    
    # X options - start with CSV data
    x_opts = [{'label': 'Index', 'value': '__index__'}]
    for c in dt_cols:
        x_opts.append({'label': f'{c} (datetime)', 'value': c})
    for c in all_cols:
        if c not in dt_cols:
            x_opts.append({'label': c, 'value': c})
    
    # Y options - start with CSV data
    y_opts = [{'label': c, 'value': c} for c in num_cols]
    
    # Add LAS channels if loaded
    las_list = SESSION.get_las_list()
    if las_list:
        # Add separator
        x_opts.append({'label': '─── LAS Data ───', 'value': '__las_sep__', 'disabled': True})
        y_opts.append({'label': '─── LAS Data ───', 'value': '__las_sep__', 'disabled': True})
        
        for las_name in las_list:
            parser = SESSION.get_las_parser(las_name)
            if not parser:
                continue
            
            # Get channels with friendly names
            all_las_cols = [parser.get_index_column()] + parser.get_data_channels()
            
            for ch in all_las_cols:
                if ch is None:
                    continue
                friendly_label = parser.get_channel_label(ch)
                value = f"LAS:{las_name}:{ch}"
                
                # Add to X options (index columns and numeric)
                x_opts.append({'label': f'[LAS] {las_name}: {friendly_label}', 'value': value})
                
                # Add to Y options (skip time-like columns)
                if ch.upper() not in ['TIME', 'TIMESTAMP'] and ch not in ['Elapsed_Hours', 'Elapsed_Minutes', 'Time_Index']:
                    y_opts.append({'label': f'[LAS] {las_name}: {friendly_label}', 'value': value})
    
    # Column list
    search_term = (search or '').lower()
    filtered = [c for c in all_cols if search_term in c.lower()] if search_term else all_cols
    
    col_items = []
    for c in filtered:
        is_num = c in num_cols
        is_dt = c in dt_cols
        badge = ('NUM', COLORS['blue']) if is_num else ('DT', COLORS['purple']) if is_dt else ('TXT', COLORS['muted'])
        
        stats_text = ''
        if is_num:
            try:
                mn, mx = df[c].min(), df[c].max()
                stats_text = f"{mn:.1f} → {mx:.1f}"
            except:
                pass
        
        col_items.append(html.Div([
            html.Div([
                html.Span(badge[0], style={
                    'background': badge[1], 'color': '#FFF', 'padding': '1px 4px',
                    'borderRadius': '2px', 'fontSize': '8px', 'marginRight': '6px'
                }),
                html.Span(c, style={'fontSize': '10px', 'fontFamily': 'JetBrains Mono'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            html.Div(stats_text, style={'fontSize': '8px', 'color': COLORS['muted'], 'marginLeft': '24px'}) if stats_text else None,
        ], style={'padding': '5px 6px', 'borderBottom': f'1px solid {COLORS["border"]}'}))
    
    # Add LAS files to column browser
    if las_list:
        col_items.append(html.Div([
            html.Span("LAS", style={
                'background': COLORS['cyan'], 'color': '#FFF', 'padding': '1px 4px',
                'borderRadius': '2px', 'fontSize': '8px', 'marginRight': '6px'
            }),
            html.Span(f"{len(las_list)} LAS file(s) loaded", style={'fontSize': '10px', 'color': COLORS['cyan']}),
        ], style={'padding': '8px 6px', 'borderTop': f'2px solid {COLORS["cyan"]}', 'marginTop': '8px'}))
    
    stats_text = f"▦ {len(df):,} rows · {len(all_cols)} cols · {len(num_cols)} numeric"
    if las_list:
        stats_text += f" · ≋ {len(las_list)} LAS"
    stats = html.Div([stats_text])
    
    cfg = SESSION.main_config
    
    return (
        x_opts, y_opts, y_opts, col_items, stats,
        cfg.get('x'), cfg.get('y1', []), cfg.get('y2', []),
        SESSION.subplots, SESSION.kpis, y_opts
    )


@app.callback(
    Output('chart', 'figure'),
    [Input('main-x', 'value'), Input('main-y1', 'value'), Input('main-y2', 'value'),
     Input('chart-type', 'value'), Input('store-subplots', 'data'), Input('store-active-dataset', 'data')]
)
def update_chart(x, y1, y2, ctype, subplots, active_dataset):
    SESSION.main_config = {'x': x, 'y1': y1 or [], 'y2': y2 or [], 'type': ctype or 'line'}
    SESSION.subplots = subplots or []
    return create_chart(SESSION.get_df(), SESSION.main_config, SESSION.subplots)


@app.callback(
    [Output('store-subplots', 'data', allow_duplicate=True),
     Output('subplot-list', 'children')],
    [Input('btn-add-subplot', 'n_clicks'),
     Input({'type': 'sp-remove', 'index': ALL}, 'n_clicks'),
     Input({'type': 'sp-x', 'index': ALL}, 'value'),
     Input({'type': 'sp-y1', 'index': ALL}, 'value'),
     Input({'type': 'sp-y2', 'index': ALL}, 'value')],
    [State('store-subplots', 'data'), State('main-y1', 'options')],
    prevent_initial_call=True
)
def manage_subplots(add_click, remove_clicks, x_vals, y1_vals, y2_vals, subplots, y_opts):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger = ctx.triggered[0]['prop_id']
    subplots = list(subplots) if subplots else []
    
    # Add subplot
    if 'btn-add-subplot' in trigger:
        subplots.append({'x': '__index__', 'y1': [], 'y2': []})
    
    # Remove subplot
    elif 'sp-remove' in trigger:
        try:
            idx = json.loads(trigger.split('.')[0])['index']
            if 0 <= idx < len(subplots):
                subplots.pop(idx)
        except:
            pass
    
    # Update subplot config
    elif any(t in trigger for t in ['sp-x', 'sp-y1', 'sp-y2']):
        for i in range(len(subplots)):
            if i < len(x_vals):
                subplots[i]['x'] = x_vals[i]
            if i < len(y1_vals):
                subplots[i]['y1'] = y1_vals[i] or []
            if i < len(y2_vals):
                subplots[i]['y2'] = y2_vals[i] or []
    
    SESSION.subplots = subplots
    SESSION.save()
    
    # Build UI
    df = SESSION.get_df()
    all_cols, num_cols, dt_cols = get_columns_info(df) if df is not None else ([], [], [])
    
    x_opts = [{'label': 'Index', 'value': '__index__'}]
    for c in dt_cols:
        x_opts.append({'label': f'◷ {c}', 'value': c})
    for c in all_cols:
        if c not in dt_cols:
            x_opts.append({'label': c, 'value': c})
    
    y_opts_list = [{'label': c, 'value': c} for c in num_cols]
    
    sp_ui = []
    for i, sp in enumerate(subplots):
        sp_ui.append(html.Div([
            html.Div([
                html.Span(f"Subplot {i+1}", style={'fontSize': '10px', 'fontWeight': '600', 'color': COLORS['orange']}),
                html.Button("×", id={'type': 'sp-remove', 'index': i}, style={
                    'background': 'none', 'border': 'none', 'color': COLORS['red'],
                    'cursor': 'pointer', 'fontSize': '14px', 'padding': '0', 'lineHeight': '1'
                }),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '6px'}),
            html.Label("X-Axis", style={'fontSize': '8px', 'color': COLORS['muted']}),
            dcc.Dropdown(id={'type': 'sp-x', 'index': i}, options=x_opts, value=sp.get('x', '__index__'), clearable=False, style={'fontSize': '10px'}),
            html.Label("Y-Left", style={'fontSize': '8px', 'color': COLORS['muted'], 'marginTop': '4px', 'display': 'block'}),
            dcc.Dropdown(id={'type': 'sp-y1', 'index': i}, options=y_opts_list, value=sp.get('y1', []), multi=True, style={'fontSize': '10px'}),
            html.Label("Y-Right", style={'fontSize': '8px', 'color': COLORS['muted'], 'marginTop': '4px', 'display': 'block'}),
            dcc.Dropdown(id={'type': 'sp-y2', 'index': i}, options=y_opts_list, value=sp.get('y2', []), multi=True, style={'fontSize': '10px'}),
        ], style={
            'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}',
            'borderRadius': '4px', 'padding': '8px', 'marginBottom': '8px'
        }))
    
    return subplots, sp_ui


# KPI Modal control
@app.callback(
    Output('kpi-modal', 'className'),
    [Input('btn-add-kpi', 'n_clicks'),
     Input('kpi-cancel', 'n_clicks'),
     Input('kpi-save', 'n_clicks')],
    [State('kpi-modal', 'className')],
    prevent_initial_call=True
)
def toggle_kpi_modal(add_click, cancel_click, save_click, current_class):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger == 'btn-add-kpi':
        return 'modal-overlay show'
    else:
        return 'modal-overlay'


# KPI Save and render
@app.callback(
    [Output('store-kpis', 'data', allow_duplicate=True),
     Output('kpi-list', 'children'),
     Output('kpi-title', 'value'),
     Output('kpi-unit', 'value')],
    [Input('kpi-save', 'n_clicks'),
     Input({'type': 'kpi-remove', 'index': ALL}, 'n_clicks'),
     Input('store-kpis', 'data'),
     Input('store-active-dataset', 'data')],
    [State('kpi-title', 'value'),
     State('kpi-col', 'value'),
     State('kpi-calc', 'value'),
     State('kpi-unit', 'value'),
     State('kpi-color', 'value')],
    prevent_initial_call=True
)
def manage_kpis(save_click, remove_clicks, kpis_store, active_dataset, title, col, calc, unit, color):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger = ctx.triggered[0]['prop_id']
    kpis = SESSION.kpis
    df = SESSION.get_df()
    
    # Save new KPI
    if 'kpi-save' in trigger:
        if title and col and calc:
            SESSION.add_kpi({
                'title': title,
                'column': col,
                'calc': calc,
                'unit': unit or '',
                'color': color or 'orange'
            })
            kpis = SESSION.kpis
    
    # Remove KPI
    elif 'kpi-remove' in trigger:
        try:
            idx = json.loads(trigger.split('.')[0])['index']
            if 0 <= idx < len(kpis):
                SESSION.remove_kpi(kpis[idx].get('id'))
                kpis = SESSION.kpis
        except:
            pass
    
    # Build KPI cards
    kpi_cards = []
    for i, kpi in enumerate(kpis):
        value = calculate_kpi(df, kpi)
        color_val = COLORS.get(kpi.get('color', 'orange'), COLORS['orange'])
        
        kpi_cards.append(html.Div([
            html.Div([
                html.Span(kpi.get('title', 'KPI'), style={
                    'fontSize': '9px', 'color': COLORS['muted'], 
                    'textTransform': 'uppercase', 'letterSpacing': '0.5px'
                }),
                html.Button("×", id={'type': 'kpi-remove', 'index': i}, style={
                    'background': 'none', 'border': 'none', 'color': COLORS['muted'],
                    'cursor': 'pointer', 'fontSize': '12px', 'padding': '0', 'lineHeight': '1'
                }),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '4px'}),
            html.Div(value, style={
                'fontSize': '22px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono',
                'color': color_val, 'lineHeight': '1.1'
            }),
            html.Div(KPI_CALC_TYPES.get(kpi.get('calc', ''), ''), style={
                'fontSize': '8px', 'color': COLORS['dim'], 'marginTop': '2px'
            }),
        ], style={
            'background': COLORS['bg'], 'border': f'1px solid {COLORS["border"]}',
            'borderLeft': f'3px solid {color_val}', 'borderRadius': '4px',
            'padding': '10px 12px', 'minWidth': '140px', 'flex': '1'
        }))
    
    if not kpi_cards:
        kpi_cards = [html.Div("Click '+ Add KPI' to create engineering metrics", 
                             style={'color': COLORS['muted'], 'fontSize': '11px', 'padding': '10px'})]
    
    # Clear form after save
    clear_title = '' if 'kpi-save' in trigger else no_update
    clear_unit = '' if 'kpi-save' in trigger else no_update
    
    return kpis, kpi_cards, clear_title, clear_unit


@app.callback(Output('autosave', 'n_intervals'), [Input('autosave', 'n_intervals')])
def autosave(_):
    SESSION.save()
    return _


# Rename Modal callbacks
@app.callback(
    [Output('rename-modal', 'className'),
     Output('rename-current-name', 'children'),
     Output('rename-new-name', 'value')],
    [Input('btn-rename-dataset', 'n_clicks'),
     Input('rename-cancel', 'n_clicks'),
     Input('rename-save', 'n_clicks')],
    [State('rename-modal', 'className'),
     State('store-active-dataset', 'data')],
    prevent_initial_call=True
)
def toggle_rename_modal(open_click, cancel_click, save_click, current_class, active_dataset):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger == 'btn-rename-dataset':
        if active_dataset:
            return 'modal-overlay show', active_dataset, ''
        raise PreventUpdate
    else:
        return 'modal-overlay', '', ''


@app.callback(
    [Output('store-refresh', 'data', allow_duplicate=True),
     Output('store-active-dataset', 'data', allow_duplicate=True)],
    [Input('rename-save', 'n_clicks')],
    [State('rename-new-name', 'value'),
     State('store-active-dataset', 'data'),
     State('store-refresh', 'data')],
    prevent_initial_call=True
)
def save_rename(save_click, new_name, current_name, refresh_count):
    if not save_click or not new_name or not current_name:
        raise PreventUpdate
    
    new_name = new_name.strip()
    if not new_name:
        raise PreventUpdate
    
    success = SESSION.rename_dataset(current_name, new_name)
    
    if success:
        return (refresh_count or 0) + 1, new_name
    raise PreventUpdate


@app.callback(Output('notif', 'children'), [Input('btn-save', 'n_clicks')], prevent_initial_call=True)
def save_workspace(_):
    SESSION.save()
    return html.Div("✅ Saved", style={
        'background': COLORS['green'], 'color': '#FFF', 'padding': '8px 16px',
        'borderRadius': '4px', 'fontSize': '11px'
    })


# Theme toggle callback - triggers page reload to apply new theme
@app.callback(
    [Output('store-theme', 'data'),
     Output('theme-toggle', 'children'),
     Output('notif', 'children', allow_duplicate=True)],
    Input('theme-toggle', 'n_clicks'),
    State('store-theme', 'data'),
    prevent_initial_call=True
)
def toggle_theme(n_clicks, current_theme):
    """Toggle between dark and light themes."""
    if not n_clicks:
        raise PreventUpdate
    
    # Toggle theme
    new_theme = 'light' if current_theme == 'dark' else 'dark'
    
    # Update session and global COLORS
    SESSION.theme = new_theme
    global COLORS
    COLORS.update(get_theme_colors(new_theme))
    SESSION.save()
    
    # Update button icon
    icon = '🌙' if new_theme == 'light' else '☀'
    
    # Notification with reload prompt
    notif = html.Div([
        html.Span(f"Theme changed to {new_theme}. "),
        html.A("Reload page", href="javascript:location.reload()", style={'color': '#FFF', 'textDecoration': 'underline'}),
        html.Span(" to apply.")
    ], style={
        'background': COLORS['blue'], 'color': '#FFF', 'padding': '10px 16px',
        'borderRadius': '4px', 'fontSize': '12px'
    })
    
    return new_theme, icon, notif


# ============================================================
# HOLE CLEANING TAB CALLBACKS
# ============================================================

def find_column(df, patterns):
    """Find column matching any of the patterns (case-insensitive)."""
    if df is None:
        return None
    cols_lower = {c.lower(): c for c in df.columns}
    for pattern in patterns:
        for cl, c in cols_lower.items():
            if pattern.lower() in cl:
                return c
    return None


def create_empty_figure(message="No data available"):
    """Create an empty figure with a message."""
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text']),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
        annotations=[dict(
            text=message, xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color=COLORS['muted'])
        )],
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


@app.callback(
    [Output('hc-tcr-ratio', 'children'),
     Output('hc-tcr-ratio', 'style'),
     Output('hc-measured-tcr', 'children'),
     Output('hc-theoretical-tcr', 'children'),
     Output('hc-excess-deficit', 'children'),
     Output('hc-excess-deficit', 'style'),
     Output('hc-excess-pct', 'children'),
     Output('hc-csd-p50', 'children'),
     Output('hc-ufo-count', 'children'),
     Output('hc-ufo-rate', 'children')],
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_hole_cleaning_kpis(active_dataset, refresh):
    """Update Hole Cleaning tab KPI cards."""
    df = SESSION.get_df()
    
    # Default styles
    default_style = {'fontSize': '28px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['orange']}
    excess_style = {'fontSize': '28px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 'color': COLORS['green']}
    
    if df is None or df.empty:
        return ("—", default_style, "—", "—", "—", excess_style, "", "—", "—", "")
    
    # Find columns
    measured_col = find_column(df, ['measured tcr', 'measured_tcr'])
    theoretical_col = find_column(df, ['theoretical lag tcr', 'theoretical_lag_tcr', 'theoretical tcr'])
    csd_col = find_column(df, ['csd p50', 'csd_p50'])
    ufo_col = find_column(df, ['ufo count', 'ufo_count'])
    time_col = find_column(df, ['time'])
    depth_col = find_column(df, ['hole depth'])
    
    # TCR Values
    measured_tcr = "—"
    theoretical_tcr = "—"
    tcr_ratio = "—"
    excess = "—"
    excess_pct = ""
    
    if measured_col and measured_col in df.columns:
        meas_val = df[measured_col].dropna().iloc[-1] if len(df[measured_col].dropna()) > 0 else None
        if meas_val is not None:
            measured_tcr = f"{meas_val:.1f}"
            
            if theoretical_col and theoretical_col in df.columns:
                theo_val = df[theoretical_col].dropna().iloc[-1] if len(df[theoretical_col].dropna()) > 0 else None
                if theo_val is not None and theo_val > 0:
                    theoretical_tcr = f"{theo_val:.1f}"
                    ratio = meas_val / theo_val
                    tcr_ratio = f"{ratio:.2f}"
                    
                    # Color based on ratio
                    if ratio < 0.85:
                        ratio_color = COLORS['yellow']  # Under-recovery
                    elif ratio <= 1.10:
                        ratio_color = COLORS['green']   # Normal
                    elif ratio <= 1.25:
                        ratio_color = COLORS['yellow']  # Warning
                    else:
                        ratio_color = COLORS['red']     # Over-recovery / Critical
                    
                    default_style = {**default_style, 'color': ratio_color}
                    
                    # Excess/Deficit
                    diff = meas_val - theo_val
                    pct = ((meas_val - theo_val) / theo_val) * 100 if theo_val > 0 else 0
                    
                    if diff >= 0:
                        excess = f"+{diff:.1f}"
                        excess_style = {**excess_style, 'color': COLORS['green'] if pct < 15 else COLORS['yellow']}
                    else:
                        excess = f"{diff:.1f}"
                        excess_style = {**excess_style, 'color': COLORS['yellow']}
                    
                    excess_pct = f"{pct:+.1f}% vs theoretical"
    
    # CSD P50
    csd_p50 = "—"
    if csd_col and csd_col in df.columns:
        csd_data = df[csd_col].dropna()
        if len(csd_data) > 0:
            csd_p50 = f"{csd_data.median():.1f}"
    
    # UFO Count
    ufo_count = "—"
    ufo_rate = ""
    if ufo_col and ufo_col in df.columns:
        ufo_data = df[ufo_col].dropna()
        if len(ufo_data) > 0:
            total_ufo = ufo_data.iloc[-1]  # Cumulative
            ufo_count = f"{int(total_ufo)}"
            
            # Calculate rate per 100m if depth available
            if depth_col and depth_col in df.columns:
                depth_data = df[depth_col].dropna()
                if len(depth_data) > 0:
                    depth_drilled = depth_data.iloc[-1] - depth_data.iloc[0]
                    if depth_drilled > 0:
                        rate_per_100m = (total_ufo / depth_drilled) * 100
                        ufo_rate = f"{rate_per_100m:.1f} per 100m"
    
    return (tcr_ratio, default_style, measured_tcr, theoretical_tcr, 
            excess, excess_style, excess_pct, csd_p50, ufo_count, ufo_rate)


@app.callback(
    Output('hc-tcr-chart', 'figure'),
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_tcr_chart(active_dataset, refresh):
    """Update TCR trend chart."""
    df = SESSION.get_df()
    
    if df is None or df.empty:
        return create_empty_figure("Upload data to view TCR analysis")
    
    measured_col = find_column(df, ['measured tcr'])
    theoretical_col = find_column(df, ['theoretical lag tcr', 'theoretical tcr'])
    time_col = find_column(df, ['time'])
    depth_col = find_column(df, ['hole depth'])
    
    if not measured_col:
        return create_empty_figure("No TCR data found")
    
    fig = go.Figure()
    
    # X-axis: prefer time, fallback to depth or index
    if time_col and time_col in df.columns:
        x_data = df[time_col]
        x_title = "Time"
    elif depth_col and depth_col in df.columns:
        x_data = df[depth_col]
        x_title = "Hole Depth (m)"
    else:
        x_data = df.index
        x_title = "Index"
    
    # Measured TCR
    if measured_col in df.columns:
        fig.add_trace(go.Scatter(
            x=x_data, y=df[measured_col],
            name='Measured TCR', mode='lines',
            line=dict(color=COLORS['blue'], width=2)
        ))
    
    # Theoretical TCR
    if theoretical_col and theoretical_col in df.columns:
        fig.add_trace(go.Scatter(
            x=x_data, y=df[theoretical_col],
            name='Theoretical TCR', mode='lines',
            line=dict(color=COLORS['cyan'], width=2, dash='dash')
        ))
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
        legend=dict(bgcolor='rgba(0,0,0,0)', x=0, y=1.1, orientation='h'),
        margin=dict(l=50, r=20, t=30, b=40),
        xaxis=dict(title=x_title, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title='TCR (m³)', gridcolor='rgba(255,255,255,0.05)'),
        hovermode='x unified',
    )
    
    return fig


@app.callback(
    Output('hc-tcr-depth-chart', 'figure'),
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_tcr_depth_chart(active_dataset, refresh):
    """Update TCR by depth interval chart."""
    df = SESSION.get_df()
    
    if df is None or df.empty:
        return create_empty_figure("No data")
    
    measured_col = find_column(df, ['measured tcr'])
    depth_col = find_column(df, ['hole depth'])
    
    if not measured_col or not depth_col:
        return create_empty_figure("TCR or Depth data not found")
    
    if measured_col not in df.columns or depth_col not in df.columns:
        return create_empty_figure("Required columns missing")
    
    # Create depth bins (100m intervals)
    df_clean = df[[depth_col, measured_col]].dropna()
    if len(df_clean) < 2:
        return create_empty_figure("Insufficient data")
    
    min_depth = df_clean[depth_col].min()
    max_depth = df_clean[depth_col].max()
    
    bin_size = 100
    bins = list(range(int(min_depth // bin_size) * bin_size, int(max_depth) + bin_size, bin_size))
    
    # Calculate TCR per interval
    df_clean['depth_bin'] = pd.cut(df_clean[depth_col], bins=bins)
    
    # Get TCR delta per bin
    tcr_by_depth = []
    bin_labels = []
    
    for i in range(len(bins) - 1):
        mask = (df_clean[depth_col] >= bins[i]) & (df_clean[depth_col] < bins[i+1])
        subset = df_clean[mask]
        if len(subset) > 1:
            tcr_delta = subset[measured_col].iloc[-1] - subset[measured_col].iloc[0]
            tcr_by_depth.append(max(0, tcr_delta))
            bin_labels.append(f"{bins[i]}-{bins[i+1]}")
    
    if not tcr_by_depth:
        return create_empty_figure("Could not calculate interval TCR")
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=tcr_by_depth,
        y=bin_labels,
        orientation='h',
        marker=dict(color=COLORS['blue']),
        text=[f"{v:.1f}" for v in tcr_by_depth],
        textposition='outside',
        textfont=dict(size=9),
    ))
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
        margin=dict(l=70, r=40, t=20, b=40),
        xaxis=dict(title='TCR (m³)', gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title='Depth (m)', gridcolor='rgba(255,255,255,0.05)'),
        bargap=0.3,
    )
    
    return fig


@app.callback(
    Output('hc-csd-chart', 'figure'),
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_csd_chart(active_dataset, refresh):
    """Update CSD distribution chart."""
    df = SESSION.get_df()
    
    if df is None or df.empty:
        return create_empty_figure("No data")
    
    csd_col = find_column(df, ['csd p50', 'csd_p50'])
    
    if not csd_col or csd_col not in df.columns:
        return create_empty_figure("CSD data not found")
    
    csd_data = df[csd_col].dropna()
    if len(csd_data) < 10:
        return create_empty_figure("Insufficient CSD data")
    
    fig = go.Figure()
    
    # Histogram
    fig.add_trace(go.Histogram(
        x=csd_data,
        nbinsx=30,
        marker=dict(color=COLORS['purple'], line=dict(color=COLORS['border'], width=1)),
        name='CSD Distribution'
    ))
    
    # Add UFO zone indicator (>30mm)
    fig.add_vline(x=30, line_dash="dash", line_color=COLORS['red'], 
                  annotation_text="UFO Zone", annotation_position="top")
    
    # Add percentile lines
    p10 = csd_data.quantile(0.1)
    p50 = csd_data.quantile(0.5)
    p90 = csd_data.quantile(0.9)
    
    fig.add_vline(x=p10, line_dash="dot", line_color=COLORS['cyan'], 
                  annotation_text=f"P10: {p10:.1f}", annotation_position="bottom")
    fig.add_vline(x=p50, line_dash="solid", line_color=COLORS['green'], 
                  annotation_text=f"P50: {p50:.1f}", annotation_position="top")
    fig.add_vline(x=p90, line_dash="dot", line_color=COLORS['yellow'], 
                  annotation_text=f"P90: {p90:.1f}", annotation_position="bottom")
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
        margin=dict(l=50, r=20, t=30, b=40),
        xaxis=dict(title='Cuttings Size (mm)', gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title='Count', gridcolor='rgba(255,255,255,0.05)'),
        showlegend=False,
    )
    
    return fig


@app.callback(
    Output('hc-crr-chart', 'figure'),
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_crr_chart(active_dataset, refresh):
    """Update CRR trend chart."""
    df = SESSION.get_df()
    
    if df is None or df.empty:
        return create_empty_figure("No data")
    
    crr_col = find_column(df, ['crr'])
    time_col = find_column(df, ['time'])
    depth_col = find_column(df, ['hole depth'])
    
    if not crr_col or crr_col not in df.columns:
        return create_empty_figure("CRR data not found")
    
    fig = go.Figure()
    
    # X-axis
    if time_col and time_col in df.columns:
        x_data = df[time_col]
        x_title = "Time"
    elif depth_col and depth_col in df.columns:
        x_data = df[depth_col]
        x_title = "Hole Depth (m)"
    else:
        x_data = df.index
        x_title = "Index"
    
    fig.add_trace(go.Scatter(
        x=x_data, y=df[crr_col],
        name='CRR', mode='lines',
        line=dict(color=COLORS['orange'], width=1.5),
        fill='tozeroy',
        fillcolor=f'rgba(242, 101, 34, 0.2)'
    ))
    
    # Add load level indicators
    fig.add_hline(y=0.006, line_dash="dot", line_color=COLORS['dim'], 
                  annotation_text="Shaker Clean", annotation_position="right")
    fig.add_hline(y=0.1, line_dash="dot", line_color=COLORS['yellow'], 
                  annotation_text="Medium Load", annotation_position="right")
    fig.add_hline(y=0.25, line_dash="dot", line_color=COLORS['red'], 
                  annotation_text="Large Load", annotation_position="right")
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
        margin=dict(l=50, r=80, t=20, b=40),
        xaxis=dict(title=x_title, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title='CRR (m³/min)', gridcolor='rgba(255,255,255,0.05)'),
        showlegend=False,
    )
    
    return fig


@app.callback(
    Output('hc-ufo-chart', 'figure'),
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_ufo_chart(active_dataset, refresh):
    """Update UFO events chart - shows UFO rate by depth interval."""
    df = SESSION.get_df()
    
    if df is None or df.empty:
        return create_empty_figure("No data")
    
    ufo_col = find_column(df, ['ufo count', 'ufo_count'])
    depth_col = find_column(df, ['hole depth'])
    
    if not ufo_col or ufo_col not in df.columns:
        return create_empty_figure("UFO data not found")
    
    if not depth_col or depth_col not in df.columns:
        return create_empty_figure("Depth data not found")
    
    # Calculate UFO events per depth interval (100m bins)
    df_clean = df[[depth_col, ufo_col]].dropna()
    if len(df_clean) < 2:
        return create_empty_figure("Insufficient data")
    
    min_depth = df_clean[depth_col].min()
    max_depth = df_clean[depth_col].max()
    
    bin_size = 100
    bins = list(range(int(min_depth // bin_size) * bin_size, int(max_depth) + bin_size, bin_size))
    
    # Calculate UFO delta per bin
    ufo_by_depth = []
    bin_centers = []
    bin_labels = []
    
    for i in range(len(bins) - 1):
        mask = (df_clean[depth_col] >= bins[i]) & (df_clean[depth_col] < bins[i+1])
        subset = df_clean[mask]
        if len(subset) > 1:
            ufo_delta = subset[ufo_col].iloc[-1] - subset[ufo_col].iloc[0]
            ufo_by_depth.append(max(0, ufo_delta))
            bin_centers.append((bins[i] + bins[i+1]) / 2)
            bin_labels.append(f"{bins[i]}-{bins[i+1]}m")
    
    if not ufo_by_depth:
        return create_empty_figure("Could not calculate UFO distribution")
    
    fig = go.Figure()
    
    # Create a horizontal bar chart (lollipop style) - depth on Y, UFO count on X
    # Color bars based on count severity
    colors = []
    for count in ufo_by_depth:
        if count == 0:
            colors.append(COLORS['green'])
        elif count <= 5:
            colors.append(COLORS['yellow'])
        elif count <= 15:
            colors.append(COLORS['orange'])
        else:
            colors.append(COLORS['red'])
    
    fig.add_trace(go.Bar(
        x=ufo_by_depth,
        y=bin_labels,
        orientation='h',
        marker=dict(color=colors, line=dict(color=COLORS['border'], width=1)),
        text=[f"{int(v)}" if v > 0 else "" for v in ufo_by_depth],
        textposition='outside',
        textfont=dict(size=9, color=COLORS['text']),
        hovertemplate='%{y}: %{x} UFOs<extra></extra>'
    ))
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
        margin=dict(l=80, r=30, t=20, b=40),
        xaxis=dict(title='UFO Events', gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title='', gridcolor='rgba(255,255,255,0.05)', autorange='reversed'),
        showlegend=False,
        bargap=0.3,
    )
    
    return fig


# ============================================================

# ============================================================
# TRIPPING TAB CALLBACKS - BU-focused implementation
# ============================================================

def calculate_bu_metrics(df):
    """
    Calculate Bottoms-Up metrics based on proper operational logic.
    
    NEW LOGIC (v3.3.0):
    - Clean = CRR drops to ≤15% of CRR at TD (85% reduction)
    - Must happen AFTER first BU complete (lag reaches TD)
    - Must sustain for ≥5 consecutive minutes
    
    BU Mode: ROP=0 AND Flow>threshold AND SPP confirms pumps AND Bit near TD
    Reference BU Time: Time from TD reached until Lag Depth reaches TD
    BU Cycles: Total circulation time at TD / Reference BU time
    """
    result = {
        'bu_cycles': None,
        'bu_completion_pct': None,
        'ref_bu_time_min': None,
        'current_circ_time_min': None,
        'td': None,
        'td_time': None,
        'lag_reaches_td_time': None,
        'is_bu_mode': False,
        'crr_current': None,
        'crr_at_td': None,
        'crr_clean_threshold': None,  # Dynamic threshold (15% of CRR at TD)
        'crr_status': 'Unknown',
        'crr_reduction_pct': None,
        'time_at_td_hrs': None,
        'bu_mode_periods': [],
        'first_bu_complete': False,
        'sustained_clean': False,
    }
    
    if df is None or df.empty:
        return result
    
    # Find required columns
    time_col = find_column(df, ['time'])
    depth_col = find_column(df, ['hole depth'])
    bit_depth_col = find_column(df, ['bit depth'])
    lag_depth_col = find_column(df, ['lag depth'])
    rop_col = find_column(df, ['rop'])
    flow_col = find_column(df, ['flow in', 'flow'])
    spp_col = find_column(df, ['pump pressure', 'spp', 'standpipe'])
    crr_col = find_column(df, ['crr'])
    
    if not all([time_col, depth_col]):
        return result
    
    try:
        df = df.copy()
        df[time_col] = pd.to_datetime(df[time_col])
        
        # Find TD (Total Depth = max hole depth)
        td = df[depth_col].max()
        td_idx = df[depth_col].idxmax()
        td_time = df.loc[td_idx, time_col]
        result['td'] = td
        result['td_time'] = td_time
        
        # Calculate time at TD
        last_time = df[time_col].iloc[-1]
        result['time_at_td_hrs'] = (last_time - td_time).total_seconds() / 3600
        
        # Get config values
        cfg = BU_CONFIG
        
        # Calculate Reference BU Time (when lag depth first reaches TD)
        lag_td_time = None
        if lag_depth_col and lag_depth_col in df.columns:
            post_td = df.loc[td_idx:]
            lag_reaches_td = post_td[post_td[lag_depth_col] >= td - 2]  # Within 2m of TD
            
            if len(lag_reaches_td) > 0:
                lag_td_time = lag_reaches_td.iloc[0][time_col]
                ref_bu_seconds = (lag_td_time - td_time).total_seconds()
                result['ref_bu_time_min'] = ref_bu_seconds / 60
                result['lag_reaches_td_time'] = lag_td_time
                result['first_bu_complete'] = True
        
        # Identify BU mode periods (ROP=0, Flow>threshold, Bit near TD)
        post_td = df.loc[td_idx:].copy()
        
        # Define conditions
        bit_col = bit_depth_col if bit_depth_col else depth_col
        post_td['at_td'] = (td - post_td[bit_col]) <= cfg['bit_td_tolerance']
        
        if rop_col and rop_col in post_td.columns:
            post_td['not_drilling'] = post_td[rop_col] <= cfg['rop_drilling_threshold']
        else:
            post_td['not_drilling'] = True
        
        if flow_col and flow_col in post_td.columns:
            post_td['flow_on'] = post_td[flow_col] > cfg['flow_min_threshold']
        else:
            post_td['flow_on'] = True
        
        # Optional: SPP confirmation
        if spp_col and spp_col in post_td.columns:
            post_td['spp_on'] = post_td[spp_col] > cfg['spp_min_threshold']
            post_td['bu_mode'] = post_td['at_td'] & post_td['not_drilling'] & post_td['flow_on'] & post_td['spp_on']
        else:
            post_td['bu_mode'] = post_td['at_td'] & post_td['not_drilling'] & post_td['flow_on']
        
        # Calculate BU mode time
        bu_rows = post_td[post_td['bu_mode']]
        if len(bu_rows) > 0:
            result['is_bu_mode'] = post_td['bu_mode'].iloc[-1] if len(post_td) > 0 else False
            
            # Total BU mode time
            bu_start = bu_rows[time_col].iloc[0]
            bu_end = bu_rows[time_col].iloc[-1]
            total_bu_seconds = (bu_end - bu_start).total_seconds()
            result['current_circ_time_min'] = total_bu_seconds / 60
            
            # Calculate BU cycles and completion
            if result['ref_bu_time_min'] and result['ref_bu_time_min'] > 0:
                result['bu_cycles'] = total_bu_seconds / (result['ref_bu_time_min'] * 60)
                
                # Current BU completion (for partial cycle display)
                if result['bu_cycles'] >= 1:
                    result['bu_completion_pct'] = 100  # Full cycle(s) completed
                else:
                    result['bu_completion_pct'] = result['bu_cycles'] * 100
        
        # ============================================
        # NEW LOGIC: CRR status with relative threshold
        # ============================================
        if crr_col and crr_col in df.columns:
            crr_data = df[crr_col].dropna()
            if len(crr_data) > 0:
                result['crr_current'] = crr_data.iloc[-1]
                
                # Get CRR at TD
                post_td_crr = post_td[crr_col].dropna()
                if len(post_td_crr) > 0:
                    crr_at_td = post_td_crr.iloc[0]
                    result['crr_at_td'] = crr_at_td
                    
                    # Calculate dynamic threshold (15% of CRR at TD)
                    clean_threshold = crr_at_td * cfg['crr_reduction_pct']
                    result['crr_clean_threshold'] = clean_threshold
                    
                    # Calculate current reduction %
                    if crr_at_td > 0:
                        result['crr_reduction_pct'] = (1 - result['crr_current'] / crr_at_td) * 100
                    
                    # Determine CRR status based on relative threshold
                    # Only consider "Clean" if first BU is complete
                    if result['first_bu_complete'] and lag_td_time is not None:
                        # Check for sustained clean (after first BU)
                        post_first_bu = post_td[post_td[time_col] >= lag_td_time].copy()
                        
                        if len(post_first_bu) > 0 and crr_col in post_first_bu.columns:
                            post_first_bu_crr = post_first_bu[[time_col, crr_col]].dropna()
                            
                            if len(post_first_bu_crr) > 0:
                                # Check if we have sustained low CRR
                                clean_start_time = None
                                for idx, row in post_first_bu_crr.iterrows():
                                    if row[crr_col] <= clean_threshold:
                                        if clean_start_time is None:
                                            clean_start_time = row[time_col]
                                        
                                        time_below = (row[time_col] - clean_start_time).total_seconds() / 60
                                        if time_below >= cfg['crr_sustain_minutes']:
                                            result['sustained_clean'] = True
                                            break
                                    else:
                                        clean_start_time = None
                        
                        # Set status based on sustained clean
                        if result['sustained_clean']:
                            result['crr_status'] = 'Clean'
                        elif result['crr_current'] <= clean_threshold:
                            result['crr_status'] = 'Near-Clean'  # Below threshold but not sustained
                        elif result['crr_current'] <= crr_at_td * 0.5:
                            result['crr_status'] = 'Reducing'  # 50% reduction
                        else:
                            result['crr_status'] = 'Active'
                    else:
                        # First BU not complete yet
                        result['crr_status'] = 'Waiting for BU'
                else:
                    # Fallback if no CRR at TD
                    if result['crr_current'] <= cfg['crr_fallback_threshold']:
                        result['crr_status'] = 'Clean'
                    elif result['crr_current'] <= cfg['crr_fallback_threshold'] * 2:
                        result['crr_status'] = 'Near-Clean'
                    else:
                        result['crr_status'] = 'Active'
        
    except Exception as e:
        print(f"BU calculation error: {e}")
    
    return result


def determine_trip_readiness(bu_metrics):
    """
    Determine trip readiness based on BU completion and CRR status.
    
    NEW LOGIC (v3.3.0):
    1. BU cycles >= target (default 1.1)
    2. CRR shows sustained clean (85% reduction from CRR at TD, sustained 5 min)
    
    Returns: (status_text, status_color, is_ready)
    """
    cfg = BU_CONFIG
    
    bu_cycles = bu_metrics.get('bu_cycles')
    sustained_clean = bu_metrics.get('sustained_clean', False)
    crr_status = bu_metrics.get('crr_status', 'Unknown')
    first_bu_complete = bu_metrics.get('first_bu_complete', False)
    
    # Check conditions
    bu_ready = bu_cycles is not None and bu_cycles >= cfg['bu_target']
    
    if bu_ready and sustained_clean:
        return ("✓ Ready", COLORS['green'], True)
    elif bu_ready and crr_status == 'Near-Clean':
        return ("Almost Ready", COLORS['yellow'], False)
    elif bu_ready and crr_status in ['Reducing', 'Active']:
        return ("Cuttings Returning", COLORS['yellow'], False)
    elif bu_cycles is not None and bu_cycles >= 1.0 and sustained_clean:
        return ("Almost Ready", COLORS['yellow'], False)
    elif not first_bu_complete:
        return ("Waiting for BU", COLORS['muted'], False)
    else:
        return ("✗ Not Ready", COLORS['red'], False)


@app.callback(
    [Output('trip-readiness-value', 'children'),
     Output('trip-readiness-value', 'style'),
     Output('trip-readiness-status', 'children'),
     Output('trip-bu-cycles', 'children'),
     Output('trip-bu-target', 'children'),
     Output('trip-bu-completion', 'children'),
     Output('trip-bu-time', 'children'),
     Output('trip-ref-bu-time', 'children'),
     Output('trip-crr-status', 'children'),
     Output('trip-crr-value', 'children'),
     Output('trip-time-td', 'children')],
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_tripping_primary_kpis(active_dataset, refresh):
    """Update primary Tripping KPIs (BU-focused)."""
    df = SESSION.get_df()
    
    # Default styles
    readiness_style = {'fontSize': '42px', 'fontWeight': '700', 'fontFamily': 'JetBrains Mono', 
                       'color': COLORS['green'], 'textAlign': 'center', 'lineHeight': '1'}
    
    defaults = ("—", readiness_style, "No data", "—", f"Target: ≥{BU_CONFIG['bu_target']}", 
                "—%", "", "—", "—", "", "—")
    
    if df is None or df.empty:
        return defaults
    
    # Calculate BU metrics
    bu = calculate_bu_metrics(df)
    
    # Trip Readiness
    status_text, status_color, is_ready = determine_trip_readiness(bu)
    readiness_style = {**readiness_style, 'color': status_color}
    
    # Readiness value (show BU cycles as main metric)
    if bu['bu_cycles'] is not None:
        readiness_val = f"{bu['bu_cycles']:.1f}"
    else:
        readiness_val = "—"
    
    # BU Cycles
    bu_cycles_str = f"{bu['bu_cycles']:.2f}" if bu['bu_cycles'] is not None else "—"
    
    # BU Target
    bu_target_str = f"Target: ≥{BU_CONFIG['bu_target']}"
    
    # Current BU completion percentage
    if bu['bu_completion_pct'] is not None:
        if bu['bu_cycles'] and bu['bu_cycles'] >= 1:
            bu_completion_str = f"{bu['bu_cycles']:.1f}x"
        else:
            bu_completion_str = f"{bu['bu_completion_pct']:.0f}%"
    else:
        bu_completion_str = "—%"
    
    # BU time info
    if bu['current_circ_time_min'] is not None:
        bu_time_str = f"{bu['current_circ_time_min']:.0f} min circulating"
    else:
        bu_time_str = ""
    
    # Reference BU time
    ref_bu_str = f"{bu['ref_bu_time_min']:.0f}" if bu['ref_bu_time_min'] is not None else "—"
    
    # CRR Status
    crr_status = bu['crr_status']
    crr_status_color = COLORS['green'] if crr_status == 'Clean' else \
                       COLORS['yellow'] if crr_status in ['Near-Clean', 'Low Load'] else \
                       COLORS['orange'] if crr_status == 'Medium' else COLORS['red']
    
    crr_value_str = f"{bu['crr_current']:.4f}" if bu['crr_current'] is not None else ""
    
    # Time at TD
    time_td_str = f"{bu['time_at_td_hrs']:.1f}" if bu['time_at_td_hrs'] is not None else "—"
    
    return (readiness_val, readiness_style, status_text,
            bu_cycles_str, bu_target_str,
            bu_completion_str, bu_time_str,
            ref_bu_str,
            crr_status, crr_value_str,
            time_td_str)


@app.callback(
    [Output('trip-tcr-ratio', 'children'),
     Output('trip-tcr-status', 'children'),
     Output('trip-ufo-total', 'children'),
     Output('trip-ufo-status', 'children'),
     Output('trip-csd-value', 'children'),
     Output('trip-csd-trend', 'children'),
     Output('trip-lag-depth', 'children'),
     Output('trip-lag-status', 'children')],
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_tripping_secondary_kpis(active_dataset, refresh):
    """Update secondary Tripping indicators."""
    df = SESSION.get_df()
    
    defaults = ("—", "", "—", "", "—", "", "—", "")
    
    if df is None or df.empty:
        return defaults
    
    # Find columns
    measured_col = find_column(df, ['measured tcr'])
    theoretical_col = find_column(df, ['theoretical lag tcr', 'theoretical tcr'])
    ufo_col = find_column(df, ['ufo count'])
    csd_col = find_column(df, ['csd p50'])
    lag_depth_col = find_column(df, ['lag depth'])
    depth_col = find_column(df, ['hole depth'])
    
    # TCR Ratio
    tcr_str = "—"
    tcr_status = ""
    if measured_col and theoretical_col:
        meas = df[measured_col].dropna()
        theo = df[theoretical_col].dropna()
        if len(meas) > 0 and len(theo) > 0 and theo.iloc[-1] > 0:
            ratio = meas.iloc[-1] / theo.iloc[-1]
            tcr_str = f"{ratio:.2f}"
            if 0.95 <= ratio <= 1.05:
                tcr_status = "✓ Normal"
            elif ratio < 0.85:
                tcr_status = "⚠ Under-recovery"
            elif ratio > 1.15:
                tcr_status = "⚠ Over-recovery"
            else:
                tcr_status = "~ Slight deviation"
    
    # UFO Total (CORRECTED: use sum, not last value)
    ufo_str = "—"
    ufo_status = ""
    if ufo_col:
        ufo_data = df[ufo_col].dropna()
        if len(ufo_data) > 0:
            total_ufo = ufo_data.sum()  # Sum of all UFO readings
            ufo_str = f"{int(total_ufo)}"
            if total_ufo < 500:
                ufo_status = "Low"
            elif total_ufo < 2000:
                ufo_status = "Moderate"
            else:
                ufo_status = "High"
    
    # CSD P50
    csd_str = "—"
    csd_trend = ""
    if csd_col:
        csd_data = df[csd_col].dropna()
        if len(csd_data) > 0:
            csd_str = f"{csd_data.median():.1f}"
            if len(csd_data) > 50:
                recent = csd_data.tail(50).mean()
                earlier = csd_data.head(50).mean()
                if recent < earlier * 0.9:
                    csd_trend = "↓ Decreasing"
                elif recent > earlier * 1.1:
                    csd_trend = "↑ Increasing"
                else:
                    csd_trend = "→ Stable"
    
    # Lag Depth
    lag_str = "—"
    lag_status = ""
    if lag_depth_col and depth_col:
        lag_data = df[lag_depth_col].dropna()
        depth_data = df[depth_col].dropna()
        if len(lag_data) > 0 and len(depth_data) > 0:
            current_lag = lag_data.iloc[-1]
            td = depth_data.max()
            lag_str = f"{current_lag:.0f}"
            gap = td - current_lag
            if gap <= 2:
                lag_status = "At TD"
            else:
                lag_status = f"{gap:.0f}m to TD"
    
    return (tcr_str, tcr_status, ufo_str, ufo_status, csd_str, csd_trend, lag_str, lag_status)


@app.callback(
    Output('trip-bu-gauge', 'figure'),
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_bu_gauge(active_dataset, refresh):
    """Update BU completion gauge."""
    df = SESSION.get_df()
    
    if df is None or df.empty:
        return create_empty_figure("Upload data to view BU progress")
    
    bu = calculate_bu_metrics(df)
    
    # Determine gauge value (0-200% scale, 100% = 1 BU)
    if bu['bu_cycles'] is not None:
        gauge_value = bu['bu_cycles'] * 100  # Convert to percentage
    else:
        gauge_value = 0
    
    # Color based on target
    target_pct = BU_CONFIG['bu_target'] * 100
    if gauge_value >= target_pct:
        gauge_color = COLORS['green']
    elif gauge_value >= 100:
        gauge_color = COLORS['yellow']
    else:
        gauge_color = COLORS['orange']
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=gauge_value,
        number={'suffix': '%', 'font': {'size': 42, 'color': gauge_color, 'family': 'JetBrains Mono'}},
        gauge={
            'axis': {'range': [0, 200], 'tickwidth': 1, 'tickcolor': COLORS['border'],
                     'tickvals': [0, 50, 100, 110, 150, 200],
                     'ticktext': ['0%', '50%', '1 BU', '1.1 BU', '1.5 BU', '2 BU']},
            'bar': {'color': gauge_color, 'thickness': 0.25},
            'bgcolor': COLORS['card'],
            'borderwidth': 2,
            'bordercolor': COLORS['border'],
            'steps': [
                {'range': [0, 100], 'color': 'rgba(242, 101, 34, 0.15)'},
                {'range': [100, 110], 'color': 'rgba(245, 158, 11, 0.15)'},
                {'range': [110, 200], 'color': 'rgba(16, 185, 129, 0.15)'}
            ],
            'threshold': {
                'line': {'color': COLORS['green'], 'width': 3},
                'thickness': 0.8,
                'value': target_pct  # Target line at 1.1 BU
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono'),
        margin=dict(l=30, r=30, t=30, b=10),
        height=300,
        annotations=[
            dict(text=f"Target: {BU_CONFIG['bu_target']} BU", x=0.5, y=-0.1, 
                 font=dict(size=11, color=COLORS['dim']), showarrow=False)
        ]
    )
    
    return fig


@app.callback(
    Output('trip-crr-trend', 'figure'),
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_crr_trend_chart(active_dataset, refresh):
    """Update CRR trend chart with clean-hole thresholds."""
    df = SESSION.get_df()
    
    if df is None or df.empty:
        return create_empty_figure("No data")
    
    crr_col = find_column(df, ['crr'])
    time_col = find_column(df, ['time'])
    depth_col = find_column(df, ['hole depth'])
    
    if not crr_col or crr_col not in df.columns:
        return create_empty_figure("CRR data not found")
    
    fig = go.Figure()
    
    # Use recent data focused on TD period
    bu = calculate_bu_metrics(df)
    if bu['td_time'] is not None and time_col:
        df[time_col] = pd.to_datetime(df[time_col])
        td_time = bu['td_time']
        # Get data from 1 hour before TD onwards
        start_time = td_time - pd.Timedelta(hours=1)
        df_plot = df[df[time_col] >= start_time].copy()
    else:
        df_plot = df.tail(min(len(df), 3000)).copy()
    
    if time_col and time_col in df_plot.columns:
        x_data = df_plot[time_col]
        x_title = "Time"
    elif depth_col and depth_col in df_plot.columns:
        x_data = df_plot[depth_col]
        x_title = "Hole Depth (m)"
    else:
        x_data = df_plot.index
        x_title = "Index"
    
    # CRR trace
    fig.add_trace(go.Scatter(
        x=x_data, y=df_plot[crr_col],
        name='CRR', mode='lines',
        line=dict(color=COLORS['orange'], width=1.5),
        fill='tozeroy', fillcolor='rgba(242, 101, 34, 0.15)'
    ))
    
    # Add threshold lines - use dynamic threshold if available
    cfg = BU_CONFIG
    
    # Get dynamic threshold from BU metrics
    clean_threshold = bu.get('crr_clean_threshold')
    crr_at_td = bu.get('crr_at_td')
    
    if clean_threshold and crr_at_td:
        # Show dynamic threshold line (15% of CRR at TD)
        fig.add_hline(y=clean_threshold, line_dash="solid", line_color=COLORS['green'], 
                      line_width=2, annotation_text=f"Clean (15% of {crr_at_td:.4f})", annotation_position="right",
                      annotation_font=dict(size=9, color=COLORS['green']))
        # Show CRR at TD reference
        fig.add_hline(y=crr_at_td, line_dash="dot", line_color=COLORS['orange'], 
                      line_width=1, annotation_text=f"CRR at TD ({crr_at_td:.4f})", annotation_position="right",
                      annotation_font=dict(size=9, color=COLORS['orange']))
    else:
        # Fallback to fixed thresholds
        fig.add_hline(y=cfg['crr_fallback_threshold'], line_dash="solid", line_color=COLORS['green'], 
                      line_width=2, annotation_text="Clean (0.006)", annotation_position="right",
                      annotation_font=dict(size=9, color=COLORS['green']))
    fig.add_hline(y=CRR_LOAD_LEVELS['low'], line_dash="dot", line_color=COLORS['dim'], 
                  annotation_text="Low (0.02)", annotation_position="right",
                  annotation_font=dict(size=9, color=COLORS['dim']))
    
    # Mark TD if known - use add_shape + add_annotation instead of add_vline (avoids Timestamp issues)
    if bu['td_time'] is not None and time_col:
        td_time_val = bu['td_time']
        # Add vertical line as shape
        fig.add_shape(
            type="line",
            x0=td_time_val, x1=td_time_val,
            y0=0, y1=1,
            yref="paper",
            line=dict(color=COLORS['cyan'], width=1, dash="dash")
        )
        # Add annotation separately
        fig.add_annotation(
            x=td_time_val,
            y=1,
            yref="paper",
            text="TD",
            showarrow=False,
            font=dict(size=10, color=COLORS['cyan']),
            yanchor="bottom"
        )
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
        margin=dict(l=50, r=80, t=20, b=40),
        xaxis=dict(title=x_title, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title='CRR (m³/min)', gridcolor='rgba(255,255,255,0.05)', 
                   range=[0, max(0.05, df_plot[crr_col].max() * 1.1) if crr_col in df_plot.columns else 0.1]),
        showlegend=False,
        hovermode='x unified',
    )
    
    return fig


@app.callback(
    Output('trip-bu-analysis', 'children'),
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_bu_analysis(active_dataset, refresh):
    """Update BU mode analysis panel."""
    df = SESSION.get_df()
    
    if df is None or df.empty:
        return [html.Div("Upload data to see BU analysis", style={'color': COLORS['muted']})]
    
    bu = calculate_bu_metrics(df)
    observations = []
    
    def add_row(label, value, color=COLORS['text'], icon=""):
        observations.append(html.Div([
            html.Span(icon, style={'marginRight': '8px', 'fontSize': '14px'}) if icon else None,
            html.Span(label, style={'color': COLORS['dim'], 'fontSize': '11px', 'minWidth': '140px', 'display': 'inline-block'}),
            html.Span(value, style={'color': color, 'fontWeight': '600', 'fontFamily': 'JetBrains Mono', 'fontSize': '12px'}),
        ], style={'padding': '8px 0', 'borderBottom': f'1px solid {COLORS["border"]}', 'display': 'flex', 'alignItems': 'center'}))
    
    # TD info
    if bu['td'] is not None:
        add_row("Total Depth (TD)", f"{bu['td']:.0f} m", COLORS['cyan'], "📍")
    
    if bu['td_time'] is not None:
        add_row("TD Reached", bu['td_time'].strftime('%Y-%m-%d %H:%M'), COLORS['text'], "🕐")
    
    # Reference BU time
    if bu['ref_bu_time_min'] is not None:
        add_row("Reference BU Time", f"{bu['ref_bu_time_min']:.0f} minutes", COLORS['purple'], "◷")
        if bu['lag_reaches_td_time'] is not None:
            add_row("Lag Reached TD", bu['lag_reaches_td_time'].strftime('%H:%M'), COLORS['dim'], "")
    else:
        add_row("Reference BU Time", "Calculating...", COLORS['muted'], "◷")
    
    # Circulation time
    if bu['current_circ_time_min'] is not None:
        add_row("Circulation at TD", f"{bu['current_circ_time_min']:.0f} minutes", COLORS['blue'], "↻")
    
    # BU cycles
    if bu['bu_cycles'] is not None:
        bu_color = COLORS['green'] if bu['bu_cycles'] >= BU_CONFIG['bu_target'] else \
                   COLORS['yellow'] if bu['bu_cycles'] >= 1.0 else COLORS['orange']
        add_row("BU Cycles Complete", f"{bu['bu_cycles']:.2f}", bu_color, "✓")
    
    # CRR Status
    crr_color = COLORS['green'] if bu['crr_status'] == 'Clean' else \
                COLORS['yellow'] if bu['crr_status'] in ['Near-Clean', 'Low Load'] else COLORS['orange']
    add_row("Cuttings Return", bu['crr_status'], crr_color, "▦")
    
    if bu['crr_current'] is not None:
        add_row("Current CRR", f"{bu['crr_current']:.4f} m³/min", COLORS['dim'], "")
    
    # Current mode
    mode_text = "Active" if bu['is_bu_mode'] else "Inactive"
    mode_color = COLORS['green'] if bu['is_bu_mode'] else COLORS['muted']
    add_row("BU Mode", mode_text, mode_color, "◉")
    
    # Final status
    status_text, status_color, is_ready = determine_trip_readiness(bu)
    observations.append(html.Div([
        html.Div(status_text, style={
            'fontSize': '14px', 'fontWeight': '600', 'color': status_color,
            'padding': '12px', 'textAlign': 'center', 'marginTop': '12px',
            'background': f'{status_color}22', 'borderRadius': '6px'
        })
    ]))
    
    return observations


@app.callback(
    Output('trip-lag-progress', 'figure'),
    [Input('store-active-dataset', 'data'), Input('store-refresh', 'data')]
)
def update_lag_progress_chart(active_dataset, refresh):
    """Update lag depth progress mini-chart."""
    df = SESSION.get_df()
    
    if df is None or df.empty:
        return create_empty_figure("No data")
    
    lag_col = find_column(df, ['lag depth'])
    depth_col = find_column(df, ['hole depth'])
    time_col = find_column(df, ['time'])
    
    if not lag_col:
        return create_empty_figure("Lag depth not found")
    
    fig = go.Figure()
    
    # Get data around TD
    bu = calculate_bu_metrics(df)
    if bu['td_time'] is not None and time_col:
        df[time_col] = pd.to_datetime(df[time_col])
        td_time = bu['td_time']
        start_time = td_time - pd.Timedelta(minutes=30)
        df_plot = df[df[time_col] >= start_time].copy()
    else:
        df_plot = df.tail(min(len(df), 500)).copy()
    
    x_data = df_plot[time_col] if time_col and time_col in df_plot.columns else df_plot.index
    
    # Lag depth trace
    fig.add_trace(go.Scatter(
        x=x_data, y=df_plot[lag_col],
        name='Lag Depth', mode='lines',
        line=dict(color=COLORS['cyan'], width=2),
    ))
    
    # TD line
    if bu['td'] is not None:
        fig.add_hline(y=bu['td'], line_dash="dash", line_color=COLORS['green'],
                      annotation_text="TD", annotation_position="right",
                      annotation_font=dict(size=9, color=COLORS['green']))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['text'], family='JetBrains Mono', size=9),
        margin=dict(l=40, r=50, t=5, b=25),
        xaxis=dict(showgrid=False, showticklabels=True, tickfont=dict(size=8)),
        yaxis=dict(title='Lag (m)', gridcolor='rgba(255,255,255,0.05)', tickfont=dict(size=8)),
        showlegend=False,
        height=140,
    )
    
    return fig


# ============================================================
# COMPARE WELLS TAB CALLBACKS
# ============================================================

# Color palette for multiple wells
WELL_COLORS = [
    '#F26522',  # Orange
    '#3B82F6',  # Blue
    '#10B981',  # Green
    '#F59E0B',  # Yellow
    '#8B5CF6',  # Purple
    '#EF4444',  # Red
    '#06B6D4',  # Cyan
    '#EC4899',  # Pink
]


@app.callback(
    Output('compare-dataset-selector', 'options'),
    [Input('store-datasets', 'data'), Input('store-refresh', 'data')]
)
def update_compare_selector_options(datasets, refresh):
    """Update compare dropdown with available datasets."""
    if not datasets:
        return []
    return [{'label': name, 'value': name} for name in datasets]


@app.callback(
    Output('compare-status', 'children'),
    [Input('compare-dataset-selector', 'value')]
)
def update_compare_status(selected):
    """Update compare status message."""
    if not selected:
        return "Select wells to compare"
    elif len(selected) == 1:
        return "Select at least one more well"
    else:
        return f"Comparing {len(selected)} wells"


@app.callback(
    Output('compare-kpi-table', 'children'),
    [Input('compare-dataset-selector', 'value'), Input('store-refresh', 'data')]
)
def update_compare_kpi_table(selected_datasets, refresh):
    """Update KPI comparison table with comprehensive metrics."""
    if not selected_datasets or len(selected_datasets) < 2:
        return [html.Div("Select 2 or more wells to compare", style={'color': COLORS['muted'], 'fontSize': '12px', 'padding': '20px', 'textAlign': 'center'})]
    
    # Gather KPIs for each dataset
    rows = []
    
    for dataset_name in selected_datasets:
        if dataset_name not in SESSION.datasets:
            continue
        
        try:
            # Get DataFrame directly from SESSION
            df = SESSION.datasets[dataset_name].get('df')
            if df is None:
                continue
        except:
            continue
        
        # Find columns
        measured_col = find_column(df, ['measured tcr'])
        theoretical_col = find_column(df, ['theoretical lag tcr', 'theoretical tcr'])
        ufo_col = find_column(df, ['ufo count'])
        depth_col = find_column(df, ['hole depth'])
        csd_col = find_column(df, ['csd p50'])
        rop_col = find_column(df, ['rop', 'lagged rop'])
        crr_col = find_column(df, ['crr'])
        time_col = find_column(df, ['time'])
        
        row_data = {'Well': dataset_name[:25]}  # Truncate long names
        drilled_m = None
        
        # Section Drilled (m)
        if depth_col:
            depth_data = df[depth_col].dropna()
            if len(depth_data) > 0:
                drilled_m = depth_data.max() - depth_data.min()
                row_data['Drilled (m)'] = f"{drilled_m:.0f}"
        
        # Measured TCR (m³)
        measured_val = None
        if measured_col:
            meas_data = df[measured_col].dropna()
            if len(meas_data) > 0:
                measured_val = meas_data.iloc[-1]
                row_data['Meas TCR'] = f"{measured_val:.1f}"
        
        # Theoretical TCR (m³)
        theoretical_val = None
        if theoretical_col:
            theo_data = df[theoretical_col].dropna()
            if len(theo_data) > 0:
                theoretical_val = theo_data.iloc[-1]
                row_data['Theo TCR'] = f"{theoretical_val:.1f}"
        
        # TCR Ratio
        if measured_val is not None and theoretical_val is not None and theoretical_val > 0:
            ratio = measured_val / theoretical_val
            row_data['Ratio'] = f"{ratio:.2f}"
        
        # TCR Deficit/Excess (m³)
        if measured_val is not None and theoretical_val is not None:
            deficit = measured_val - theoretical_val
            sign = "+" if deficit >= 0 else ""
            row_data['Δ TCR'] = f"{sign}{deficit:.1f}"
        
        # UFO Metrics - CORRECTED: sum of instantaneous readings
        if ufo_col:
            ufo_data = df[ufo_col].dropna()
            if len(ufo_data) > 0:
                # Total UFO events (sum of all readings)
                total_ufo = ufo_data.sum()
                row_data['UFOs'] = f"{int(total_ufo)}"
                
                # Peak UFO (max instantaneous)
                peak_ufo = ufo_data.max()
                row_data['Peak UFO'] = f"{int(peak_ufo)}"
                
                # UFO Rate per 100m
                if drilled_m and drilled_m > 0:
                    ufo_rate = (total_ufo / drilled_m) * 100
                    row_data['UFO/100m'] = f"{ufo_rate:.1f}"
        
        # CSD P50 (mm)
        if csd_col:
            csd_data = df[csd_col].dropna()
            if len(csd_data) > 0:
                row_data['CSD P50'] = f"{csd_data.median():.1f}"
                # % Large cuttings (>20mm)
                pct_large = (csd_data > 20).sum() / len(csd_data) * 100
                row_data['%>20mm'] = f"{pct_large:.0f}%"
        
        # Avg ROP (m/hr)
        if rop_col:
            rop_data = df[rop_col].dropna()
            if len(rop_data) > 0:
                # ROP might be in ft/h, convert if needed
                avg_rop = rop_data.mean()
                # Check if likely ft/h (values typically > 10)
                if avg_rop > 50:  # Probably ft/h
                    avg_rop = avg_rop * 0.3048  # Convert to m/hr
                row_data['Avg ROP'] = f"{avg_rop:.1f}"
        
        # Avg CRR (m³/min)
        if crr_col:
            crr_data = df[crr_col].dropna()
            if len(crr_data) > 0:
                avg_crr = crr_data.mean()
                row_data['Avg CRR'] = f"{avg_crr:.3f}"
        
        rows.append(row_data)
    
    if not rows:
        return [html.Div("No valid data found", style={'color': COLORS['muted'], 'fontSize': '12px', 'padding': '20px', 'textAlign': 'center'})]
    
    # Define columns with grouping headers
    columns = [
        'Well', 'Drilled (m)', 
        'Meas TCR', 'Theo TCR', 'Ratio', 'Δ TCR',
        'UFOs', 'Peak UFO', 'UFO/100m',
        'CSD P50', '%>20mm',
        'Avg ROP', 'Avg CRR'
    ]
    
    # Column styling rules
    def get_cell_style(col, value, row_idx):
        style = {
            'padding': '8px 10px', 'borderBottom': f'1px solid {COLORS["border"]}',
            'fontSize': '11px', 'fontFamily': 'JetBrains Mono', 'whiteSpace': 'nowrap'
        }
        
        if col == 'Well':
            style['color'] = WELL_COLORS[row_idx % len(WELL_COLORS)]
            style['fontWeight'] = '600'
            style['position'] = 'sticky'
            style['left'] = '0'
            style['background'] = COLORS['card']
        elif col == 'Ratio':
            try:
                ratio = float(value)
                if 0.95 <= ratio <= 1.05:
                    style['color'] = COLORS['green']
                elif 0.85 <= ratio <= 1.15:
                    style['color'] = COLORS['yellow']
                else:
                    style['color'] = COLORS['red']
                style['fontWeight'] = '600'
            except:
                style['color'] = COLORS['text']
        elif col == 'Δ TCR':
            try:
                val = float(value.replace('+', ''))
                if val >= 0:
                    style['color'] = COLORS['green']
                elif val >= -5:
                    style['color'] = COLORS['yellow']
                else:
                    style['color'] = COLORS['red']
            except:
                style['color'] = COLORS['text']
        elif col in ['UFOs', 'Peak UFO', 'UFO/100m']:
            style['color'] = COLORS['orange']
        elif col in ['CSD P50', '%>20mm']:
            style['color'] = COLORS['purple']
        elif col in ['Avg ROP', 'Avg CRR']:
            style['color'] = COLORS['cyan']
        else:
            style['color'] = COLORS['text']
        
        return style
    
    # Header row
    header_cells = [html.Th(col, style={
        'padding': '8px 10px', 'textAlign': 'left', 'borderBottom': f'2px solid {COLORS["border"]}',
        'color': COLORS['muted'], 'fontSize': '9px', 'fontWeight': '600', 'letterSpacing': '0.3px',
        'whiteSpace': 'nowrap', 'position': 'sticky' if col == 'Well' else 'static',
        'left': '0' if col == 'Well' else 'auto', 'background': COLORS['card']
    }) for col in columns]
    
    # Data rows
    table_rows = [html.Tr(header_cells)]
    for i, row in enumerate(rows):
        cells = []
        for col in columns:
            value = row.get(col, '—')
            style = get_cell_style(col, value, i)
            cells.append(html.Td(value, style=style))
        table_rows.append(html.Tr(cells))
    
    return [
        html.Div([
            html.Table(table_rows, style={'width': '100%', 'borderCollapse': 'collapse'})
        ], style={'overflowX': 'auto'})
    ]


@app.callback(
    [Output('compare-tcr-chart', 'figure'), Output('compare-tcr-subtitle', 'children')],
    [Input('compare-dataset-selector', 'value'), 
     Input('compare-normalization', 'value'),
     Input('compare-chart-mode', 'value'),
     Input('store-refresh', 'data')]
)
def update_compare_tcr_chart(selected_datasets, normalization, chart_mode, refresh):
    """Update TCR comparison chart with overlay or side-by-side mode."""
    subtitle = " — Measured TCR"
    x_title = "Index"  # Default value
    
    if not selected_datasets or len(selected_datasets) < 2:
        return create_empty_figure("Select 2 or more wells to compare"), subtitle
    
    # Collect data for all wells first
    well_data = []
    for i, dataset_name in enumerate(selected_datasets):
        if dataset_name not in SESSION.datasets:
            continue
        
        try:
            df = SESSION.datasets[dataset_name].get('df')
            if df is None:
                continue
        except:
            continue
        
        measured_col = find_column(df, ['measured tcr'])
        depth_col = find_column(df, ['hole depth'])
        time_col = find_column(df, ['time'])
        
        if not measured_col:
            continue
        
        # Create short name
        name_parts = dataset_name.replace('_', ' ').replace('-', ' ').split()
        short_name = f"{name_parts[0]}_{name_parts[1]}" if len(name_parts) > 1 else name_parts[0]
        short_name = short_name[:15]
        
        # Determine X axis based on normalization
        if normalization == 'depth' and depth_col:
            x_data = df[depth_col]
            x_title = "Hole Depth (m)"
            subtitle = " — by Depth"
        elif normalization == 'elapsed' and time_col:
            try:
                times = pd.to_datetime(df[time_col])
                x_data = (times - times.iloc[0]).dt.total_seconds() / 3600
                x_title = "Elapsed Time (hours)"
                subtitle = " — by Elapsed Time"
            except:
                x_data = df.index
                x_title = "Index"
        elif normalization == 'percent' and depth_col:
            depth_data = df[depth_col].dropna()
            if len(depth_data) > 0:
                min_d, max_d = depth_data.min(), depth_data.max()
                if max_d > min_d:
                    x_data = ((df[depth_col] - min_d) / (max_d - min_d)) * 100
                else:
                    x_data = df.index
                x_title = "Section Complete (%)"
                subtitle = " — by % Section"
            else:
                x_data = df.index
                x_title = "Index"
        else:
            x_data = df.index
            x_title = "Index"
        
        well_data.append({
            'name': short_name,
            'x': x_data,
            'y': df[measured_col],
            'color': WELL_COLORS[i % len(WELL_COLORS)],
            'index': i
        })
    
    if not well_data:
        return create_empty_figure("No TCR data found"), subtitle
    
    # Side-by-side mode: Create subplots
    if chart_mode == 'sidebyside':
        from plotly.subplots import make_subplots
        
        n_wells = len(well_data)
        fig = make_subplots(
            rows=n_wells, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=[wd['name'] for wd in well_data]
        )
        
        for idx, wd in enumerate(well_data):
            fig.add_trace(
                go.Scatter(
                    x=wd['x'], y=wd['y'],
                    name=wd['name'], mode='lines',
                    line=dict(color=wd['color'], width=2),
                    showlegend=False
                ),
                row=idx+1, col=1
            )
        
        # Update subplot title colors
        for i, annotation in enumerate(fig.layout.annotations):
            annotation.font.color = WELL_COLORS[i % len(WELL_COLORS)]
            annotation.font.size = 10
        
        fig.update_layout(
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['card'],
            font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
            margin=dict(l=50, r=20, t=30, b=40),
            height=max(320, 100 * n_wells),  # Dynamic height
            hovermode='x unified',
        )
        
        # Update all x and y axes
        fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
        fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)', title_text='TCR (m³)')
        fig.update_xaxes(title_text=x_title, row=n_wells, col=1)
        
        subtitle = f" — Side-by-Side ({normalization})"
        
    else:
        # Overlay mode: All wells on same axes
        fig = go.Figure()
        
        for wd in well_data:
            fig.add_trace(go.Scatter(
                x=wd['x'], y=wd['y'],
                name=wd['name'], mode='lines',
                line=dict(color=wd['color'], width=2),
            ))
        
        fig.update_layout(
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['card'],
            font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
            legend=dict(bgcolor='rgba(0,0,0,0)', x=0, y=1.15, orientation='h'),
            margin=dict(l=50, r=20, t=40, b=40),
            xaxis=dict(title=x_title, gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(title='TCR (m³)', gridcolor='rgba(255,255,255,0.05)'),
            hovermode='x unified',
        )
    
    return fig, subtitle


@app.callback(
    Output('compare-crr-chart', 'figure'),
    [Input('compare-dataset-selector', 'value'), 
     Input('compare-normalization', 'value'),
     Input('compare-chart-mode', 'value'),
     Input('store-refresh', 'data')]
)
def update_compare_crr_chart(selected_datasets, normalization, chart_mode, refresh):
    """Update CRR comparison chart with overlay or side-by-side mode."""
    if not selected_datasets or len(selected_datasets) < 2:
        return create_empty_figure("Select 2 or more wells")
    
    x_title = "Index"
    well_data = []
    
    for i, dataset_name in enumerate(selected_datasets):
        if dataset_name not in SESSION.datasets:
            continue
        
        try:
            df = SESSION.datasets[dataset_name].get('df')
            if df is None:
                continue
        except:
            continue
        
        crr_col = find_column(df, ['crr'])
        depth_col = find_column(df, ['hole depth'])
        time_col = find_column(df, ['time'])
        
        if not crr_col:
            continue
        
        # Create short name
        name_parts = dataset_name.replace('_', ' ').replace('-', ' ').split()
        short_name = f"{name_parts[0]}_{name_parts[1]}" if len(name_parts) > 1 else name_parts[0]
        short_name = short_name[:12]
        
        # Determine X axis
        if normalization == 'depth' and depth_col:
            x_data = df[depth_col]
            x_title = "Hole Depth (m)"
        elif normalization == 'elapsed' and time_col:
            try:
                times = pd.to_datetime(df[time_col])
                x_data = (times - times.iloc[0]).dt.total_seconds() / 3600
                x_title = "Elapsed Time (hrs)"
            except:
                x_data = df.index
                x_title = "Index"
        elif normalization == 'percent' and depth_col:
            depth_data = df[depth_col].dropna()
            if len(depth_data) > 0:
                min_d, max_d = depth_data.min(), depth_data.max()
                if max_d > min_d:
                    x_data = ((df[depth_col] - min_d) / (max_d - min_d)) * 100
                else:
                    x_data = df.index
                x_title = "Section (%)"
            else:
                x_data = df.index
                x_title = "Index"
        else:
            x_data = df.index
            x_title = "Index"
        
        well_data.append({
            'name': short_name,
            'x': x_data,
            'y': df[crr_col],
            'color': WELL_COLORS[i % len(WELL_COLORS)]
        })
    
    if not well_data:
        return create_empty_figure("No CRR data found")
    
    # Side-by-side mode
    if chart_mode == 'sidebyside':
        from plotly.subplots import make_subplots
        
        n_wells = len(well_data)
        fig = make_subplots(
            rows=n_wells, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=[wd['name'] for wd in well_data]
        )
        
        for idx, wd in enumerate(well_data):
            fig.add_trace(
                go.Scatter(
                    x=wd['x'], y=wd['y'],
                    name=wd['name'], mode='lines',
                    line=dict(color=wd['color'], width=1.5),
                    showlegend=False
                ),
                row=idx+1, col=1
            )
        
        for i, annotation in enumerate(fig.layout.annotations):
            annotation.font.color = WELL_COLORS[i % len(WELL_COLORS)]
            annotation.font.size = 9
        
        fig.update_layout(
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['card'],
            font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
            margin=dict(l=50, r=20, t=30, b=40),
            height=max(280, 80 * n_wells),
            hovermode='x unified',
        )
        
        fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
        fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
        fig.update_xaxes(title_text=x_title, row=n_wells, col=1)
        
    else:
        # Overlay mode
        fig = go.Figure()
        
        for wd in well_data:
            fig.add_trace(go.Scatter(
                x=wd['x'], y=wd['y'],
                name=wd['name'], mode='lines',
                line=dict(color=wd['color'], width=1.5),
            ))
        
        fig.update_layout(
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['card'],
            font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
            legend=dict(bgcolor='rgba(0,0,0,0)', x=0, y=1.15, orientation='h'),
            margin=dict(l=50, r=20, t=40, b=40),
            xaxis=dict(title=x_title, gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(title='CRR (m³/min)', gridcolor='rgba(255,255,255,0.05)'),
            hovermode='x unified',
        )
    
    return fig


@app.callback(
    Output('compare-ufo-chart', 'figure'),
    [Input('compare-dataset-selector', 'value'), Input('store-refresh', 'data')]
)
def update_compare_ufo_chart(selected_datasets, refresh):
    """Update UFO comparison bar chart - shows total UFO events per well."""
    if not selected_datasets or len(selected_datasets) < 2:
        return create_empty_figure("Select 2 or more wells")
    
    well_data = []
    
    for i, dataset_name in enumerate(selected_datasets):
        if dataset_name not in SESSION.datasets:
            continue
        
        try:
            # Get DataFrame directly from SESSION
            df = SESSION.datasets[dataset_name].get('df')
            if df is None:
                continue
        except:
            continue
        
        ufo_col = find_column(df, ['ufo count'])
        
        if ufo_col:
            ufo_data = df[ufo_col].dropna()
            if len(ufo_data) > 0:
                # CORRECTED: Sum all instantaneous UFO readings for total
                total_ufo = ufo_data.sum()
                # Create a unique short name
                # Extract key identifiers from filename
                name_parts = dataset_name.replace('_', ' ').replace('-', ' ').split()
                # Try to find well identifier (like WT_1P11, HH_1i01, etc.)
                short_name = name_parts[0] if name_parts else f"Well {i+1}"
                if len(name_parts) > 1:
                    short_name = f"{name_parts[0]}_{name_parts[1]}" if len(name_parts[1]) < 6 else name_parts[0]
                # Ensure unique by adding index if needed
                short_name = short_name[:12]
                
                well_data.append({
                    'name': short_name,
                    'full_name': dataset_name,
                    'total': total_ufo,
                    'color': WELL_COLORS[i % len(WELL_COLORS)],
                    'index': i
                })
    
    if not well_data:
        return create_empty_figure("No UFO data found")
    
    # Ensure unique names by appending index if duplicates exist
    names_seen = {}
    for wd in well_data:
        if wd['name'] in names_seen:
            names_seen[wd['name']] += 1
            wd['name'] = f"{wd['name']}({names_seen[wd['name']]})"
        else:
            names_seen[wd['name']] = 0
    
    fig = go.Figure()
    
    # Create individual bars for each well
    fig.add_trace(go.Bar(
        x=[wd['name'] for wd in well_data],
        y=[wd['total'] for wd in well_data],
        marker=dict(
            color=[wd['color'] for wd in well_data],
            line=dict(color=COLORS['border'], width=1)
        ),
        text=[f"{int(wd['total'])}" for wd in well_data],
        textposition='outside',
        textfont=dict(size=11, color=COLORS['text']),
        hovertemplate='%{x}<br>Total UFOs: %{y:,.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
        margin=dict(l=50, r=20, t=30, b=80),
        xaxis=dict(
            title='', 
            gridcolor='rgba(255,255,255,0.05)', 
            tickangle=-25,
            tickfont=dict(size=9)
        ),
        yaxis=dict(title='Total UFO Events', gridcolor='rgba(255,255,255,0.05)'),
        showlegend=False,
        bargap=0.25,
        barmode='group',  # Ensure bars are grouped, not stacked
    )
    
    return fig


# --- Flexible Comparison Chart Callbacks ---

@app.callback(
    [Output('compare-flex-x', 'options'),
     Output('compare-flex-y1', 'options'),
     Output('compare-flex-y2', 'options')],
    [Input('compare-dataset-selector', 'value'),
     Input('store-refresh', 'data')]
)
def update_compare_flex_dropdowns(selected_datasets, refresh):
    """Update the flexible comparison dropdowns based on selected wells."""
    if not selected_datasets or len(selected_datasets) < 1:
        return [], [], []
    
    # Get common columns across all selected datasets
    all_columns = None
    for name in selected_datasets:
        ds = SESSION.datasets.get(name)
        if ds and 'df' in ds:
            df = ds['df']
            cols = set(df.columns.tolist())
            if all_columns is None:
                all_columns = cols
            else:
                all_columns = all_columns.intersection(cols)
    
    if not all_columns:
        return [], [], []
    
    # Sort and create options
    sorted_cols = sorted(list(all_columns))
    options = [{'label': col, 'value': col} for col in sorted_cols]
    
    return options, options, options


@app.callback(
    Output('compare-flex-chart', 'figure'),
    [Input('compare-dataset-selector', 'value'),
     Input('compare-flex-x', 'value'),
     Input('compare-flex-y1', 'value'),
     Input('compare-flex-y2', 'value'),
     Input('compare-flex-options', 'value'),
     Input('store-refresh', 'data')]
)
def update_compare_flex_chart(selected_datasets, x_col, y1_cols, y2_cols, options, refresh):
    """Update the flexible comparison chart."""
    fig = go.Figure()
    
    # Empty state
    if not selected_datasets or len(selected_datasets) < 1:
        fig.update_layout(
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['card'],
            font=dict(color=COLORS['text']),
            annotations=[dict(text="Select wells to compare", x=0.5, y=0.5, xref='paper', yref='paper', 
                             showarrow=False, font=dict(size=14, color=COLORS['muted']))]
        )
        return fig
    
    if not x_col:
        fig.update_layout(
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['card'],
            font=dict(color=COLORS['text']),
            annotations=[dict(text="Select X-axis parameter", x=0.5, y=0.5, xref='paper', yref='paper', 
                             showarrow=False, font=dict(size=14, color=COLORS['muted']))]
        )
        return fig
    
    if not y1_cols and not y2_cols:
        fig.update_layout(
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['card'],
            font=dict(color=COLORS['text']),
            annotations=[dict(text="Select Y-axis parameters", x=0.5, y=0.5, xref='paper', yref='paper', 
                             showarrow=False, font=dict(size=14, color=COLORS['muted']))]
        )
        return fig
    
    # Parse options
    normalize_x = 'normalize_x' in (options or [])
    
    y1_cols = y1_cols or []
    y2_cols = y2_cols or []
    
    # Well colors - distinct colors for each well
    well_colors = [
        '#F26522', '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
        '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#A855F7',
    ]
    
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Track which parameters we've added to legend (to avoid duplicate legend entries per param)
    
    for well_idx, well_name in enumerate(selected_datasets):
        ds = SESSION.datasets.get(well_name)
        if not ds or 'df' not in ds:
            continue
        
        df = ds['df']
        well_color = well_colors[well_idx % len(well_colors)]
        
        # Get X data
        if x_col not in df.columns:
            continue
        x_data = df[x_col]
        
        # Normalize X if requested (useful for comparing time series that start at different times)
        if normalize_x:
            if pd.api.types.is_datetime64_any_dtype(x_data):
                # Convert to hours from start
                x_data = (x_data - x_data.min()).dt.total_seconds() / 3600
            elif pd.api.types.is_numeric_dtype(x_data):
                x_data = x_data - x_data.min()
        
        # Add Y1 traces (primary y-axis)
        for y_col in y1_cols:
            if y_col not in df.columns:
                continue
            y_data = pd.to_numeric(df[y_col], errors='coerce')
            
            fig.add_trace(
                go.Scatter(
                    x=x_data, y=y_data,
                    name=f"{well_name} - {y_col}",
                    mode='lines',
                    line=dict(color=well_color, width=1.5),
                    hovertemplate=f'{well_name}<br>{y_col}: %{{y:.3f}}<extra></extra>'
                ),
                secondary_y=False
            )
        
        # Add Y2 traces (secondary y-axis) - use dashed lines to differentiate
        for y_col in y2_cols:
            if y_col not in df.columns:
                continue
            y_data = pd.to_numeric(df[y_col], errors='coerce')
            
            fig.add_trace(
                go.Scatter(
                    x=x_data, y=y_data,
                    name=f"{well_name} - {y_col} (R)",
                    mode='lines',
                    line=dict(color=well_color, width=1.5, dash='dash'),
                    hovertemplate=f'{well_name}<br>{y_col}: %{{y:.3f}}<extra></extra>'
                ),
                secondary_y=True
            )
    
    # X-axis label
    x_label = x_col
    if normalize_x:
        if 'time' in x_col.lower() or 'timestamp' in x_col.lower():
            x_label = f"{x_col} (hours from start)"
        else:
            x_label = f"{x_col} (normalized)"
    
    # Update layout
    fig.update_layout(
        paper_bgcolor=COLORS['bg'],
        plot_bgcolor=COLORS['card'],
        font=dict(color=COLORS['text'], family='JetBrains Mono', size=10),
        margin=dict(l=60, r=60, t=30, b=50),
        legend=dict(
            bgcolor='rgba(17,24,32,0.95)', bordercolor=COLORS['border'], borderwidth=1,
            orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
            font=dict(size=9),
        ),
        hovermode='x unified',
    )
    
    fig.update_xaxes(title_text=x_label, gridcolor='rgba(255,255,255,0.05)')
    
    # Y-axis labels
    if y1_cols:
        y1_label = ', '.join(y1_cols[:2]) + ('...' if len(y1_cols) > 2 else '')
        fig.update_yaxes(title_text=y1_label, gridcolor='rgba(255,255,255,0.05)', secondary_y=False)
    
    if y2_cols:
        y2_label = ', '.join(y2_cols[:2]) + ('...' if len(y2_cols) > 2 else '')
        fig.update_yaxes(title_text=y2_label, gridcolor='rgba(255,255,255,0.05)', secondary_y=True)
    
    return fig


# ============================================================
# LWD/PWD CALLBACKS
# ============================================================

@app.callback(
    [Output('las-upload-status', 'children'),
     Output('las-file-selector', 'options'),
     Output('las-file-selector', 'value'),
     Output('las-compare-selector', 'options'),
     Output('store-refresh', 'data', allow_duplicate=True)],
    [Input('las-upload', 'contents')],
    [State('las-upload', 'filename'),
     State('store-refresh', 'data')],
    prevent_initial_call=True
)
def handle_las_upload(contents_list, filenames, refresh_count):
    """Handle LAS file upload."""
    if not contents_list:
        # Return current state
        las_list = SESSION.get_las_list()
        options = [{'label': name, 'value': name} for name in las_list]
        active = SESSION.active_las
        return no_update, options, active, options, no_update
    
    if not isinstance(contents_list, list):
        contents_list = [contents_list]
        filenames = [filenames]
    
    loaded = []
    errors = []
    
    for contents, filename in zip(contents_list, filenames):
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            
            # Try different encodings
            content_text = None
            for enc in ['utf-8', 'latin-1', 'cp1252', 'utf-16']:
                try:
                    content_text = decoded.decode(enc)
                    break
                except:
                    continue
            
            if content_text is None:
                content_text = decoded.decode('utf-8', errors='replace')
            
            # Parse the LAS file
            parser = parse_las_file(content_text, filename)
            
            if parser.data is not None and len(parser.data) > 0:
                # Create a clean name
                name = filename.replace('.las', '').replace('.LAS', '').replace('.txt', '')
                name = name.replace('_', ' ').strip()
                
                # Avoid duplicates
                base_name = name
                counter = 1
                while name in SESSION.las_files:
                    name = f"{base_name} ({counter})"
                    counter += 1
                
                SESSION.add_las_file(name, parser, content_text)
                loaded.append(name)
            else:
                errors.append(f"{filename}: No data found")
        except Exception as e:
            errors.append(f"{filename}: {str(e)[:50]}")
    
    # Build status message
    status_parts = []
    if loaded:
        status_parts.append(html.Span(f"✓ Loaded: {', '.join(loaded)}", style={'color': COLORS['green']}))
    if errors:
        status_parts.append(html.Span(f" ✗ {'; '.join(errors)}", style={'color': COLORS['red']}))
    
    # Build options
    las_list = SESSION.get_las_list()
    options = [{'label': name, 'value': name} for name in las_list]
    active = SESSION.active_las
    
    # Increment refresh to trigger Main tab dropdown update
    new_refresh = (refresh_count or 0) + 1
    
    return status_parts or "Ready for upload", options, active, options, new_refresh


@app.callback(
    [Output('las-file-info', 'children'),
     Output('las-x-axis', 'options'),
     Output('las-x-axis', 'value'),
     Output('las-y1-channels', 'options'),
     Output('las-y2-channels', 'options')],
    [Input('las-file-selector', 'value')]
)
def update_las_file_selection(selected_file):
    """Update UI when a LAS file is selected."""
    if not selected_file:
        return "No file selected", [], None, [], []
    
    SESSION.active_las = selected_file
    SESSION.save()
    
    parser = SESSION.get_las_parser(selected_file)
    if not parser:
        return "File not found", [], None, [], []
    
    summary = parser.get_summary()
    
    # Build info text
    info_parts = [
        f"Well: {summary['well_name']}",
        f"Type: {summary['index_type'].title()}-indexed",
        f"Rows: {summary['n_rows']:,}",
        f"Channels: {len(summary['channels'])}",
    ]
    if summary['depth_range'] and summary['depth_range'][0] is not None:
        info_parts.append(f"Depth: {summary['depth_range'][0]:.1f} - {summary['depth_range'][1]:.1f} m")
    
    info = " | ".join(info_parts)
    
    # Build channel options with friendly names
    index_col = summary['index_column']
    all_channels = [index_col] + summary['channels'] if index_col else summary['channels']
    
    # X-axis options - for time-indexed, default to Elapsed_Hours
    x_options = []
    default_x = index_col
    
    for ch in all_channels:
        label = parser.get_channel_label(ch)
        x_options.append({'label': label, 'value': ch})
        
        # Prefer Elapsed_Hours for time-indexed files
        if ch == 'Elapsed_Hours' and parser.index_type == 'time':
            default_x = 'Elapsed_Hours'
    
    # Y-axis options (data channels excluding time/index columns)
    y_options = []
    skip_for_y = ['TIME', 'DEPT', 'DEPTH', 'Elapsed_Hours', 'Elapsed_Minutes', 'Time_Index']
    
    for ch in summary['channels']:
        if ch.upper() not in [s.upper() for s in skip_for_y] and ch not in skip_for_y:
            label = parser.get_channel_label(ch)
            y_options.append({'label': label, 'value': ch})
    
    return info, x_options, default_x, y_options, y_options


@app.callback(
    Output('las-compare-container', 'style'),
    [Input('las-view-mode', 'value')]
)
def toggle_compare_selector(mode):
    """Show/hide compare file selector based on mode."""
    if mode == 'compare':
        return {'display': 'block'}
    return {'display': 'none'}


@app.callback(
    [Output('las-main-chart', 'figure'),
     Output('las-chart-subtitle', 'children')],
    [Input('las-file-selector', 'value'),
     Input('las-x-axis', 'value'),
     Input('las-y1-channels', 'value'),
     Input('las-y2-channels', 'value'),
     Input('las-view-mode', 'value'),
     Input('las-compare-selector', 'value')]
)
def update_las_main_chart(selected_file, x_col, y1_cols, y2_cols, view_mode, compare_files):
    """Update the main LAS chart."""
    fig = go.Figure()
    
    if not selected_file:
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': COLORS['text']},
        )
        fig.add_annotation(text="Select a LAS file to display", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=14, color=COLORS['muted']))
        return fig, ""
    
    # Get primary parser for axis labels
    primary_parser = SESSION.get_las_parser(selected_file)
    
    # Build axis titles with friendly names
    x_title = primary_parser.get_channel_label(x_col) if primary_parser and x_col else 'Index'
    
    # Y1 title: combine selected channel names
    y1_title = 'Primary'
    if y1_cols and primary_parser:
        y1_labels = [primary_parser.get_friendly_name(c) for c in y1_cols[:2]]
        y1_units = list(set([primary_parser.get_unit(c) for c in y1_cols if primary_parser.get_unit(c)]))
        y1_title = ', '.join(y1_labels)
        if len(y1_units) == 1:
            y1_title += f' ({y1_units[0]})'
    
    # Y2 title
    y2_title = 'Secondary'
    if y2_cols and primary_parser:
        y2_labels = [primary_parser.get_friendly_name(c) for c in y2_cols[:2]]
        y2_units = list(set([primary_parser.get_unit(c) for c in y2_cols if primary_parser.get_unit(c)]))
        y2_title = ', '.join(y2_labels)
        if len(y2_units) == 1:
            y2_title += f' ({y2_units[0]})'
    
    # Apply dark theme
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': COLORS['text']},
        margin=dict(l=60, r=60, t=40, b=60),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title=x_title),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title=y1_title),
        yaxis2=dict(gridcolor='rgba(255,255,255,0.05)', title=y2_title, overlaying='y', side='right'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        hovermode='x unified',
    )
    
    # Get files to plot
    files_to_plot = [selected_file]
    if view_mode == 'compare' and compare_files:
        files_to_plot = [selected_file] + [f for f in compare_files if f != selected_file]
    
    subtitle_parts = []
    color_idx = 0
    
    for file_name in files_to_plot:
        parser = SESSION.get_las_parser(file_name)
        if not parser:
            continue
        
        df = parser.to_dataframe()
        if df is None or df.empty:
            continue
        
        subtitle_parts.append(parser.get_well_name())
        
        # Get X data - preserve datetime for Timestamp column
        if x_col and x_col in df.columns:
            if x_col == 'Timestamp' or pd.api.types.is_datetime64_any_dtype(df[x_col]):
                x_data = df[x_col]  # Keep as datetime
            else:
                x_data = pd.to_numeric(df[x_col], errors='coerce')
        else:
            x_data = df.index
        
        # Plot primary Y channels
        if y1_cols:
            for y_col in y1_cols:
                if y_col in df.columns:
                    y_data = pd.to_numeric(df[y_col], errors='coerce')
                    color = TRACE_COLORS[color_idx % len(TRACE_COLORS)]
                    # Use friendly name for trace
                    friendly_name = parser.get_friendly_name(y_col)
                    name = friendly_name if len(files_to_plot) == 1 else f"{file_name}: {friendly_name}"
                    fig.add_trace(go.Scatter(
                        x=x_data, y=y_data, mode='lines', name=name,
                        line=dict(color=color, width=1.5),
                        yaxis='y1',
                    ))
                    color_idx += 1
        
        # Plot secondary Y channels
        if y2_cols:
            for y_col in y2_cols:
                if y_col in df.columns:
                    y_data = pd.to_numeric(df[y_col], errors='coerce')
                    color = TRACE_COLORS[color_idx % len(TRACE_COLORS)]
                    friendly_name = parser.get_friendly_name(y_col)
                    name = f"{friendly_name} (R)" if len(files_to_plot) == 1 else f"{file_name}: {friendly_name} (R)"
                    fig.add_trace(go.Scatter(
                        x=x_data, y=y_data, mode='lines', name=name,
                        line=dict(color=color, width=1.5, dash='dot'),
                        yaxis='y2',
                    ))
                    color_idx += 1
    
    subtitle = f"— {', '.join(subtitle_parts)}" if subtitle_parts else ""
    
    return fig, subtitle


@app.callback(
    Output('las-temp-chart', 'figure'),
    [Input('las-file-selector', 'value'),
     Input('las-view-mode', 'value'),
     Input('las-compare-selector', 'value')]
)
def update_las_temp_chart(selected_file, view_mode, compare_files):
    """Update the temperature chart."""
    fig = go.Figure()
    
    if not selected_file:
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': COLORS['text']},
            margin=dict(l=50, r=20, t=20, b=50),
        )
        fig.add_annotation(text="No data", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=12, color=COLORS['muted']))
        return fig
    
    # Get files to plot
    files_to_plot = [selected_file]
    if view_mode == 'compare' and compare_files:
        files_to_plot = [selected_file] + [f for f in compare_files if f != selected_file]
    
    color_idx = 0
    temp_cols = ['PANTM', 'PBRTM', 'PANTM_DR', 'PBRTM_DR']
    has_data = False
    x_title = 'Index'
    
    for file_name in files_to_plot:
        parser = SESSION.get_las_parser(file_name)
        if not parser:
            continue
        
        df = parser.to_dataframe()
        if df is None or df.empty:
            continue
        
        # Get index - prefer Elapsed_Hours for time-indexed
        if parser.index_type == 'time' and 'Elapsed_Hours' in df.columns:
            x_data = df['Elapsed_Hours']
            x_title = 'Elapsed Time (hrs)'
        elif parser.index_type == 'depth':
            index_col = parser.get_index_column()
            if index_col and index_col in df.columns:
                x_data = pd.to_numeric(df[index_col], errors='coerce')
                x_title = parser.get_channel_label(index_col)
            else:
                x_data = df.index
        else:
            x_data = df.index
        
        # Find and plot temperature columns
        for temp_col in temp_cols:
            if temp_col in df.columns:
                y_data = pd.to_numeric(df[temp_col], errors='coerce')
                if y_data.notna().sum() > 0:
                    has_data = True
                    color = TRACE_COLORS[color_idx % len(TRACE_COLORS)]
                    friendly_name = parser.get_friendly_name(temp_col)
                    name = friendly_name if len(files_to_plot) == 1 else f"{file_name}: {friendly_name}"
                    fig.add_trace(go.Scatter(
                        x=x_data, y=y_data, mode='lines', name=name,
                        line=dict(color=color, width=1.5),
                    ))
                    color_idx += 1
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': COLORS['text']},
        margin=dict(l=50, r=20, t=20, b=50),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title=x_title),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='Temperature (°C)'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5, font=dict(size=10)),
        showlegend=True,
    )
    
    if not has_data:
        fig.add_annotation(text="No temperature data in file", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=12, color=COLORS['muted']))
    
    return fig


@app.callback(
    Output('las-ecd-chart', 'figure'),
    [Input('las-file-selector', 'value'),
     Input('las-view-mode', 'value'),
     Input('las-compare-selector', 'value')]
)
def update_las_ecd_chart(selected_file, view_mode, compare_files):
    """Update the ECD/Pressure chart."""
    fig = go.Figure()
    
    if not selected_file:
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': COLORS['text']},
            margin=dict(l=50, r=50, t=20, b=50),
        )
        fig.add_annotation(text="No data", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=12, color=COLORS['muted']))
        return fig
    
    # Get files to plot
    files_to_plot = [selected_file]
    if view_mode == 'compare' and compare_files:
        files_to_plot = [selected_file] + [f for f in compare_files if f != selected_file]
    
    color_idx = 0
    ecd_cols = ['PWEA', 'PWEAAF', 'PWEANF', 'PWEAXF']
    pressure_cols = ['PWPA', 'PWPD', 'PWPI']
    has_data = False
    x_title = 'Index'
    
    for file_name in files_to_plot:
        parser = SESSION.get_las_parser(file_name)
        if not parser:
            continue
        
        df = parser.to_dataframe()
        if df is None or df.empty:
            continue
        
        # Get index - prefer Elapsed_Hours for time-indexed
        if parser.index_type == 'time' and 'Elapsed_Hours' in df.columns:
            x_data = df['Elapsed_Hours']
            x_title = 'Elapsed Time (hrs)'
        elif parser.index_type == 'depth':
            index_col = parser.get_index_column()
            if index_col and index_col in df.columns:
                x_data = pd.to_numeric(df[index_col], errors='coerce')
                x_title = parser.get_channel_label(index_col)
            else:
                x_data = df.index
        else:
            x_data = df.index
        
        # Plot ECD columns (primary Y)
        for ecd_col in ecd_cols:
            if ecd_col in df.columns:
                y_data = pd.to_numeric(df[ecd_col], errors='coerce')
                if y_data.notna().sum() > 0:
                    has_data = True
                    color = TRACE_COLORS[color_idx % len(TRACE_COLORS)]
                    friendly_name = parser.get_friendly_name(ecd_col)
                    name = friendly_name if len(files_to_plot) == 1 else f"{file_name}: {friendly_name}"
                    fig.add_trace(go.Scatter(
                        x=x_data, y=y_data, mode='lines', name=name,
                        line=dict(color=color, width=1.5),
                        yaxis='y1',
                    ))
                    color_idx += 1
        
        # Plot pressure columns (secondary Y)
        for press_col in pressure_cols:
            if press_col in df.columns:
                y_data = pd.to_numeric(df[press_col], errors='coerce')
                if y_data.notna().sum() > 0:
                    has_data = True
                    color = TRACE_COLORS[color_idx % len(TRACE_COLORS)]
                    friendly_name = parser.get_friendly_name(press_col)
                    name = f"{friendly_name}" if len(files_to_plot) == 1 else f"{file_name}: {friendly_name}"
                    fig.add_trace(go.Scatter(
                        x=x_data, y=y_data, mode='lines', name=name,
                        line=dict(color=color, width=1.5, dash='dot'),
                        yaxis='y2',
                    ))
                    color_idx += 1
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': COLORS['text']},
        margin=dict(l=50, r=50, t=20, b=50),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title=x_title),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='ECD (sg)'),
        yaxis2=dict(gridcolor='rgba(255,255,255,0.05)', title='Pressure (bar)', overlaying='y', side='right'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5, font=dict(size=10)),
        showlegend=True,
    )
    
    if not has_data:
        fig.add_annotation(text="No ECD/Pressure data in file", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=12, color=COLORS['muted']))
    
    return fig


@app.callback(
    Output('las-files-table', 'children'),
    [Input('las-file-selector', 'value'),
     Input('las-file-selector', 'options'),  # Triggers on rename/add/remove
     Input('las-upload', 'contents')]
)
def update_las_files_table(selected, options_trigger, upload_trigger):
    """Update the LAS files summary table."""
    las_list = SESSION.get_las_list()
    
    if not las_list:
        return html.Div("No LAS files loaded. Upload LAS files above.", 
                       style={'color': COLORS['muted'], 'fontSize': '12px', 'padding': '20px', 'textAlign': 'center'})
    
    # Build table
    rows = []
    for name in las_list:
        parser = SESSION.get_las_parser(name)
        if not parser:
            continue
        
        summary = parser.get_summary()
        
        # Depth/Time range
        if summary['index_type'] == 'depth' and summary['depth_range']:
            range_str = f"{summary['depth_range'][0]:.1f} - {summary['depth_range'][1]:.1f} m"
        else:
            range_str = f"{summary['n_rows']:,} points"
        
        # Channels summary
        channels = summary['channels']
        if len(channels) > 5:
            channels_str = f"{', '.join(channels[:5])}... (+{len(channels)-5})"
        else:
            channels_str = ', '.join(channels)
        
        is_active = name == SESSION.active_las
        row_style = {
            'padding': '10px 12px', 
            'borderBottom': f'1px solid {COLORS["border"]}',
            'background': 'rgba(242, 101, 34, 0.1)' if is_active else 'transparent',
            'display': 'flex', 
            'alignItems': 'center',
            'gap': '16px',
        }
        
        rows.append(html.Div([
            html.Div([
                html.Span("≋ " if summary['index_type'] == 'time' else "▭ ", style={'marginRight': '4px', 'color': COLORS['muted']}),
                html.Span(name, style={'fontWeight': '600' if is_active else '400', 'color': COLORS['cyan'] if is_active else COLORS['text']}),
            ], style={'flex': '2', 'minWidth': '200px'}),
            html.Div(summary['well_name'], style={'flex': '1.5', 'color': COLORS['dim'], 'fontSize': '11px'}),
            html.Div(summary['index_type'].title(), style={'flex': '0.8', 'color': COLORS['muted'], 'fontSize': '11px'}),
            html.Div(range_str, style={'flex': '1.2', 'color': COLORS['dim'], 'fontSize': '11px'}),
            html.Div(channels_str, style={'flex': '2', 'color': COLORS['muted'], 'fontSize': '10px', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'nowrap'}),
            html.Button("✎", id={'type': 'las-rename-btn', 'index': name}, title='Rename', style={
                'background': COLORS['card'], 'border': f'1px solid {COLORS["border"]}', 'color': COLORS['text'],
                'cursor': 'pointer', 'fontSize': '12px', 'padding': '4px 8px', 'borderRadius': '3px', 'marginRight': '4px',
            }),
            html.Button("⬇", id={'type': 'las-export-btn', 'index': name}, title='Export to CSV', style={
                'background': COLORS['blue'], 'border': 'none', 'color': '#fff',
                'cursor': 'pointer', 'fontSize': '12px', 'padding': '4px 8px', 'borderRadius': '3px', 'marginRight': '4px',
            }),
            html.Button("✕", id={'type': 'las-remove-btn', 'index': name}, style={
                'background': 'transparent', 'border': 'none', 'color': COLORS['red'],
                'cursor': 'pointer', 'fontSize': '14px', 'padding': '4px 8px',
            }),
        ], style=row_style))
    
    # Header row
    header = html.Div([
        html.Div("File", style={'flex': '2', 'minWidth': '200px', 'fontWeight': '600', 'color': COLORS['muted'], 'fontSize': '10px'}),
        html.Div("Well", style={'flex': '1.5', 'fontWeight': '600', 'color': COLORS['muted'], 'fontSize': '10px'}),
        html.Div("Type", style={'flex': '0.8', 'fontWeight': '600', 'color': COLORS['muted'], 'fontSize': '10px'}),
        html.Div("Range", style={'flex': '1.2', 'fontWeight': '600', 'color': COLORS['muted'], 'fontSize': '10px'}),
        html.Div("Channels", style={'flex': '2', 'fontWeight': '600', 'color': COLORS['muted'], 'fontSize': '10px'}),
        html.Div("", style={'width': '80px'}),  # Wider for 3 buttons
    ], style={'display': 'flex', 'padding': '8px 12px', 'borderBottom': f'2px solid {COLORS["border"]}', 'gap': '16px'})
    
    return html.Div([header] + rows)


@app.callback(
    Output('las-file-selector', 'options', allow_duplicate=True),
    [Input({'type': 'las-remove-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'las-remove-btn', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def remove_las_file(n_clicks_list, ids):
    """Handle LAS file removal."""
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate
    
    # Find which button was clicked
    for n_clicks, btn_id in zip(n_clicks_list, ids):
        if n_clicks:
            file_name = btn_id['index']
            SESSION.remove_las_file(file_name)
            break
    
    # Return updated options
    las_list = SESSION.get_las_list()
    return [{'label': name, 'value': name} for name in las_list]


@app.callback(
    Output('las-csv-download-single', 'data'),
    [Input({'type': 'las-export-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'las-export-btn', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def export_single_las_to_csv(n_clicks_list, ids):
    """Export a single LAS file to CSV."""
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate
    
    # Find which button was clicked
    file_name = None
    for n_clicks, btn_id in zip(n_clicks_list, ids):
        if n_clicks:
            file_name = btn_id['index']
            break
    
    if not file_name:
        raise PreventUpdate
    
    parser = SESSION.get_las_parser(file_name)
    if not parser:
        raise PreventUpdate
    
    df = parser.to_dataframe()
    if df is None or df.empty:
        raise PreventUpdate
    
    # Convert Timestamp to string for CSV export
    if 'Timestamp' in df.columns:
        df['Timestamp'] = df['Timestamp'].astype(str)
    
    # Create CSV
    csv_string = df.to_csv(index=True)
    
    # Clean filename for download
    safe_name = file_name.replace(' ', '_').replace('/', '-')
    
    return dict(content=csv_string, filename=f"{safe_name}.csv")


@app.callback(
    Output('las-csv-download', 'data'),
    Input('las-export-all-btn', 'n_clicks'),
    prevent_initial_call=True
)
def export_all_las_to_csv(n_clicks):
    """Export all loaded LAS files to a combined CSV."""
    if not n_clicks:
        raise PreventUpdate
    
    las_list = SESSION.get_las_list()
    if not las_list:
        raise PreventUpdate
    
    all_dfs = []
    
    for name in las_list:
        parser = SESSION.get_las_parser(name)
        if not parser:
            continue
        
        df = parser.to_dataframe()
        if df is None or df.empty:
            continue
        
        # Add file identifier column
        df = df.copy()
        df.insert(0, 'LAS_File', name)
        df.insert(1, 'Well', parser.get_well_name())
        
        # Convert Timestamp to string for CSV export
        if 'Timestamp' in df.columns:
            df['Timestamp'] = df['Timestamp'].astype(str)
        
        all_dfs.append(df)
    
    if not all_dfs:
        raise PreventUpdate
    
    # Combine all dataframes
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Create CSV
    csv_string = combined_df.to_csv(index=False)
    
    # Filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return dict(content=csv_string, filename=f"LAS_Export_All_{timestamp}.csv")


# --- LAS File Rename Callbacks ---

@app.callback(
    [Output('las-rename-modal', 'className'),
     Output('las-rename-current-name', 'children'),
     Output('las-rename-new-name', 'value'),
     Output('las-rename-original-name', 'data')],
    [Input({'type': 'las-rename-btn', 'index': ALL}, 'n_clicks'),
     Input('las-rename-cancel', 'n_clicks')],
    [State({'type': 'las-rename-btn', 'index': ALL}, 'id'),
     State('las-rename-modal', 'className')],
    prevent_initial_call=True
)
def open_las_rename_modal(rename_clicks, cancel_click, ids, current_class):
    """Open or close the LAS rename modal."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id']
    
    # Cancel button closes modal
    if 'las-rename-cancel' in trigger_id:
        return 'modal-overlay', '—', '', None
    
    # Check for rename button clicks - filter out None values
    valid_clicks = [c for c in rename_clicks if c is not None and c > 0]
    if valid_clicks:
        for n_clicks, btn_id in zip(rename_clicks, ids):
            if n_clicks is not None and n_clicks > 0:
                file_name = btn_id['index']
                return 'modal-overlay show', file_name, file_name, file_name
    
    raise PreventUpdate


@app.callback(
    [Output('las-file-selector', 'options', allow_duplicate=True),
     Output('las-rename-modal', 'className', allow_duplicate=True),
     Output('notif', 'children', allow_duplicate=True)],
    Input('las-rename-save', 'n_clicks'),
    [State('las-rename-original-name', 'data'),
     State('las-rename-new-name', 'value')],
    prevent_initial_call=True
)
def save_las_rename(n_clicks, original_name, new_name):
    """Save the LAS file rename."""
    if not n_clicks or not original_name or not new_name:
        raise PreventUpdate
    
    new_name = new_name.strip()
    if not new_name or new_name == original_name:
        raise PreventUpdate
    
    # Check if new name already exists
    las_list = SESSION.get_las_list()
    if new_name in las_list:
        notif = html.Div(f"Name '{new_name}' already exists", style={
            'background': COLORS['red'], 'color': '#FFF', 'padding': '10px 16px',
            'borderRadius': '4px', 'fontSize': '12px'
        })
        return dash.no_update, dash.no_update, notif
    
    # Rename the file in SESSION
    if original_name in SESSION.las_files:
        # Pop the whole dict (contains 'parser' and 'path')
        file_data = SESSION.las_files.pop(original_name)
        SESSION.las_files[new_name] = file_data
        
        # Update active_las if it was the renamed file
        if SESSION.active_las == original_name:
            SESSION.active_las = new_name
        
        # Update cache file path
        old_cache_path = CACHE_DIR / f"{original_name}.las"
        new_cache_path = CACHE_DIR / f"{new_name}.las"
        if old_cache_path.exists():
            old_cache_path.rename(new_cache_path)
            # Update the path in file_data
            file_data['path'] = new_cache_path
        
        SESSION.save()
    
    # Success notification
    notif = html.Div(f"Renamed to '{new_name}'", style={
        'background': COLORS['green'], 'color': '#FFF', 'padding': '10px 16px',
        'borderRadius': '4px', 'fontSize': '12px'
    })
    
    # Return updated options
    las_list = SESSION.get_las_list()
    options = [{'label': name, 'value': name} for name in las_list]
    
    return options, 'modal-overlay', notif


# ============================================================
# MULTI-WELL CUC COMPARISON CALLBACKS (v3.3.0)
# ============================================================

def calculate_cuc_metrics_for_well(df, well_name):
    """
    Calculate CUC metrics for a single well.
    
    NEW LOGIC (v3.3.0):
    - "Clean" = CRR drops to ≤15% of CRR at TD (85% reduction)
    - Must happen AFTER first BU complete (lag reaches TD)
    - Must sustain for ≥5 consecutive minutes
    
    v3.3.1 Addition:
    - "Excess Circulation Time" = Time between clean threshold reached and when bit starts moving
    - Bit moving = bit depth changes by >30m from TD position (starting to trip out)
    
    Returns a dict with all key metrics for comparison.
    """
    result = {
        'well_name': well_name,
        'td_m': None,
        'td_time': None,
        'ref_bu_time_min': None,
        'crr_at_td': None,
        'crr_clean_time': None,
        'time_to_clean_min': None,
        'crr_at_clean': None,
        'bu_cycles': None,
        'crr_data_post_td': [],  # For overlay chart
        'time_since_td_min': [],  # For overlay chart
        'reached_threshold': False,
        'clean_threshold_used': None,  # Dynamic threshold (15% of CRR at TD)
        'pct_reduction': None,  # Actual % reduction achieved
        'first_bu_time': None,  # When first BU completed
        # NEW v3.3.1: Excess circulation tracking
        'trip_start_time': None,  # When bit started moving (trip out began)
        'excess_circ_min': None,  # Minutes circulating after clean before trip started
        'bit_at_clean': None,  # Bit depth when clean threshold reached
        'total_time_at_td_min': None,  # Total time from TD to trip start
        # NEW v3.3.3: Normalized data for BU cycles chart
        'bu_cycles_x': [],  # X-axis: BU cycles (time/ref_bu_time)
        'crr_normalized_y': [],  # Y-axis: CRR / CRR_at_TD
    }
    
    # Configuration for clean detection
    REDUCTION_PCT = 0.15  # Clean = CRR drops to 15% of peak (85% reduction)
    SUSTAIN_MINUTES = 5   # Must stay below threshold for this long
    BIT_MOVE_THRESHOLD = 30  # meters - bit must move this much to indicate trip start
    
    if df is None or df.empty:
        return result
    
    # Find columns
    time_col = find_column(df, ['time'])
    depth_col = find_column(df, ['hole depth'])
    lag_depth_col = find_column(df, ['lag depth'])
    crr_col = find_column(df, ['crr'])
    
    if not all([time_col, depth_col]):
        return result
    
    try:
        df = df.copy()
        df[time_col] = pd.to_datetime(df[time_col])
        
        # Find TD
        td = df[depth_col].max()
        td_idx = df[depth_col].idxmax()
        td_time = df.loc[td_idx, time_col]
        result['td_m'] = round(td, 1)
        result['td_time'] = td_time.strftime('%Y-%m-%d %H:%M')
        
        # Get post-TD data
        post_td = df.loc[td_idx:].copy()
        
        # Reference BU Time (when lag first reaches TD)
        first_bu_complete_time = None
        if lag_depth_col and lag_depth_col in df.columns:
            lag_reaches_td = post_td[post_td[lag_depth_col] >= td - 2]
            if len(lag_reaches_td) > 0:
                first_bu_complete_time = lag_reaches_td.iloc[0][time_col]
                ref_bu_seconds = (first_bu_complete_time - td_time).total_seconds()
                result['ref_bu_time_min'] = round(ref_bu_seconds / 60, 1)
                result['first_bu_time'] = first_bu_complete_time.strftime('%H:%M')
        
        # CRR at TD
        if crr_col and crr_col in df.columns:
            crr_at_td_series = post_td[crr_col].dropna()
            if len(crr_at_td_series) > 0:
                crr_at_td = crr_at_td_series.iloc[0]
                result['crr_at_td'] = round(crr_at_td, 6)
                
                # Calculate dynamic threshold (15% of CRR at TD)
                clean_threshold = crr_at_td * REDUCTION_PCT
                result['clean_threshold_used'] = round(clean_threshold, 6)
                
                # Post-TD CRR data for overlay chart
                post_td_crr = post_td[[time_col, crr_col]].dropna().copy()
                
                if len(post_td_crr) > 0:
                    # Calculate time since TD in minutes
                    post_td_crr['time_since_td'] = (post_td_crr[time_col] - td_time).dt.total_seconds() / 60
                    
                    # Store for chart (sample every 5th point for performance)
                    result['time_since_td_min'] = post_td_crr['time_since_td'].tolist()[::5]
                    result['crr_data_post_td'] = post_td_crr[crr_col].tolist()[::5]
                    
                    # ============================================
                    # NEW v3.3.3: Calculate normalized data for BU cycles chart
                    # X = time_since_td / ref_bu_time (in BU cycles)
                    # Y = CRR / CRR_at_TD (normalized 0-1 scale)
                    # ============================================
                    if result['ref_bu_time_min'] and result['ref_bu_time_min'] > 0 and crr_at_td > 0:
                        # Filter to first 4 BU cycles for chart
                        max_bu = 4.0
                        max_time = max_bu * result['ref_bu_time_min']
                        
                        norm_data = post_td_crr[post_td_crr['time_since_td'] <= max_time].copy()
                        
                        if len(norm_data) > 0:
                            # Calculate BU cycles (X-axis)
                            bu_cycles_arr = norm_data['time_since_td'] / result['ref_bu_time_min']
                            # Calculate normalized CRR (Y-axis), capped at 1.5 for display
                            crr_norm_arr = (norm_data[crr_col] / crr_at_td).clip(upper=1.5)
                            
                            # Sample every 5th point for performance
                            result['bu_cycles_x'] = bu_cycles_arr.tolist()[::5]
                            result['crr_normalized_y'] = crr_norm_arr.tolist()[::5]
                    
                    # ============================================
                    # NEW LOGIC: Find sustained clean time
                    # ============================================
                    
                    # Only look for clean AFTER first BU complete
                    if first_bu_complete_time is not None:
                        post_first_bu = post_td_crr[post_td_crr[time_col] >= first_bu_complete_time].copy()
                        
                        if len(post_first_bu) > 0:
                            # Find where CRR drops below threshold
                            post_first_bu['below_threshold'] = post_first_bu[crr_col] <= clean_threshold
                            
                            # Look for sustained period below threshold
                            clean_start_time = None
                            sustained_count = 0
                            
                            for idx, row in post_first_bu.iterrows():
                                if row['below_threshold']:
                                    if clean_start_time is None:
                                        clean_start_time = row[time_col]
                                    
                                    # Check if we've sustained for SUSTAIN_MINUTES
                                    time_below = (row[time_col] - clean_start_time).total_seconds() / 60
                                    if time_below >= SUSTAIN_MINUTES:
                                        # Found sustained clean period!
                                        result['crr_clean_time'] = clean_start_time.strftime('%H:%M')
                                        result['time_to_clean_min'] = round((clean_start_time - td_time).total_seconds() / 60, 1)
                                        result['crr_at_clean'] = round(row[crr_col], 6)
                                        result['reached_threshold'] = True
                                        
                                        # Calculate actual % reduction
                                        if crr_at_td > 0:
                                            result['pct_reduction'] = round((1 - row[crr_col] / crr_at_td) * 100, 1)
                                        break
                                else:
                                    # Reset if CRR goes back above threshold
                                    clean_start_time = None
                    
                    # Edge case: CRR at TD already very low (well was already clean)
                    if not result['reached_threshold'] and crr_at_td <= 0.006:
                        result['crr_clean_time'] = td_time.strftime('%H:%M')
                        result['time_to_clean_min'] = 0
                        result['crr_at_clean'] = crr_at_td
                        result['reached_threshold'] = True
                        result['pct_reduction'] = 0
        
        # ============================================
        # NEW v3.3.1: Find when trip started (bit moving)
        # ============================================
        bit_depth_col = find_column(df, ['bit depth'])
        
        if result['reached_threshold'] and result['crr_clean_time']:
            # Parse clean time back to datetime for comparison
            clean_time_str = result['crr_clean_time']
            # Reconstruct full datetime from TD date + clean time
            td_date = td_time.date()
            clean_hour, clean_min = map(int, clean_time_str.split(':'))
            from datetime import time as dt_time
            clean_datetime = datetime.combine(td_date, dt_time(clean_hour, clean_min))
            
            # Handle day rollover (if clean time is earlier than TD time, it's next day)
            if clean_datetime < td_time:
                clean_datetime = clean_datetime + pd.Timedelta(days=1)
            
            # Get data after clean threshold reached
            post_clean = post_td[post_td[time_col] >= clean_datetime].copy()
            
            if bit_depth_col and bit_depth_col in df.columns and len(post_clean) > 0:
                # Get bit depth at clean time
                bit_at_clean = post_clean[bit_depth_col].iloc[0] if len(post_clean) > 0 else td
                result['bit_at_clean'] = round(bit_at_clean, 1)
                
                # Find when bit starts moving up (trip out begins)
                # Bit moving = bit depth decreases by more than BIT_MOVE_THRESHOLD from position at clean
                bit_moved = post_clean[post_clean[bit_depth_col] < (bit_at_clean - BIT_MOVE_THRESHOLD)]
                
                if len(bit_moved) > 0:
                    trip_start_time = bit_moved.iloc[0][time_col]
                    result['trip_start_time'] = trip_start_time.strftime('%Y-%m-%d %H:%M')
                    
                    # Calculate excess circulation time (time between clean and trip start)
                    excess_seconds = (trip_start_time - clean_datetime).total_seconds()
                    result['excess_circ_min'] = round(excess_seconds / 60, 1)
                    
                    # Calculate total time at TD (from TD to trip start)
                    total_seconds = (trip_start_time - td_time).total_seconds()
                    result['total_time_at_td_min'] = round(total_seconds / 60, 1)
                else:
                    # Bit never moved significantly - still at TD or data ends before trip
                    result['excess_circ_min'] = None  # Unknown - trip didn't start in data
                    result['trip_start_time'] = "—"
            else:
                # No bit depth column available
                result['excess_circ_min'] = None
                result['trip_start_time'] = "N/A"
        
        # Calculate BU cycles if we have ref BU time
        if result['ref_bu_time_min'] and result['ref_bu_time_min'] > 0 and result['time_to_clean_min']:
            result['bu_cycles'] = round(result['time_to_clean_min'] / result['ref_bu_time_min'], 2)
        
    except Exception as e:
        print(f"CUC calculation error for {well_name}: {e}")
    
    return result


def parse_well_name_from_filename(filename):
    """Extract well name from filename."""
    import re
    # Remove common prefixes and extensions
    name = filename.replace('.csv', '').replace('.CSV', '')
    name = name.replace('Data_Export__Rig_Data___', '').replace('Data Export  Rig Data _ ', '')
    name = name.replace('_dataasjoinbyfield', '').replace('dataasjoinbyfield', '')
    # Remove timestamp patterns
    name = re.sub(r'\d{8}_\d{2}_\d{2}_\d{2}', '', name)
    name = re.sub(r'\d{8}\s+\d{2}_\d{2}_\d{2}', '', name)
    # Clean up
    name = name.strip('_ ').replace('__', '_').replace('  ', ' ')
    return name if name else filename


@app.callback(
    [Output('store-multiwell-data', 'data'),
     Output('multiwell-count', 'children'),
     Output('multiwell-status', 'children')],
    [Input('upload-multiwell-batch', 'contents'),
     Input('btn-process-multiwell', 'n_clicks')],
    [State('upload-multiwell-batch', 'filename'),
     State('store-datasets', 'data')],
    prevent_initial_call=True
)
def process_multiwell_batch(contents_list, process_clicks, filenames, datasets):
    """Process multiple CSV files for CUC comparison."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    results = []
    
    # If batch upload triggered
    if triggered_id == 'upload-multiwell-batch' and contents_list:
        for content, filename in zip(contents_list, filenames):
            try:
                content_type, content_string = content.split(',')
                decoded = base64.b64decode(content_string)
                
                df = None
                # Try different encoding/separator combinations
                # 12.25" files: UTF-16-LE tab-separated
                # 16.5" files: UTF-8 comma-separated
                encoding_sep_combos = [
                    ('utf-8', ','),       # New 16.5" format
                    ('utf-16-le', '\t'),  # Original 12.25" format
                    ('utf-16', '\t'),
                    ('cp1252', ','),
                    ('cp1252', '\t'),
                ]
                
                for encoding, sep in encoding_sep_combos:
                    try:
                        test_df = pd.read_csv(io.BytesIO(decoded), encoding=encoding, sep=sep)
                        if len(test_df.columns) > 5:
                            df = test_df
                            print(f"Successfully parsed {filename} with {encoding}/{sep}")
                            break
                    except:
                        continue
                
                if df is None:
                    print(f"Could not parse {filename} with any encoding/separator combo")
                    continue
                
                well_name = parse_well_name_from_filename(filename)
                metrics = calculate_cuc_metrics_for_well(df, well_name)
                results.append(metrics)
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                continue
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                continue
    
    # If "Process All Loaded Wells" button triggered
    elif triggered_id == 'btn-process-multiwell' and datasets:
        for ds in datasets:
            try:
                df = SESSION.get_df(ds.get('name'))
                if df is not None:
                    metrics = calculate_cuc_metrics_for_well(df, ds.get('name', 'Unknown'))
                    results.append(metrics)
            except Exception as e:
                print(f"Error processing {ds.get('name')}: {e}")
                continue
    
    if not results:
        return [], "0", "No wells processed"
    
    count = len(results)
    status = f"{count} well(s) processed"
    
    return results, str(count), status


@app.callback(
    [Output('multiwell-cuc-table', 'children'),
     Output('multiwell-crr-overlay', 'figure'),
     Output('multiwell-normalized-bu', 'figure'),
     Output('multiwell-bu-bar-chart', 'figure'),
     Output('threshold-reached-count', 'children'),
     Output('threshold-reached-pct', 'children'),
     Output('avg-bu-cycles', 'children'),
     Output('avg-ref-bu-time', 'children'),
     Output('avg-time-to-clean', 'children'),
     Output('avg-excess-circ', 'children')],
    Input('store-multiwell-data', 'data'),
    prevent_initial_call=True
)
def update_multiwell_display(data):
    """Update the multi-well comparison display."""
    empty_fig = go.Figure()
    empty_fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=20, t=30, b=40),
        annotations=[dict(
            text="Process wells to see comparison",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color='#666')
        )]
    )
    
    if not data:
        return (
            html.Div("No data to display", style={'color': COLORS['muted'], 'textAlign': 'center', 'padding': '20px'}),
            empty_fig,
            empty_fig,
            empty_fig,
            "—", "", "—", "—", "—", "—"
        )
    
    # Build comparison table
    # Table header style
    th_style = {'padding': '8px 10px', 'textAlign': 'right', 'background': COLORS['bg'], 'fontWeight': '600', 'fontSize': '10px', 'color': COLORS['text'], 'whiteSpace': 'nowrap'}
    th_style_left = {**th_style, 'textAlign': 'left'}
    th_style_center = {**th_style, 'textAlign': 'center'}
    
    table_header = html.Tr([
        html.Th("Well", style=th_style_left),
        html.Th("TD (m)", style=th_style),
        html.Th("TD Reached", style=th_style),
        html.Th("Ref BU (min)", style=th_style),
        html.Th("CRR@TD", style=th_style),
        html.Th("Clean (min)", style=th_style),
        html.Th("BU to Clean", style=th_style),
        html.Th("Trip Start", style=th_style),
        html.Th("Excess (min)", style=th_style),
        html.Th("Status", style=th_style_center),
    ])
    
    table_rows = []
    colors_list = ['#F26522', '#06B6D4', '#10B981', '#8B5CF6', '#EC4899', '#F59E0B', '#3B82F6', '#EF4444', '#14B8A6', '#A855F7']
    
    for i, well in enumerate(data):
        color = colors_list[i % len(colors_list)]
        status_color = COLORS['green'] if well.get('reached_threshold') else COLORS['yellow']
        status_text = "✓ Clean" if well.get('reached_threshold') else "— Pending"
        
        # Determine excess circulation color (red if >30 min, yellow if >15 min, green otherwise)
        excess_min = well.get('excess_circ_min')
        if excess_min is not None:
            if excess_min > 30:
                excess_color = COLORS['red']
            elif excess_min > 15:
                excess_color = COLORS['yellow']
            else:
                excess_color = COLORS['green']
            excess_str = f"{excess_min:.0f}"
        else:
            excess_color = COLORS['muted']
            excess_str = "—"
        
        # BU Cycles color coding (green <2, yellow 2-3, red >3)
        bu_cycles = well.get('bu_cycles')
        if bu_cycles is not None:
            if bu_cycles <= 2:
                bu_color = COLORS['green']
            elif bu_cycles <= 3:
                bu_color = COLORS['yellow']
            else:
                bu_color = COLORS['red']
            bu_str = f"{bu_cycles:.2f}"
        else:
            bu_color = COLORS['muted']
            bu_str = "—"
        
        # Cell style
        td_style = {'padding': '6px 10px', 'textAlign': 'right', 'fontSize': '10px', 'fontFamily': 'JetBrains Mono', 'color': COLORS['text']}
        
        row = html.Tr([
            html.Td(html.Span([
                html.Span("●", style={'color': color, 'marginRight': '6px'}),
                well.get('well_name', '—')
            ]), style={**td_style, 'textAlign': 'left', 'fontFamily': 'inherit'}),
            html.Td(well.get('td_m', '—'), style=td_style),
            html.Td(well.get('td_time', '—'), style={**td_style, 'color': COLORS['dim']}),
            html.Td(well.get('ref_bu_time_min', '—'), style={**td_style, 'color': COLORS['blue']}),
            html.Td(f"{well.get('crr_at_td', 0):.4f}" if well.get('crr_at_td') else '—', style={**td_style, 'color': COLORS['orange']}),
            html.Td(f"{well.get('time_to_clean_min', 0):.0f}" if well.get('time_to_clean_min') is not None else '—', style={**td_style, 'color': COLORS['green']}),
            html.Td(bu_str, style={**td_style, 'color': bu_color, 'fontWeight': '600'}),
            html.Td(well.get('trip_start_time', '—'), style={**td_style, 'color': COLORS['dim']}),
            html.Td(excess_str, style={**td_style, 'fontWeight': '600', 'color': excess_color}),
            html.Td(status_text, style={**td_style, 'textAlign': 'center', 'fontWeight': '600', 'color': status_color}),
        ], style={'borderBottom': f'1px solid {COLORS["border"]}'})
        table_rows.append(row)
    
    table = html.Table([
        html.Thead(table_header),
        html.Tbody(table_rows)
    ], style={'width': '100%', 'borderCollapse': 'collapse', 'fontSize': '11px'})
    
    # Build CRR overlay chart
    fig = go.Figure()
    
    for i, well in enumerate(data):
        color = colors_list[i % len(colors_list)]
        x_data = well.get('time_since_td_min', [])
        y_data = well.get('crr_data_post_td', [])
        
        if x_data and y_data:
            fig.add_trace(go.Scatter(
                x=x_data,
                y=y_data,
                mode='lines',
                name=well.get('well_name', f'Well {i+1}'),
                line=dict(color=color, width=1.5),
                hovertemplate='%{y:.4f} m³/min<br>%{x:.0f} min from TD<extra></extra>'
            ))
            
            # Add horizontal line for each well's clean threshold (15% of CRR at TD)
            threshold = well.get('clean_threshold_used')
            if threshold:
                fig.add_hline(
                    y=threshold,
                    line_dash="dot",
                    line_color=color,
                    line_width=1,
                    opacity=0.5,
                )
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#1a1a2e',
        plot_bgcolor='#1a1a2e',
        margin=dict(l=50, r=20, t=30, b=50),
        xaxis=dict(
            title='Time since TD (minutes)',
            gridcolor='rgba(255,255,255,0.1)',
            zerolinecolor='rgba(255,255,255,0.2)',
        ),
        yaxis=dict(
            title='CRR (m³/min)',
            type='log',
            gridcolor='rgba(255,255,255,0.1)',
            zerolinecolor='rgba(255,255,255,0.2)',
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='left',
            x=0,
            font=dict(size=10)
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor='#1a1a2e',
            bordercolor='#333',
            font=dict(color='#e5e5e5', size=11)
        )
    )
    
    # ============================================
    # NEW: Build Normalized CRR vs BU Cycles chart
    # ============================================
    fig_norm = go.Figure()
    
    for i, well in enumerate(data):
        color = colors_list[i % len(colors_list)]
        x_norm = well.get('bu_cycles_x', [])
        y_norm = well.get('crr_normalized_y', [])
        
        if x_norm and y_norm and len(x_norm) > 5:
            fig_norm.add_trace(go.Scatter(
                x=x_norm,
                y=y_norm,
                mode='lines',
                name=well.get('well_name', f'Well {i+1}'),
                line=dict(color=color, width=2),
                hovertemplate='CRR: %{y:.2f}x<br>BU: %{x:.2f}<extra></extra>'
            ))
    
    # Add 15% threshold line
    fig_norm.add_hline(
        y=0.15,
        line_dash="dash",
        line_color='#ef4444',
        line_width=2,
        annotation_text="15% threshold (Clean)",
        annotation_position="right",
        annotation_font=dict(size=10, color='#ef4444')
    )
    
    # Add 1 BU reference line
    fig_norm.add_vline(
        x=1.0,
        line_dash="dot",
        line_color='#6b7280',
        line_width=1,
        annotation_text="1 BU",
        annotation_position="top",
        annotation_font=dict(size=9, color='#6b7280')
    )
    
    fig_norm.update_layout(
        template='plotly_dark',
        paper_bgcolor='#1a1a2e',
        plot_bgcolor='#1a1a2e',
        margin=dict(l=50, r=80, t=30, b=50),
        xaxis=dict(
            title='BU Cycles',
            gridcolor='rgba(255,255,255,0.1)',
            zerolinecolor='rgba(255,255,255,0.2)',
            range=[0, 4],
            tickvals=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4],
        ),
        yaxis=dict(
            title='CRR / CRR at TD',
            gridcolor='rgba(255,255,255,0.1)',
            zerolinecolor='rgba(255,255,255,0.2)',
            range=[0, 1.6],
            tickvals=[0, 0.15, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4],
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='left',
            x=0,
            font=dict(size=10)
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor='#1a1a2e',
            bordercolor='#333',
            font=dict(color='#e5e5e5', size=11)
        )
    )
    
    # Calculate summary statistics
    reached_count = sum(1 for w in data if w.get('reached_threshold'))
    total_count = len(data)
    reached_pct = f"({reached_count}/{total_count} = {100*reached_count/total_count:.0f}%)" if total_count > 0 else ""
    
    # Average BU cycles to clean (KEY NORMALIZED METRIC)
    bu_cycles_list = [w.get('bu_cycles') for w in data if w.get('bu_cycles')]
    avg_bu_cycles = f"{np.mean(bu_cycles_list):.2f}" if bu_cycles_list else "—"
    
    # Average Reference BU time
    ref_bu_times = [w.get('ref_bu_time_min') for w in data if w.get('ref_bu_time_min')]
    avg_ref_bu = f"{np.mean(ref_bu_times):.0f}" if ref_bu_times else "—"
    
    # Average time to clean
    times_to_clean = [w.get('time_to_clean_min') for w in data if w.get('time_to_clean_min')]
    avg_time = f"{np.mean(times_to_clean):.0f}" if times_to_clean else "—"
    
    # Calculate average excess circulation time
    excess_times = [w.get('excess_circ_min') for w in data if w.get('excess_circ_min') is not None]
    avg_excess = f"{np.mean(excess_times):.0f}" if excess_times else "—"
    
    # ============================================
    # BU Cycles Bar Chart (like XOM style)
    # ============================================
    fig_bar = go.Figure()
    
    # Get well names and BU cycles
    well_names = []
    bu_values = []
    bar_colors = []
    
    for well in data:
        well_name = well.get('well_name', 'Unknown')
        bu_cycle = well.get('bu_cycles')
        
        if bu_cycle is not None:
            well_names.append(well_name)
            bu_values.append(bu_cycle)
            # Color based on performance (green <2, yellow 2-3, red >3)
            # But using a consistent blue for clean look as requested
            bar_colors.append('#3b82f6')  # Blue for all bars
    
    if bu_values:
        # Add bars
        fig_bar.add_trace(go.Bar(
            x=well_names,
            y=bu_values,
            marker_color=bar_colors,
            marker_line_color='#fff',
            marker_line_width=0.5,
            text=[f'{v:.1f}' for v in bu_values],
            textposition='outside',
            textfont=dict(size=11, color='#e5e5e5'),
            hovertemplate='%{x}<br>BU Cycles: %{y:.2f}<extra></extra>'
        ))
        
        # Calculate and add average line
        avg_bu_val = np.mean(bu_values)
        fig_bar.add_hline(
            y=avg_bu_val,
            line_dash="dash",
            line_color='#f59e0b',
            line_width=2,
            annotation_text=f"Avg: {avg_bu_val:.1f}",
            annotation_position="right",
            annotation_font=dict(size=11, color='#f59e0b')
        )
    
    fig_bar.update_layout(
        template='plotly_dark',
        paper_bgcolor='#1a1a2e',
        plot_bgcolor='#1a1a2e',
        margin=dict(l=50, r=60, t=30, b=80),
        xaxis=dict(
            title='',
            tickangle=-45,
            tickfont=dict(size=10),
            gridcolor='rgba(255,255,255,0.05)',
        ),
        yaxis=dict(
            title='BU Cycles to Clean',
            gridcolor='rgba(255,255,255,0.1)',
            zerolinecolor='rgba(255,255,255,0.2)',
            range=[0, max(bu_values) * 1.2 if bu_values else 5],
        ),
        showlegend=False,
        bargap=0.3,
        hoverlabel=dict(
            bgcolor='#1a1a2e',
            bordercolor='#333',
            font=dict(color='#e5e5e5', size=11)
        )
    )
    
    return (
        table,
        fig,
        fig_norm,
        fig_bar,
        str(reached_count),
        reached_pct,
        avg_bu_cycles,
        avg_ref_bu,
        avg_time,
        avg_excess
    )


@app.callback(
    Output('download-multiwell-excel', 'data'),
    Input('btn-export-multiwell', 'n_clicks'),
    State('store-multiwell-data', 'data'),
    prevent_initial_call=True
)
def export_multiwell_to_excel(n_clicks, data):
    """Export multi-well CUC comparison to Excel."""
    if not n_clicks or not data:
        raise PreventUpdate
    
    # Build dataframe
    rows = []
    for well in data:
        rows.append({
            'Well': well.get('well_name', ''),
            'TD (m)': well.get('td_m', ''),
            'TD Time': well.get('td_time', ''),
            'Ref BU Time (min)': well.get('ref_bu_time_min', ''),
            'First BU Complete': well.get('first_bu_time', ''),
            'CRR at TD (m³/min)': well.get('crr_at_td', ''),
            'Clean Threshold (15%)': well.get('clean_threshold_used', ''),
            'Time to Clean (min)': well.get('time_to_clean_min', ''),
            'CRR at Clean': well.get('crr_at_clean', ''),
            'BU Cycles': well.get('bu_cycles', ''),
            'CRR Reduction (%)': well.get('pct_reduction', ''),
            'Trip Start Time': well.get('trip_start_time', ''),
            'Excess Circulation (min)': well.get('excess_circ_min', ''),
            'Total Time at TD (min)': well.get('total_time_at_td_min', ''),
            'Reached Threshold': 'Yes' if well.get('reached_threshold') else 'No',
        })
    
    df = pd.DataFrame(rows)
    
    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='CUC Comparison', index=False)
    
    output.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return dcc.send_bytes(output.getvalue(), f"CUC_MultiWell_Comparison_{timestamp}.xlsx")


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print()
    print("=" * 50)
    print(f"  {APP_TITLE} v{APP_VERSION}")
    print("=" * 50)
    print()
    
    if SESSION.datasets:
        print(f"  ✅ Restored {len(SESSION.datasets)} dataset(s)")
        if SESSION.kpis:
            print(f"  ✅ Restored {len(SESSION.kpis)} KPI(s)")
    else:
        print("  ℹ️  No previous session")
    
    if SESSION.las_files:
        print(f"  ✅ Restored {len(SESSION.las_files)} LAS file(s)")
    
    print()
    print("  🌐 http://localhost:8050")
    print("  🛑 Ctrl+C to stop")
    print()
    print("=" * 50)
    
    app.run(debug=False, host='127.0.0.1', port=8050)
