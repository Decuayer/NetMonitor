"""
Data Aggregator Module
Thread-safe aggregation of network traffic data for real-time dashboard
Maintains circular buffers and calculates bandwidth statistics
"""

import threading
from collections import deque, defaultdict
from typing import Dict, List, Tuple
import time
import config


class DataAggregator:
    """
    Thread-safe data aggregator for real-time network statistics.
    Maintains recent packet history and calculates bandwidth metrics.
    """
    
    def __init__(self):
        """Initialize data aggregator with thread-safe structures"""
        self.lock = threading.Lock()
        
        # Recent packets (circular buffer)
        self.recent_packets = deque(maxlen=config.MAX_RECENT_PACKETS)
        
        # Bandwidth tracking per application
        self.app_bandwidth = defaultdict(int)  # total bytes per app
        self.app_packet_count = defaultdict(int)  # packet count per app
        
        # Category tracking
        self.category_bandwidth = defaultdict(int)  # total bytes per category
        
        # Time-series data for bandwidth graph (time, upload_bytes, download_bytes)
        self.bandwidth_history = deque(maxlen=100)  # Last 100 time points
        
        # Real-time rate calculation
        self.last_rate_calc = time.time()
        self.bytes_since_last_calc = 0
        self.current_rate = 0  # bytes per second
        
        # Upload/Download tracking
        self.total_upload = 0
        self.total_download = 0
        
        # Statistics
        self.total_packets = 0
        self.start_time = time.time()
        
        # Local IP cache (for determining upload vs download)
        self.local_ips = set()
    
    def add_packet(self, packet_data: Dict):
        """
        Add a packet to the aggregator.
        Updates all statistics and buffers.
        
        Args:
            packet_data: Dictionary with packet information
        """
        with self.lock:
            # Add to recent packets buffer
            self.recent_packets.append(packet_data)
            
            # Update app bandwidth
            app_name = packet_data.get('app_name', 'Unknown')
            packet_size = packet_data.get('packet_size', 0)
            self.app_bandwidth[app_name] += packet_size
            self.app_packet_count[app_name] += 1
            
            # Update category bandwidth
            category = packet_data.get('category', 'Other')
            self.category_bandwidth[category] += packet_size
            
            # Update total packets
            self.total_packets += 1
            
            # Update upload/download tracking
            source_ip = packet_data.get('source_ip', '')
            if self._is_outgoing(source_ip):
                self.total_upload += packet_size
            else:
                self.total_download += packet_size
            
            # Update rate calculation
            self.bytes_since_last_calc += packet_size
            current_time = time.time()
            if current_time - self.last_rate_calc >= 1.0:
                # Calculate rate (bytes per second)
                time_diff = current_time - self.last_rate_calc
                self.current_rate = self.bytes_since_last_calc / time_diff
                
                # Add to bandwidth history
                self.bandwidth_history.append({
                    'timestamp': current_time,
                    'rate': self.current_rate,
                    'upload_rate': self.total_upload / (current_time - self.start_time),
                    'download_rate': self.total_download / (current_time - self.start_time)
                })
                
                # Reset for next calculation
                self.bytes_since_last_calc = 0
                self.last_rate_calc = current_time
    
    def _is_outgoing(self, ip: str) -> bool:
        """
        Determine if packet is outgoing based on source IP.
        
        Args:
            ip: Source IP address
            
        Returns:
            True if outgoing, False if incoming
        """
        # Check if IP is in local IP cache
        if ip in self.local_ips:
            return True
        
        # Common patterns for local IPs
        if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
            self.local_ips.add(ip)
            return True
        
        return False
    
    def get_recent_packets(self, limit: int = 50) -> List[Dict]:
        """
        Get most recent packets.
        
        Args:
            limit: Maximum number of packets to return
            
        Returns:
            List of packet dictionaries
        """
        with self.lock:
            # Convert deque to list and return last N items
            packets = list(self.recent_packets)
            return packets[-limit:] if len(packets) > limit else packets
    
    def get_top_apps(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get top applications by bandwidth usage.
        
        Args:
            limit: Number of apps to return
            
        Returns:
            List of tuples (app_name, total_bytes) sorted by bandwidth
        """
        with self.lock:
            # Sort apps by bandwidth
            sorted_apps = sorted(
                self.app_bandwidth.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_apps[:limit]
    
    def get_bandwidth_by_category(self) -> List[Tuple[str, int]]:
        """
        Get bandwidth usage by category.
        
        Returns:
            List of tuples (category, total_bytes)
        """
        with self.lock:
            return sorted(
                self.category_bandwidth.items(),
                key=lambda x: x[1],
                reverse=True
            )
    
    def get_bandwidth_history(self) -> List[Dict]:
        """
        Get bandwidth history for graphing.
        
        Returns:
            List of bandwidth data points
        """
        with self.lock:
            return list(self.bandwidth_history)
    
    def get_current_stats(self) -> Dict:
        """
        Get current statistics snapshot.
        
        Returns:
            Dictionary with current statistics
        """
        with self.lock:
            uptime = time.time() - self.start_time
            
            return {
                'total_packets': self.total_packets,
                'total_bandwidth': self.total_upload + self.total_download,
                'total_upload': self.total_upload,
                'total_download': self.total_download,
                'current_rate': self.current_rate,
                'active_apps': len(self.app_bandwidth),
                'uptime': uptime,
                'packets_per_second': self.total_packets / uptime if uptime > 0 else 0
            }
    
    def get_app_details(self, app_name: str) -> Dict:
        """
        Get detailed statistics for a specific application.
        
        Args:
            app_name: Application name
            
        Returns:
            Dictionary with app statistics
        """
        with self.lock:
            return {
                'app_name': app_name,
                'total_bandwidth': self.app_bandwidth.get(app_name, 0),
                'packet_count': self.app_packet_count.get(app_name, 0)
            }
    
    def reset_stats(self):
        """Reset all statistics (useful for testing)"""
        with self.lock:
            self.recent_packets.clear()
            self.app_bandwidth.clear()
            self.app_packet_count.clear()
            self.category_bandwidth.clear()
            self.bandwidth_history.clear()
            self.total_packets = 0
            self.total_upload = 0
            self.total_download = 0
            self.bytes_since_last_calc = 0
            self.current_rate = 0
            self.start_time = time.time()
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of current stats.
        
        Returns:
            Summary string
        """
        stats = self.get_current_stats()
        
        # Format bytes to human-readable
        def format_bytes(bytes_val):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_val < 1024:
                    return f"{bytes_val:.2f} {unit}"
                bytes_val /= 1024
            return f"{bytes_val:.2f} TB"
        
        summary = f"""
Network Monitor Statistics
---------------------------
Uptime: {stats['uptime']:.1f} seconds
Total Packets: {stats['total_packets']}
Total Bandwidth: {format_bytes(stats['total_bandwidth'])}
  Upload: {format_bytes(stats['total_upload'])}
  Download: {format_bytes(stats['total_download'])}
Current Rate: {format_bytes(stats['current_rate'])}/s
Active Applications: {stats['active_apps']}
Packets/Second: {stats['packets_per_second']:.2f}
        """
        
        return summary.strip()


# Global singleton instance
_aggregator_instance = None


def get_aggregator() -> DataAggregator:
    """
    Get singleton DataAggregator instance.
    
    Returns:
        Shared DataAggregator instance
    """
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = DataAggregator()
    return _aggregator_instance
