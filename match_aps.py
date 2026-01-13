#!/usr/bin/env python3
"""
Match new APs to old AP locations based on CDP neighbor data.
Supports both separate files and combined shows.txt format.
"""

import csv
import os
import re

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

def load_data():
    """Load data from either combined or separate files."""
    cdp_data = {}
    meraki_data = {}
    
    # Check for combined file first
    if os.path.exists('shows.txt'):
        print("Found shows.txt - parsing combined output")
        sections = parse_combined_shows('shows.txt')
        cdp_data = parse_cdp_from_lines(sections['cdp_neighbors'])
        meraki_data = parse_meraki_from_lines(sections['meraki_monitoring'])
    else:
        print("Using separate files")
        # Parse CDP neighbors from separate file
        if os.path.exists('show_ap_cdp_neighbors.txt'):
            with open('show_ap_cdp_neighbors.txt', 'r') as f:
                lines = f.readlines()
            cdp_data = parse_cdp_from_lines(lines[4:11])
        
        # Parse Meraki monitoring from separate file
        if os.path.exists('show_ap_meraki_monitoring_summary.txt'):
            with open('show_ap_meraki_monitoring_summary.txt', 'r') as f:
                lines = f.readlines()
            meraki_data = parse_meraki_from_lines(lines[8:15])
    
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

def main():
    print("=== AP Replacement Matching Tool ===\n")
    
    # Load data
    cdp_data, meraki_data = load_data()
    print(f"Loaded {len(cdp_data)} APs from CDP neighbors")
    print(f"Loaded {len(meraki_data)} APs from Meraki monitoring\n")
    
    # Create mapping
    port_to_ap = create_port_mapping(cdp_data, meraki_data)
    
    # Update CSV
    output_file, rows = update_csv(port_to_ap)
    
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

if __name__ == '__main__':
    main()
