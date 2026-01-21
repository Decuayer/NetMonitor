"""
Network Monitor - Main Application
Orchestrates packet capture, processing, and dashboard
Requires sudo permissions on macOS
"""

import sys
import os
import time
import threading
import signal
from datetime import datetime

# Import all components
from packet_sniffer import PacketSniffer
from process_mapper import get_mapper
from dns_resolver import get_resolver
from database import NetworkDatabase
from data_aggregator import get_aggregator
import config


class NetworkMonitor:
    """
    Main Network Monitor application.
    Coordinates packet capture, processing, and data storage.
    """
    
    def __init__(self):
        """Initialize the network monitor"""
        self.sniffer = None
        self.processor_thread = None
        self.is_running = False
        
        # Initialize components
        self.db = NetworkDatabase()
        self.mapper = get_mapper()
        self.resolver = get_resolver()
        self.aggregator = get_aggregator()
        
        # Batch processing
        self.batch_buffer = []
        self.batch_lock = threading.Lock()
        
        print("Network Monitor initialized")
    
    def packet_processor_worker(self):
        """
        Worker thread that processes captured packets.
        Enriches packets with process info, DNS resolution, and stores in DB.
        """
        print("Packet processor thread started")
        
        while self.is_running:
            try:
                # Get packet from sniffer queue (with timeout)
                packet_data = self.sniffer.get_packet(timeout=1.0)
                
                if packet_data is None:
                    continue
                
                # Enrich packet data
                enriched_data = self._enrich_packet(packet_data)
                
                # Add to aggregator for real-time stats
                self.aggregator.add_packet(enriched_data)
                
                # Add to batch buffer for database
                with self.batch_lock:
                    self.batch_buffer.append(enriched_data)
                    
                    # Insert batch when buffer is full
                    if len(self.batch_buffer) >= config.BATCH_INSERT_SIZE:
                        self.db.insert_batch(self.batch_buffer)
                        self.batch_buffer.clear()
            
            except Exception as e:
                # Log error but don't crash the processor
                print(f"Error processing packet: {e}")
        
        # Flush remaining packets on shutdown
        with self.batch_lock:
            if self.batch_buffer:
                self.db.insert_batch(self.batch_buffer)
                self.batch_buffer.clear()
        
        print("Packet processor thread stopped")
    
    def _enrich_packet(self, packet_data: dict) -> dict:
        """
        Enrich packet data with process info, DNS, and categorization.
        
        Args:
            packet_data: Raw packet data from sniffer
            
        Returns:
            Enriched packet data dictionary
        """
        enriched = packet_data.copy()
        
        # Find process using this connection
        local_port = packet_data.get('source_port')
        remote_ip = packet_data.get('dest_ip')
        remote_port = packet_data.get('dest_port')
        
        if local_port:
            pid, process_name = self.mapper.find_process_by_port(
                local_port, remote_ip, remote_port
            )
            
            if process_name:
                # Get user-friendly app name
                app_name = self.mapper.get_app_name_from_process_name(process_name)
                enriched['app_name'] = app_name
                enriched['pid'] = pid
            else:
                enriched['app_name'] = 'Unknown'
                enriched['pid'] = None
        
        # Resolve destination IP to hostname
        dest_ip = packet_data.get('dest_ip')
        if dest_ip and not self.resolver.is_local_ip(dest_ip):
            hostname, category = self.resolver.resolve_and_categorize(dest_ip)
            enriched['dest_hostname'] = hostname
            enriched['category'] = category
        else:
            enriched['dest_hostname'] = 'Local Network'
            enriched['category'] = 'Local'
        
        return enriched
    
    def start(self):
        """Start the network monitor"""
        if self.is_running:
            print("Monitor is already running")
            return
        
        print("\n" + "="*60)
        print("Starting Network Monitor")
        print("="*60)
        
        # Check for sudo permissions
        if os.geteuid() != 0:
            print("\n❌ ERROR: This application requires sudo permissions on macOS")
            print("Please run with: sudo python monitor.py")
            print("\nPacket capture on macOS requires root privileges to access")
            print("the Berkeley Packet Filter (BPF) interface.")
            sys.exit(1)
        
        self.is_running = True
        
        # Start packet sniffer
        print(f"\n🔍 Starting packet sniffer on interface: {config.NETWORK_INTERFACE}")
        self.sniffer = PacketSniffer(interface=config.NETWORK_INTERFACE)
        self.sniffer.start()
        
        # Wait a moment for sniffer to initialize
        time.sleep(2)
        
        # Start packet processor thread
        print("⚙️  Starting packet processor thread...")
        self.processor_thread = threading.Thread(
            target=self.packet_processor_worker,
            daemon=True,
            name="PacketProcessorThread"
        )
        self.processor_thread.start()
        
        print("\n✅ Network Monitor is now running!")
        print(f"📊 Dashboard: Start with 'streamlit run dashboard.py'")
        print(f"💾 Database: {config.DATABASE_PATH}")
        print(f"⏹️  Stop: Press Ctrl+C\n")
        print("="*60 + "\n")
    
    def stop(self):
        """Stop the network monitor"""
        if not self.is_running:
            return
        
        print("\n\n" + "="*60)
        print("Stopping Network Monitor...")
        print("="*60)
        
        self.is_running = False
        
        # Stop packet sniffer
        if self.sniffer:
            self.sniffer.stop()
        
        # Wait for processor thread to finish
        if self.processor_thread:
            print("Waiting for packet processor to finish...")
            self.processor_thread.join(timeout=5)
        
        # Print summary
        print("\n📊 Session Summary:")
        print(self.aggregator.get_summary())
        
        print("\n✅ Network Monitor stopped")
        print("="*60 + "\n")
    
    def run(self):
        """Run the monitor until interrupted"""
        self.start()
        
        try:
            # Keep main thread alive
            while self.is_running:
                time.sleep(1)
                
                # Print periodic status (every 30 seconds)
                if int(self.sniffer.get_uptime()) % 30 == 0:
                    stats = self.aggregator.get_current_stats()
                    print(f"[Status] Packets: {stats['total_packets']:,} | "
                          f"Apps: {stats['active_apps']} | "
                          f"Rate: {stats['current_rate']/1024:.2f} KB/s")
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupt received (Ctrl+C)")
        finally:
            self.stop()


def print_banner():
    """Print application banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           🌐 Network Monitor for macOS 🌐                ║
    ║                                                           ║
    ║     Real-time Network Traffic Analysis & Monitoring       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_dependencies():
    """Check if all required dependencies are installed"""
    missing = []
    
    try:
        import scapy
    except ImportError:
        missing.append('scapy')
    
    try:
        import psutil
    except ImportError:
        missing.append('psutil')
    
    try:
        import streamlit
    except ImportError:
        missing.append('streamlit')
    
    if missing:
        print("❌ Missing required dependencies:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nInstall with: pip install -r requirements.txt")
        sys.exit(1)


def main():
    """Main entry point"""
    print_banner()
    
    # Check dependencies
    check_dependencies()
    
    # Create and run monitor
    monitor = NetworkMonitor()
    
    # Set up signal handler for clean shutdown
    def signal_handler(sig, frame):
        print("\n⚠️  Signal received, shutting down...")
        monitor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run monitor
    monitor.run()


if __name__ == "__main__":
    main()