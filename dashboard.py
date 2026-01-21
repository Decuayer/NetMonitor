"""
Enhanced Real-time Network Monitoring Dashboard
Built with Streamlit with advanced analytics and filtering capabilities
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import sys
import os
from collections import Counter

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_aggregator import get_aggregator
from database import NetworkDatabase


# Page configuration
st.set_page_config(
    page_title="Network Monitor Pro",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .unknown-section {
        background-color: #fff3cd;
        padding: 0.8rem;
        border-radius: 0.3rem;
        border-left: 4px solid #ffc107;
    }
    </style>
""", unsafe_allow_html=True)


def format_bytes(bytes_val):
    """Convert bytes to human-readable format"""
    if bytes_val is None or bytes_val == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"


def format_timestamp(ts):
    """Convert Unix timestamp to readable format"""
    return datetime.fromtimestamp(ts).strftime('%H:%M:%S')


def smooth_bandwidth_data(data_points, window_size=5):
    """
    Apply moving average smoothing to bandwidth data.
    
    Args:
        data_points: List of data values
        window_size: Size of moving average window
        
    Returns:
        Smoothed data as numpy array
    """
    if len(data_points) < window_size:
        return np.array(data_points)
    
    # Calculate moving average
    weights = np.ones(window_size) / window_size
    smoothed = np.convolve(data_points, weights, mode='valid')
    
    # Pad the beginning to maintain array length
    padding = np.full(window_size - 1, smoothed[0])
    return np.concatenate([padding, smoothed])


def categorize_unknown_app(dest_ip, dest_hostname):
    """
    Attempt to categorize Unknown apps based on destination.
    
    Args:
        dest_ip: Destination IP address
        dest_hostname: Resolved hostname
        
    Returns:
        Best guess app name or 'Unknown'
    """
    if not dest_hostname or dest_hostname == 'Local Network':
        # Check for common IP patterns
        if dest_ip.startswith('192.168.') or dest_ip.startswith('10.'):
            return 'Local Network'
        return 'Unknown'
    
    hostname_lower = dest_hostname.lower()
    
    # Common service patterns
    patterns = {
        'google': 'Google Services',
        'gstatic': 'Google Services',
        'apple': 'Apple Services',
        'icloud': 'Apple Services',
        'microsoft': 'Microsoft Services',
        'amazonaws': 'AWS Services',
        'cloudfront': 'CDN Services',
        'akamai': 'CDN Services',
        'facebook': 'Meta Services',
        'instagram': 'Meta Services',
    }
    
    for pattern, service in patterns.items():
        if pattern in hostname_lower:
            return service
    
    return 'Unknown'


def main():
    """Main dashboard application"""
    
    # Title
    st.markdown('<div class="main-header">🌐 Network Monitor Pro</div>', 
                unsafe_allow_html=True)
    
    # Get data sources
    aggregator = get_aggregator()
    db = NetworkDatabase()
    
    # Check if we have live data or need to use database
    stats = aggregator.get_current_stats()
    has_live_data = stats['total_packets'] > 0
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Data source indicator
        if has_live_data:
            st.success("📡 Live Data Active")
            st.caption("Monitor.py is running")
        else:
            st.warning("📊 Database Mode")
            st.caption("Showing historical data")
            st.caption("Start monitor.py for live updates")
        
        st.divider()
        
        # Time range filter
        st.subheader("📅 Time Range")
        time_filter = st.selectbox(
            "Show data from",
            ["All Time", "Last Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days"],
            index=0
        )
        
        # Refresh rate
        refresh_rate = st.slider("Refresh Rate (seconds)", 1, 10, 2)
        
        # Display options
        st.subheader("Display Options")
        show_recent_count = st.number_input("Recent Connections", 10, 100, 50, 10)
        show_top_apps = st.number_input("Top Apps", 5, 20, 10, 5)
        show_unknown = st.checkbox("Show Unknown Apps Detail", value=True)
        
        # Database stats
        st.subheader("📊 Database Stats")
        total_connections = db.get_connection_count()
        total_db_bandwidth = db.get_total_bandwidth()
        st.metric("Total Records", f"{total_connections:,}")
        st.metric("Total Bandwidth (DB)", format_bytes(total_db_bandwidth))
        
        # Actions
        st.subheader("🔧 Actions")
        if st.button("Reset Live Stats"):
            aggregator.reset_stats()
            st.success("Statistics reset!")
            time.sleep(1)
            st.rerun()
    
    # Apply time filter
    cutoff_time = None
    if time_filter != "All Time":
        time_map = {
            "Last Hour": 1,
            "Last 6 Hours": 6,
            "Last 24 Hours": 24,
            "Last 7 Days": 168
        }
        hours = time_map.get(time_filter, 0)
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
    
    # Get filtered statistics
    if has_live_data:
        total_bandwidth = stats['total_bandwidth']
        total_packets = stats['total_packets']
        current_rate = stats['current_rate']
        packets_per_second = stats['packets_per_second']
        active_apps = stats['active_apps']
        uptime = stats['uptime']
        total_upload = stats['total_upload']
        total_download = stats['total_download']
    else:
        # Use database data with time filter
        if cutoff_time:
            filtered_data = db.get_connections_by_timerange(cutoff_time, datetime.now().timestamp())
            total_bandwidth = sum(c['packet_size'] for c in filtered_data)
            total_packets = len(filtered_data)
        else:
            total_bandwidth = total_db_bandwidth
            total_packets = total_connections
        
        current_rate = 0
        packets_per_second = 0
        active_apps = len(db.get_top_apps_by_bandwidth(limit=100))
        uptime = 0
        total_upload = 0
        total_download = 0
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Total Bandwidth",
            value=format_bytes(total_bandwidth),
            delta=f"{format_bytes(current_rate)}/s" if has_live_data else None
        )
    
    with col2:
        st.metric(
            label="📦 Total Packets",
            value=f"{total_packets:,}",
            delta=f"{packets_per_second:.1f}/s" if has_live_data else None
        )
    
    with col3:
        st.metric(
            label="📱 Active Apps",
            value=active_apps
        )
    
    with col4:
        if has_live_data:
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            seconds = int(uptime % 60)
            uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            st.metric(label="⏱️ Uptime", value=uptime_str)
        else:
            st.metric(label="📅 Mode", value="Historical")
    
    # Upload/Download stats (only for live data)
    if has_live_data:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("⬆️ Upload", format_bytes(total_upload))
        with col2:
            st.metric("⬇️ Download", format_bytes(total_download))
    
    st.divider()
    
    # Bandwidth history chart with smoothing
    st.subheader("📈 Bandwidth Monitor (Smoothed)")
    
    if has_live_data:
        bandwidth_history = aggregator.get_bandwidth_history()
        
        if bandwidth_history and len(bandwidth_history) > 1:
            chart_data = pd.DataFrame(bandwidth_history)
            chart_data['timestamp'] = pd.to_datetime(chart_data['timestamp'], unit='s')
            chart_data['rate_kb'] = chart_data['rate'] / 1024
            
            # Apply smoothing
            smoothed_rate = smooth_bandwidth_data(chart_data['rate_kb'].values, window_size=5)
            chart_data['smoothed_rate_kb'] = smoothed_rate
            
            # Create chart with both original and smoothed data
            st.line_chart(
                chart_data.set_index('timestamp')[['smoothed_rate_kb']],
                use_container_width=True
            )
            st.caption("📊 Smoothed bandwidth using 5-point moving average (KB/s)")
        else:
            st.info("Collecting bandwidth data... Please wait.")
    else:
        # Historical mode - aggregate data
        recent_data = db.get_recent_connections(limit=200)
        if recent_data:
            df = pd.DataFrame(recent_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df['size_kb'] = df['packet_size'] / 1024
            
            # Group by 10-second intervals
            df_grouped = df.groupby(df['timestamp'].dt.floor('10s'))['size_kb'].sum().reset_index()
            
            # Apply smoothing
            if len(df_grouped) > 3:
                smoothed = smooth_bandwidth_data(df_grouped['size_kb'].values, window_size=3)
                df_grouped['smoothed_kb'] = smoothed
                
                st.line_chart(
                    df_grouped.set_index('timestamp')['smoothed_kb']
                )
                st.caption("📊 Historical bandwidth (smoothed, 10-second intervals)")
            else:
                st.line_chart(df_grouped.set_index('timestamp')['size_kb'])
                st.caption("📊 Historical bandwidth (10-second intervals)")
        else:
            st.info("No data available in database")
    
    st.divider()
    
    # Three columns: Apps, Categories, Destinations
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🏆 Top Apps")
        
        if has_live_data:
            top_apps = aggregator.get_top_apps(limit=show_top_apps)
        else:
            top_apps = db.get_top_apps_by_bandwidth(limit=show_top_apps)
        
        if top_apps:
            # Filter and enhance Unknown apps
            enhanced_apps = []
            unknown_details = []
            
            for app_name, bytes_val in top_apps:
                if app_name == 'Unknown' and show_unknown:
                    # Get details for unknown connections
                    unknown_connections = [c for c in (aggregator.get_recent_packets(100) if has_live_data 
                                                      else db.get_recent_connections(100))
                                          if c.get('app_name') == 'Unknown']
                    
                    # Try to categorize
                    for conn in unknown_connections[:5]:
                        best_guess = categorize_unknown_app(
                            conn.get('dest_ip', ''),
                            conn.get('dest_hostname', '')
                        )
                        unknown_details.append({
                            'destination': conn.get('dest_hostname') or conn.get('dest_ip'),
                            'guess': best_guess,
                            'bytes': conn.get('packet_size', 0)
                        })
                
                enhanced_apps.append((app_name, bytes_val))
            
            # Create DataFrame
            apps_df = pd.DataFrame(enhanced_apps, columns=['Application', 'Bytes'])
            apps_df['Bandwidth'] = apps_df['Bytes'].apply(format_bytes)
            
            # Bar chart
            st.bar_chart(apps_df.set_index('Application')['Bytes'])
            
            # Table
            st.dataframe(
                apps_df[['Application', 'Bandwidth']],
                width='stretch',
                hide_index=True
            )
            
            # Show Unknown app details if enabled
            if show_unknown and unknown_details:
                with st.expander("🔍 Unknown Apps Analysis", expanded=False):
                    st.markdown('<div class="unknown-section">', unsafe_allow_html=True)
                    st.write("**Possible categorization based on destinations:**")
                    unknown_df = pd.DataFrame(unknown_details)
                    if not unknown_df.empty:
                        summary = unknown_df.groupby('guess').size().reset_index(name='connections')
                        st.dataframe(summary, width='stretch', hide_index=True)
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No application data yet...")
    
    with col2:
        st.subheader("📂 Categories")
        
        if has_live_data:
            category_data = aggregator.get_bandwidth_by_category()
        else:
            category_data = db.get_bandwidth_by_category()
        
        if category_data:
            cat_df = pd.DataFrame(category_data, columns=['Category', 'Bytes'])
            cat_df['Bandwidth'] = cat_df['Bytes'].apply(format_bytes)
            
            st.bar_chart(cat_df.set_index('Category')['Bytes'])
            
            st.dataframe(
                cat_df[['Category', 'Bandwidth']],
                width='stretch',
                hide_index=True
            )
        else:
            st.info("No category data yet...")
    
    with col3:
        st.subheader("🎯 Top Destinations")
        
        # Get recent connections for destination analysis
        recent = aggregator.get_recent_packets(100) if has_live_data else db.get_recent_connections(100)
        
        if recent:
            # Count destinations
            dest_counter = Counter()
            dest_bytes = {}
            
            for conn in recent:
                dest = conn.get('dest_hostname') or conn.get('dest_ip', 'Unknown')
                size = conn.get('packet_size', 0)
                dest_counter[dest] += 1
                dest_bytes[dest] = dest_bytes.get(dest, 0) + size
            
            # Get top destinations by bandwidth
            top_dests = sorted(dest_bytes.items(), key=lambda x: x[1], reverse=True)[:10]
            
            if top_dests:
                dest_df = pd.DataFrame(top_dests, columns=['Destination', 'Bytes'])
                dest_df['Bandwidth'] = dest_df['Bytes'].apply(format_bytes)
                
                st.bar_chart(dest_df.set_index('Destination')['Bytes'])
                
                st.dataframe(
                    dest_df[['Destination', 'Bandwidth']],
                    width='stretch',
                    hide_index=True
                )
        else:
            st.info("No destination data yet...")
    
    st.divider()
    
    # Protocol Distribution
    st.subheader("📡 Protocol Distribution & Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Protocol breakdown
        recent = aggregator.get_recent_packets(100) if has_live_data else db.get_recent_connections(100)
        
        if recent:
            protocol_counter = Counter(conn.get('protocol', 'Unknown') for conn in recent)
            protocol_df = pd.DataFrame(protocol_counter.items(), columns=['Protocol', 'Count'])
            
            st.bar_chart(protocol_df.set_index('Protocol')['Count'])
            st.caption("Protocol distribution in recent traffic")
        else:
            st.info("No protocol data available")
    
    with col2:
        # Connection statistics
        st.write("**Connection Statistics:**")
        
        if recent:
            unique_ips = len(set(conn.get('dest_ip') for conn in recent))
            unique_apps = len(set(conn.get('app_name') for conn in recent if conn.get('app_name') != 'Unknown'))
            avg_packet_size = np.mean([conn.get('packet_size', 0) for conn in recent])
            
            stats_data = {
                "Metric": ["Unique Destinations", "Unique Apps", "Avg Packet Size"],
                "Value": [unique_ips, unique_apps, format_bytes(avg_packet_size)]
            }
            st.dataframe(pd.DataFrame(stats_data), width='stretch', hide_index=True)
        else:
            st.info("No statistics available")
    
    st.divider()
    
    # Recent connections table
    st.subheader("🔄 Recent Connections")
    
    if has_live_data:
        recent_packets = aggregator.get_recent_packets(limit=show_recent_count)
    else:
        recent_packets = db.get_recent_connections(limit=show_recent_count)
    
    if recent_packets:
        # Prepare DataFrame
        if not has_live_data:
            df = pd.DataFrame(recent_packets)
        else:
            recent_packets_reversed = list(reversed(recent_packets))
            df = pd.DataFrame(recent_packets_reversed)
        
        # Format columns
        if 'timestamp' in df.columns:
            df['Time'] = df['timestamp'].apply(format_timestamp)
        
        # Enhance Unknown app names
        if 'app_name' in df.columns and 'dest_hostname' in df.columns:
            df['Enhanced App'] = df.apply(
                lambda row: categorize_unknown_app(row.get('dest_ip', ''), row.get('dest_hostname', ''))
                if row.get('app_name') == 'Unknown' else row.get('app_name'),
                axis=1
            )
        
        display_columns = []
        column_config = {}
        
        if 'Time' in df.columns:
            display_columns.append('Time')
        if 'Enhanced App' in df.columns:
            display_columns.append('Enhanced App')
            column_config['Enhanced App'] = st.column_config.TextColumn('Application')
        elif 'app_name' in df.columns:
            display_columns.append('app_name')
            column_config['app_name'] = st.column_config.TextColumn('Application')
        
        if 'dest_hostname' in df.columns:
            display_columns.append('dest_hostname')
            column_config['dest_hostname'] = st.column_config.TextColumn('Destination')
        if 'category' in df.columns:
            display_columns.append('category')
            column_config['category'] = st.column_config.TextColumn('Category')
        if 'protocol' in df.columns:
            display_columns.append('protocol')
            column_config['protocol'] = st.column_config.TextColumn('Protocol')
        if 'packet_size' in df.columns:
            df['Size'] = df['packet_size'].apply(format_bytes)
            display_columns.append('Size')
        
        # Display table
        st.dataframe(
            df[display_columns] if display_columns else df,
            width='stretch',
            hide_index=True,
            column_config=column_config
        )
    else:
        if has_live_data:
            st.info("No connections captured yet. Make sure the packet sniffer is running.")
        else:
            st.info("No connections in database yet.")
    
    # Auto-refresh
    time.sleep(refresh_rate)
    st.rerun()


if __name__ == "__main__":
    main()
