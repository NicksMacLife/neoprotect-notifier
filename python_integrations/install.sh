#!/bin/bash
# Installation script for NeoProtect Python Discord Bot

set -e

echo "🤖 Installing NeoProtect Python Discord Bot..."

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
min_version="3.8"

if [[ "$(printf '%s\n' "$min_version" "$python_version" | sort -V | head -n1)" != "$min_version" ]]; then
    echo "❌ Error: Python $min_version or higher required. Found Python $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Create config if it doesn't exist
if [[ ! -f "config.json" ]]; then
    echo "📝 Creating config.json from example..."
    cp config.example.json config.json
    echo "⚠️  Please edit config.json with your settings before running the bot"
else
    echo "✅ config.json already exists"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.json with your Discord bot token and NeoProtect API key"
echo "2. Run the bot: python3 main.py --config config.json"
echo ""
echo "For detailed setup instructions, see README.md"