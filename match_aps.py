#!/usr/bin/env python3
"""
Match new APs to old AP locations based on CDP neighbor data.
Supports both separate files and combined shows.txt format.
"""

import argparse
import csv
import os
import re
import sys

def convert_mac_format(cisco_mac):
    """Convert Cisco MAC format (aaaa.bbbb.cccc) to standard format (AA:BB:CC:DD:EE:FF).
    
    Args:
        cisco_mac: MAC address in Cisco format (e.g., '6cef.abcd.1234')
    
    Returns:
        MAC address in standard format (e.g., '6C:EF:AB:CD:12:34')
    """
    # Remove dots and any other separators
    mac_clean = cisco_mac.replace('.', '').replace(':', '').replace('-', '')
    
    # Split into pairs and join with colons
    mac_pairs = [mac_clean[i:i+2] for i in range(0, len(mac_clean), 2)]
    
    # Return uppercase with colon separators
    return ':'.join(mac_pairs).upper()

def parse_combined_shows(file_path):
    """Parse shows.txt containing multiple show commands.
    Handles Cisco IOS CLI command abbreviations:
    - sh ap sum -> show ap summary
    - sh ap cd n -> show ap cdp neighbors
    - sh ap me m s -> show ap meraki monitoring summary
    """
    sections = {
        'ap_sum': [],
        'cdp_neighbors': [],
        'meraki_monitoring': []
    }
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    current_section = None
    i = 0
    
    while i < len(lines):
        line = lines[i]
        line_lower = line.lower()
        
        # Detect command prompts - handle CLI abbreviations
        # Must contain '#' and 'show'/'sho'/'sh' and 'ap'
        if '#' in line and re.search(r'#\s*(sh|sho|show)\s+ap', line_lower):
            # Check for specific command types using prefix matching
            
            # AP Summary: sh[ow] ap sum[mary]
            # Minimum: sh ap sum, Maximum: show ap summary
            if re.search(r'#\s*(sh|sho|show)\s+ap\s+sum', line_lower):
                current_section = 'ap_sum'
                i += 1
                continue
            
            # CDP Neighbors: sh[ow] ap cd[p] [n[eighbors]]
            # Minimum: sh ap cd n, Maximum: show ap cdp neighbors
            elif re.search(r'#\s*(sh|sho|show)\s+ap\s+cd', line_lower):
                current_section = 'cdp_neighbors'
                i += 1
                continue
            
            # Meraki Monitoring: sh[ow] ap me[raki] m[onitoring] [s[ummary]]
            # Minimum: sh ap me m s, Maximum: show ap meraki monitoring summary
            elif re.search(r'#\s*(sh|sho|show)\s+ap\s+me\w*\s+m', line_lower):
                current_section = 'meraki_monitoring'
                i += 1
                continue
            
            else:
                # Different command, stop current section
                current_section = None
                i += 1
                continue
        
        # Add line to current section
        if current_section:
            # Stop if we hit another prompt
            if '#' in line and re.search(r'#\s*(sh|sho|show)', line_lower):
                current_section = None
            else:
                sections[current_section].append(line)
        
        i += 1
    
    return sections

def parse_cdp_from_lines(lines):
    """Parse CDP neighbor data from lines."""
    cdp_data = {}
    
    for line in lines:
        parts = line.split()
        if len(parts) >= 5 and not ('---' in line or 'AP Name' in line or 'Number of neighbors' in line):
            # Check if first part looks like an AP name (not a number or empty)
            if parts[0] and not parts[0].isdigit():
                ap_name = parts[0]
                neighbor = parts[2]  # Neighbor Name
                port = parts[4]      # Port
                cdp_data[ap_name] = {'neighbor': neighbor, 'port': port}
    
    return cdp_data

def parse_meraki_from_lines(lines):
    """Parse Meraki monitoring data from lines."""
    meraki_data = {}
    
    for line in lines:
        parts = line.split()
        if len(parts) >= 7 and not ('---' in line or 'AP Name' in line or 'Meraki Monitoring' in line or 'Number of Supported' in line):
            # Check if line looks like AP data
            if parts[0] and parts[0].startswith('AP') or parts[0].startswith('canary'):
                ap_name = parts[0]
                mac_cisco = parts[3]
                serial = parts[4]
                cloud_id = parts[5]
                
                # Convert MAC address from Cisco format to standard format
                mac_standard = convert_mac_format(mac_cisco)
                
                meraki_data[ap_name] = {
                    'mac': mac_standard,
                    'serial': serial,
                    'meraki_serial': cloud_id
                }
    
    return meraki_data

def load_data(combined_file=None, cdp_file=None, meraki_file=None):
    """Load data from either combined or separate files."""
    cdp_data = {}
    meraki_data = {}
    
    # Check for combined file first
    if combined_file and os.path.exists(combined_file):
        print(f"Parsing combined output from {combined_file}")
        sections = parse_combined_shows(combined_file)
        cdp_data = parse_cdp_from_lines(sections['cdp_neighbors'])
        meraki_data = parse_meraki_from_lines(sections['meraki_monitoring'])
    elif combined_file:
        print(f"ERROR: Combined file {combined_file} not found")
        sys.exit(1)
    else:
        print("Using separate files")
        # Parse CDP neighbors from separate file
        if cdp_file and os.path.exists(cdp_file):
            print(f"Reading CDP data from {cdp_file}")
            with open(cdp_file, 'r') as f:
                lines = f.readlines()
            cdp_data = parse_cdp_from_lines(lines)
        elif cdp_file:
            print(f"ERROR: CDP file {cdp_file} not found")
            sys.exit(1)
        
        # Parse Meraki monitoring from separate file
        if meraki_file and os.path.exists(meraki_file):
            print(f"Reading Meraki data from {meraki_file}")
            with open(meraki_file, 'r') as f:
                lines = f.readlines()
            meraki_data = parse_meraki_from_lines(lines)
        elif meraki_file:
            print(f"ERROR: Meraki file {meraki_file} not found")
            sys.exit(1)
    
    return cdp_data, meraki_data

def create_port_mapping(cdp_data, meraki_data):
    """Create mapping from (neighbor, port) to AP data."""
    port_to_ap = {}
    
    for ap_name, cdp_info in cdp_data.items():
        neighbor_full = cdp_info['neighbor']
        neighbor_short = neighbor_full.split('.')[0]  # Get short name
        port = cdp_info['port']
        
        if ap_name in meraki_data:
            ap_data = {
                'mac': meraki_data[ap_name]['mac'],
                'serial': meraki_data[ap_name]['serial'],
                'meraki_serial': meraki_data[ap_name]['meraki_serial']
            }
            # Store with both short and full names
            port_to_ap[(neighbor_full, port)] = ap_data
            port_to_ap[(neighbor_short, port)] = ap_data
    
    return port_to_ap

def update_csv(port_to_ap, input_file='input.csv', output_file='input_updated.csv'):
    """Update CSV with matched AP data."""
    rows = []
    
    with open(input_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        
        for row in reader:
            if len(row) >= 9 and row[0]:  # Has AP Name
                ap_name = row[0]
                cdp_neighbor = row[7]
                cdp_port = row[8]
                
                # Look up the AP data by CDP neighbor and port
                key = (cdp_neighbor, cdp_port)
                if key in port_to_ap:
                    ap_data = port_to_ap[key]
                    row[1] = ap_data['mac']  # MAC Address
                    row[2] = ap_data['serial']  # Serial Number
                    row[3] = ap_data['meraki_serial']  # Meraki Serial Number
            
            rows.append(row)
    
    # Write updated CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    return output_file, rows

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Match new APs to old AP locations based on CDP neighbor data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using combined shows file:
  %(prog)s -c shows.txt -i tracking.csv -o output.csv

  # Using separate files:
  %(prog)s -i tracking.csv -o output.csv \\
    --cdp show_ap_cdp_neighbors.txt \\
    --meraki show_ap_meraki_monitoring_summary.txt

  # With custom log directory:
  %(prog)s -c data/shows.txt -i data/tracking.csv \\
    -o results/updated.csv --log-dir logs/
        """
    )
    
    # Input files
    input_group = parser.add_argument_group('input files')
    input_group.add_argument('-c', '--combined',
                            help='Combined shows.txt file with all show commands')
    input_group.add_argument('--cdp',
                            help='Separate file: show ap cdp neighbors output')
    input_group.add_argument('--meraki',
                            help='Separate file: show ap meraki monitoring summary output')
    input_group.add_argument('-i', '--input-csv', required=True,
                            help='Input CSV tracking spreadsheet (required)')
    
    # Output files
    output_group = parser.add_argument_group('output files')
    output_group.add_argument('-o', '--output-csv',
                             help='Output CSV file (default: <input>_updated.csv)')
    output_group.add_argument('--log-dir',
                             help='Directory for logs and debug files (default: current directory)')
    
    args = parser.parse_args()
    
    # Validation
    if not args.combined and not (args.cdp or args.meraki):
        parser.error('Must provide either --combined or at least one of --cdp/--meraki')
    
    if args.combined and (args.cdp or args.meraki):
        parser.error('Cannot use both --combined and separate files (--cdp/--meraki)')
    
    # Set default output file if not provided
    if not args.output_csv:
        base_name = os.path.splitext(args.input_csv)[0]
        args.output_csv = f"{base_name}_updated.csv"
    
    # Create log directory if specified
    if args.log_dir:
        os.makedirs(args.log_dir, exist_ok=True)
    
    return args

def main():
    args = parse_args()
    
    print("=== AP Replacement Matching Tool ===\n")
    
    # Verify input CSV exists
    if not os.path.exists(args.input_csv):
        print(f"ERROR: Input CSV file not found: {args.input_csv}")
        sys.exit(1)
    
    # Load data
    cdp_data, meraki_data = load_data(
        combined_file=args.combined,
        cdp_file=args.cdp,
        meraki_file=args.meraki
    )
    print(f"Loaded {len(cdp_data)} APs from CDP neighbors")
    print(f"Loaded {len(meraki_data)} APs from Meraki monitoring\n")
    
    # Create mapping
    port_to_ap = create_port_mapping(cdp_data, meraki_data)
    
    # Update CSV
    output_file, rows = update_csv(port_to_ap, args.input_csv, args.output_csv)
    
    # Count matches
    matched_count = 0
    for row in rows[1:]:  # Skip header
        if len(row) >= 9 and row[0] and row[1]:  # Has AP name and MAC
            matched_count += 1
    
    print(f"✓ Generated {output_file}")
    print(f"✓ Successfully matched {matched_count} APs to their locations")
    
    # Show matched APs
    print("\nMatched APs:")
    for row in rows[1:20]:  # Show first 20
        if len(row) >= 9 and row[0] and row[1]:
            print(f"  {row[0]:15} → {row[1]:17} {row[2]:15} {row[3]}")
    
    # Save debug log if log-dir specified
    if args.log_dir:
        log_file = os.path.join(args.log_dir, 'debug.log')
        with open(log_file, 'w') as f:
            f.write(f"=== AP Matching Debug Log ===\n\n")
            f.write(f"Input files:\n")
            f.write(f"  CSV: {args.input_csv}\n")
            f.write(f"  Combined: {args.combined}\n")
            f.write(f"  CDP: {args.cdp}\n")
            f.write(f"  Meraki: {args.meraki}\n\n")
            f.write(f"Output file: {args.output_csv}\n\n")
            f.write(f"CDP data ({len(cdp_data)} APs):\n")
            for ap, info in cdp_data.items():
                f.write(f"  {ap}: {info}\n")
            f.write(f"\nMeraki data ({len(meraki_data)} APs):\n")
            for ap, info in meraki_data.items():
                f.write(f"  {ap}: {info}\n")
            f.write(f"\nPort mapping ({len(port_to_ap)} entries):\n")
            for key, value in port_to_ap.items():
                f.write(f"  {key}: {value}\n")
            f.write(f"\nMatched {matched_count} APs\n")
        print(f"✓ Debug log saved to {log_file}")

if __name__ == '__main__':
    main()
