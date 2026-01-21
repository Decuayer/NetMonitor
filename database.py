"""
Database operations for Network Monitor
Thread-safe SQLite implementation for storing captured network traffic
"""

import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import config


class NetworkDatabase:
    """
    Thread-safe database handler for network traffic data.
    Uses SQLite for local persistence with automatic table creation.
    """
    
    def __init__(self, db_path: str = config.DATABASE_PATH):
        """
        Initialize database connection and create tables if needed.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Main connections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    app_name TEXT,
                    pid INTEGER,
                    source_ip TEXT NOT NULL,
                    dest_ip TEXT NOT NULL,
                    dest_hostname TEXT,
                    category TEXT DEFAULT 'Other',
                    protocol TEXT NOT NULL,
                    source_port INTEGER,
                    dest_port INTEGER,
                    packet_size INTEGER NOT NULL
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON connections(timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_app_name 
                ON connections(app_name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_category 
                ON connections(category)
            """)
            
            conn.commit()
            conn.close()
    
    def insert_connection(self, data: Dict):
        """
        Insert a single connection record.
        
        Args:
            data: Dictionary with connection details
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO connections (
                    timestamp, app_name, pid, source_ip, dest_ip,
                    dest_hostname, category, protocol, source_port,
                    dest_port, packet_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('timestamp', datetime.now().timestamp()),
                data.get('app_name', 'Unknown'),
                data.get('pid'),
                data.get('source_ip'),
                data.get('dest_ip'),
                data.get('dest_hostname', ''),
                data.get('category', 'Other'),
                data.get('protocol'),
                data.get('source_port'),
                data.get('dest_port'),
                data.get('packet_size', 0)
            ))
            
            conn.commit()
            conn.close()
    
    def insert_batch(self, data_list: List[Dict]):
        """
        Insert multiple connection records in a batch for better performance.
        
        Args:
            data_list: List of connection dictionaries
        """
        if not data_list:
            return
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            records = [
                (
                    data.get('timestamp', datetime.now().timestamp()),
                    data.get('app_name', 'Unknown'),
                    data.get('pid'),
                    data.get('source_ip'),
                    data.get('dest_ip'),
                    data.get('dest_hostname', ''),
                    data.get('category', 'Other'),
                    data.get('protocol'),
                    data.get('source_port'),
                    data.get('dest_port'),
                    data.get('packet_size', 0)
                )
                for data in data_list
            ]
            
            cursor.executemany("""
                INSERT INTO connections (
                    timestamp, app_name, pid, source_ip, dest_ip,
                    dest_hostname, category, protocol, source_port,
                    dest_port, packet_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            
            conn.commit()
            conn.close()
    
    def get_recent_connections(self, limit: int = 50) -> List[Dict]:
        """
        Get most recent connections.
        
        Args:
            limit: Number of connections to retrieve
            
        Returns:
            List of connection dictionaries
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM connections
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
    
    def get_top_apps_by_bandwidth(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get top applications by total bandwidth usage.
        
        Args:
            limit: Number of apps to return
            
        Returns:
            List of tuples (app_name, total_bytes)
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT app_name, SUM(packet_size) as total_bytes
                FROM connections
                WHERE app_name IS NOT NULL AND app_name != 'Unknown'
                GROUP BY app_name
                ORDER BY total_bytes DESC
                LIMIT ?
            """, (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return results
    
    def get_bandwidth_by_category(self) -> List[Tuple[str, int]]:
        """
        Get total bandwidth usage grouped by category.
        
        Returns:
            List of tuples (category, total_bytes)
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT category, SUM(packet_size) as total_bytes
                FROM connections
                GROUP BY category
                ORDER BY total_bytes DESC
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            return results
    
    def get_total_bandwidth(self) -> int:
        """
        Get total bandwidth usage across all connections.
        
        Returns:
            Total bytes transferred
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT SUM(packet_size) FROM connections")
            result = cursor.fetchone()[0]
            conn.close()
            
            return result or 0
    
    def get_connections_by_timerange(self, start_time: float, end_time: float) -> List[Dict]:
        """
        Get connections within a specific time range.
        
        Args:
            start_time: Unix timestamp for start
            end_time: Unix timestamp for end
            
        Returns:
            List of connection dictionaries
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM connections
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            """, (start_time, end_time))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
    
    def get_connection_count(self) -> int:
        """
        Get total number of connections recorded.
        
        Returns:
            Total connection count
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM connections")
            result = cursor.fetchone()[0]
            conn.close()
            
            return result
    
    def cleanup_old_data(self, days: int = 7):
        """
        Remove connections older than specified days.
        
        Args:
            days: Number of days to keep
        """
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM connections
                WHERE timestamp < ?
            """, (cutoff_time,))
            
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
            
            return deleted
