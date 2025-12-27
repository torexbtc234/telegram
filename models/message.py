"""
Message data models
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

class MessageType(str, Enum):
    """Message type enumeration"""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"
    ADMIN = "admin"
    ERROR = "error"
    TYPING = "typing"
    READ_RECEIPT = "read_receipt"
    JOIN = "join"
    LEAVE = "leave"

class MessageDirection(str, Enum):
    """Message direction enumeration"""
    VISITOR_TO_ADMIN = "visitor_to_admin"
    ADMIN_TO_VISITOR = "admin_to_visitor"
    SYSTEM = "system"

@dataclass
class Message:
    """Base message model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    content: str = ""
    message_type: MessageType = MessageType.TEXT
    direction: MessageDirection = MessageDirection.VISITOR_TO_ADMIN
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "content": self.content,
            "type": self.message_type.value,
            "direction": self.direction.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            session_id=data["session_id"],
            content=data["content"],
            message_type=MessageType(data["type"]),
            direction=MessageDirection(data.get("direction", "visitor_to_admin")),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )

class TextMessage(BaseModel):
    """Text message model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            MessageType: lambda mt: mt.value,
        }

class VoiceMessage(BaseModel):
    """Voice message model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    audio_data: Optional[bytes] = None
    audio_url: Optional[str] = None
    duration: float = 0.0  # in seconds
    message_type: MessageType = MessageType.VOICE
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ImageMessage(BaseModel):
    """Image message model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    image_data: Optional[bytes] = None
    image_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    caption: Optional[str] = None
    message_type: MessageType = MessageType.IMAGE
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FileMessage(BaseModel):
    """File message model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    file_data: Optional[bytes] = None
    file_url: Optional[str] = None
    file_name: str
    file_size: int
    mime_type: str
    message_type: MessageType = MessageType.FILE
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SystemMessage(BaseModel):
    """System message model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = "system"
    content: str
    message_type: MessageType = MessageType.SYSTEM
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TypingIndicator(BaseModel):
    """Typing indicator model"""
    session_id: str
    is_typing: bool = True
    message_type: MessageType = MessageType.TYPING
    timestamp: datetime = Field(default_factory=datetime.now)

class ReadReceipt(BaseModel):
    """Read receipt model"""
    message_id: str
    session_id: str
    read_at: datetime = Field(default_factory=datetime.now)
    message_type: MessageType = MessageType.READ_RECEIPT

class MessageBatch(BaseModel):
    """Batch of messages"""
    messages: List[Message]
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)

# Union type for all message types
MessageUnion = TextMessage | VoiceMessage | ImageMessage | FileMessage | SystemMessage | TypingIndicator | ReadReceipt
