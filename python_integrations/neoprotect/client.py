"""NeoProtect API client."""
import aiohttp
import asyncio
from typing import List, Optional, Dict, Any
from .models import Attack, IPAddressModel, IPSettings


class NoActiveAttackError(Exception):
    """Raised when no active attack is found."""
    pass


class RequestFailedError(Exception):
    """Raised when API request fails."""
    pass


class IPNotFoundError(Exception):
    """Raised when IP address is not found."""
    pass


class Client:
    """NeoProtect API client."""

    def __init__(self, api_key: str, base_url: str = "https://api.neoprotect.net/v2"):
        """Initialize client."""
        if not api_key:
            raise ValueError("API key is required")
        
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'Authorization': f'Bearer {self.api_key}'}
            )
        return self.session

    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """Make HTTP request to API."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with session.get(url) as response:
                if response.status == 404:
                    raise IPNotFoundError(f"IP address not found")
                elif response.status != 200:
                    raise RequestFailedError(f"API request failed with status {response.status}")
                
                return await response.json()
        except aiohttp.ClientError as e:
            raise RequestFailedError(f"HTTP request failed: {e}")

    async def get_attacks(self, ip: str, page: int = 0) -> List[Attack]:
        """Get attacks for a specific IP address with pagination."""
        endpoint = f"/ips/{ip}/attacks"
        if page > 0:
            endpoint += f"?page={page}"
        
        try:
            data = await self._make_request(endpoint)
            if not data or 'data' not in data:
                return []
            
            attacks = []
            for attack_data in data['data']:
                attacks.append(Attack.from_dict(attack_data))
            
            return attacks
        except IPNotFoundError:
            raise
        except Exception as e:
            raise RequestFailedError(f"Failed to get attacks: {e}")

    async def get_active_attack(self, ip: str) -> Optional[Attack]:
        """Get active attack for IP address."""
        try:
            attacks = await self.get_attacks(ip, 0)
            # Find the first active attack (no end date)
            for attack in attacks:
                if attack.ended_at is None and attack.started_at is not None:
                    return attack
            
            raise NoActiveAttackError("No active attack found")
        except IPNotFoundError:
            raise
        except NoActiveAttackError:
            raise
        except Exception as e:
            raise RequestFailedError(f"Failed to get active attack: {e}")

    async def get_ip_addresses(self) -> List[IPAddressModel]:
        """Get all IP addresses in the account."""
        try:
            data = await self._make_request("/ips")
            if not data or 'data' not in data:
                return []
            
            ip_addresses = []
            for ip_data in data['data']:
                settings = None
                if 'settings' in ip_data and ip_data['settings']:
                    settings = IPSettings(auto_mitigation=ip_data['settings'].get('autoMitigation', False))
                
                ip_addresses.append(IPAddressModel(
                    ipv4=ip_data.get('ipv4', ''),
                    settings=settings
                ))
            
            return ip_addresses
        except Exception as e:
            raise RequestFailedError(f"Failed to get IP addresses: {e}")

    async def get_all_attacks_all_pages(self, active_only: bool = False) -> List[Attack]:
        """Get all attacks across all IP addresses and pages."""
        all_attacks = []
        
        try:
            ip_addresses = await self.get_ip_addresses()
            
            for ip_addr in ip_addresses:
                if not ip_addr.ipv4:
                    continue
                
                try:
                    if active_only:
                        # For active attacks, just check the first page
                        attacks = await self.get_attacks(ip_addr.ipv4, 0)
                        active_attacks = [a for a in attacks if a.ended_at is None and a.started_at is not None]
                        all_attacks.extend(active_attacks)
                    else:
                        # Get all attacks with pagination
                        page = 0
                        max_pages = 20  # Limit to prevent infinite loops
                        
                        while page < max_pages:
                            attacks = await self.get_attacks(ip_addr.ipv4, page)
                            if not attacks:
                                break
                            
                            all_attacks.extend(attacks)
                            
                            # If we got less than expected, we're probably at the end
                            if len(attacks) < 10:  # Assuming API returns 10 per page
                                break
                            
                            page += 1
                
                except IPNotFoundError:
                    continue  # Skip this IP
                except Exception as e:
                    print(f"Warning: Failed to fetch attacks for IP {ip_addr.ipv4}: {e}")
                    continue
            
            return all_attacks
        
        except Exception as e:
            raise RequestFailedError(f"Failed to get all attacks: {e}")

    def __del__(self):
        """Cleanup when object is destroyed."""
        if self.session and not self.session.closed:
            # In an async environment, this won't work properly
            # The session should be closed explicitly with await client.close()
            pass