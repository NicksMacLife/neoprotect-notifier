#!/usr/bin/env python3
"""Example usage of the NeoProtect Python Discord bot components."""
import asyncio
import json
import sys
import os
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neoprotect.models import Attack, AttackSignature, IPAddressModel
from neoprotect.client import Client as NeoProtectClient
from integrations.utils import format_bps, format_pps, format_duration_readable, format_time_to_local


async def example_usage():
    """Demonstrate the Python components without requiring real API credentials."""
    print("🐍 NeoProtect Python Discord Bot - Example Usage\n")
    
    # Example 1: Create and work with attack models
    print("📊 Example 1: Working with Attack Models")
    print("-" * 40)
    
    # Create example attack signature
    signature = AttackSignature(
        id="sig123",
        name="UDP Flood",
        started_at=datetime.now(),
        ended_at=None,
        pps_peak=150000,
        bps_peak=2000000
    )
    
    # Create example attack
    attack = Attack(
        id="attack123",
        dst_address_string="192.168.1.100",
        dst_address=None,
        signatures=[signature],
        started_at=datetime.now(),
        ended_at=None,
        sample_rate=100
    )
    
    print(f"Attack ID: {attack.id}")
    print(f"Target IP: {attack.dst_address_string}")
    print(f"Peak BPS: {format_bps(attack.get_peak_bps())}")
    print(f"Peak PPS: {format_pps(attack.get_peak_pps())}")
    print(f"Duration: {format_duration_readable(attack.duration())}")
    print(f"Signatures: {', '.join(attack.get_signature_names())}")
    print()
    
    # Example 2: Utility functions
    print("🔧 Example 2: Utility Functions")
    print("-" * 40)
    
    test_values = [
        (1500, "bytes/sec"),
        (150000, "bytes/sec"),
        (15000000, "bytes/sec"),
        (1500000000, "bytes/sec")
    ]
    
    for value, unit in test_values:
        if "bytes" in unit:
            print(f"{value:>10} {unit} = {format_bps(value)}")
        else:
            print(f"{value:>10} {unit} = {format_pps(value)}")
    
    print()
    
    # Example 3: Attack comparison
    print("🔍 Example 3: Attack Comparison")
    print("-" * 40)
    
    # Create a second attack with changes
    signature2 = AttackSignature(
        id="sig123",
        name="UDP Flood",
        started_at=datetime.now(),
        ended_at=None,
        pps_peak=200000,  # Increased
        bps_peak=2500000  # Increased
    )
    
    signature3 = AttackSignature(
        id="sig456",
        name="TCP SYN Flood",  # New signature
        started_at=datetime.now(),
        ended_at=None,
        pps_peak=100000,
        bps_peak=1500000
    )
    
    attack2 = Attack(
        id="attack123",
        dst_address_string="192.168.1.100",
        dst_address=None,
        signatures=[signature2, signature3],  # Added new signature
        started_at=datetime.now(),
        ended_at=None,
        sample_rate=100
    )
    
    print("Original attack:")
    print(f"  Peak BPS: {format_bps(attack.get_peak_bps())}")
    print(f"  Peak PPS: {format_pps(attack.get_peak_pps())}")
    print(f"  Signatures: {', '.join(attack.get_signature_names())}")
    
    print("\nUpdated attack:")
    print(f"  Peak BPS: {format_bps(attack2.get_peak_bps())}")
    print(f"  Peak PPS: {format_pps(attack2.get_peak_pps())}")
    print(f"  Signatures: {', '.join(attack2.get_signature_names())}")
    
    print("\nChanges detected:")
    diff = attack2.calculate_diff(attack)
    for key, value in diff.items():
        if key == 'newSignatures':
            print(f"  New signatures: {', '.join(value)}")
        else:
            print(f"  {key}: {value}")
    
    print()
    
    # Example 4: Configuration loading
    print("⚙️ Example 4: Configuration")
    print("-" * 40)
    
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            config = json.load(f)
        
        print("Configuration loaded successfully:")
        print(f"  API Endpoint: {config.get('apiEndpoint', 'Not set')}")
        print(f"  Poll Interval: {config.get('pollIntervalSeconds', 'Not set')} seconds")
        print(f"  Monitor Mode: {config.get('monitorMode', 'Not set')}")
        print(f"  Enabled Integrations: {', '.join(config.get('enabledIntegrations', []))}")
        
        discord_config = config.get('integrationConfigs', {}).get('discord_bot', {})
        if discord_config:
            print("  Discord Bot Config:")
            print(f"    Commands Enabled: {discord_config.get('commandsEnabled', False)}")
            print(f"    Allowed Roles: {len(discord_config.get('allowedRoles', []))} roles configured")
    else:
        print("No config.json found. Run ./install.sh to create one from the example.")
    
    print()
    
    # Example 5: NeoProtect Client (without real connection)
    print("🌐 Example 5: NeoProtect Client")
    print("-" * 40)
    
    try:
        # This will fail without real credentials, but shows the API
        client = NeoProtectClient("dummy_key", "https://api.neoprotect.net/v2")
        print(f"Client created with base URL: {client.base_url}")
        print("Note: Real API calls require valid credentials")
        
        # Clean up
        await client.close()
        
    except Exception as e:
        print(f"Client creation: {e}")
    
    print()
    print("✅ Example usage complete!")
    print("\nTo run the actual Discord bot:")
    print("1. Configure config.json with real credentials")
    print("2. Run: python main.py --config config.json")


if __name__ == "__main__":
    asyncio.run(example_usage())