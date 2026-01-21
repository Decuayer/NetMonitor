#!/bin/bash

# Network Monitor - Quick Start Script
# This script helps you get started with the Network Monitor

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║      🌐 Network Monitor - Quick Start Setup 🌐           ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This tool is designed for macOS only."
    exit 1
fi

echo "📋 Checking system requirements..."
echo ""

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "✅ Python 3 found: $PYTHON_VERSION"
else
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    echo "✅ pip3 found"
else
    echo "❌ pip3 not found. Please install pip."
    exit 1
fi

echo ""
echo "📦 Installing dependencies..."
echo ""

# Install requirements
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All dependencies installed successfully!"
else
    echo ""
    echo "❌ Failed to install dependencies. Please check the error above."
    exit 1
fi

echo ""
echo "🔍 Checking network interface..."
echo ""

# List available interfaces
echo "Available network interfaces:"
ifconfig | grep "^[a-z]" | cut -d: -f1 | while read iface; do
    echo "  - $iface"
done

echo ""
echo "✅ Setup complete!"
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    📖 QUICK START GUIDE                   ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Step 1: Start the Network Monitor (requires sudo)"
echo "  $ sudo python3 monitor.py"
echo ""
echo "Step 2: In a new terminal, start the Dashboard"
echo "  $ streamlit run dashboard.py"
echo ""
echo "Step 3: Open your browser and navigate to:"
echo "  http://localhost:8501"
echo ""
echo "⚠️  IMPORTANT NOTES:"
echo "  • The monitor MUST be run with sudo on macOS"
echo "  • Make sure en0 is your active network interface"
echo "  • Check config.py to change the interface if needed"
echo ""
echo "📚 For more information, see README.md"
echo ""
echo "🌐 Happy Monitoring! 🌐"
echo ""
