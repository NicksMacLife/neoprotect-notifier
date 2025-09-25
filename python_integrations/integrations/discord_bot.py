"""Discord bot integration using discord.py."""
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

import discord
from discord.ext import commands

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neoprotect.client import Client as NeoProtectClient, NoActiveAttackError, IPNotFoundError
from neoprotect.models import Attack
from integrations.utils import (
    format_bps, format_pps, format_duration_readable, format_time_to_local,
    calculate_percentage_change, DISCORD_COLOR_RED, DISCORD_COLOR_YELLOW,
    DISCORD_COLOR_GREEN, DISCORD_COLOR_BLUE
)


class DiscordBotIntegration:
    """Discord bot integration using discord.py."""
    
    def __init__(self):
        """Initialize the Discord bot integration."""
        self.bot: Optional[commands.Bot] = None
        self.neoprotect_api: Optional[NeoProtectClient] = None
        self.token = ""
        self.client_id = ""
        self.guild_id = ""
        self.channel_id = ""
        self.username = ""
        self.avatar_url = ""
        self.commands_enabled = True
        self.allowed_roles: List[str] = []
        self.attack_cache: Dict[str, str] = {}  # attack_id -> message_id
        self.logger = logging.getLogger(__name__)

    def name(self) -> str:
        """Get integration name."""
        return "discord_bot"

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the Discord bot."""
        # Parse configuration
        self.token = config.get("token", "")
        self.client_id = config.get("clientId", "")
        self.guild_id = config.get("guildId", "")
        self.channel_id = config.get("channelId", "")
        self.username = config.get("username", "")
        self.avatar_url = config.get("avatarUrl", "")
        self.commands_enabled = config.get("commandsEnabled", True)
        self.allowed_roles = config.get("allowedRoles", [])

        if not self.token:
            raise ValueError("Bot token must be provided")
        if not self.channel_id:
            raise ValueError("Channel ID must be provided")

        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        # Create bot instance
        self.bot = commands.Bot(command_prefix='!', intents=intents)

        # Set up event handlers
        self.bot.event(self._on_ready)

        # Register slash commands if enabled
        if self.commands_enabled:
            await self._register_commands()

        # Start the bot
        await self.bot.start(self.token)

    async def _on_ready(self):
        """Called when the bot is ready."""
        self.logger.info("Discord bot is now ready!")
        
        # Set bot presence
        activity = discord.Activity(type=discord.ActivityType.watching, name="DDoS attacks")
        await self.bot.change_presence(activity=activity)
        
        # Send welcome message
        try:
            channel = self.bot.get_channel(int(self.channel_id))
            if channel:
                await channel.send("🤖 **NeoProtect Monitor Bot is online!**")
        except Exception as e:
            self.logger.warning(f"Failed to send welcome message: {e}")

    async def _register_commands(self):
        """Register slash commands."""
        if not self.commands_enabled:
            self.logger.info("Commands are disabled, skipping registration")
            return

        @self.bot.tree.command(name="attack", description="Get information about a specific attack")
        async def attack_command(interaction: discord.Interaction, attack_id: str = None):
            await self._handle_attack_command(interaction, attack_id)

        @self.bot.tree.command(name="stats", description="Get detailed statistics about DDoS attacks")
        async def stats_command(interaction: discord.Interaction, ip: str = None):
            await self._handle_stats_command(interaction, ip)

        @self.bot.tree.command(name="history", description="Get attack history")
        async def history_command(interaction: discord.Interaction, limit: int = 5):
            await self._handle_history_command(interaction, limit)

        # Sync commands
        try:
            if self.guild_id:
                guild = discord.Object(id=int(self.guild_id))
                synced = await self.bot.tree.sync(guild=guild)
            else:
                synced = await self.bot.tree.sync()
            
            self.logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}")

    def _has_allowed_role(self, interaction: discord.Interaction) -> bool:
        """Check if user has allowed role."""
        if not self.allowed_roles:
            return True
        
        if not interaction.guild:
            self.logger.info("Command used in DM, can't check roles")
            return False
        
        if not interaction.user:
            self.logger.info("No user object available, can't check roles")
            return False

        user_roles = [str(role.id) for role in interaction.user.roles] if hasattr(interaction.user, 'roles') else []
        
        for user_role_id in user_roles:
            if user_role_id in self.allowed_roles:
                return True
        
        return False

    async def _handle_attack_command(self, interaction: discord.Interaction, attack_id: Optional[str]):
        """Handle /attack command."""
        await interaction.response.defer()

        if not self.commands_enabled:
            await interaction.followup.send("❌ Bot commands are currently disabled by the administrator.", ephemeral=True)
            return

        if not self._has_allowed_role(interaction):
            await interaction.followup.send("❌ You don't have permission to use this command. Please contact an administrator.", ephemeral=True)
            return

        if not self.neoprotect_api:
            await interaction.followup.send("⚠️ NeoProtect API client is not configured for this bot.", ephemeral=True)
            return

        try:
            if not attack_id:
                # Find current active attack
                ip_addresses = await self.neoprotect_api.get_ip_addresses()
                attack = None
                
                for ip in ip_addresses:
                    try:
                        attack = await self.neoprotect_api.get_active_attack(ip.ipv4)
                        if attack:
                            break
                    except NoActiveAttackError:
                        continue
                
                if not attack:
                    await interaction.followup.send("✅ No active attacks found.")
                    return
            else:
                await interaction.followup.send("❌ Looking up attacks by ID is not currently supported. Please use `/history` to view recent attacks.")
                return

            embed = self._create_discord_embed(attack, None, DISCORD_COLOR_BLUE, "DDoS Attack Details")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in attack command: {e}")
            await interaction.followup.send(f"❌ Failed to fetch attack information: {e}")

    async def _handle_stats_command(self, interaction: discord.Interaction, ip: Optional[str]):
        """Handle /stats command."""
        await interaction.response.defer()

        if not self.commands_enabled:
            await interaction.followup.send("❌ Bot commands are currently disabled by the administrator.", ephemeral=True)
            return

        if not self._has_allowed_role(interaction):
            await interaction.followup.send("❌ You don't have permission to use this command. Please contact an administrator.", ephemeral=True)
            return

        if not self.neoprotect_api:
            await interaction.followup.send("⚠️ NeoProtect API client is not available. Please check your configuration.", ephemeral=True)
            return

        try:
            ip_addresses = await self.neoprotect_api.get_ip_addresses()

            if not ip:
                # Show overview of all IPs
                description = ""
                
                for ip_addr in ip_addresses:
                    if not ip_addr.ipv4:
                        continue
                    
                    try:
                        attack = await self.neoprotect_api.get_active_attack(ip_addr.ipv4)
                        status = f"`🚨` Under attack since {format_time_to_local(attack.started_at)}"
                    except NoActiveAttackError:
                        status = "✅ No active attack"
                    except Exception as e:
                        status = f"❓ Error checking status: {e}"
                    
                    panel_link = f"https://panel.neoprotect.net/network/ips/{ip_addr.ipv4}?tab=attacks"
                    description += f"**IP:** `{ip_addr.ipv4}` | **Status:** {status} | [View in Panel]({panel_link})\n\n"

                if not description:
                    description = "No IP addresses found in your account."

                embed = discord.Embed(
                    title="NeoProtect Protection Status",
                    description=description,
                    color=DISCORD_COLOR_BLUE,
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Use /stats ip:<ip-address> for detailed statistics", 
                               icon_url="https://cms.mscode.pl/uploads/icon_blue_84fa10dde8.png")

                await interaction.followup.send(embed=embed)

            else:
                # Show details for specific IP
                if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
                    await interaction.followup.send("❌ Invalid IP address format. Please use dotted decimal notation (e.g., 192.168.1.1).")
                    return

                # Check if IP exists in account
                ip_exists = any(ip_addr.ipv4 == ip for ip_addr in ip_addresses)
                if not ip_exists:
                    await interaction.followup.send(f"❌ IP address `{ip}` was not found in your NeoProtect account.")
                    return

                # Get current attack status
                try:
                    current_attack = await self.neoprotect_api.get_active_attack(ip)
                except NoActiveAttackError:
                    current_attack = None

                # Get attack history
                all_attacks = []
                for page in range(20):  # Limit to 20 pages
                    try:
                        attacks = await self.neoprotect_api.get_attacks(ip, page)
                        if not attacks:
                            break
                        all_attacks.extend(attacks)
                        if len(all_attacks) >= 100:
                            break
                    except Exception as e:
                        self.logger.warning(f"Error fetching attacks for IP {ip}, page {page}: {e}")
                        break

                panel_link = f"https://panel.neoprotect.net/network/ips/{ip}?tab=attacks"
                
                description = f"## Statistics for IP: `{ip}`\n\n"
                description += f"**`🔗`** [View in NeoProtect Panel]({panel_link})\n\n"

                if current_attack and current_attack.started_at:
                    description += "**`🚨`** Current Status: Under Attack\n"
                    description += f"**Attack Start:** {format_time_to_local(current_attack.started_at)}\n"
                    description += f"**Duration:** {format_duration_readable(current_attack.duration())}\n"
                    description += f"**Peak Bandwidth:** {format_bps(current_attack.get_peak_bps())}\n"
                    description += f"**Peak Packet Rate:** {format_pps(current_attack.get_peak_pps())}\n"
                else:
                    description += "**`✅`** Current Status: No Active Attack\n"

                attack_count = len(all_attacks)
                total_message = f"{attack_count} (showing latest {attack_count})"
                if attack_count >= 100:
                    total_message = f"{attack_count}+ (showing latest {attack_count}, see panel for full history)"

                description += f"\n## Attack History\n\n"
                description += f"**Total Attacks:** {total_message}\n"

                # Calculate statistics
                total_duration = 0
                peak_bps = 0
                peak_pps = 0

                for attack in all_attacks:
                    if attack.duration():
                        total_duration += attack.duration()
                    
                    if attack.get_peak_bps() > peak_bps:
                        peak_bps = attack.get_peak_bps()
                    
                    if attack.get_peak_pps() > peak_pps:
                        peak_pps = attack.get_peak_pps()

                description += f"**Total Attack Time:** {format_duration_readable(total_duration)}\n"
                description += f"**All-Time Peak Bandwidth:** {format_bps(peak_bps)}\n"
                description += f"**All-Time Peak Packet Rate:** {format_pps(peak_pps)}\n"

                embed = discord.Embed(
                    title="NeoProtect IP Statistics",
                    description=description,
                    color=DISCORD_COLOR_BLUE,
                    url=panel_link,
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Use /history for detailed attack history",
                               icon_url="https://cms.mscode.pl/uploads/icon_blue_84fa10dde8.png")

                await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in stats command: {e}")
            await interaction.followup.send(f"❌ Failed to fetch statistics: {e}")

    async def _handle_history_command(self, interaction: discord.Interaction, limit: int):
        """Handle /history command."""
        await interaction.response.defer()

        if not self.commands_enabled:
            await interaction.followup.send("❌ Bot commands are currently disabled by the administrator.", ephemeral=True)
            return

        if not self._has_allowed_role(interaction):
            await interaction.followup.send("❌ You don't have permission to use this command. Please contact an administrator.", ephemeral=True)
            return

        if not self.neoprotect_api:
            await interaction.followup.send("⚠️ NeoProtect API client is not configured for this bot.", ephemeral=True)
            return

        # Limit the number of results
        if limit < 1:
            limit = 1
        elif limit > 20:
            limit = 20

        try:
            ip_addresses = await self.neoprotect_api.get_ip_addresses()
            all_attacks = []

            for ip_addr in ip_addresses:
                if not ip_addr.ipv4:
                    continue

                # Get attacks for this IP (multiple pages)
                for page in range(5):  # Limit to 5 pages per IP
                    try:
                        attacks = await self.neoprotect_api.get_attacks(ip_addr.ipv4, page)
                        if not attacks:
                            break
                        
                        all_attacks.extend(attacks)
                        
                        if len(all_attacks) >= limit * 3:
                            break
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch attacks for IP {ip_addr.ipv4}, page {page}: {e}")
                        break

                if len(all_attacks) >= limit * 2:
                    break

            # Sort by start time (most recent first)
            all_attacks.sort(key=lambda x: x.started_at or datetime.min, reverse=True)
            
            # Limit results
            all_attacks = all_attacks[:limit]

            description = "## Recent Attack History\n\n"

            if not all_attacks:
                description += "No attack history found."
            else:
                for i, attack in enumerate(all_attacks):
                    if not attack.started_at:
                        continue

                    status = "✅ Ended"
                    duration = "N/A"
                    panel_link = f"https://panel.neoprotect.net/network/ips/{attack.dst_address_string}?tab=attacks"

                    if attack.ended_at:
                        duration = format_duration_readable(attack.duration())
                    else:
                        status = "`🚨` Active"
                        duration = f"{format_duration_readable(attack.duration())} (ongoing)"

                    description += f"### {i+1}. Attack on {attack.dst_address_string}\n"
                    description += f"**ID:** `{attack.id}`\n"
                    description += f"**Started:** {format_time_to_local(attack.started_at)}\n"
                    description += f"**Status:** {status}\n"
                    description += f"**Duration:** {duration}\n"
                    description += f"**Peak:** {format_bps(attack.get_peak_bps())} / {format_pps(attack.get_peak_pps())}\n"
                    description += f"**Panel:** [View Details]({panel_link})\n"

                    signatures = attack.get_signature_names()
                    if signatures:
                        description += "**Signatures:** "
                        description += ", ".join(f"`{sig}`" for sig in signatures)
                        description += "\n"

                    description += "\n"

            embed = discord.Embed(
                title="NeoProtect Attack History",
                description=description,
                color=DISCORD_COLOR_BLUE,
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Showing {len(all_attacks)} most recent attacks",
                           icon_url="https://cms.mscode.pl/uploads/icon_blue_84fa10dde8.png")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in history command: {e}")
            await interaction.followup.send(f"❌ Failed to fetch attack history: {e}")

    def _create_discord_embed(self, attack: Attack, previous: Optional[Attack], color: int, title: str) -> discord.Embed:
        """Create Discord embed for attack."""
        description = ""

        if attack.started_at:
            description += "### Attack Timeline\n"
            description += f"**`🕒`** Started: {format_time_to_local(attack.started_at)}\n"

            if attack.ended_at:
                description += f"**`🛑`** Ended: {format_time_to_local(attack.ended_at)}\n"
                description += f"**`⏱️`** Duration: {format_duration_readable(attack.duration())}\n"
            else:
                description += "**`⚠️`** Status: Active\n"
                description += f"**`⏱️`** Duration: {format_duration_readable(attack.duration())}\n"

        description += "### Attack Details\n"
        target_ip = attack.dst_address_string or "unknown"
        description += f"**`🎯`** Target IP: `{target_ip}`\n"

        attack_id = attack.id or "unknown"
        description += f"**`🔍`** Attack ID: `{attack_id}`\n"

        panel_link = f"https://panel.neoprotect.net/network/ips/{target_ip}?tab=attacks"
        description += f"**`🔗`** [View in NeoProtect Panel]({panel_link})\n"

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            url=panel_link,
            timestamp=attack.started_at or datetime.now()
        )

        # Add traffic statistics field
        embed.add_field(
            name="**`📊`** Traffic Statistics",
            value=f"**Peak Bandwidth:** {format_bps(attack.get_peak_bps())}\n**Peak Packet Rate:** {format_pps(attack.get_peak_pps())}",
            inline=False
        )

        # Add signatures field
        signatures = self._format_signatures(attack)
        embed.add_field(
            name="**`🔎`** Attack Signatures",
            value=signatures,
            inline=False
        )

        # Add changes field if previous attack provided
        if previous:
            diff = attack.calculate_diff(previous)
            if diff:
                changes = ""
                
                if 'bpsPeakChange' in diff:
                    bps_change = diff['bpsPeakChange']
                    change_symbol = "`📈`" if bps_change > 0 else "`📉`"
                    changes += f"{change_symbol} **Bandwidth:** {format_bps(previous.get_peak_bps())} → {format_bps(attack.get_peak_bps())} ({calculate_percentage_change(previous.get_peak_bps(), attack.get_peak_bps()):+d}%)\n"

                if 'ppsPeakChange' in diff:
                    pps_change = diff['ppsPeakChange']
                    change_symbol = "`📈`" if pps_change > 0 else "`📉`"
                    changes += f"{change_symbol} **Packet Rate:** {format_pps(previous.get_peak_pps())} → {format_pps(attack.get_peak_pps())} ({calculate_percentage_change(previous.get_peak_pps(), attack.get_peak_pps()):+d}%)\n"

                if 'newSignatures' in diff:
                    new_sigs = diff['newSignatures']
                    changes += "**`⚠️`** New Attack Signatures:\n"
                    for sig in new_sigs:
                        changes += f"• `{sig}`\n"

                if changes:
                    embed.add_field(
                        name="**`📝`** Changes Detected",
                        value=changes,
                        inline=False
                    )

        embed.set_footer(
            text="NeoProtect Monitor Bot",
            icon_url="https://cms.mscode.pl/uploads/icon_blue_84fa10dde8.png"
        )

        return embed

    def _format_signatures(self, attack: Attack) -> str:
        """Format attack signatures."""
        names = attack.get_signature_names()
        if not names:
            return "No signatures detected"
        
        return "\n".join(f"• `{name}`" for name in names)

    async def notify_new_attack(self, attack: Attack) -> Optional[str]:
        """Notify about new attack."""
        if not self.bot:
            raise RuntimeError("Discord bot not initialized")

        try:
            channel = self.bot.get_channel(int(self.channel_id))
            if not channel:
                raise RuntimeError(f"Channel {self.channel_id} not found")

            embed = self._create_discord_embed(attack, None, DISCORD_COLOR_RED, "`🔥` New DDoS Attack Detected")
            message = await channel.send(embed=embed)
            
            # Cache message ID for future updates
            self.attack_cache[attack.id] = str(message.id)
            
            return str(message.id)

        except Exception as e:
            self.logger.error(f"Failed to send Discord message: {e}")
            raise

    async def notify_attack_update(self, attack: Attack, previous: Attack, message_id: Optional[str] = None) -> None:
        """Notify about attack update."""
        if not self.bot:
            raise RuntimeError("Discord bot not initialized")

        try:
            channel = self.bot.get_channel(int(self.channel_id))
            if not channel:
                raise RuntimeError(f"Channel {self.channel_id} not found")

            embed = self._create_discord_embed(attack, previous, DISCORD_COLOR_YELLOW, "`📶` DDoS Attack Updated")

            # Use cached message ID if not provided
            if not message_id:
                message_id = self.attack_cache.get(attack.id)

            if message_id:
                try:
                    message = await channel.fetch_message(int(message_id))
                    await message.edit(embed=embed)
                    return
                except discord.NotFound:
                    # Message not found, send new one
                    pass

            # Send new message if editing failed
            message = await channel.send(embed=embed)
            self.attack_cache[attack.id] = str(message.id)

        except Exception as e:
            self.logger.error(f"Failed to update Discord message: {e}")
            raise

    async def notify_attack_ended(self, attack: Attack, message_id: Optional[str] = None) -> None:
        """Notify about attack end."""
        if not self.bot:
            raise RuntimeError("Discord bot not initialized")

        try:
            channel = self.bot.get_channel(int(self.channel_id))
            if not channel:
                raise RuntimeError(f"Channel {self.channel_id} not found")

            embed = self._create_discord_embed(attack, None, DISCORD_COLOR_GREEN, "`🚀` DDoS Attack Ended")

            # Use cached message ID if not provided
            if not message_id:
                message_id = self.attack_cache.get(attack.id)

            if message_id:
                try:
                    message = await channel.fetch_message(int(message_id))
                    await message.edit(embed=embed)
                    # Remove from cache after attack ends
                    self.attack_cache.pop(attack.id, None)
                    return
                except discord.NotFound:
                    # Message not found, send new one
                    pass

            # Send new message if editing failed
            await channel.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Failed to send attack ended message: {e}")
            raise

    def set_api_client(self, client: NeoProtectClient) -> None:
        """Set the NeoProtect API client."""
        self.neoprotect_api = client

    async def shutdown(self) -> None:
        """Shutdown the Discord bot."""
        if self.bot:
            self.logger.info("Shutting down Discord bot...")
            
            # Close NeoProtect API client if it exists
            if self.neoprotect_api:
                await self.neoprotect_api.close()
            
            # Close the bot
            await self.bot.close()
            self.logger.info("Discord bot integration shutdown complete")