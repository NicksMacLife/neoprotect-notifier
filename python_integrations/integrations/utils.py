"""Utility functions for integrations."""
from datetime import datetime, timezone
from typing import Optional


def format_bps(bytes_per_second: int) -> str:
    """Format bytes per second to human readable string."""
    bps = bytes_per_second * 8
    
    if bps < 1000:
        return f"{bps} bps"
    elif bps < 1000000:
        return f"{bps/1000:.2f} Kbps"
    elif bps < 1000000000:
        return f"{bps/1000000:.2f} Mbps"
    elif bps < 1000000000000:
        return f"{bps/1000000000:.2f} Gbps"
    else:
        return f"{bps/1000000000000:.2f} Tbps"


def format_pps(pps: int) -> str:
    """Format packets per second to human readable string."""
    if pps < 1000:
        return f"{pps} pps"
    elif pps < 1000000:
        return f"{pps/1000:.2f} Kpps"
    elif pps < 1000000000:
        return f"{pps/1000000:.2f} Mpps"
    else:
        return f"{pps/1000000000:.2f} Gpps"


def calculate_percentage_change(old: int, new: int) -> int:
    """Calculate percentage change between two values."""
    if old == 0:
        return 100 if new > 0 else 0
    return int((new - old) / old * 100)


def format_duration_readable(seconds: Optional[float]) -> str:
    """Format duration in seconds to human readable string."""
    if seconds is None or seconds <= 0:
        return "N/A"
    
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        if remaining_seconds == 0:
            return f"{minutes} minutes"
        return f"{minutes} minutes, {remaining_seconds} seconds"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if minutes == 0:
            return f"{hours} hours"
        return f"{hours} hours, {minutes} minutes"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        if hours == 0:
            return f"{days} days"
        return f"{days} days, {hours} hours"


def format_time_to_local(dt: Optional[datetime]) -> str:
    """Format datetime to local time string."""
    if dt is None:
        return "unknown"
    
    # Convert to local timezone if it's not already timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to local time
    local_dt = dt.astimezone()
    
    return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")


# Discord color constants
DISCORD_COLOR_GREEN = 0x00FF00   # Success
DISCORD_COLOR_YELLOW = 0xFFFF00  # Warning
DISCORD_COLOR_RED = 0xFF0000     # Error
DISCORD_COLOR_BLUE = 0x3498DB    # Info


# Console color constants
COLOR_RESET = "\033[0m"
COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_BLUE = "\033[34m"
COLOR_MAGENTA = "\033[35m"
COLOR_CYAN = "\033[36m"
COLOR_WHITE = "\033[37m"