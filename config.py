"""
Configuration settings for Network Monitor
macOS-optimized settings for packet capture and monitoring
"""

import os

# Network Interface Settings
# macOS uses 'en0' for primary WiFi/Ethernet interface
# You can check your interfaces using: ifconfig or networksetup -listallhardwareports
NETWORK_INTERFACE = "en0"

# Alternative interfaces you might need:
# - en1: Secondary network interface (if available)
# - lo0: Loopback interface (localhost traffic)
# - awdl0: Apple Wireless Direct Link (AirDrop, etc.)

# Database Settings
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "network_monitor.db")

# Packet Capture Settings
# BPF (Berkeley Packet Filter) for efficient packet filtering
# Filter for TCP and UDP only (most common protocols)
PACKET_FILTER = "tcp or udp"

# Maximum number of packets to capture (0 = unlimited)
MAX_PACKETS = 0

# Packet capture timeout (seconds)
CAPTURE_TIMEOUT = 1

# Dashboard Settings
DASHBOARD_PORT = 8501
DASHBOARD_REFRESH_RATE = 2  # seconds

# Data Aggregation Settings
MAX_RECENT_PACKETS = 100  # Number of recent packets to keep in memory
MAX_CACHED_DNS = 1000  # Maximum DNS cache entries
PROCESS_CACHE_SIZE = 500  # Maximum process mapping cache entries

# Bandwidth Calculation
BANDWIDTH_WINDOW = 5  # seconds - rolling window for rate calculation

# Thread Settings
SNIFFER_QUEUE_SIZE = 1000  # Maximum queue size for packet processing
BATCH_INSERT_SIZE = 10  # Number of records to batch before database insert

# macOS Specific Settings
REQUIRES_SUDO = True  # Packet capture requires root privileges on macOS

# DNS Resolution
DNS_TIMEOUT = 2  # seconds - timeout for reverse DNS lookup

# Category Keywords for Traffic Classification
CATEGORY_KEYWORDS = {
    "Streaming": [
        "youtube", "youtu.be", "netflix", "hulu", "spotify", "twitch",
        "vimeo", "dailymotion", "soundcloud", "tidal", "pandora",
        "disneyplus", "hbomax", "primevideo", "appletv"
    ],
    "Social Media": [
        "facebook", "fb.com", "instagram", "twitter", "tiktok",
        "linkedin", "reddit", "snapchat", "pinterest", "whatsapp",
        "telegram", "discord", "slack"
    ],
    "Development": [
        "github", "gitlab", "bitbucket", "stackoverflow", "stackexchange",
        "npmjs", "pypi", "docker", "kubernetes", "jenkins"
    ],
    "Cloud Services": [
        "amazonaws", "aws", "azure", "googlecloud", "gcp",
        "cloudflare", "digitalocean", "heroku", "vercel"
    ],
    "Shopping": [
        "amazon", "ebay", "shopify", "etsy", "walmart",
        "alibaba", "aliexpress", "target"
    ],
    "Communication": [
        "zoom", "teams", "meet.google", "webex", "skype",
        "gotomeeting", "bluejeans"
    ],
    "Gaming": [
        "steam", "epicgames", "origin", "battle.net", "playstation",
        "xbox", "nintendo", "twitch"
    ],
    "News": [
        "nytimes", "cnn", "bbc", "reuters", "bloomberg",
        "theguardian", "wsj", "washingtonpost"
    ],
    "Apple Services": [
        "apple.com", "icloud", "itunes", "appstore", "apple-dns"
    ]
}

# Logging
ENABLE_LOGGING = True
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
