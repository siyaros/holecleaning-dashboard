# CleanSight Data Explorer v2.0

**Professional Local Engineering Analytics Platform**

A fully local, interactive data visualization dashboard designed for drilling data analysis and engineering workflows. No cloud dependencies - all data stays on your machine.

---

## 🚀 Features

### 1. Flexible Axis Control
- **Primary Y-Axis (Left)**: Main variables
- **Secondary Y-Axis (Right)**: Comparison variables with different scales
- **Unlimited Subplots**: Stack additional charts below
- **Flexible X-Axis**: Time, depth, index, or any column

### 2. Full Column Visibility
- **Scrollable list**: See ALL columns, no truncation
- **Search/filter**: Find columns quickly
- **Type badges**: NUM (numeric), DT (datetime), TXT (text)
- **Stats preview**: Min/max range for numeric columns

### 3. Configurable KPI Cards
- **Multiple calculations**: Last, First, Max, Min, Mean, Sum, Delta, Delta%
- **Auto-detection**: Recognizes TCR, UFO, and other drilling metrics
- **Zoom-responsive**: KPIs update based on visible data range
- **Custom formulas**: Apply post-processing calculations

### 4. Session Persistence
- **Auto-save**: Every 30 seconds
- **Dataset caching**: Files saved as Parquet for fast reload
- **Workspace save/load**: Save named configurations
- **Full state recovery**: Reopens exactly where you left off

### 5. Interactive Plotting
- **Zoom**: Click and drag
- **Pan**: Shift + drag
- **Reset**: Double-click
- **Hover**: See values
- **Toggle traces**: Click legend items
- **Export**: Save as PNG

---

## 📦 Installation

### Step 1: Install Python 3.8+
Download from [python.org](https://www.python.org/downloads/)

**Important**: Check "Add Python to PATH" during installation.

### Step 2: Extract Files
Unzip the package to any folder.

### Step 3: Run
**Windows**: Double-click `start_dashboard.bat`

**Mac/Linux**:
```bash
pip install -r requirements.txt
python app.py
```

### Step 4: Open Browser
Navigate to: **http://localhost:8050**

---

## 📁 File Structure

```
cleansight_explorer_v2/
├── app.py              # Main application
├── requirements.txt    # Python dependencies
├── start_dashboard.bat # Windows launcher
├── README.md          # This file
├── .cache/            # Auto-created: Dataset cache (Parquet)
├── workspaces/        # Auto-created: Saved workspace configs
└── .autosave.json     # Auto-created: Session state
```

---

## 🎯 Usage Guide

### Loading Data
1. Drag & drop a CSV or Excel file onto the upload area
2. Or click to browse files
3. File is automatically cached for future sessions

### Creating Charts
1. **X-Axis**: Select time, depth, or index
2. **Primary Y-Axis**: Add main variables (left scale)
3. **Secondary Y-Axis**: Add comparison variables (right scale, dashed lines)
4. **Subplots**: Click "+ Add" to create stacked charts

### Saving Your Work
- **Auto-save**: Runs every 30 seconds automatically
- **Manual save**: Click "💾 Save Workspace" to create a named checkpoint
- **Load**: Click "📂 Load Workspace" to restore a saved state

### Switching Between Datasets
- Load multiple files - they all stay cached
- Use the dataset dropdown to switch between them
- Each dataset remembers its own plot configuration

---

## 🔧 Supported File Formats

| Format | Extensions | Notes |
|--------|------------|-------|
| CSV | .csv | UTF-8, UTF-16, Latin-1; comma/tab/semicolon separated |
| Excel | .xlsx, .xls | First sheet loaded |

**AkerBP Format**: Automatically handles UTF-16-LE tab-separated exports.

---

## ⚡ Performance Tips

- **Large files (>100K rows)**: First load may take a few seconds, but cached loads are instant
- **Many traces**: Use subplots instead of overlapping many lines
- **Zoom performance**: Handled client-side, very fast

---

## 🐛 Troubleshooting

### "Module not found" Error
```bash
python -m pip install dash plotly pandas numpy openpyxl xlrd pyarrow
```

### Dashboard Resets on Tab Switch
This is fixed in v2.0! The session auto-saves and restores automatically.

### File Won't Load
- Check encoding (UTF-8 or UTF-16)
- Ensure file isn't open in Excel
- Try saving as CSV from Excel first

### Port 8050 In Use
Edit `app.py`, change the last line:
```python
app.run(debug=True, host='0.0.0.0', port=8051)  # Different port
```

---

## 📊 Engineering Use Cases

- **Hole Cleaning Analysis**: Plot TCR, CRR, UFO vs depth/time
- **Trip Planning**: Compare multiple trips with subplots
- **Trend Analysis**: Zoom into specific intervals
- **KPI Tracking**: Monitor key metrics in real-time
- **Report Generation**: Export charts as PNG

---

## 🗺️ Roadmap

Future enhancements planned:
- [ ] KPI configuration modal
- [ ] More chart types (bar, area, histogram)
- [ ] Data export to Excel
- [ ] Annotation tools
- [ ] Multiple chart pages/tabs
- [ ] Custom color schemes

---

## 📝 Version History

### v2.0.0 (May 2026)
- Dual Y-axis support
- Unlimited subplots
- Full column browser with search
- Session persistence & autosave
- Workspace save/load
- Dataset caching (Parquet)

### v1.0.0 (May 2026)
- Initial release
- Basic plotting
- Single Y-axis

---

*Built with ❤️ by DrillDocs*
