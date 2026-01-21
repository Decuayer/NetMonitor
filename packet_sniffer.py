"""
Packet Sniffer Module
Captures network packets on macOS using scapy
Designed to run in a separate thread with queue-based communication
"""

from scapy.all import sniff, IP, TCP, UDP
import threading
import queue
from typing import Callable, Optional
import config
import time


class PacketSniffer:
    """
    Network packet sniffer using scapy.
    Captures TCP and UDP packets on specified network interface.
    Optimized for macOS (en0 interface).
    """
    
    def __init__(self, interface: str = config.NETWORK_INTERFACE, 
                 packet_callback: Optional[Callable] = None):
        """
        Initialize packet sniffer.
        
        Args:
            interface: Network interface to monitor (default: en0 on macOS)
            packet_callback: Optional callback function to handle each packet
        """
        self.interface = interface
        self.packet_callback = packet_callback
        self.packet_queue = queue.Queue(maxsize=config.SNIFFER_QUEUE_SIZE)
        self.is_running = False
        self.sniffer_thread = None
        self.start_time = None
    
    def _packet_handler(self, packet):
        """
        Internal handler for each captured packet.
        Extracts relevant information and adds to queue or calls callback.
        
        Args:
            packet: Scapy packet object
        """
        try:
            # Only process IP packets with TCP or UDP
            if not packet.haslayer(IP):
                return
            
            ip_layer = packet[IP]
            protocol = None
            src_port = None
            dst_port = None
            packet_size = len(packet)
            
            # Extract TCP/UDP specific information
            if packet.haslayer(TCP):
                protocol = 'TCP'
                tcp_layer = packet[TCP]
                src_port = tcp_layer.sport
                dst_port = tcp_layer.dport
            elif packet.haslayer(UDP):
                protocol = 'UDP'
                udp_layer = packet[UDP]
                src_port = udp_layer.sport
                dst_port = udp_layer.dport
            else:
                # Skip other protocols
                return
            
            # Create packet data dictionary
            packet_data = {
                'timestamp': time.time(),
                'source_ip': ip_layer.src,
                'dest_ip': ip_layer.dst,
                'protocol': protocol,
                'source_port': src_port,
                'dest_port': dst_port,
                'packet_size': packet_size
            }
            
            # Use callback if provided, otherwise add to queue
            if self.packet_callback:
                self.packet_callback(packet_data)
            else:
                # Add to queue (non-blocking, drop if full)
                try:
                    self.packet_queue.put_nowait(packet_data)
                except queue.Full:
                    # Queue is full, drop oldest packet
                    try:
                        self.packet_queue.get_nowait()
                        self.packet_queue.put_nowait(packet_data)
                    except queue.Empty:
                        pass
        
        except Exception as e:
            # Silently handle packet processing errors
            # Avoid crashing the sniffer thread
            pass
    
    def _sniffer_worker(self):
        """
        Worker function that runs in separate thread.
        Starts scapy packet sniffing.
        """
        try:
            # Start packet capture
            # BPF filter: only capture TCP and UDP packets
            # prn: callback function for each packet
            # store: don't store packets in memory (we process on-the-fly)
            # iface: network interface to monitor
            sniff(
                filter=config.PACKET_FILTER,
                prn=self._packet_handler,
                store=False,
                iface=self.interface,
                stop_filter=lambda x: not self.is_running
            )
        except PermissionError:
            print("ERROR: Packet capture requires sudo permissions on macOS")
            print("Please run with: sudo python monitor.py")
            self.is_running = False
        except Exception as e:
            print(f"ERROR: Packet sniffer failed: {e}")
            self.is_running = False
    
    def start(self):
        """
        Start packet capture in background thread.
        NOTE: Requires sudo permissions on macOS!
        """
        if self.is_running:
            print("Sniffer is already running")
            return
        
        self.is_running = True
        self.start_time = time.time()
        
        # Create and start sniffer thread
        self.sniffer_thread = threading.Thread(
            target=self._sniffer_worker,
            daemon=True,
            name="PacketSnifferThread"
        )
        self.sniffer_thread.start()
        
        print(f"Packet sniffer started on interface: {self.interface}")
        print("Monitoring TCP and UDP traffic...")
    
    def stop(self):
        """Stop packet capture"""
        if not self.is_running:
            return
        
        print("Stopping packet sniffer...")
        self.is_running = False
        
        # Wait for thread to finish (with timeout)
        if self.sniffer_thread:
            self.sniffer_thread.join(timeout=3)
        
        print("Packet sniffer stopped")
    
    def get_packet(self, timeout: float = 1.0) -> Optional[dict]:
        """
        Get next packet from queue (blocking with timeout).
        
        Args:
            timeout: Maximum time to wait for packet (seconds)
            
        Returns:
            Packet data dictionary or None if timeout
        """
        try:
            return self.packet_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_packet_nowait(self) -> Optional[dict]:
        """
        Get next packet from queue (non-blocking).
        
        Returns:
            Packet data dictionary or None if queue is empty
        """
        try:
            return self.packet_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_uptime(self) -> float:
        """
        Get sniffer uptime in seconds.
        
        Returns:
            Seconds since sniffer started
        """
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time
    
    def get_queue_size(self) -> int:
        """
        Get current number of packets in queue.
        
        Returns:
            Queue size
        """
        return self.packet_queue.qsize()


def test_sniffer():
    """Test function to verify packet capture works"""
    import sys
    import os
    
    # Check for sudo
    if os.geteuid() != 0:
        print("ERROR: This script must be run with sudo on macOS")
        print("Usage: sudo python packet_sniffer.py")
        sys.exit(1)
    
    print("Starting packet sniffer test...")
    print("Capture 10 packets and display them")
    print("-" * 60)
    
    def print_packet(pkt):
        print(f"[{pkt['protocol']}] {pkt['source_ip']}:{pkt['source_port']} "
              f"-> {pkt['dest_ip']}:{pkt['dest_port']} "
              f"({pkt['packet_size']} bytes)")
    
    sniffer = PacketSniffer(packet_callback=print_packet)
    sniffer.start()
    
    try:
        # Run for 30 seconds then stop
        time.sleep(30)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        sniffer.stop()
        print(f"Uptime: {sniffer.get_uptime():.2f} seconds")


if __name__ == "__main__":
    test_sniffer()
