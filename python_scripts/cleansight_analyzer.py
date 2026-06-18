#!/usr/bin/env python3
"""
CleanSight Data Analysis Tool
==============================
A local Python-based tool for analyzing DrillDocs/CleanSight drilling data exports.

Features:
- Import and clean CleanSight CSV exports (handles UTF-16 encoding)
- Calculate derived hole cleaning metrics (TCR ratio, transport efficiency)
- Generate diagnostic plots for hole cleaning evaluation
- Detect anomalies (poor cleaning, cavings, sensor artifacts)
- Export analysis reports

Usage:
    python cleansight_analyzer.py path/to/your/data.csv

Requirements:
    pip install pandas numpy matplotlib seaborn plotly scipy

Author: Generated for DrillDocs CleanSight analysis
"""

import os
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Analysis configuration and thresholds."""
    
    # TCR Recovery Ratio thresholds
    TCR_RATIO_LOW_ALARM = 0.70
    TCR_RATIO_LOW_WARNING = 0.85
    TCR_RATIO_HIGH_WARNING = 1.15
    TCR_RATIO_HIGH_ALARM = 1.30
    
    # UFO (Caving) thresholds
    UFO_COUNT_WARNING = 10  # per hour
    UFO_SIZE_WARNING = 50   # mm
    
    # CSD P50 shift threshold (%)
    CSD_SHIFT_WARNING = 30
    
    # Operational state detection
    ROP_DRILLING_THRESHOLD = 0.1  # ft/h - above this = drilling
    RPM_DRILLING_THRESHOLD = 5    # RPM - above this = rotating
    BLOCK_HEIGHT_CONNECTION = 40  # m - above this = near surface (connection)
    
    # Rolling window sizes (in data points)
    ROLLING_WINDOW_SHORT = 30   # ~30 min at 1-min data
    ROLLING_WINDOW_LONG = 60    # ~1 hour
    
    # Plot settings
    FIGURE_DPI = 150
    FIGURE_SIZE_LARGE = (14, 8)
    FIGURE_SIZE_MEDIUM = (12, 6)
    FIGURE_SIZE_SMALL = (10, 5)
    
    # Color palette
    COLORS = {
        'primary': '#ff6b35',
        'secondary': '#00d9ff',
        'success': '#3fb950',
        'warning': '#f0b429',
        'danger': '#f85149',
        'purple': '#a371f7',
        'gray': '#8b949e',
        'dark': '#0a0e14',
        'light': '#e6edf3'
    }


# =============================================================================
# DATA LOADING AND CLEANING
# =============================================================================

class DataLoader:
    """Handles loading and initial cleaning of CleanSight data exports."""
    
    # Standard column name mappings (from various export formats)
    COLUMN_MAPPINGS = {
        'time': ['time', 'Time', 'TIME', 'Timestamp', 'DateTime'],
        'crr_bbl': ['CRR (bbl/min)', 'CRR_bbl', 'CRR bbl/min', 'CRR'],
        'crr_lbm': ['CRR (lbm/min)', 'CRR_lbm', 'CRR lbm/min'],
        'hole_depth': ['Hole Depth (m)', 'Hole_Depth', 'HoleDepth', 'DEPTHOLE'],
        'bit_depth': ['Bit Depth (m)', 'Bit_Depth', 'BitDepth', 'DEPTBIT'],
        'flow_in': ['Flow In (gpm)', 'Flow_In', 'FlowIn', 'FLOWIN', 'SPP_Flow'],
        'rop': ['ROP (ft/h)', 'ROP', 'ROP_ft_h', 'ROPA'],
        'lag_depth': ['Lag Depth (m)', 'Lag_Depth', 'LagDepth'],
        'lag_time': ['Lag Time (min)', 'Lag_Time', 'LagTime'],
        'pump_pressure': ['Pump Pressure (psi)', 'Pump_Pressure', 'SPP', 'SPPA'],
        'ecd': ['ECD (ppg)', 'ECD', 'ECD_ppg'],
        'inclination': ['Inclination (degrees)', 'Inclination', 'INC', 'INCL'],
        'rpm': ['RPM', 'Surface RPM', 'RPMA', 'Rotary_RPM'],
        'pit_volume': ['Pit Volume (bbl)', 'Pit_Volume', 'PitVol', 'PTVOL'],
        'gas': ['GAS', 'Gas', 'TotalGas'],
        'hook_load': ['Hook Load (klbf)', 'Hook_Load', 'HookLoad', 'HKLA'],
        'block_height': ['Block Height (m)', 'Block_Height', 'BlockHeight', 'BLKPOS'],
        'csd_p50': ['CSD P50 (mm)', 'CSD_P50', 'CuttingSize'],
        'ufo_count': ['UFO Count', 'UFO_Count', 'Cavings'],
        'rig_message': ['Rig Message', 'Rig_Message', 'RigState'],
        'lagged_rop': ['Lagged ROP (m/hr)', 'Lagged_ROP', 'LaggedROP'],
        'measured_tcr': ['Measured TCR (bbl)', 'Measured_TCR', 'TCR_Measured'],
        'theoretical_tcr': ['Theoretical TCR (bbl)', 'Theoretical_TCR', 'TCR_Theoretical'],
        'theoretical_lag_tcr': ['Theoretical Lag Depth TCR (bbl)', 'Theoretical_Lag_TCR'],
        'measured_tcr_lbm': ['Measured TCR (lbm)', 'Measured_TCR_lbm'],
        'theoretical_tcr_lbm': ['Theoretical TCR (lbm)', 'Theoretical_TCR_lbm'],
        'wob': ['Weight on Bit', 'WOB', 'WOBA'],
        'torque': ['Rotary Torque', 'Torque', 'TORA', 'TRQ'],
        'mud_density_in': ['Mud Density IN', 'MW_In', 'MWIN'],
        'mud_density_out': ['Mud Density OUT', 'MW_Out', 'MWOUT'],
        'sle_avg': ['SLE_AVG', 'SLE Average', 'ShakerLoadEstimate'],
    }
    
    @staticmethod
    def detect_encoding(filepath: str) -> str:
        """Detect file encoding by reading first few bytes."""
        with open(filepath, 'rb') as f:
            raw = f.read(4)
        
        if raw.startswith(b'\xff\xfe'):
            return 'utf-16-le'
        elif raw.startswith(b'\xfe\xff'):
            return 'utf-16-be'
        elif raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        else:
            return 'utf-8'
    
    @staticmethod
    def detect_delimiter(filepath: str, encoding: str) -> str:
        """Detect CSV delimiter."""
        with open(filepath, 'r', encoding=encoding, errors='replace') as f:
            first_line = f.readline()
        
        if '\t' in first_line:
            return '\t'
        elif ';' in first_line:
            return ';'
        else:
            return ','
    
    @classmethod
    def load(cls, filepath: str) -> pd.DataFrame:
        """
        Load CleanSight data export file.
        
        Handles:
        - UTF-16 and UTF-8 encodings
        - Tab, comma, and semicolon delimiters
        - Various column naming conventions
        
        Args:
            filepath: Path to CSV export file
            
        Returns:
            Cleaned DataFrame with standardized column names
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        print(f"Loading: {filepath.name}")
        
        # Detect encoding and delimiter
        encoding = cls.detect_encoding(str(filepath))
        delimiter = cls.detect_delimiter(str(filepath), encoding)
        
        print(f"  Encoding: {encoding}, Delimiter: {'TAB' if delimiter == '\t' else delimiter}")
        
        # Load data
        df = pd.read_csv(filepath, encoding=encoding, sep=delimiter, low_memory=False)
        
        # Clean column names
        df.columns = df.columns.str.strip().str.replace('"', '').str.replace('\ufeff', '')
        
        # Standardize column names
        df = cls._standardize_columns(df)
        
        # Convert data types
        df = cls._convert_types(df)
        
        print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
        print(f"  Time range: {df['time'].min()} to {df['time'].max()}")
        
        return df
    
    @classmethod
    def _standardize_columns(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names to internal format."""
        rename_map = {}
        
        for standard_name, possible_names in cls.COLUMN_MAPPINGS.items():
            for col in df.columns:
                if col in possible_names or col.lower().replace(' ', '_') == standard_name:
                    rename_map[col] = standard_name
                    break
        
        df = df.rename(columns=rename_map)
        return df
    
    @classmethod
    def _convert_types(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to appropriate data types."""
        # Time column
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], errors='coerce')
        
        # Numeric columns
        numeric_cols = [
            'crr_bbl', 'crr_lbm', 'hole_depth', 'bit_depth', 'flow_in', 'rop',
            'pump_pressure', 'ecd', 'inclination', 'rpm', 'pit_volume', 'gas',
            'hook_load', 'block_height', 'csd_p50', 'ufo_count', 'lagged_rop',
            'measured_tcr', 'theoretical_tcr', 'theoretical_lag_tcr',
            'lag_depth', 'lag_time', 'wob', 'torque', 'sle_avg'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df


# =============================================================================
# DATA PROCESSING AND DERIVED METRICS
# =============================================================================

class DataProcessor:
    """Calculate derived metrics and enrich data."""
    
    def __init__(self, df: pd.DataFrame, config: Config = None):
        self.df = df.copy()
        self.config = config or Config()
        self._process()
    
    def _process(self):
        """Run all processing steps."""
        self._calculate_tcr_ratio()
        self._classify_operational_state()
        self._calculate_rolling_metrics()
        self._calculate_transport_efficiency()
        self._detect_connections()
    
    def _calculate_tcr_ratio(self):
        """Calculate TCR recovery ratio (measured/theoretical)."""
        if 'measured_tcr' in self.df.columns and 'theoretical_tcr' in self.df.columns:
            mask = (self.df['theoretical_tcr'] > 0) & (self.df['measured_tcr'] > 0)
            self.df['tcr_ratio'] = np.nan
            self.df.loc[mask, 'tcr_ratio'] = (
                self.df.loc[mask, 'measured_tcr'] / self.df.loc[mask, 'theoretical_tcr']
            )
    
    def _classify_operational_state(self):
        """Classify each data point as drilling, circulating, connection, etc."""
        self.df['is_drilling'] = False
        self.df['is_rotating'] = False
        self.df['is_circulating'] = False
        self.df['rig_state'] = 'Unknown'
        
        # Drilling: ROP > 0 and RPM > 0
        if 'rop' in self.df.columns and 'rpm' in self.df.columns:
            drilling_mask = (
                (self.df['rop'] > self.config.ROP_DRILLING_THRESHOLD) &
                (self.df['rpm'] > self.config.RPM_DRILLING_THRESHOLD)
            )
            self.df.loc[drilling_mask, 'is_drilling'] = True
            self.df.loc[drilling_mask, 'rig_state'] = 'Drilling'
        
        # Rotating (but not drilling)
        if 'rpm' in self.df.columns:
            rotating_mask = (
                (self.df['rpm'] > self.config.RPM_DRILLING_THRESHOLD) &
                (~self.df['is_drilling'])
            )
            self.df.loc[rotating_mask, 'is_rotating'] = True
            self.df.loc[rotating_mask, 'rig_state'] = 'Rotating'
        
        # Circulating (flow but no drilling)
        if 'flow_in' in self.df.columns:
            circ_mask = (
                (self.df['flow_in'] > 100) &
                (~self.df['is_drilling'])
            )
            self.df.loc[circ_mask, 'is_circulating'] = True
            self.df.loc[circ_mask & ~self.df['is_rotating'], 'rig_state'] = 'Circulating'
    
    def _calculate_rolling_metrics(self):
        """Calculate rolling averages and statistics."""
        if 'crr_bbl' in self.df.columns:
            self.df['crr_rolling_mean'] = self.df['crr_bbl'].rolling(
                window=self.config.ROLLING_WINDOW_SHORT, min_periods=1
            ).mean()
            
            self.df['crr_rolling_std'] = self.df['crr_bbl'].rolling(
                window=self.config.ROLLING_WINDOW_SHORT, min_periods=1
            ).std()
        
        if 'tcr_ratio' in self.df.columns:
            self.df['tcr_ratio_rolling'] = self.df['tcr_ratio'].rolling(
                window=self.config.ROLLING_WINDOW_LONG, min_periods=1
            ).mean()
        
        if 'csd_p50' in self.df.columns:
            self.df['csd_rolling_mean'] = self.df['csd_p50'].rolling(
                window=self.config.ROLLING_WINDOW_SHORT, min_periods=1
            ).mean()
    
    def _calculate_transport_efficiency(self):
        """Calculate cuttings transport efficiency index."""
        if 'crr_bbl' in self.df.columns and 'flow_in' in self.df.columns:
            mask = self.df['flow_in'] > 0
            self.df['transport_efficiency'] = np.nan
            self.df.loc[mask, 'transport_efficiency'] = (
                self.df.loc[mask, 'crr_bbl'] / self.df.loc[mask, 'flow_in'] * 1000
            )
    
    def _detect_connections(self):
        """Detect connection events based on block height patterns."""
        self.df['is_connection'] = False
        
        if 'block_height' in self.df.columns:
            # Connection = block near surface
            self.df['is_connection'] = self.df['block_height'] > self.config.BLOCK_HEIGHT_CONNECTION
    
    def get_data(self) -> pd.DataFrame:
        """Return processed DataFrame."""
        return self.df


# =============================================================================
# ANOMALY DETECTION
# =============================================================================

class AnomalyDetector:
    """Detect anomalies in drilling data."""
    
    def __init__(self, df: pd.DataFrame, config: Config = None):
        self.df = df
        self.config = config or Config()
        self.anomalies = []
    
    def detect_all(self) -> List[Dict[str, Any]]:
        """Run all anomaly detection routines."""
        self.anomalies = []
        
        self._detect_tcr_anomalies()
        self._detect_ufo_events()
        self._detect_csd_shifts()
        self._detect_sensor_artifacts()
        
        return self.anomalies
    
    def _detect_tcr_anomalies(self):
        """Detect abnormal TCR recovery ratios."""
        if 'tcr_ratio' not in self.df.columns:
            return
        
        # Under-recovery (poor hole cleaning)
        under_recovery = self.df[
            self.df['tcr_ratio'] < self.config.TCR_RATIO_LOW_WARNING
        ]
        if len(under_recovery) > 0:
            self.anomalies.append({
                'type': 'Under-Recovery',
                'severity': 'Warning' if under_recovery['tcr_ratio'].min() >= self.config.TCR_RATIO_LOW_ALARM else 'Alarm',
                'count': len(under_recovery),
                'min_ratio': under_recovery['tcr_ratio'].min(),
                'description': 'TCR ratio below threshold - possible cuttings bed buildup',
                'time_start': under_recovery['time'].min(),
                'time_end': under_recovery['time'].max()
            })
        
        # Over-recovery (hole enlargement)
        over_recovery = self.df[
            self.df['tcr_ratio'] > self.config.TCR_RATIO_HIGH_WARNING
        ]
        if len(over_recovery) > 0:
            self.anomalies.append({
                'type': 'Over-Recovery',
                'severity': 'Warning' if over_recovery['tcr_ratio'].max() <= self.config.TCR_RATIO_HIGH_ALARM else 'Alarm',
                'count': len(over_recovery),
                'max_ratio': over_recovery['tcr_ratio'].max(),
                'description': 'TCR ratio above threshold - possible hole enlargement or calibration issue',
                'time_start': over_recovery['time'].min(),
                'time_end': over_recovery['time'].max()
            })
    
    def _detect_ufo_events(self):
        """Detect UFO (caving) events."""
        if 'ufo_count' not in self.df.columns:
            return
        
        ufo_events = self.df[self.df['ufo_count'] > 0]
        if len(ufo_events) > 0:
            total_ufos = ufo_events['ufo_count'].sum()
            
            # Calculate UFO rate per hour
            if 'time' in self.df.columns:
                duration_hours = (self.df['time'].max() - self.df['time'].min()).total_seconds() / 3600
                ufo_rate = total_ufos / duration_hours if duration_hours > 0 else 0
            else:
                ufo_rate = 0
            
            severity = 'Alarm' if ufo_rate > self.config.UFO_COUNT_WARNING else 'Info'
            
            self.anomalies.append({
                'type': 'UFO Events',
                'severity': severity,
                'count': int(total_ufos),
                'rate_per_hour': round(ufo_rate, 2),
                'description': f'{int(total_ufos)} caving events detected ({ufo_rate:.1f}/hr)',
                'time_start': ufo_events['time'].min() if 'time' in ufo_events.columns else None,
                'time_end': ufo_events['time'].max() if 'time' in ufo_events.columns else None
            })
    
    def _detect_csd_shifts(self):
        """Detect significant shifts in cutting size distribution."""
        if 'csd_p50' not in self.df.columns:
            return
        
        # Calculate baseline and detect shifts
        csd_data = self.df['csd_p50'].dropna()
        if len(csd_data) < 100:
            return
        
        baseline = csd_data.iloc[:50].mean()
        if baseline == 0:
            return
        
        # Find periods where CSD shifted significantly
        self.df['csd_pct_change'] = (
            (self.df['csd_p50'] - baseline) / baseline * 100
        )
        
        significant_shifts = self.df[
            abs(self.df['csd_pct_change']) > self.config.CSD_SHIFT_WARNING
        ]
        
        if len(significant_shifts) > 0:
            self.anomalies.append({
                'type': 'CSD Shift',
                'severity': 'Warning',
                'count': len(significant_shifts),
                'max_shift_pct': significant_shifts['csd_pct_change'].abs().max(),
                'description': 'Significant cutting size shift - possible formation change or transport issue',
                'baseline_mm': round(baseline, 1)
            })
    
    def _detect_sensor_artifacts(self):
        """Detect potential sensor/data quality issues."""
        artifacts = []
        
        # Check for sustained zero readings during drilling
        if 'crr_bbl' in self.df.columns and 'is_drilling' in self.df.columns:
            drilling_data = self.df[self.df['is_drilling']]
            zero_crr_drilling = drilling_data[drilling_data['crr_bbl'] == 0]
            
            if len(zero_crr_drilling) > 10:
                artifacts.append({
                    'type': 'Zero CRR During Drilling',
                    'count': len(zero_crr_drilling),
                    'description': 'CRR reading zero while drilling - possible sensor issue'
                })
        
        # Check for unrealistic values
        if 'crr_bbl' in self.df.columns:
            extreme_crr = self.df[self.df['crr_bbl'] > 5]  # > 5 bbl/min is extreme
            if len(extreme_crr) > 0:
                artifacts.append({
                    'type': 'Extreme CRR Values',
                    'count': len(extreme_crr),
                    'max_value': extreme_crr['crr_bbl'].max(),
                    'description': 'CRR values exceeding reasonable limits'
                })
        
        if artifacts:
            for artifact in artifacts:
                artifact['severity'] = 'Info'
                self.anomalies.append(artifact)
    
    def get_summary(self) -> pd.DataFrame:
        """Return anomalies as DataFrame."""
        if not self.anomalies:
            return pd.DataFrame()
        return pd.DataFrame(self.anomalies)


# =============================================================================
# STATISTICS AND ANALYSIS
# =============================================================================

class StatisticsCalculator:
    """Calculate summary statistics for the dataset."""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.stats = {}
    
    def calculate_all(self) -> Dict[str, Any]:
        """Calculate all statistics."""
        self.stats = {
            'overview': self._calculate_overview(),
            'drilling': self._calculate_drilling_stats(),
            'hole_cleaning': self._calculate_hole_cleaning_stats(),
            'correlations': self._calculate_correlations()
        }
        return self.stats
    
    def _calculate_overview(self) -> Dict[str, Any]:
        """Calculate overview statistics."""
        stats = {
            'total_rows': len(self.df),
            'columns': list(self.df.columns)
        }
        
        if 'time' in self.df.columns:
            stats['time_start'] = self.df['time'].min()
            stats['time_end'] = self.df['time'].max()
            stats['duration'] = self.df['time'].max() - self.df['time'].min()
            
            # Calculate time interval
            time_diffs = self.df['time'].diff().dropna()
            if len(time_diffs) > 0:
                stats['time_interval'] = time_diffs.mode().iloc[0]
        
        if 'hole_depth' in self.df.columns:
            stats['depth_start'] = self.df['hole_depth'].min()
            stats['depth_end'] = self.df['hole_depth'].max()
            stats['total_drilled'] = stats['depth_end'] - stats['depth_start']
        
        if 'bit_depth' in self.df.columns:
            stats['bit_depth_min'] = self.df['bit_depth'].min()
            stats['bit_depth_max'] = self.df['bit_depth'].max()
        
        return stats
    
    def _calculate_drilling_stats(self) -> Dict[str, Any]:
        """Calculate drilling-specific statistics."""
        stats = {}
        
        if 'is_drilling' in self.df.columns:
            drilling_df = self.df[self.df['is_drilling']]
            non_drilling_df = self.df[~self.df['is_drilling']]
            
            stats['drilling_points'] = len(drilling_df)
            stats['non_drilling_points'] = len(non_drilling_df)
            stats['drilling_pct'] = len(drilling_df) / len(self.df) * 100 if len(self.df) > 0 else 0
            
            if 'rop' in drilling_df.columns:
                stats['rop_mean'] = drilling_df['rop'].mean()
                stats['rop_max'] = drilling_df['rop'].max()
            
            if 'rpm' in drilling_df.columns:
                stats['rpm_mean'] = drilling_df['rpm'].mean()
            
            if 'flow_in' in drilling_df.columns:
                stats['flow_mean'] = drilling_df['flow_in'].mean()
        
        return stats
    
    def _calculate_hole_cleaning_stats(self) -> Dict[str, Any]:
        """Calculate hole cleaning statistics."""
        stats = {}
        
        # CRR statistics
        if 'crr_bbl' in self.df.columns:
            crr_data = self.df['crr_bbl'].dropna()
            stats['crr_mean'] = crr_data.mean()
            stats['crr_max'] = crr_data.max()
            stats['crr_std'] = crr_data.std()
            
            # During drilling only
            if 'is_drilling' in self.df.columns:
                drilling_crr = self.df.loc[self.df['is_drilling'], 'crr_bbl'].dropna()
                if len(drilling_crr) > 0:
                    stats['crr_drilling_mean'] = drilling_crr.mean()
        
        # TCR ratio statistics
        if 'tcr_ratio' in self.df.columns:
            tcr_data = self.df['tcr_ratio'].dropna()
            if len(tcr_data) > 0:
                stats['tcr_ratio_mean'] = tcr_data.mean()
                stats['tcr_ratio_min'] = tcr_data.min()
                stats['tcr_ratio_max'] = tcr_data.max()
                stats['tcr_ratio_final'] = tcr_data.iloc[-1]
        
        # CSD statistics
        if 'csd_p50' in self.df.columns:
            csd_data = self.df['csd_p50'].dropna()
            csd_data = csd_data[csd_data > 0]
            if len(csd_data) > 0:
                stats['csd_mean'] = csd_data.mean()
                stats['csd_min'] = csd_data.min()
                stats['csd_max'] = csd_data.max()
        
        # UFO statistics
        if 'ufo_count' in self.df.columns:
            stats['ufo_total'] = self.df['ufo_count'].sum()
            stats['ufo_events'] = (self.df['ufo_count'] > 0).sum()
        
        return stats
    
    def _calculate_correlations(self) -> Dict[str, float]:
        """Calculate key correlations."""
        correlations = {}
        
        # Only calculate during drilling
        if 'is_drilling' in self.df.columns:
            drilling_df = self.df[self.df['is_drilling']]
        else:
            drilling_df = self.df
        
        pairs = [
            ('crr_bbl', 'rop', 'CRR vs ROP'),
            ('crr_bbl', 'flow_in', 'CRR vs Flow'),
            ('crr_bbl', 'rpm', 'CRR vs RPM'),
            ('crr_bbl', 'csd_p50', 'CRR vs CSD')
        ]
        
        for col1, col2, name in pairs:
            if col1 in drilling_df.columns and col2 in drilling_df.columns:
                valid_data = drilling_df[[col1, col2]].dropna()
                if len(valid_data) > 10:
                    corr = valid_data[col1].corr(valid_data[col2])
                    correlations[name] = round(corr, 3)
        
        return correlations
    
    def print_summary(self):
        """Print formatted summary."""
        if not self.stats:
            self.calculate_all()
        
        print("\n" + "=" * 60)
        print("CLEANSIGHT DATA ANALYSIS SUMMARY")
        print("=" * 60)
        
        # Overview
        ov = self.stats['overview']
        print(f"\n{'DATASET OVERVIEW':=^60}")
        print(f"  Total data points: {ov['total_rows']:,}")
        if 'time_start' in ov:
            print(f"  Time range: {ov['time_start']} to {ov['time_end']}")
            print(f"  Duration: {ov['duration']}")
        if 'depth_start' in ov:
            print(f"  Depth range: {ov['depth_start']:.0f}m to {ov['depth_end']:.0f}m")
            print(f"  Total drilled: {ov['total_drilled']:.0f}m")
        
        # Drilling stats
        dr = self.stats['drilling']
        if dr:
            print(f"\n{'DRILLING STATISTICS':=^60}")
            print(f"  Drilling time: {dr.get('drilling_pct', 0):.1f}%")
            if 'rop_mean' in dr:
                print(f"  Average ROP: {dr['rop_mean']:.1f} ft/h (max: {dr['rop_max']:.1f})")
            if 'rpm_mean' in dr:
                print(f"  Average RPM: {dr['rpm_mean']:.0f}")
            if 'flow_mean' in dr:
                print(f"  Average Flow: {dr['flow_mean']:.0f} gpm")
        
        # Hole cleaning stats
        hc = self.stats['hole_cleaning']
        if hc:
            print(f"\n{'HOLE CLEANING METRICS':=^60}")
            if 'crr_drilling_mean' in hc:
                print(f"  Average CRR (drilling): {hc['crr_drilling_mean']:.4f} bbl/min")
            if 'tcr_ratio_mean' in hc:
                print(f"  TCR Ratio - Mean: {hc['tcr_ratio_mean']:.2f}, Final: {hc.get('tcr_ratio_final', 'N/A')}")
                print(f"  TCR Ratio - Range: {hc['tcr_ratio_min']:.2f} to {hc['tcr_ratio_max']:.2f}")
            if 'csd_mean' in hc:
                print(f"  CSD P50 - Mean: {hc['csd_mean']:.1f}mm (range: {hc['csd_min']:.1f} - {hc['csd_max']:.1f})")
            if 'ufo_total' in hc:
                print(f"  UFO Events: {hc['ufo_events']} events, {int(hc['ufo_total'])} total count")
        
        # Correlations
        corr = self.stats['correlations']
        if corr:
            print(f"\n{'CORRELATIONS (DRILLING ONLY)':=^60}")
            for name, value in corr.items():
                strength = 'Strong' if abs(value) > 0.6 else 'Moderate' if abs(value) > 0.4 else 'Weak'
                print(f"  {name}: {value:.3f} ({strength})")
        
        print("\n" + "=" * 60)


# =============================================================================
# VISUALIZATION
# =============================================================================

class Plotter:
    """Generate diagnostic plots."""
    
    def __init__(self, df: pd.DataFrame, config: Config = None, output_dir: str = None):
        self.df = df
        self.config = config or Config()
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / 'plots'
        self.output_dir.mkdir(exist_ok=True)
        
        # Import plotting libraries
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        self.plt = plt
        self.mdates = mdates
        
        # Set style
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
    
    def plot_all(self, show: bool = True, save: bool = True):
        """Generate all diagnostic plots."""
        print(f"\nGenerating plots...")
        
        plots_created = []
        
        # 1. TCR Comparison (most important)
        if 'measured_tcr' in self.df.columns and 'theoretical_tcr' in self.df.columns:
            self._plot_tcr_comparison(show, save)
            plots_created.append('tcr_comparison')
        
        # 2. TCR Ratio Trend
        if 'tcr_ratio' in self.df.columns:
            self._plot_tcr_ratio(show, save)
            plots_created.append('tcr_ratio')
        
        # 3. CRR Time Series
        if 'crr_bbl' in self.df.columns:
            self._plot_crr_timeseries(show, save)
            plots_created.append('crr_timeseries')
        
        # 4. CRR + ROP + Flow
        self._plot_drilling_params(show, save)
        plots_created.append('drilling_params')
        
        # 5. CSD P50 Trend
        if 'csd_p50' in self.df.columns:
            self._plot_csd_trend(show, save)
            plots_created.append('csd_trend')
        
        # 6. Cross-plots
        self._plot_crossplots(show, save)
        plots_created.append('crossplots')
        
        # 7. UFO Timeline
        if 'ufo_count' in self.df.columns:
            self._plot_ufo_timeline(show, save)
            plots_created.append('ufo_timeline')
        
        # 8. Depth-based plots
        self._plot_depth_analysis(show, save)
        plots_created.append('depth_analysis')
        
        # 9. Operational state analysis
        if 'is_drilling' in self.df.columns:
            self._plot_state_comparison(show, save)
            plots_created.append('state_comparison')
        
        print(f"  Created {len(plots_created)} plot sets")
        if save:
            print(f"  Saved to: {self.output_dir}")
        
        return plots_created
    
    def _plot_tcr_comparison(self, show: bool, save: bool):
        """Plot Measured vs Theoretical TCR."""
        fig, ax = self.plt.subplots(figsize=self.config.FIGURE_SIZE_LARGE)
        
        x = self.df['time'] if 'time' in self.df.columns else range(len(self.df))
        
        ax.fill_between(x, self.df['measured_tcr'], alpha=0.3, color=self.config.COLORS['primary'], label='Measured TCR')
        ax.plot(x, self.df['measured_tcr'], color=self.config.COLORS['primary'], linewidth=1)
        
        ax.fill_between(x, self.df['theoretical_tcr'], alpha=0.3, color=self.config.COLORS['secondary'], label='Theoretical TCR')
        ax.plot(x, self.df['theoretical_tcr'], color=self.config.COLORS['secondary'], linewidth=1)
        
        ax.set_xlabel('Time')
        ax.set_ylabel('TCR (bbl)')
        ax.set_title('Cuttings Recovery: Measured vs Theoretical TCR', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        if 'time' in self.df.columns:
            ax.xaxis.set_major_formatter(self.mdates.DateFormatter('%m/%d %H:%M'))
            fig.autofmt_xdate()
        
        self.plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / 'tcr_comparison.png', dpi=self.config.FIGURE_DPI, 
                       facecolor=fig.get_facecolor(), edgecolor='none')
        if show:
            self.plt.show()
        self.plt.close(fig)
    
    def _plot_tcr_ratio(self, show: bool, save: bool):
        """Plot TCR ratio trend with thresholds."""
        fig, ax = self.plt.subplots(figsize=self.config.FIGURE_SIZE_MEDIUM)
        
        x = self.df['time'] if 'time' in self.df.columns else range(len(self.df))
        
        ax.fill_between(x, self.df['tcr_ratio'], alpha=0.3, color=self.config.COLORS['success'])
        ax.plot(x, self.df['tcr_ratio'], color=self.config.COLORS['success'], linewidth=1)
        
        # Add threshold lines
        ax.axhline(y=1.0, color='white', linestyle='--', alpha=0.5, label='Ideal (1.0)')
        ax.axhline(y=self.config.TCR_RATIO_LOW_WARNING, color=self.config.COLORS['warning'], 
                   linestyle='--', alpha=0.7, label=f'Low Warning ({self.config.TCR_RATIO_LOW_WARNING})')
        ax.axhline(y=self.config.TCR_RATIO_HIGH_WARNING, color=self.config.COLORS['warning'], 
                   linestyle='--', alpha=0.7, label=f'High Warning ({self.config.TCR_RATIO_HIGH_WARNING})')
        
        ax.set_xlabel('Time')
        ax.set_ylabel('TCR Ratio (Measured/Theoretical)')
        ax.set_title('TCR Recovery Ratio Trend', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 2)
        
        if 'time' in self.df.columns:
            ax.xaxis.set_major_formatter(self.mdates.DateFormatter('%m/%d %H:%M'))
            fig.autofmt_xdate()
        
        self.plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / 'tcr_ratio.png', dpi=self.config.FIGURE_DPI,
                       facecolor=fig.get_facecolor(), edgecolor='none')
        if show:
            self.plt.show()
        self.plt.close(fig)
    
    def _plot_crr_timeseries(self, show: bool, save: bool):
        """Plot CRR time series with rolling average."""
        fig, ax = self.plt.subplots(figsize=self.config.FIGURE_SIZE_LARGE)
        
        x = self.df['time'] if 'time' in self.df.columns else range(len(self.df))
        
        ax.fill_between(x, self.df['crr_bbl'], alpha=0.3, color=self.config.COLORS['primary'])
        ax.plot(x, self.df['crr_bbl'], color=self.config.COLORS['primary'], linewidth=0.5, alpha=0.7, label='CRR')
        
        if 'crr_rolling_mean' in self.df.columns:
            ax.plot(x, self.df['crr_rolling_mean'], color=self.config.COLORS['secondary'], 
                   linewidth=2, label='Rolling Mean (30-min)')
        
        ax.set_xlabel('Time')
        ax.set_ylabel('CRR (bbl/min)')
        ax.set_title('Cuttings Recovery Rate Over Time', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        if 'time' in self.df.columns:
            ax.xaxis.set_major_formatter(self.mdates.DateFormatter('%m/%d %H:%M'))
            fig.autofmt_xdate()
        
        self.plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / 'crr_timeseries.png', dpi=self.config.FIGURE_DPI,
                       facecolor=fig.get_facecolor(), edgecolor='none')
        if show:
            self.plt.show()
        self.plt.close(fig)
    
    def _plot_drilling_params(self, show: bool, save: bool):
        """Plot CRR with ROP and Flow on multiple axes."""
        fig, axes = self.plt.subplots(3, 1, figsize=(14, 10), sharex=True)
        
        x = self.df['time'] if 'time' in self.df.columns else range(len(self.df))
        
        # CRR
        if 'crr_bbl' in self.df.columns:
            axes[0].fill_between(x, self.df['crr_bbl'], alpha=0.3, color=self.config.COLORS['primary'])
            axes[0].plot(x, self.df['crr_bbl'], color=self.config.COLORS['primary'], linewidth=0.5)
            axes[0].set_ylabel('CRR (bbl/min)')
            axes[0].set_title('Cuttings Recovery Rate', fontsize=12)
            axes[0].grid(True, alpha=0.3)
        
        # ROP and RPM
        if 'rop' in self.df.columns:
            ax1 = axes[1]
            ax1.fill_between(x, self.df['rop'], alpha=0.3, color=self.config.COLORS['secondary'])
            ax1.plot(x, self.df['rop'], color=self.config.COLORS['secondary'], linewidth=0.5, label='ROP')
            ax1.set_ylabel('ROP (ft/h)', color=self.config.COLORS['secondary'])
            
            if 'rpm' in self.df.columns:
                ax2 = ax1.twinx()
                ax2.plot(x, self.df['rpm'], color=self.config.COLORS['warning'], linewidth=0.5, label='RPM')
                ax2.set_ylabel('RPM', color=self.config.COLORS['warning'])
            
            ax1.set_title('Drilling Parameters: ROP & RPM', fontsize=12)
            ax1.grid(True, alpha=0.3)
        
        # Flow and Pressure
        if 'flow_in' in self.df.columns:
            ax3 = axes[2]
            ax3.fill_between(x, self.df['flow_in'], alpha=0.3, color=self.config.COLORS['success'])
            ax3.plot(x, self.df['flow_in'], color=self.config.COLORS['success'], linewidth=0.5, label='Flow In')
            ax3.set_ylabel('Flow (gpm)', color=self.config.COLORS['success'])
            
            if 'pump_pressure' in self.df.columns:
                ax4 = ax3.twinx()
                ax4.plot(x, self.df['pump_pressure'], color=self.config.COLORS['danger'], linewidth=0.5, label='Pressure')
                ax4.set_ylabel('Pressure (psi)', color=self.config.COLORS['danger'])
            
            ax3.set_title('Hydraulics: Flow & Pressure', fontsize=12)
            ax3.grid(True, alpha=0.3)
            ax3.set_xlabel('Time')
        
        if 'time' in self.df.columns:
            axes[-1].xaxis.set_major_formatter(self.mdates.DateFormatter('%m/%d %H:%M'))
            fig.autofmt_xdate()
        
        self.plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / 'drilling_params.png', dpi=self.config.FIGURE_DPI,
                       facecolor=fig.get_facecolor(), edgecolor='none')
        if show:
            self.plt.show()
        self.plt.close(fig)
    
    def _plot_csd_trend(self, show: bool, save: bool):
        """Plot cutting size distribution trend."""
        fig, ax = self.plt.subplots(figsize=self.config.FIGURE_SIZE_MEDIUM)
        
        x = self.df['time'] if 'time' in self.df.columns else range(len(self.df))
        
        ax.fill_between(x, self.df['csd_p50'], alpha=0.3, color=self.config.COLORS['purple'])
        ax.plot(x, self.df['csd_p50'], color=self.config.COLORS['purple'], linewidth=0.5)
        
        if 'csd_rolling_mean' in self.df.columns:
            ax.plot(x, self.df['csd_rolling_mean'], color='white', linewidth=2, 
                   label='Rolling Mean', alpha=0.8)
        
        ax.set_xlabel('Time')
        ax.set_ylabel('CSD P50 (mm)')
        ax.set_title('Cutting Size Distribution (P50) Trend', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        if 'time' in self.df.columns:
            ax.xaxis.set_major_formatter(self.mdates.DateFormatter('%m/%d %H:%M'))
            fig.autofmt_xdate()
        
        self.plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / 'csd_trend.png', dpi=self.config.FIGURE_DPI,
                       facecolor=fig.get_facecolor(), edgecolor='none')
        if show:
            self.plt.show()
        self.plt.close(fig)
    
    def _plot_crossplots(self, show: bool, save: bool):
        """Generate cross-plots for correlation analysis."""
        # Filter to drilling only
        if 'is_drilling' in self.df.columns:
            plot_df = self.df[self.df['is_drilling']].copy()
        else:
            plot_df = self.df.copy()
        
        fig, axes = self.plt.subplots(2, 2, figsize=(12, 10))
        
        crossplot_configs = [
            ('rop', 'crr_bbl', 'ROP (ft/h)', 'CRR (bbl/min)', axes[0, 0], self.config.COLORS['primary']),
            ('flow_in', 'crr_bbl', 'Flow In (gpm)', 'CRR (bbl/min)', axes[0, 1], self.config.COLORS['success']),
            ('rpm', 'crr_bbl', 'RPM', 'CRR (bbl/min)', axes[1, 0], self.config.COLORS['warning']),
            ('csd_p50', 'crr_bbl', 'CSD P50 (mm)', 'CRR (bbl/min)', axes[1, 1], self.config.COLORS['purple']),
        ]
        
        for x_col, y_col, x_label, y_label, ax, color in crossplot_configs:
            if x_col in plot_df.columns and y_col in plot_df.columns:
                valid = plot_df[[x_col, y_col]].dropna()
                valid = valid[(valid[x_col] > 0) & (valid[y_col] > 0)]
                
                if len(valid) > 0:
                    ax.scatter(valid[x_col], valid[y_col], alpha=0.3, s=10, c=color)
                    
                    # Add correlation coefficient
                    corr = valid[x_col].corr(valid[y_col])
                    ax.text(0.05, 0.95, f'r = {corr:.3f}', transform=ax.transAxes,
                           fontsize=12, verticalalignment='top',
                           bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
                    
                    # Add trendline
                    z = np.polyfit(valid[x_col], valid[y_col], 1)
                    p = np.poly1d(z)
                    x_line = np.linspace(valid[x_col].min(), valid[x_col].max(), 100)
                    ax.plot(x_line, p(x_line), color='white', linestyle='--', alpha=0.7)
                
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
                ax.grid(True, alpha=0.3)
        
        fig.suptitle('Cross-Plots (Drilling Only)', fontsize=14, fontweight='bold')
        self.plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / 'crossplots.png', dpi=self.config.FIGURE_DPI,
                       facecolor=fig.get_facecolor(), edgecolor='none')
        if show:
            self.plt.show()
        self.plt.close(fig)
    
    def _plot_ufo_timeline(self, show: bool, save: bool):
        """Plot UFO events timeline."""
        ufo_df = self.df[self.df['ufo_count'] > 0].copy()
        
        if len(ufo_df) == 0:
            print("  No UFO events to plot")
            return
        
        fig, ax = self.plt.subplots(figsize=self.config.FIGURE_SIZE_MEDIUM)
        
        x = ufo_df['time'] if 'time' in ufo_df.columns else range(len(ufo_df))
        
        scatter = ax.scatter(x, ufo_df['ufo_count'], c=ufo_df['bit_depth'] if 'bit_depth' in ufo_df.columns else 'red',
                            s=ufo_df['ufo_count'] * 50, alpha=0.7, cmap='plasma')
        
        if 'bit_depth' in ufo_df.columns:
            cbar = self.plt.colorbar(scatter, ax=ax)
            cbar.set_label('Bit Depth (m)')
        
        ax.set_xlabel('Time')
        ax.set_ylabel('UFO Count')
        ax.set_title(f'UFO (Caving) Events Timeline ({len(ufo_df)} events)', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        if 'time' in ufo_df.columns:
            ax.xaxis.set_major_formatter(self.mdates.DateFormatter('%m/%d %H:%M'))
            fig.autofmt_xdate()
        
        self.plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / 'ufo_timeline.png', dpi=self.config.FIGURE_DPI,
                       facecolor=fig.get_facecolor(), edgecolor='none')
        if show:
            self.plt.show()
        self.plt.close(fig)
    
    def _plot_depth_analysis(self, show: bool, save: bool):
        """Generate depth-based analysis plots."""
        if 'bit_depth' not in self.df.columns:
            return
        
        fig, axes = self.plt.subplots(1, 3, figsize=(15, 8))
        
        # CRR vs Depth
        if 'crr_bbl' in self.df.columns:
            axes[0].scatter(self.df['crr_bbl'], self.df['bit_depth'], 
                           alpha=0.3, s=5, c=self.config.COLORS['primary'])
            axes[0].set_xlabel('CRR (bbl/min)')
            axes[0].set_ylabel('Bit Depth (m)')
            axes[0].set_title('CRR vs Depth')
            axes[0].invert_yaxis()
            axes[0].grid(True, alpha=0.3)
        
        # CSD vs Depth
        if 'csd_p50' in self.df.columns:
            valid = self.df[self.df['csd_p50'] > 0]
            axes[1].scatter(valid['csd_p50'], valid['bit_depth'], 
                           alpha=0.3, s=5, c=self.config.COLORS['purple'])
            axes[1].set_xlabel('CSD P50 (mm)')
            axes[1].set_ylabel('Bit Depth (m)')
            axes[1].set_title('Cutting Size vs Depth')
            axes[1].invert_yaxis()
            axes[1].grid(True, alpha=0.3)
        
        # TCR Ratio vs Depth
        if 'tcr_ratio' in self.df.columns:
            valid = self.df[self.df['tcr_ratio'].notna()]
            scatter = axes[2].scatter(valid['tcr_ratio'], valid['bit_depth'], 
                                      alpha=0.3, s=5, c=valid['tcr_ratio'],
                                      cmap='RdYlGn', vmin=0.5, vmax=1.5)
            axes[2].axvline(x=1.0, color='white', linestyle='--', alpha=0.5)
            axes[2].set_xlabel('TCR Ratio')
            axes[2].set_ylabel('Bit Depth (m)')
            axes[2].set_title('Recovery Ratio vs Depth')
            axes[2].invert_yaxis()
            axes[2].grid(True, alpha=0.3)
            self.plt.colorbar(scatter, ax=axes[2], label='TCR Ratio')
        
        fig.suptitle('Depth-Based Analysis', fontsize=14, fontweight='bold')
        self.plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / 'depth_analysis.png', dpi=self.config.FIGURE_DPI,
                       facecolor=fig.get_facecolor(), edgecolor='none')
        if show:
            self.plt.show()
        self.plt.close(fig)
    
    def _plot_state_comparison(self, show: bool, save: bool):
        """Compare metrics between drilling and non-drilling states."""
        fig, axes = self.plt.subplots(1, 2, figsize=(12, 5))
        
        drilling = self.df[self.df['is_drilling']]
        non_drilling = self.df[~self.df['is_drilling']]
        
        # CRR boxplot comparison
        if 'crr_bbl' in self.df.columns:
            data = [drilling['crr_bbl'].dropna(), non_drilling['crr_bbl'].dropna()]
            bp = axes[0].boxplot(data, labels=['Drilling', 'Non-Drilling'], patch_artist=True)
            bp['boxes'][0].set_facecolor(self.config.COLORS['primary'])
            bp['boxes'][1].set_facecolor(self.config.COLORS['secondary'])
            for box in bp['boxes']:
                box.set_alpha(0.7)
            axes[0].set_ylabel('CRR (bbl/min)')
            axes[0].set_title('CRR Distribution by State')
            axes[0].grid(True, alpha=0.3)
        
        # CSD boxplot comparison
        if 'csd_p50' in self.df.columns:
            data = [drilling['csd_p50'].dropna(), non_drilling['csd_p50'].dropna()]
            data = [d[d > 0] for d in data]
            bp = axes[1].boxplot(data, labels=['Drilling', 'Non-Drilling'], patch_artist=True)
            bp['boxes'][0].set_facecolor(self.config.COLORS['purple'])
            bp['boxes'][1].set_facecolor(self.config.COLORS['gray'])
            for box in bp['boxes']:
                box.set_alpha(0.7)
            axes[1].set_ylabel('CSD P50 (mm)')
            axes[1].set_title('Cutting Size by State')
            axes[1].grid(True, alpha=0.3)
        
        fig.suptitle('Operational State Comparison', fontsize=14, fontweight='bold')
        self.plt.tight_layout()
        
        if save:
            fig.savefig(self.output_dir / 'state_comparison.png', dpi=self.config.FIGURE_DPI,
                       facecolor=fig.get_facecolor(), edgecolor='none')
        if show:
            self.plt.show()
        self.plt.close(fig)


# =============================================================================
# INTERACTIVE DASHBOARD (OPTIONAL - REQUIRES PLOTLY)
# =============================================================================

class InteractiveDashboard:
    """Generate interactive HTML dashboard using Plotly."""
    
    def __init__(self, df: pd.DataFrame, config: Config = None):
        self.df = df
        self.config = config or Config()
        
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import plotly.express as px
            self.go = go
            self.make_subplots = make_subplots
            self.px = px
            self.available = True
        except ImportError:
            print("  Plotly not installed. Install with: pip install plotly")
            self.available = False
    
    def create_dashboard(self, output_path: str = 'cleansight_dashboard.html'):
        """Create interactive HTML dashboard."""
        if not self.available:
            print("  Cannot create interactive dashboard - plotly not installed")
            return None
        
        print(f"\nCreating interactive dashboard...")
        
        # Create figure with subplots
        fig = self.make_subplots(
            rows=4, cols=2,
            subplot_titles=(
                'Measured vs Theoretical TCR', 'TCR Recovery Ratio',
                'CRR + ROP Over Time', 'CSD P50 Trend',
                'CRR vs Flow (Cross-plot)', 'CRR vs ROP (Cross-plot)',
                'Depth Progression', 'UFO Events'
            ),
            vertical_spacing=0.08,
            horizontal_spacing=0.08
        )
        
        x = self.df['time'] if 'time' in self.df.columns else list(range(len(self.df)))
        
        # 1. TCR Comparison
        if 'measured_tcr' in self.df.columns:
            fig.add_trace(
                self.go.Scatter(x=x, y=self.df['measured_tcr'], name='Measured TCR',
                               line=dict(color='#ff6b35'), fill='tozeroy'),
                row=1, col=1
            )
        if 'theoretical_tcr' in self.df.columns:
            fig.add_trace(
                self.go.Scatter(x=x, y=self.df['theoretical_tcr'], name='Theoretical TCR',
                               line=dict(color='#00d9ff'), fill='tozeroy'),
                row=1, col=1
            )
        
        # 2. TCR Ratio
        if 'tcr_ratio' in self.df.columns:
            fig.add_trace(
                self.go.Scatter(x=x, y=self.df['tcr_ratio'], name='TCR Ratio',
                               line=dict(color='#3fb950'), fill='tozeroy'),
                row=1, col=2
            )
            fig.add_hline(y=1.0, line_dash="dash", line_color="white", row=1, col=2)
        
        # 3. CRR + ROP
        if 'crr_bbl' in self.df.columns:
            fig.add_trace(
                self.go.Scatter(x=x, y=self.df['crr_bbl'], name='CRR',
                               line=dict(color='#ff6b35')),
                row=2, col=1
            )
        if 'rop' in self.df.columns:
            fig.add_trace(
                self.go.Scatter(x=x, y=self.df['rop'], name='ROP', yaxis='y3',
                               line=dict(color='#00d9ff')),
                row=2, col=1
            )
        
        # 4. CSD
        if 'csd_p50' in self.df.columns:
            fig.add_trace(
                self.go.Scatter(x=x, y=self.df['csd_p50'], name='CSD P50',
                               line=dict(color='#a371f7'), fill='tozeroy'),
                row=2, col=2
            )
        
        # 5. Cross-plot: CRR vs Flow
        if 'crr_bbl' in self.df.columns and 'flow_in' in self.df.columns:
            drilling = self.df[self.df['is_drilling']] if 'is_drilling' in self.df.columns else self.df
            fig.add_trace(
                self.go.Scatter(x=drilling['flow_in'], y=drilling['crr_bbl'], 
                               mode='markers', name='CRR vs Flow',
                               marker=dict(color='#3fb950', size=4, opacity=0.5)),
                row=3, col=1
            )
        
        # 6. Cross-plot: CRR vs ROP
        if 'crr_bbl' in self.df.columns and 'rop' in self.df.columns:
            drilling = self.df[self.df['is_drilling']] if 'is_drilling' in self.df.columns else self.df
            fig.add_trace(
                self.go.Scatter(x=drilling['rop'], y=drilling['crr_bbl'], 
                               mode='markers', name='CRR vs ROP',
                               marker=dict(color='#ff6b35', size=4, opacity=0.5)),
                row=3, col=2
            )
        
        # 7. Depth
        if 'bit_depth' in self.df.columns:
            fig.add_trace(
                self.go.Scatter(x=x, y=self.df['bit_depth'], name='Bit Depth',
                               line=dict(color='#00d9ff')),
                row=4, col=1
            )
            fig.update_yaxes(autorange="reversed", row=4, col=1)
        
        # 8. UFO Events
        if 'ufo_count' in self.df.columns:
            ufo_df = self.df[self.df['ufo_count'] > 0]
            if len(ufo_df) > 0:
                fig.add_trace(
                    self.go.Scatter(
                        x=ufo_df['time'] if 'time' in ufo_df.columns else list(range(len(ufo_df))),
                        y=ufo_df['ufo_count'], 
                        mode='markers', name='UFO Events',
                        marker=dict(color='#f85149', size=10)
                    ),
                    row=4, col=2
                )
        
        # Update layout
        fig.update_layout(
            height=1200,
            title_text="CleanSight Hole Cleaning Analysis Dashboard",
            title_font_size=20,
            template='plotly_dark',
            paper_bgcolor='#0a0e14',
            plot_bgcolor='#151d28',
            showlegend=False
        )
        
        # Save
        fig.write_html(output_path)
        print(f"  Dashboard saved to: {output_path}")
        
        return output_path


# =============================================================================
# REPORT GENERATOR
# =============================================================================

class ReportGenerator:
    """Generate analysis reports."""
    
    def __init__(self, df: pd.DataFrame, stats: Dict, anomalies: List[Dict], config: Config = None):
        self.df = df
        self.stats = stats
        self.anomalies = anomalies
        self.config = config or Config()
    
    def generate_text_report(self, output_path: str = 'analysis_report.txt'):
        """Generate text-based report."""
        lines = []
        lines.append("=" * 70)
        lines.append("CLEANSIGHT HOLE CLEANING ANALYSIS REPORT")
        lines.append("=" * 70)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Overview
        ov = self.stats.get('overview', {})
        lines.append("DATASET OVERVIEW")
        lines.append("-" * 40)
        lines.append(f"Total data points: {ov.get('total_rows', 'N/A'):,}")
        if 'time_start' in ov:
            lines.append(f"Time range: {ov['time_start']} to {ov['time_end']}")
            lines.append(f"Duration: {ov['duration']}")
        if 'depth_start' in ov:
            lines.append(f"Depth range: {ov['depth_start']:.0f}m to {ov['depth_end']:.0f}m")
            lines.append(f"Total drilled: {ov['total_drilled']:.0f}m")
        lines.append("")
        
        # Hole cleaning
        hc = self.stats.get('hole_cleaning', {})
        lines.append("HOLE CLEANING ASSESSMENT")
        lines.append("-" * 40)
        if 'tcr_ratio_mean' in hc:
            ratio = hc['tcr_ratio_mean']
            if ratio > self.config.TCR_RATIO_HIGH_WARNING:
                status = "OVER-RECOVERY - Possible hole enlargement"
            elif ratio < self.config.TCR_RATIO_LOW_WARNING:
                status = "UNDER-RECOVERY - Possible cuttings accumulation"
            else:
                status = "NORMAL - Hole cleaning appears effective"
            lines.append(f"Status: {status}")
            lines.append(f"Average TCR Ratio: {ratio:.2f}")
            lines.append(f"TCR Ratio Range: {hc['tcr_ratio_min']:.2f} to {hc['tcr_ratio_max']:.2f}")
        if 'crr_drilling_mean' in hc:
            lines.append(f"Average CRR (drilling): {hc['crr_drilling_mean']:.4f} bbl/min")
        if 'csd_mean' in hc:
            lines.append(f"Average Cutting Size: {hc['csd_mean']:.1f}mm")
        if 'ufo_total' in hc:
            lines.append(f"UFO Events: {hc['ufo_events']} ({int(hc['ufo_total'])} total)")
        lines.append("")
        
        # Anomalies
        if self.anomalies:
            lines.append("DETECTED ANOMALIES")
            lines.append("-" * 40)
            for anom in self.anomalies:
                lines.append(f"[{anom.get('severity', 'Info')}] {anom.get('type', 'Unknown')}")
                lines.append(f"  {anom.get('description', '')}")
            lines.append("")
        
        # Correlations
        corr = self.stats.get('correlations', {})
        if corr:
            lines.append("CORRELATIONS (DRILLING ONLY)")
            lines.append("-" * 40)
            for name, value in corr.items():
                lines.append(f"{name}: {value:.3f}")
            lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 40)
        hc = self.stats.get('hole_cleaning', {})
        if hc.get('tcr_ratio_mean', 1) > self.config.TCR_RATIO_HIGH_WARNING:
            lines.append("- Verify theoretical volume inputs (bit diameter, porosity)")
            lines.append("- Check for hole enlargement via caliper log")
            lines.append("- Review calibration of CleanSight sensors")
        elif hc.get('tcr_ratio_mean', 1) < self.config.TCR_RATIO_LOW_WARNING:
            lines.append("- Consider increasing flow rate")
            lines.append("- Evaluate sweep pill effectiveness")
            lines.append("- Monitor for pack-off risk during connections")
        else:
            lines.append("- Continue monitoring TCR ratio trends")
            lines.append("- Document current parameters as baseline for future comparison")
        
        if hc.get('ufo_total', 0) > 50:
            lines.append("- Review ECD management in UFO-prone intervals")
            lines.append("- Consider mud weight adjustment")
        
        lines.append("")
        lines.append("=" * 70)
        
        # Write file
        report = "\n".join(lines)
        with open(output_path, 'w') as f:
            f.write(report)
        
        print(f"Report saved to: {output_path}")
        return output_path
    
    def generate_csv_summary(self, output_path: str = 'analysis_summary.csv'):
        """Export key metrics to CSV."""
        summary_data = []
        
        # Overview metrics
        ov = self.stats.get('overview', {})
        summary_data.append({'Category': 'Overview', 'Metric': 'Total Rows', 'Value': ov.get('total_rows', '')})
        summary_data.append({'Category': 'Overview', 'Metric': 'Duration', 'Value': str(ov.get('duration', ''))})
        summary_data.append({'Category': 'Overview', 'Metric': 'Depth Start (m)', 'Value': ov.get('depth_start', '')})
        summary_data.append({'Category': 'Overview', 'Metric': 'Depth End (m)', 'Value': ov.get('depth_end', '')})
        
        # Drilling metrics
        dr = self.stats.get('drilling', {})
        summary_data.append({'Category': 'Drilling', 'Metric': 'Drilling %', 'Value': dr.get('drilling_pct', '')})
        summary_data.append({'Category': 'Drilling', 'Metric': 'Avg ROP (ft/h)', 'Value': dr.get('rop_mean', '')})
        summary_data.append({'Category': 'Drilling', 'Metric': 'Avg RPM', 'Value': dr.get('rpm_mean', '')})
        
        # Hole cleaning metrics
        hc = self.stats.get('hole_cleaning', {})
        summary_data.append({'Category': 'Hole Cleaning', 'Metric': 'Avg CRR (bbl/min)', 'Value': hc.get('crr_drilling_mean', '')})
        summary_data.append({'Category': 'Hole Cleaning', 'Metric': 'TCR Ratio Mean', 'Value': hc.get('tcr_ratio_mean', '')})
        summary_data.append({'Category': 'Hole Cleaning', 'Metric': 'TCR Ratio Final', 'Value': hc.get('tcr_ratio_final', '')})
        summary_data.append({'Category': 'Hole Cleaning', 'Metric': 'Avg CSD P50 (mm)', 'Value': hc.get('csd_mean', '')})
        summary_data.append({'Category': 'Hole Cleaning', 'Metric': 'UFO Events', 'Value': hc.get('ufo_events', '')})
        
        # Correlations
        for name, value in self.stats.get('correlations', {}).items():
            summary_data.append({'Category': 'Correlation', 'Metric': name, 'Value': value})
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_csv(output_path, index=False)
        
        print(f"Summary CSV saved to: {output_path}")
        return output_path


# =============================================================================
# MAIN ANALYZER CLASS
# =============================================================================

class CleanSightAnalyzer:
    """
    Main analyzer class that orchestrates the full analysis workflow.
    
    Usage:
        analyzer = CleanSightAnalyzer('path/to/data.csv')
        analyzer.run_analysis()
        analyzer.generate_plots()
        analyzer.generate_report()
    """
    
    def __init__(self, filepath: str, config: Config = None, output_dir: str = None):
        """
        Initialize analyzer with data file.
        
        Args:
            filepath: Path to CleanSight data export CSV
            config: Configuration object (uses defaults if None)
            output_dir: Directory for output files (creates 'output' in current dir if None)
        """
        self.filepath = filepath
        self.config = config or Config()
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / 'cleansight_output'
        self.output_dir.mkdir(exist_ok=True)
        
        self.df = None
        self.stats = None
        self.anomalies = None
        
        # Load data
        self._load_data()
    
    def _load_data(self):
        """Load and process data."""
        # Load raw data
        self.df = DataLoader.load(self.filepath)
        
        # Process and add derived metrics
        processor = DataProcessor(self.df, self.config)
        self.df = processor.get_data()
        
        print(f"  Processed {len(self.df):,} data points")
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run full analysis and return results."""
        print("\nRunning analysis...")
        
        # Calculate statistics
        stats_calc = StatisticsCalculator(self.df)
        self.stats = stats_calc.calculate_all()
        stats_calc.print_summary()
        
        # Detect anomalies
        detector = AnomalyDetector(self.df, self.config)
        self.anomalies = detector.detect_all()
        
        if self.anomalies:
            print(f"\n  Detected {len(self.anomalies)} anomaly types")
            for anom in self.anomalies:
                print(f"    [{anom.get('severity', 'Info')}] {anom.get('type')}: {anom.get('description', '')[:60]}")
        
        return {'stats': self.stats, 'anomalies': self.anomalies}
    
    def generate_plots(self, show: bool = False, save: bool = True) -> List[str]:
        """Generate all diagnostic plots."""
        plotter = Plotter(self.df, self.config, output_dir=str(self.output_dir / 'plots'))
        return plotter.plot_all(show=show, save=save)
    
    def generate_dashboard(self) -> Optional[str]:
        """Generate interactive HTML dashboard."""
        dashboard = InteractiveDashboard(self.df, self.config)
        output_path = str(self.output_dir / 'dashboard.html')
        return dashboard.create_dashboard(output_path)
    
    def generate_report(self) -> str:
        """Generate analysis report."""
        if self.stats is None:
            self.run_analysis()
        
        report_gen = ReportGenerator(self.df, self.stats, self.anomalies, self.config)
        
        # Text report
        report_path = report_gen.generate_text_report(
            str(self.output_dir / 'analysis_report.txt')
        )
        
        # CSV summary
        report_gen.generate_csv_summary(
            str(self.output_dir / 'analysis_summary.csv')
        )
        
        return report_path
    
    def export_processed_data(self, filename: str = 'processed_data.csv') -> str:
        """Export processed data with derived metrics."""
        output_path = str(self.output_dir / filename)
        self.df.to_csv(output_path, index=False)
        print(f"Processed data exported to: {output_path}")
        return output_path
    
    def get_data(self) -> pd.DataFrame:
        """Return the processed DataFrame for custom analysis."""
        return self.df.copy()


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """Command-line entry point."""
    if len(sys.argv) < 2:
        print("CleanSight Data Analysis Tool")
        print("-" * 40)
        print("Usage: python cleansight_analyzer.py <data_file.csv> [options]")
        print("")
        print("Options:")
        print("  --show-plots    Display plots interactively")
        print("  --no-plots      Skip plot generation")
        print("  --no-dashboard  Skip interactive dashboard")
        print("  --output-dir    Output directory (default: ./cleansight_output)")
        print("")
        print("Example:")
        print("  python cleansight_analyzer.py Data_Export.csv --show-plots")
        sys.exit(1)
    
    filepath = sys.argv[1]
    show_plots = '--show-plots' in sys.argv
    skip_plots = '--no-plots' in sys.argv
    skip_dashboard = '--no-dashboard' in sys.argv
    
    # Parse output dir
    output_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == '--output-dir' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
    
    print("\n" + "=" * 60)
    print("CLEANSIGHT DATA ANALYSIS TOOL")
    print("=" * 60)
    
    # Run analysis
    analyzer = CleanSightAnalyzer(filepath, output_dir=output_dir)
    analyzer.run_analysis()
    
    if not skip_plots:
        analyzer.generate_plots(show=show_plots)
    
    if not skip_dashboard:
        analyzer.generate_dashboard()
    
    analyzer.generate_report()
    analyzer.export_processed_data()
    
    print("\n" + "=" * 60)
    print(f"Analysis complete! Output saved to: {analyzer.output_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
