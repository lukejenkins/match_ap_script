# AP Replacement Tracking Script

A Python script to match newly installed Cisco Catalyst 9800 Wireless Controller Access Points to their intended locations by correlating WLC command output with a tracking spreadsheet.

## Purpose

When replacing Access Points in a network, this script automates the tedious process of:
1. Identifying where each new AP physically installed (via CDP neighbor data)
2. Matching the new AP to its intended location in your tracking spreadsheet
3. Populating MAC addresses, serial numbers, and Meraki serial numbers for the new APs

## How It Works

The script:
- Parses Cisco 9800 WLC command outputs (`show ap cdp neighbors`, `show ap summary`, `show ap meraki monitoring summary`)
- Reads your tracking spreadsheet with expected AP locations (CDP neighbor switch and port)
- Matches new APs to their locations using **both CDP neighbor switch name AND port number**
- Outputs an updated CSV with MAC addresses, serial numbers, and Meraki serial numbers populated

## Input Files

### 1. Tracking Spreadsheet (CSV)
Contains columns like:
- AP Name
- MAC Address (to be populated)
- Serial Number (to be populated)
- Meraki Serial Number (to be populated)
- CDP Neighbor (switch name)
- Port of CDP Neighbor

### 2. WLC Command Output

**Option A: Separate files**
- `show_ap_cdp_neighbors.txt`
- `show_ap_sum.txt`
- `show_ap_meraki_monitoring_summary.txt`

**Option B: Combined file**
- Single file with all commands and their outputs (CLI prompts included)

## Usage

```bash
python match_aps.py <tracking_spreadsheet.csv> <wlc_output_file_or_directory>
```

### Examples

With separate command files:
```bash
python match_aps.py tracking.csv output_files/
```

With combined command file:
```bash
python match_aps.py tracking.csv shows.txt
```

## Output

Generates `<input_filename>_updated.csv` with populated AP details and a summary report showing:
- Number of successful matches
- Any unmatched APs

## Key Features

- **Accurate Matching**: Uses both CDP neighbor switch name AND port number to avoid false positives
- **MAC Address Conversion**: Automatically converts Cisco format (`aaaa.bbbb.cccc`) to standard format (`AA:BB:CC:DD:EE:FF`)
- **Flexible Input**: Supports both separate command files and combined output files
- **CLI Abbreviation Support**: Handles Cisco IOS CLI command abbreviations (e.g., `sh ap sum`, `show ap summary`)

## Requirements

- Python 3.6+
- Standard library only (no external dependencies)

## License

MIT License - see [LICENSE](LICENSE) file for details
