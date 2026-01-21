"""
DNS Resolver and Traffic Categorizer
Enriches IP addresses with hostnames and categorizes traffic based on domains
"""

import socket
from functools import lru_cache
from typing import Optional, Tuple
import config


class DNSResolver:
    """
    DNS resolution and traffic categorization with caching.
    Uses reverse DNS lookup to resolve IP addresses to hostnames.
    """
    
    def __init__(self):
        """Initialize DNS resolver with category mappings"""
        self.category_keywords = config.CATEGORY_KEYWORDS
        self.timeout = config.DNS_TIMEOUT
    
    @lru_cache(maxsize=config.MAX_CACHED_DNS)
    def resolve_ip(self, ip_address: str) -> Optional[str]:
        """
        Perform reverse DNS lookup for an IP address.
        Uses LRU cache to avoid repeated lookups for the same IP.
        
        Args:
            ip_address: IP address to resolve
            
        Returns:
            Hostname if resolved, None if lookup fails
        """
        try:
            # Set socket timeout for DNS queries
            socket.setdefaulttimeout(self.timeout)
            
            # Reverse DNS lookup
            hostname = socket.gethostbyaddr(ip_address)[0]
            return hostname
        except (socket.herror, socket.gaierror, socket.timeout):
            # DNS lookup failed or timed out
            return None
        except Exception as e:
            # Unexpected error
            return None
    
    def categorize_domain(self, hostname: Optional[str]) -> str:
        """
        Categorize traffic based on hostname/domain.
        Uses keyword matching against predefined category lists.
        
        Args:
            hostname: Domain name or hostname
            
        Returns:
            Category name (e.g., "Streaming", "Social Media", "Other")
        """
        if not hostname:
            return "Other"
        
        # Convert to lowercase for case-insensitive matching
        hostname_lower = hostname.lower()
        
        # Check each category's keywords
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in hostname_lower:
                    return category
        
        # No match found
        return "Other"
    
    def resolve_and_categorize(self, ip_address: str) -> Tuple[Optional[str], str]:
        """
        Perform reverse DNS lookup and categorize in one call.
        
        Args:
            ip_address: IP address to resolve and categorize
            
        Returns:
            Tuple of (hostname, category)
        """
        hostname = self.resolve_ip(ip_address)
        category = self.categorize_domain(hostname)
        return hostname, category
    
    def get_cache_info(self) -> dict:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Dictionary with cache hit/miss information
        """
        info = self.resolve_ip.cache_info()
        return {
            'hits': info.hits,
            'misses': info.misses,
            'size': info.currsize,
            'maxsize': info.maxsize
        }
    
    def clear_cache(self):
        """Clear the DNS resolution cache"""
        self.resolve_ip.cache_clear()
    
    def is_local_ip(self, ip_address: str) -> bool:
        """
        Check if IP address is in a local/private range.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            True if local/private IP, False otherwise
        """
        try:
            # Common local IP ranges
            local_prefixes = [
                '127.',      # Loopback
                '10.',       # Private Class A
                '192.168.',  # Private Class C
                '172.16.',   # Private Class B (partial)
                '172.17.',
                '172.18.',
                '172.19.',
                '172.20.',
                '172.21.',
                '172.22.',
                '172.23.',
                '172.24.',
                '172.25.',
                '172.26.',
                '172.27.',
                '172.28.',
                '172.29.',
                '172.30.',
                '172.31.',
                '169.254.',  # Link-local
                'fe80::',    # IPv6 link-local
                '::1',       # IPv6 loopback
            ]
            
            for prefix in local_prefixes:
                if ip_address.startswith(prefix):
                    return True
            
            return False
        except Exception:
            return False


# Global singleton instance
_resolver_instance = None


def get_resolver() -> DNSResolver:
    """
    Get singleton DNS resolver instance.
    
    Returns:
        Shared DNSResolver instance
    """
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = DNSResolver()
    return _resolver_instance
