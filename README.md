# 🌐 Network Monitor for macOS

A comprehensive network monitoring and analysis tool for macOS, similar to GlassWire or Little Snitch. Monitor real-time network traffic, identify bandwidth-consuming applications, and visualize your network activity with an elegant dashboard.

![Network Monitor](https://img.shields.io/badge/Platform-macOS-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- 🔍 **Real-time Packet Capture**: Monitor all TCP/UDP traffic on your macOS system
- 📊 **Application Tracking**: Identify which apps are consuming bandwidth
- 🌐 **DNS Resolution**: Automatically resolve IP addresses to hostnames
- 🏷️ **Smart Categorization**: Categorize traffic (Streaming, Social Media, Development, etc.)
- 💾 **SQLite Database**: Store historical data for analysis
- 📈 **Live Dashboard**: Beautiful real-time web dashboard using Streamlit
- 🎯 **macOS Optimized**: Specifically designed for macOS networking stack

## 🖼️ Screenshots

### Dashboard Overview
The dashboard provides real-time insights into your network activity:
- Live bandwidth monitoring
- Top applications by traffic
- Recent connections with details
- Category-based traffic analysis

## 🔧 Requirements

- **Operating System**: macOS (tested on macOS 10.15+)
- **Python**: 3.8 or higher
- **Permissions**: sudo/root access (required for packet capture)

## 📦 Installation

### 1. Clone or navigate to the project directory

```bash
cd /NetMonitor
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install scapy>=2.5.0 psutil>=5.9.0 streamlit>=1.30.0 pandas>=2.0.0
```

### 3. Verify installation

```bash
python -c "import scapy, psutil, streamlit; print('All dependencies installed!')"
```

## 🚀 Usage

### Step 1: Start the Network Monitor (Backend)

The monitor must run with **sudo** privileges to capture packets:

```bash
sudo python monitor.py
```

You should see output like:

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           🌐 Network Monitor for macOS 🌐                ║
║                                                           ║
║     Real-time Network Traffic Analysis & Monitoring       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

✅ Network Monitor is now running!
📊 Dashboard: Start with 'streamlit run dashboard.py'
💾 Database: /path/to/network_monitor.db
⏹️  Stop: Press Ctrl+C
```

### Step 2: Start the Dashboard (Frontend)

In a **separate terminal** (no sudo required):

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Step 3: Monitor Your Network

- Generate some network activity (browse websites, stream videos, etc.)
- Watch the dashboard update in real-time
- Explore bandwidth usage by application and category

## 🏗️ Architecture

```
┌─────────────────┐
│ Packet Sniffer  │  ← Captures packets using scapy (en0 interface)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Packet Processor│  ← Enriches with process info, DNS, category
└────────┬────────┘
         │
         ├──────────────┐
         ▼              ▼
┌─────────────┐  ┌──────────────┐
│  Database   │  │ Aggregator   │  ← Real-time stats
│  (SQLite)   │  │ (In-Memory)  │
└─────────────┘  └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │  Dashboard   │  ← Streamlit UI
                 │ (Web Browser)│
                 └──────────────┘
```

## 📁 Project Structure

```
NetMonitor/
├── monitor.py           # Main application entry point
├── packet_sniffer.py    # Packet capture using scapy
├── process_mapper.py    # Maps ports to applications (psutil/lsof)
├── dns_resolver.py      # DNS resolution and categorization
├── database.py          # SQLite database operations
├── data_aggregator.py   # Real-time data aggregation
├── dashboard.py         # Streamlit web dashboard
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
└── network_monitor.db   # SQLite database (created on first run)
```

## ⚙️ Configuration

Edit `config.py` to customize settings:

```python
# Network interface (check with: ifconfig)
NETWORK_INTERFACE = "en0"  # WiFi/Ethernet on macOS

# Dashboard refresh rate
DASHBOARD_REFRESH_RATE = 2  # seconds

# Packet capture filter
PACKET_FILTER = "tcp or udp"  # BPF filter syntax

# Database path
DATABASE_PATH = "network_monitor.db"
```

### Finding Your Network Interface

```bash
ifconfig | grep "^[a-z]" | cut -d: -f1
```

Common macOS interfaces:
- `en0`: Primary WiFi/Ethernet
- `en1`: Secondary network adapter
- `lo0`: Loopback (localhost)

## 🔍 How It Works

### 1. Packet Capture
The `PacketSniffer` uses **scapy** to capture network packets at the interface level. On macOS, this requires sudo permissions to access the BPF (Berkeley Packet Filter).

### 2. Process Mapping
The `ProcessMapper` uses **psutil** and **lsof** to map network connections to specific processes:
- `psutil.net_connections()`: Gets active connections with PIDs
- `lsof -i :PORT`: Fallback for reliable port-to-process mapping

### 3. DNS Resolution
The `DNSResolver` performs reverse DNS lookups to convert IP addresses to hostnames and categorizes traffic based on domain keywords.

### 4. Data Storage
All captured traffic is stored in a **SQLite** database for historical analysis. The database includes indexes for efficient querying.

### 5. Real-time Dashboard
The **Streamlit** dashboard reads from both the in-memory aggregator (for live stats) and the database (for historical data), updating automatically every few seconds.

## 🐛 Troubleshooting

### Permission Denied Error

```
ERROR: Packet capture requires sudo permissions on macOS
```

**Solution**: Run with sudo:
```bash
sudo python monitor.py
```

### Interface Not Found

```
ERROR: Interface 'en0' not found
```

**Solution**: Check your network interface:
```bash
ifconfig
# Update config.py with the correct interface name
```

### No Packets Captured

1. **Check if monitor is running with sudo**
2. **Verify interface is active**: `ifconfig en0`
3. **Generate network traffic**: Open a browser, stream a video
4. **Check firewall settings**: System Preferences → Security & Privacy → Firewall

### Dashboard Not Updating

1. **Ensure monitor.py is running**
2. **Check that packets are being captured** (watch terminal output)
3. **Refresh browser page**
4. **Verify dashboard refresh rate** in sidebar settings

### Missing Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install individually
pip install scapy psutil streamlit pandas
```

## 🔒 Security & Privacy

- ⚠️ **This tool captures network traffic**: Use responsibly and only on networks you own or have permission to monitor
- 🔐 **Requires root access**: Packet capture needs elevated privileges
- 💾 **Data is stored locally**: All captured data remains on your machine
- 🚫 **No external connections**: The tool doesn't send data anywhere

## 🎯 Use Cases

- 📊 **Bandwidth Monitoring**: Track which apps use the most data
- 🔍 **Network Debugging**: Identify unexpected connections
- 📈 **Usage Analysis**: Understand your network patterns
- 🎓 **Learning Tool**: Study network protocols and traffic patterns
- 🔐 **Security**: Detect suspicious outbound connections

## 🛠️ Advanced Usage

### Custom Categories

Edit `config.py` to add custom category keywords:

```python
CATEGORY_KEYWORDS = {
    "Streaming": ["youtube", "netflix", "twitch"],
    "Custom Category": ["example.com", "myservice"],
    # Add more categories...
}
```

### Database Queries

Access the SQLite database directly:

```bash
sqlite3 network_monitor.db

# Example queries
SELECT app_name, SUM(packet_size) as total FROM connections GROUP BY app_name;
SELECT category, COUNT(*) FROM connections GROUP BY category;
```

### Export Data

```bash
# Export to CSV
sqlite3 -header -csv network_monitor.db "SELECT * FROM connections;" > export.csv
```

## 📝 Known Limitations

- **macOS Only**: Designed specifically for macOS (uses BPF, lsof)
- **Requires sudo**: Cannot run without elevated privileges
- **TCP/UDP Only**: Other protocols (ICMP, etc.) are not captured
- **DNS Caching**: Some DNS lookups may be cached, affecting categorization
- **Process Resolution**: Encrypted traffic (HTTPS) doesn't reveal application details beyond the process name

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Support for additional network protocols
- Enhanced traffic categorization
- Export/reporting features
- Performance optimizations
- Cross-platform support

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **scapy**: Powerful packet manipulation library
- **psutil**: Cross-platform process and system utilities
- **Streamlit**: Beautiful web app framework
- **macOS**: BPF packet capture interface

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify you're running with sudo
3. Ensure all dependencies are installed
4. Check that your network interface is correct

---

**Made with ❤️ for macOS network monitoring**

🌐 Happy Monitoring! 🌐
