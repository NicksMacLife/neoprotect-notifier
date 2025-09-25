#!/usr/bin/env python3
"""Main entry point for the Python Discord bot."""
import argparse
import asyncio
import json
import logging
import signal
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neoprotect.client import Client as NeoProtectClient
from integrations.discord_bot import DiscordBotIntegration


from typing import Dict, Any, Optional


class Config:
    """Configuration loader."""
    
    def __init__(self, config_path: str):
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            self.api_key = data.get('apiKey', '')
            self.api_endpoint = data.get('apiEndpoint', 'https://api.neoprotect.net/v2')
            self.poll_interval_seconds = data.get('pollIntervalSeconds', 60)
            self.monitor_mode = data.get('monitorMode', 'all')
            self.specific_ips = data.get('specificIPs', [])
            self.blacklisted_ips = data.get('blacklistedIPs', [])
            self.enabled_integrations = data.get('enabledIntegrations', [])
            self.integration_configs = data.get('integrationConfigs', {})
            
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")
    
    def is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted."""
        return ip in self.blacklisted_ips


class AttackMonitor:
    """Attack monitoring system."""
    
    def __init__(self, config: Config):
        """Initialize attack monitor."""
        self.config = config
        self.neoprotect_client: Optional[NeoProtectClient] = None
        self.discord_bot: Optional[DiscordBotIntegration] = None
        self.known_attacks: Dict[str, Any] = {}
        self.running = False
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize all components."""
        # Create NeoProtect client
        self.neoprotect_client = NeoProtectClient(
            self.config.api_key,
            self.config.api_endpoint
        )
        
        # Initialize Discord bot if enabled
        if 'discord_bot' in self.config.enabled_integrations:
            discord_config = self.config.integration_configs.get('discord_bot', {})
            if discord_config:
                self.discord_bot = DiscordBotIntegration()
                self.discord_bot.set_api_client(self.neoprotect_client)
                await self.discord_bot.initialize(discord_config)
                self.logger.info("Discord bot integration initialized")
            else:
                self.logger.warning("Discord bot enabled but no configuration found")

    async def start_monitoring(self):
        """Start the attack monitoring loop."""
        self.running = True
        self.logger.info("Starting attack monitoring...")
        
        # Initial fetch
        await self._fetch_and_process_attacks()
        
        # Start monitoring loop
        while self.running:
            try:
                await asyncio.sleep(self.config.poll_interval_seconds)
                await self._fetch_and_process_attacks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _fetch_and_process_attacks(self):
        """Fetch and process active attacks."""
        if not self.neoprotect_client:
            return
        
        try:
            # Get all active attacks
            attacks = await self.neoprotect_client.get_all_attacks_all_pages(active_only=True)
            
            # Filter attacks based on monitor mode
            if self.config.monitor_mode == "specific":
                filtered_attacks = [
                    attack for attack in attacks
                    if attack.dst_address_string in self.config.specific_ips
                    and not self.config.is_blacklisted(attack.dst_address_string)
                ]
            elif self.config.monitor_mode == "all":
                filtered_attacks = [
                    attack for attack in attacks
                    if not self.config.is_blacklisted(attack.dst_address_string)
                ]
            else:
                self.logger.error(f"Invalid monitor mode: {self.config.monitor_mode}")
                return
            
            # Filter out invalid attacks
            valid_attacks = [
                attack for attack in filtered_attacks
                if self._is_valid_attack(attack)
            ]
            
            # Process attacks
            await self._process_active_attacks(valid_attacks)
            await self._check_for_ended_attacks(valid_attacks)
            self._cleanup_ended_attacks()
            
        except Exception as e:
            self.logger.error(f"Error fetching attacks: {e}")

    def _is_valid_attack(self, attack) -> bool:
        """Check if attack is valid."""
        return (
            attack and
            attack.id and
            attack.dst_address_string
        )

    async def _process_active_attacks(self, attacks):
        """Process active attacks."""
        seen_attacks = set()
        
        for attack in attacks:
            seen_attacks.add(attack.id)
            existing_attack = self.known_attacks.get(attack.id)
            
            if not existing_attack:
                # New attack
                self.known_attacks[attack.id] = attack
                await self._notify_new_attack(attack)
                
            elif not attack.equal(existing_attack):
                # Attack updated
                previous_state = existing_attack
                self.known_attacks[attack.id] = attack
                await self._notify_attack_update(attack, previous_state)

    async def _check_for_ended_attacks(self, active_attacks):
        """Check for attacks that have ended."""
        active_attack_ids = {attack.id for attack in active_attacks}
        
        for attack_id, attack in list(self.known_attacks.items()):
            if attack_id not in active_attack_ids and not attack.ended_at:
                # Attack has ended
                from datetime import datetime
                attack.ended_at = datetime.now()
                await self._notify_attack_ended(attack)
                self.known_attacks[attack_id] = attack

    def _cleanup_ended_attacks(self):
        """Clean up old ended attacks."""
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for attack_id, attack in list(self.known_attacks.items()):
            if attack.ended_at and attack.ended_at < cutoff_time:
                del self.known_attacks[attack_id]

    async def _notify_new_attack(self, attack):
        """Notify about new attack."""
        self.logger.info(f"New attack detected: {attack.id} on {attack.dst_address_string}")
        
        if self.discord_bot:
            try:
                await self.discord_bot.notify_new_attack(attack)
            except Exception as e:
                self.logger.error(f"Failed to notify Discord about new attack: {e}")

    async def _notify_attack_update(self, attack, previous):
        """Notify about attack update."""
        self.logger.info(f"Attack updated: {attack.id} on {attack.dst_address_string}")
        
        if self.discord_bot:
            try:
                await self.discord_bot.notify_attack_update(attack, previous)
            except Exception as e:
                self.logger.error(f"Failed to notify Discord about attack update: {e}")

    async def _notify_attack_ended(self, attack):
        """Notify about attack end."""
        self.logger.info(f"Attack ended: {attack.id} on {attack.dst_address_string}")
        
        if self.discord_bot:
            try:
                await self.discord_bot.notify_attack_ended(attack)
            except Exception as e:
                self.logger.error(f"Failed to notify Discord about attack end: {e}")

    async def shutdown(self):
        """Shutdown the monitor."""
        self.running = False
        self.logger.info("Shutting down attack monitor...")
        
        if self.discord_bot:
            await self.discord_bot.shutdown()
        
        if self.neoprotect_client:
            await self.neoprotect_client.close()
        
        self.logger.info("Shutdown complete")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='NeoProtect Discord Bot')
    parser.add_argument('-c', '--config', default='config.json', help='Configuration file path')
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('discord_bot.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting NeoProtect Discord Bot")
    
    try:
        # Load configuration
        config = Config(args.config)
        
        # Create and initialize monitor
        monitor = AttackMonitor(config)
        await monitor.initialize()
        
        # Setup signal handlers
        def signal_handler():
            logger.info("Received termination signal")
            monitor.running = False
        
        # Register signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: signal_handler())
        
        # Start monitoring
        try:
            await monitor.start_monitoring()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
        # Shutdown
        await monitor.shutdown()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))