# NeoProtect Discord Bot (Python Implementation)

This is a Python rewrite of the Discord bot integration for NeoProtect attack monitoring using the `discord.py` library.

## Features

- **Discord Bot Commands**:
  - `/attack [id]` - Get information about a specific attack or current active attack
  - `/stats [ip]` - Get detailed statistics about DDoS attacks for specific IP or all IPs
  - `/history [limit]` - Get attack history (default limit: 5, max: 20)

- **Attack Notifications**:
  - Real-time notifications for new attacks
  - Live updates of ongoing attacks with edited embeds
  - End-of-attack notifications

- **Role-based Permissions**: Configure allowed roles for command usage
- **Rich Discord Embeds**: Beautiful attack information with links to NeoProtect panel

## Requirements

- Python 3.8+
- discord.py 2.3.0+
- aiohttp 3.8.0+
- python-dateutil 2.8.0+

## Installation

1. **Install Python dependencies**:
   ```bash
   cd python_integrations
   pip install -r requirements.txt
   ```

2. **Or install using setup.py**:
   ```bash
   cd python_integrations
   pip install -e .
   ```

## Configuration

1. **Copy the example configuration**:
   ```bash
   cp config.example.json config.json
   ```

2. **Edit the configuration file**:
   ```json
   {
      "apiKey": "your-neoprotect-api-key",
      "apiEndpoint": "https://api.neoprotect.net/v2",
      "pollIntervalSeconds": 60,
      "monitorMode": "all",
      "enabledIntegrations": ["discord_bot"],
      "integrationConfigs": {
         "discord_bot": {
            "token": "YOUR_DISCORD_BOT_TOKEN",
            "clientId": "YOUR_DISCORD_CLIENT_ID",
            "guildId": "YOUR_DISCORD_GUILD_ID",
            "channelId": "YOUR_DISCORD_CHANNEL_ID",
            "commandsEnabled": true,
            "allowedRoles": ["ROLE_ID_1", "ROLE_ID_2"]
         }
      }
   }
   ```

### Configuration Options

- `token` (required): Discord bot token
- `clientId` (optional): Discord application client ID (required for slash commands)
- `guildId` (optional): Discord server ID for guild-specific commands
- `channelId` (required): Discord channel ID for notifications
- `commandsEnabled` (optional): Enable/disable slash commands (default: `true`)
- `allowedRoles` (optional): Array of role IDs allowed to use bot commands. If not set, all users can use commands

## Usage

### Running the Bot

```bash
cd python_integrations
python main.py --config config.json
```

### Available Commands

- **`/attack [id]`** - Get information about a specific attack or current active attack
- **`/stats [ip]`** - Get detailed statistics about DDoS attacks for specific IP or all IPs  
- **`/history [limit]`** - Get attack history (default limit: 5, max: 20)

### Setting Up Discord Bot

1. **Create a Discord Application**:
   - Go to https://discord.com/developers/applications
   - Click "New Application"
   - Give it a name and create it

2. **Create a Bot**:
   - Go to the "Bot" section
   - Click "Add Bot"
   - Copy the token for your configuration

3. **Set Bot Permissions**:
   - Go to the "OAuth2" → "URL Generator" section
   - Select "bot" and "applications.commands" scopes
   - Select these bot permissions:
     - Send Messages
     - Use Slash Commands
     - Embed Links
     - Read Message History

4. **Invite Bot to Server**:
   - Use the generated URL to invite the bot to your Discord server
   - Make sure the bot has permissions to post in your target channel

## Differences from Go Implementation

This Python implementation provides the same functionality as the original Go version but with these improvements:

- **Modern async/await syntax** for better performance
- **discord.py library** which is more actively maintained than discordgo
- **Better error handling** with more descriptive error messages
- **Cleaner code structure** with better separation of concerns
- **Type hints** for better code maintainability

## Logging

The bot creates logs in `discord_bot.log` and also outputs to console. Log levels can be configured by modifying the logging setup in `main.py`.

## Development

To contribute to this Python implementation:

1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

2. Run the bot in development mode:
   ```bash
   python main.py --config config.json
   ```

## Troubleshooting

### Common Issues

1. **Bot doesn't respond to commands**:
   - Check if the bot has proper permissions in the Discord server
   - Verify the bot token is correct
   - Ensure slash commands are synced (check bot logs)

2. **Commands show "You don't have permission"**:
   - Check if your role ID is in the `allowedRoles` list
   - If `allowedRoles` is empty, all users should have access

3. **API errors**:
   - Verify your NeoProtect API key is correct
   - Check if the API endpoint is accessible
   - Look for rate limiting messages in logs

4. **Import errors**:
   - Make sure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version (3.8+ required)

## Support

For issues specific to this Python implementation, please check the logs and ensure your configuration is correct. For NeoProtect API issues, consult the NeoProtect documentation.