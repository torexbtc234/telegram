"""
Session data models
"""
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    BANNED = "banned"

@dataclass
class VisitorInfo:
    """Visitor information"""
    user_agent: str = ""
    ip_address: str = ""
    language: str = "en"
    timezone: str = "UTC"
    referrer: str = ""
    page_url: str = ""

@dataclass
class Session:
    """Visitor session"""
    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    visitor_info: VisitorInfo = field(default_factory=VisitorInfo)
    message_count: int = 0
    file_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def is_active(self, timeout_seconds: int = 86400) -> bool:
        """Check if session is still active"""
        if self.status != SessionStatus.ACTIVE:
            return False
        
        time_since_activity = (datetime.now() - self.last_activity).total_seconds()
        return time_since_activity <= timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "visitor_info": {
                "user_agent": self.visitor_info.user_agent,
                "ip_address": self.visitor_info.ip_address,
                "language": self.visitor_info.language,
                "timezone": self.visitor_info.timezone,
                "referrer": self.visitor_info.referrer,
                "page_url": self.visitor_info.page_url,
            },
            "message_count": self.message_count,
            "file_count": self.file_count,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create session from dictionary"""
        visitor_info = VisitorInfo(**data.get("visitor_info", {}))
        
        # Parse datetime strings
        created_at = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        last_activity = datetime.fromisoformat(data["last_activity"].replace('Z', '+00:00'))
        
        return cls(
            session_id=data["session_id"],
            status=SessionStatus(data["status"]),
            created_at=created_at,
            last_activity=last_activity,
            visitor_info=visitor_info,
            message_count=data.get("message_count", 0),
            file_count=data.get("file_count", 0),
            metadata=data.get("metadata", {}),
        )

@dataclass
class SessionStats:
    """Session statistics"""
    total_sessions: int = 0
    active_sessions: int = 0
    messages_today: int = 0
    files_today: int = 0
    avg_session_duration: float = 0.0  # in seconds
    peak_concurrent: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "messages_today": self.messages_today,
            "files_today": self.files_today,
            "avg_session_duration": self.avg_session_duration,
            "peak_concurrent": self.peak_concurrent,
  }
