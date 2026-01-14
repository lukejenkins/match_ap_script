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
python match_aps.py -i INPUT_CSV [options]
```

### Required Arguments

- `-i, --input-csv`: Input CSV tracking spreadsheet (required)

### Input File Options

You must provide either:
- `-c, --combined`: Combined shows.txt file with all show commands
  
OR one or both of:
- `--cdp`: Separate file with `show ap cdp neighbors` output
- `--meraki`: Separate file with `show ap meraki monitoring summary` output

### Output Options

- `-o, --output-csv`: Output CSV file (default: `<input>_updated.csv`)
- `--log-dir`: Directory for logs and debug files (default: current directory)

### Examples

**Using combined shows file:**
```bash
python match_aps.py -c shows.txt -i tracking.csv -o output.csv
```

**Using separate files:**
```bash
python match_aps.py -i tracking.csv -o output.csv \
  --cdp show_ap_cdp_neighbors.txt \
  --meraki show_ap_meraki_monitoring_summary.txt
```

**With custom directories:**
```bash
python match_aps.py -c data/shows.txt -i data/tracking.csv \
  -o results/updated.csv --log-dir logs/
```

**Minimal example (auto-generates output filename):**
```bash
python match_aps.py -c shows.txt -i tracking.csv
# Output will be: tracking_updated.csv
```

**Using .env file for configuration:**
```bash
# Set up .env file once
cp .env.example .env
# Edit .env with your paths

# Then run without arguments
python match_aps.py
```

### Getting Help

```bash
python match_aps.py --help
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
- **Environment Configuration**: Support for `.env` files to set default paths and avoid repetitive CLI arguments
- **Debug Logging**: Optional detailed logging for troubleshooting

## Requirements

- Python 3.6+
- `python-dotenv` (optional, for .env file support)

### Installation

```bash
# Install optional dependencies
pip install -r requirements.txt
```

The script will work without `python-dotenv`, but you won't be able to use `.env` files for configuration.

## Configuration

### Option 1: Environment Variables (.env file)

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your file paths:

```bash
# Example .env configuration
COMBINED_FILE=./examples/private/shows.txt
INPUT_CSV=./examples/private/tracking.csv
OUTPUT_CSV=./output/updated.csv
LOG_DIR=./logs/
```

Then run the script without arguments:

```bash
python match_aps.py
```

**Note:** CLI arguments override `.env` settings.

### Option 2: Command Line Arguments

See usage examples below.

## AI Disclosure

**Here there be robots!** I *think* they are friendly, but they might just be very good at pretending. You might be a fool if you use this project for anything other than as an example of how silly it can be to use AI to code with.

> This project was developed with the assistance of language models from companies such as OpenAI and Anthropic, which provided suggestions and code snippets to enhance the functionality and efficiency of the tools. The models were used to generate code, documentation, distraction, moral support, moral turpitude, and explanations for various components of the project.

## AI Agents

Operational guidance for all AI agents is centralized in [AGENTS.md](AGENTS.md).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
