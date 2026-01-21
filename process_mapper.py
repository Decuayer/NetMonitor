"""
Process Mapper for Network Monitor
Maps network connections to specific applications/processes on macOS
Uses psutil primarily with lsof fallback for comprehensive coverage
"""

import psutil
import subprocess
from functools import lru_cache
from typing import Optional, Tuple, Dict
import re
import config


class ProcessMapper:
    """
    Maps network connections (ports/IPs) to process IDs and application names.
    Optimized for macOS using psutil and lsof.
    """
    
    def __init__(self):
        """Initialize process mapper"""
        self.connection_cache = {}
        self._refresh_counter = 0
        self._refresh_interval = 10  # Refresh cache every N lookups
    
    def _refresh_connections(self) -> Dict:
        """
        Refresh the connection-to-process mapping cache.
        Uses psutil.net_connections() which requires sudo on macOS.
        
        Returns:
            Dictionary mapping (local_port, remote_ip, remote_port) -> (pid, process_name)
        """
        connections = {}
        
        try:
            # Get all network connections (requires sudo on macOS)
            net_connections = psutil.net_connections(kind='inet')
            
            for conn in net_connections:
                # Skip connections without remote address
                if not conn.raddr:
                    continue
                
                # Extract connection details
                local_port = conn.laddr.port if conn.laddr else None
                remote_ip = conn.raddr.ip if conn.raddr else None
                remote_port = conn.raddr.port if conn.raddr else None
                pid = conn.pid
                
                if local_port and remote_ip and pid:
                    # Get process name
                    try:
                        process = psutil.Process(pid)
                        process_name = process.name()
                        
                        # Create mapping key
                        key = (local_port, remote_ip, remote_port)
                        connections[key] = (pid, process_name)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            
        except Exception as e:
            # psutil may fail without sudo permissions
            pass
        
        return connections
    
    def find_process_by_port(self, local_port: int, remote_ip: str = None, 
                            remote_port: int = None) -> Tuple[Optional[int], Optional[str]]:
        """
        Find process ID and name for a given network connection.
        
        Args:
            local_port: Local port number
            remote_ip: Remote IP address (optional)
            remote_port: Remote port number (optional)
            
        Returns:
            Tuple of (pid, process_name) or (None, None) if not found
        """
        # Periodically refresh the connection cache
        self._refresh_counter += 1
        if self._refresh_counter >= self._refresh_interval:
            self.connection_cache = self._refresh_connections()
            self._refresh_counter = 0
        
        # If cache is empty, try to refresh immediately
        if not self.connection_cache:
            self.connection_cache = self._refresh_connections()
        
        # Try exact match first (local_port, remote_ip, remote_port)
        if remote_ip and remote_port:
            key = (local_port, remote_ip, remote_port)
            if key in self.connection_cache:
                return self.connection_cache[key]
        
        # Fallback: match by local_port only
        for (l_port, r_ip, r_port), (pid, name) in self.connection_cache.items():
            if l_port == local_port:
                return pid, name
        
        # If psutil cache didn't work, try lsof as fallback
        return self._find_process_with_lsof(local_port)
    
    def _find_process_with_lsof(self, port: int) -> Tuple[Optional[int], Optional[str]]:
        """
        Fallback method using lsof command (macOS-specific).
        lsof is more reliable on macOS for finding process-to-port mappings.
        
        Args:
            port: Port number to search for
            
        Returns:
            Tuple of (pid, process_name) or (None, None)
        """
        try:
            # Run lsof command to find process using the port
            # -i :PORT = find connections on specific port
            # -n = don't resolve hostnames (faster)
            # -P = don't resolve port names (faster)
            # -F pcn = formatted output: pid, command name
            cmd = ['lsof', '-i', f':{port}', '-n', '-P', '-F', 'pcn']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0 and result.stdout:
                # Parse lsof output
                lines = result.stdout.strip().split('\n')
                pid = None
                process_name = None
                
                for line in lines:
                    if line.startswith('p'):
                        # Process ID line
                        pid = int(line[1:])
                    elif line.startswith('c'):
                        # Command name line
                        process_name = line[1:]
                        break
                
                if pid and process_name:
                    return pid, process_name
        
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
            pass
        
        return None, None
    
    @lru_cache(maxsize=config.PROCESS_CACHE_SIZE)
    def get_process_name(self, pid: int) -> Optional[str]:
        """
        Get process name from PID with caching.
        
        Args:
            pid: Process ID
            
        Returns:
            Process name or None
        """
        try:
            process = psutil.Process(pid)
            return process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def get_app_name_from_process_name(self, process_name: str) -> str:
        """
        Convert process name to user-friendly application name.
        Example: "Google Chrome Helper" -> "Chrome"
        
        Args:
            process_name: Raw process name from system
            
        Returns:
            Cleaned application name
        """
        if not process_name:
            return "Unknown"
        
        # Common macOS process name mappings
        name_mappings = {
            'Google Chrome': 'Chrome',
            'Google Chrome Helper': 'Chrome',
            'Safari': 'Safari',
            'Safari Networking': 'Safari',
            'firefox': 'Firefox',
            'Spotify': 'Spotify',
            'Spotify Helper': 'Spotify',
            'Code': 'VS Code',
            'Code Helper': 'VS Code',
            'Python': 'Python',
            'python3': 'Python',
            'node': 'Node.js',
            'Slack': 'Slack',
            'Slack Helper': 'Slack',
            'Discord': 'Discord',
            'Discord Helper': 'Discord',
            'Zoom': 'Zoom',
            'zoom.us': 'Zoom',
            'Microsoft Teams': 'Teams',
            'Dropbox': 'Dropbox',
            'OneDrive': 'OneDrive',
        }
        
        # Check for exact match
        if process_name in name_mappings:
            return name_mappings[process_name]
        
        # Check for partial match
        for key, value in name_mappings.items():
            if key.lower() in process_name.lower():
                return value
        
        # Remove "Helper", "Renderer", etc.
        cleaned = re.sub(r'\s+(Helper|Renderer|GPU|Network)', '', process_name)
        
        return cleaned.strip() or process_name
    
    def clear_cache(self):
        """Clear all caches"""
        self.connection_cache.clear()
        self.get_process_name.cache_clear()
        self._refresh_counter = 0


# Global singleton instance
_mapper_instance = None


def get_mapper() -> ProcessMapper:
    """
    Get singleton ProcessMapper instance.
    
    Returns:
        Shared ProcessMapper instance
    """
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = ProcessMapper()
    return _mapper_instance
