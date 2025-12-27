"""
Session management for visitor connections
"""
import asyncio
import logging
import psutil
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

from config.config import settings

logger = logging.getLogger(__name__)

@dataclass
class Session:
    """Visitor session data"""
    session_id: str
    created_at: datetime
    last_activity: datetime
    data: Dict[str, Any]
    message_count: int = 0
    is_active: bool = True

class SessionManager:
    """Manages visitor sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.start_time = datetime.now()
        self.daily_stats = defaultdict(int)
        
    def create_session(self, session_id: str, initial_data: Dict[str, Any] = None) -> Session:
        """Create a new visitor session"""
        now = datetime.now()
        session = Session(
            session_id=session_id,
            created_at=now,
            last_activity=now,
            data=initial_data or {},
            message_count=0,
            is_active=True
        )
        self.sessions[session_id] = session
        self.daily_stats['sessions_created'] += 1
        logger.info(f"Created session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def update_session_activity(self, session_id: str):
        """Update session last activity time"""
        if session_id in self.sessions:
            self.sessions[session_id].last_activity = datetime.now()
            self.sessions[session_id].is_active = True
    
    def increment_message_count(self, session_id: str):
        """Increment message count for session"""
        if session_id in self.sessions:
            self.sessions[session_id].message_count += 1
            self.daily_stats['messages'] += 1
    
    def end_session(self, session_id: str):
        """Mark session as ended"""
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            self.daily_stats['sessions_ended'] += 1
            logger.info(f"Ended session: {session_id}")
    
    def validate_session(self, session_id: str) -> bool:
        """Validate if session exists and is active"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Check if session timed out
        timeout = timedelta(seconds=settings.SESSION_TIMEOUT)
        if datetime.now() - session.last_activity > timeout:
            session.is_active = False
            return False
        
        return session.is_active
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions"""
        active = []
        now = datetime.now()
        timeout = timedelta(seconds=settings.SESSION_TIMEOUT)
        
        for session_id, session in self.sessions.items():
            # Check if session is still active
            if now - session.last_activity > timeout:
                session.is_active = False
                continue
            
            if session.is_active:
                session_data = asdict(session)
                session_data['duration'] = str(now - session.created_at)
                session_data['inactive_for'] = str(now - session.last_activity)
                active.append(session_data)
        
        return active
    
    def get_session_duration(self, session_id: str) -> str:
        """Get duration of session"""
        if session_id not in self.sessions:
            return "Session not found"
        
        session = self.sessions[session_id]
        if session.is_active:
            duration = datetime.now() - session.created_at
        else:
            duration = session.last_activity - session.created_at
        
        # Format duration
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    async def cleanup_old_sessions(self):
        """Cleanup old inactive sessions periodically"""
        while True:
            try:
                await self._perform_cleanup()
                await asyncio.sleep(settings.CLEANUP_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _perform_cleanup(self):
        """Perform actual session cleanup"""
        now = datetime.now()
        timeout = timedelta(seconds=settings.SESSION_TIMEOUT)
        removed_count = 0
        
        # Find sessions to remove
        to_remove = []
        for session_id, session in self.sessions.items():
            # Remove if inactive for timeout period
            if not session.is_active or (now - session.last_activity > timeout):
                to_remove.append(session_id)
        
        # Remove sessions
        for session_id in to_remove:
            del self.sessions[session_id]
            removed_count += 1
        
        # Reset daily stats if new day
        if now.date() != self.start_time.date():
            self.daily_stats.clear()
            self.start_time = now
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old sessions")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get server statistics"""
        active_sessions = len([s for s in self.sessions.values() if s.is_active])
        
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Get memory usage
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            'active_sessions': active_sessions,
            'total_sessions': len(self.sessions),
            'total_sessions_today': self.daily_stats.get('sessions_created', 0),
            'messages_today': self.daily_stats.get('messages', 0),
            'uptime': uptime_str,
            'memory_usage_mb': round(memory_usage, 2),
            'start_time': self.start_time.isoformat(),
        }
    
    async def cleanup(self):
        """Cleanup all sessions on shutdown"""
        self.sessions.clear()
        logger.info("All sessions cleaned up")
