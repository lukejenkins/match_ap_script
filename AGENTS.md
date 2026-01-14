# AI Agents Operational Guidance

This document provides centralized operational guidance for all AI agents working with this project.

## Project Guidelines

### Project Goals

**Primary Goal:** Automate the matching of newly installed Cisco Catalyst 9800 Wireless Controller Access Points to their intended locations by correlating WLC command output with a tracking spreadsheet.

**Secondary Goal:** Optionally generate Cisco 9800 WLC CLI commands for AP configuration:
1. **Renaming APs** - Generate commands to rename APs from temporary names to permanent names
2. **Adding APs to Building Groups** - Generate commands to assign APs to appropriate building/site groups
3. **Setting Geolocation Height** - Generate commands to configure AP height for location accuracy

**Output Format:** Commands should be ready to paste into WLC CLI or save as a configuration script.

### Documentation Requirements

**1. User Documentation Maintenance**
- **README.md**: Keep user-facing documentation comprehensive and up-to-date
  - Document all features, CLI options, and .env configuration
  - Provide clear examples for common use cases
  - Include installation instructions and requirements
  - Update whenever features are added or changed

- **CLI Help Output**: Maintain `--help` output in sync with README
  - Use `argparse` with detailed help text for all arguments
  - Include usage examples in epilog section
  - Document environment variable alternatives
  - Keep help text concise but informative

**2. Configuration Priority System**

All features must support multiple configuration methods with this priority order:

**Priority (highest to lowest):**
1. **CLI Arguments** - Direct command-line flags override everything
2. **Environment Variables (.env file)** - Default values from .env file
3. **Hardcoded Defaults** - Sensible defaults or interactive prompts

**Implementation Guidelines:**
- Every CLI option should have an environment variable equivalent
- CLI arguments must override .env settings
- .env settings must override hardcoded defaults
- Non-optional arguments without defaults should prompt the user for input
- Use `argparse` `default` parameter to read from `os.getenv()`
- Make `required=False` when env var provides the value

**Example Pattern:**
```python
env_value = os.getenv('ENV_VAR_NAME')
parser.add_argument('--flag', default=env_value, 
                    required=not env_value,
                    help='Description (can be set via ENV_VAR_NAME)')
```

**3. Environment Configuration Template**
- **Keep `.env.example` synchronized** with all possible configuration options
- Every new environment variable must be documented in `.env.example`
- Include:
  - Descriptive comments for each variable
  - Example values showing proper format
  - Notes about optional vs required settings
  - Grouping of related variables
- Review and update `.env.example` whenever adding new features
- Never commit actual `.env` files (ensure in `.gitignore`)

---

# Wireless Access Point Replacement Tracking Task

## Objective
Match newly installed Access Points to their intended locations by correlating Cisco 9800 WLC command output with a tracking spreadsheet, then populate the spreadsheet with the new AP details.

## Input Files

### 1. Tracking Spreadsheet
**Filename:**
Will likely be a .csv file.
**Structure:**
- Header row with columns: `AP Name`, `MAC Address`, `Serial Number`, `Meraki Serial Number`, `CDP Neighbor`, `Port of CDP Neighbor`, etc.
- Rows with AP Names have their expected CDP Neighbor switch and port
- Blank MAC/Serial/Meraki fields need to be populated
- Some rows contain only MAC/Serial/Meraki data (new AP inventory - not yet assigned)
- **IMPORTANT:** CSV structure must NOT be modified - it's for another system
- For CLI command generation, use only existing columns or separate configuration

### 2. Cisco 9800 WLC Command Outputs

**Two possible formats:**

#### Option A: Separate Files
- `show_ap_cdp_neighbors.txt` - Shows which switch/port each AP is currently connected to
- `show_ap_sum.txt` - Contains AP names with Ethernet MAC addresses
- `show_ap_meraki_monitoring_summary.txt` - Contains AP names with MAC, Serial Number, and Cloud ID (Meraki Serial)

#### Option B: Combined File
**Filename:**
Will likely be a .txt or .log file.
**Structure:**
All commands in a single file with CLI prompts. Parse by detecting command prompts:
- Look for lines matching pattern: `hostname#show ap ...`
- Extract the command after the `#` prompt
- Parse subsequent lines until the next prompt

**Command Abbreviation Support:**
Cisco IOS CLI accepts any unambiguous abbreviation of commands. Must handle all variations:
- `show ap summary`: Minimum `sh ap sum`, maximum `show ap summary`
- `show ap cdp neighbors`: Minimum `sh ap cd n`, maximum `show ap cdp neighbors`
- `show ap meraki monitoring summary`: Minimum `sh ap me m s`, maximum `show ap meraki monitoring summary`

**Parsing Strategy:**
- Match commands using prefix patterns (not exact strings)
- For AP summary: Match `#` + `sh` (or `sho`/`show`) + `ap` + `sum` (or `su`/`summary`)
- For CDP neighbors: Match `#` + `sh` (or `sho`/`show`) + `ap` + `cd` (or `cdp`) + optional `n` (or `ne`/`neighbor`/`neighbors`)
- For Meraki: Match `#` + `sh` (or `sho`/`show`) + `ap` + `me` (or `mer`/`meraki`) + `m` (or `mo`/`mon`/`monitoring`) + optional `s` (or `su`/`sum`/`summary`)

## Critical Matching Logic

**⚠️ IMPORTANT: Must match by BOTH CDP neighbor AND port**

The matching key is the tuple: `(CDP Neighbor, Port)`

**Why this matters:**
- Multiple switches can have identical port numbers (e.g., both `building-1a-gw1` and `building-1a-sw1` have `TenGigabitEthernet1/0/45`)
- Matching by port number alone will create FALSE POSITIVES
- Example:
  - ❌ WRONG: Match only by port `TenGigabitEthernet1/0/45`
  - ✓ CORRECT: Match by `(building-1a-gw1, TenGigabitEthernet1/0/45)` vs `(building-1a-sw1, TenGigabitEthernet1/0/45)`

## Data Parsing Details

### Parsing `show_ap_cdp_neighbors.txt`
```
Format (space-separated):
AP Name          AP IP            Neighbor Name              Neighbor IP    Neighbor Port
APXXXX-XXXX-XXXX 10.11.12.xxx    building-1a-gw1.network.example.com   10.11.12.x   TenGigabitEthernet1/0/XX
```
- Split by whitespace
- Index 0: AP Name (current/temp name like `AP6CEF-BDC7-B420`)
- Index 2: Neighbor Name (switch FQDN like `building-1a-gw1.network.example.com`)
- Index 4: Neighbor Port (like `TenGigabitEthernet1/0/45`)
- Extract short neighbor name by splitting on `.` and taking first part

### Parsing `show_ap_meraki_monitoring_summary.txt`
```
Format (space-separated):
AP Name          AP Model  Radio MAC      MAC Address    AP Serial Number  Cloud ID        Status
APXXXX-XXXX-XXXX CW9176I   xxxx.xxxx.xxxx xxxx.xxxx.xxxx WVN2901ABCD      Q5BK-ABCD-1234  Registered
```
- MAC Address is typically in format `xxxx.xxxx.xxxx` (Cisco format)
- **Must convert to standard format:** `XX:XX:XX:XX:XX:XX` (colon-separated pairs)
  - Example: `6cef.abcd.1234` → `6C:EF:AB:CD:12:34`
  - Remove dots, split into pairs, join with colons, uppercase
- Cloud ID column contains the Meraki Serial Number

## Processing Algorithm

1. **Detect input format:**
   - Check if `shows.txt` exists → parse combined file by splitting on CLI prompts
   - Otherwise, use separate files (`show_ap_cdp_neighbors.txt`, etc.)

2. **Parse CDP neighbors** → Build dict: `AP_name -> {neighbor, port}`
3. **Parse Meraki monitoring** → Build dict: `AP_name -> {mac, serial, meraki_serial}`
4. **Transform MAC addresses:** Convert from Cisco format (`aaaa.bbbb.cccc`) to standard format (`AA:BB:CC:DD:EE:FF`)
5. **Create mapping** → Build dict: `(neighbor, port) -> {mac, serial, meraki_serial}`
   - Use BOTH full FQDN and short hostname as keys (for robustness)
6. **Update CSV:**
   - For each row with an AP Name and CDP Neighbor/Port
   - Look up `(cdp_neighbor, cdp_port)` in mapping
   - If found: populate MAC Address (in XX:XX:XX:XX:XX:XX format), Serial Number, Meraki Serial Number
   - If not found: leave blank (AP not yet installed at that location)

## Expected Output

### 1. Updated CSV File
Generate: `<input-spreadsheet-name>_updated.csv`
- Same structure as input CSV
- Populated MAC/Serial/Meraki fields for APs that are installed and visible in show commands
- Blank fields for APs not yet installed
- Report summary: number of successful matches

### 2. Optional: Cisco 9800 CLI Commands
When enabled, generate CLI commands file with:

**AP Rename Commands:**
```
ap name <temporary-name> rename <permanent-name>
```
- Temporary name: From WLC output (CDP neighbors data)
- Permanent name: From CSV `AP Name` column

**Building Group Assignment Commands:**
```
ap name <ap-name> site-tag <building-group>
```
- Building group must be provided via CLI argument, .env variable, or derived from AP name pattern

**Geolocation Height Configuration:**
```
ap name <ap-name> location height <height-value>
```
- Height value must be provided via CLI argument, .env variable, or configuration file

**Requirements:**
- Commands should be in correct Cisco IOS order
- Include comments for clarity (using `!` prefix)
- Group commands by type for readability
- Validate AP names exist before generating commands
- Output to separate file (e.g., `<input>_commands.txt`)
- Support dry-run mode to preview without file creation
- **Do NOT modify the CSV structure** - use separate configuration sources for building group and height data

## Validation

Before finalizing, verify:
1. No duplicate assignments (same physical AP assigned to multiple locations)
2. All matches respect both switch name AND port number
3. Count of matches equals number of unique APs in CDP neighbor output (excluding management/test APs)

## Common Pitfalls to Avoid

❌ Matching by port number only
❌ Not handling FQDN vs short hostname differences
❌ Hardcoding line numbers (file formats may vary slightly)
❌ Not preserving original CSV formatting and columns
❌ Using exact command string matching (must support CLI abbreviations)
❌ Generating CLI commands for APs that don't exist in WLC output
❌ Not validating required CSV columns exist before generating commands

## CLI Command Generation Guidelines

When implementing CLI command output feature:
- **Never modify the CSV structure** - it must remain compatible with external systems
- For building group and height data, use:
  - CLI arguments (e.g., `--building-group`, `--default-height`)
  - Environment variables (e.g., `BUILDING_GROUP`, `DEFAULT_HEIGHT`)
  - Separate configuration file (e.g., JSON/YAML mapping AP names to settings)
  - Pattern matching on AP names (e.g., `ce-106-ap1` → building `ce-106`, site-tag `CE`)
- Verify the CSV has the required columns for each command type
- Use temporary AP names from WLC output, target names from CSV
- Include error handling for missing data
- Add comments in output file explaining command groups
- Validate AP names exist before generating rename commands
- Support enabling/disabling individual command types
- Allow custom output file path for commands
- Consider command order and dependencies
