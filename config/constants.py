"""
Application constants
"""

# Message Types
class MessageType:
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"
    ADMIN = "admin"
    ERROR = "error"
    TYPING = "typing"
    READ_RECEIPT = "read_receipt"

# WebSocket Message Types
class WSMessageType:
    CONNECT = "connect"
    MESSAGE = "message"
    TYPING = "typing"
    READ = "read"
    DISCONNECT = "disconnect"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"

# Error Codes
class ErrorCode:
    # WebSocket errors
    WS_NORMAL_CLOSE = 1000
    WS_GOING_AWAY = 1001
    WS_PROTOCOL_ERROR = 1002
    WS_UNSUPPORTED_DATA = 1003
    WS_NO_STATUS_RECEIVED = 1005
    WS_ABNORMAL_CLOSURE = 1006
    WS_INVALID_PAYLOAD = 1007
    WS_POLICY_VIOLATION = 1008
    WS_MESSAGE_TOO_BIG = 1009
    WS_INTERNAL_ERROR = 1011
    WS_SERVICE_RESTART = 1012
    WS_TRY_AGAIN_LATER = 1013
    
    # Application errors
    SESSION_EXPIRED = 4001
    RATE_LIMITED = 4002
    INVALID_MESSAGE = 4003
    FILE_TOO_LARGE = 4004
    INVALID_FILE_TYPE = 4005
    UNAUTHORIZED = 4006

# Session Status
class SessionStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    BANNED = "banned"

# File size limits (in bytes)
FILE_SIZE_LIMITS = {
    "image": 10 * 1024 * 1024,  # 10MB
    "voice": 20 * 1024 * 1024,  # 20MB
    "video": 50 * 1024 * 1024,  # 50MB
    "document": 50 * 1024 * 1024,  # 50MB
}

# MIME type mappings
MIME_TYPE_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "video/mp4": ".mp4",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
}

# Default values
DEFAULT_VALUES = {
    "SESSION_TIMEOUT": 86400,  # 24 hours
    "MAX_SESSIONS": 1000,
    "RATE_LIMIT": 100,  # messages per minute
    "WEBSOCKET_TIMEOUT": 30,  # seconds
    "RECONNECT_DELAY": 5,  # seconds
}

# Response messages
RESPONSE_MESSAGES = {
    "welcome": "👋 Welcome to the chat! An admin will respond shortly.",
    "session_expired": "⚠️ Your session has expired. Please refresh the page.",
    "rate_limited": "⚠️ You're sending messages too fast. Please wait a moment.",
    "file_too_large": "⚠️ File is too large. Maximum size is {size}.",
    "invalid_file": "⚠️ File type not allowed.",
    "connection_lost": "⚠️ Connection lost. Reconnecting...",
    "reconnected": "✅ Reconnected successfully.",
    "admin_online": "💬 Admin is online.",
    "admin_offline": "⏳ Admin is currently offline. Your message will be delivered when they're back.",
}

# Telegram formatting
TELEGRAM_FORMATTING = {
    "bold": "*{}*",
    "italic": "_{}_",
    "code": "`{}`",
    "pre": "```{}```",
    "link": "[{}]({})",
}
