"""NeoProtect API models."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json


@dataclass
class IPSettings:
    """IP settings model."""
    auto_mitigation: bool


@dataclass
class IPAddressModel:
    """IP address model."""
    ipv4: str
    settings: Optional[IPSettings] = None


@dataclass
class AttackSignature:
    """Attack signature model."""
    id: str
    name: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    pps_peak: int
    bps_peak: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AttackSignature':
        """Create AttackSignature from dictionary."""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            started_at=cls._parse_datetime(data.get('startedAt')),
            ended_at=cls._parse_datetime(data.get('endedAt')),
            pps_peak=data.get('ppsPeak', 0),
            bps_peak=data.get('bpsPeak', 0)
        )

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string."""
        if not dt_str:
            return None
        try:
            # Try ISO format first
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None


@dataclass
class Attack:
    """Attack model."""
    id: str
    dst_address_string: str
    dst_address: Optional[IPAddressModel]
    signatures: List[AttackSignature]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    sample_rate: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Attack':
        """Create Attack from dictionary."""
        signatures = []
        if 'signatures' in data and data['signatures']:
            signatures = [AttackSignature.from_dict(sig) for sig in data['signatures']]

        dst_address = None
        if 'dstAddress' in data and data['dstAddress']:
            dst_addr_data = data['dstAddress']
            settings = None
            if 'settings' in dst_addr_data and dst_addr_data['settings']:
                settings = IPSettings(auto_mitigation=dst_addr_data['settings'].get('autoMitigation', False))
            dst_address = IPAddressModel(
                ipv4=dst_addr_data.get('ipv4', ''),
                settings=settings
            )

        return cls(
            id=data.get('id', ''),
            dst_address_string=data.get('dstAddressString', ''),
            dst_address=dst_address,
            signatures=signatures,
            started_at=AttackSignature._parse_datetime(data.get('startedAt')),
            ended_at=AttackSignature._parse_datetime(data.get('endedAt')),
            sample_rate=data.get('sampleRate', 0)
        )

    def get_peak_bps(self) -> int:
        """Get peak bandwidth in bytes per second."""
        if not self.signatures:
            return 0
        return max(sig.bps_peak for sig in self.signatures)

    def get_peak_pps(self) -> int:
        """Get peak packets per second."""
        if not self.signatures:
            return 0
        return max(sig.pps_peak for sig in self.signatures)

    def get_signature_names(self) -> List[str]:
        """Get list of signature names."""
        return [sig.name for sig in self.signatures if sig.name]

    def duration(self) -> Optional[float]:
        """Get attack duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.ended_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    def equal(self, other: 'Attack') -> bool:
        """Check if two attacks are equal."""
        if not isinstance(other, Attack):
            return False
        
        return (
            self.id == other.id and
            self.dst_address_string == other.dst_address_string and
            self.get_peak_bps() == other.get_peak_bps() and
            self.get_peak_pps() == other.get_peak_pps() and
            len(self.signatures) == len(other.signatures) and
            set(self.get_signature_names()) == set(other.get_signature_names())
        )

    def calculate_diff(self, previous: 'Attack') -> Dict[str, Any]:
        """Calculate differences between attacks."""
        diff = {}
        
        # Calculate BPS change
        if self.get_peak_bps() != previous.get_peak_bps():
            diff['bpsPeakChange'] = self.get_peak_bps() - previous.get_peak_bps()
        
        # Calculate PPS change
        if self.get_peak_pps() != previous.get_peak_pps():
            diff['ppsPeakChange'] = self.get_peak_pps() - previous.get_peak_pps()
        
        # Check for new signatures
        previous_sigs = set(previous.get_signature_names())
        current_sigs = set(self.get_signature_names())
        new_sigs = current_sigs - previous_sigs
        if new_sigs:
            diff['newSignatures'] = list(new_sigs)
        
        return diff