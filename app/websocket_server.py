"""
WebSocket server implementation for real-time communication
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Set, Optional
from dataclasses import dataclass, asdict

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol

from config.config import settings
from models.message import Message, MessageType
from app.session_manager import SessionManager
from app.file_handler import FileHandler

logger = logging.getLogger(__name__)

@dataclass
class ClientConnection:
    """Represents a connected WebSocket client"""
    websocket: WebSocketServerProtocol
    session_id: str
    connected_at: datetime
    last_activity: datetime
    user_agent: str = ""
    ip_address: str = ""

class WebSocketManager:
    """Manages WebSocket connections and message routing"""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.file_handler = FileHandler()
        self.connections: Dict[str, ClientConnection] = {}
        self.server = None
        self.is_running = False
        
    async def start(self):
        """Start the WebSocket server"""
        try:
            self.server = await websockets.serve(
                self._handle_client,
                settings.HOST,
                settings.PORT,
                ping_interval=settings.WS_PING_INTERVAL,
                ping_timeout=settings.WS_PING_TIMEOUT,
                max_size=settings.WS_MAX_SIZE,
            )
            self.is_running = True
            logger.info(f"WebSocket server started on ws://{settings.HOST}:{settings.PORT}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop(self):
        """Stop the WebSocket server"""
        self.is_running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connection"""
        session_id = path.strip("/")
        if not session_id or session_id == "ws":
            # Generate new session ID
            session_id = str(uuid.uuid4())
        
        # Get client info
        headers = dict(websocket.request_headers)
        user_agent = headers.get("User-Agent", "")
        ip_address = headers.get("X-Forwarded-For", websocket.remote_address[0])
        
        # Create connection record
        connection = ClientConnection(
            websocket=websocket,
            session_id=session_id,
            connected_at=datetime.now(),
            last_activity=datetime.now(),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        
        # Register connection
        self.connections[session_id] = connection
        self.session_manager.create_session(session_id, {
            "user_agent": user_agent,
            "ip_address": ip_address,
            "connected_at": connection.connected_at.isoformat(),
        })
        
        logger.info(f"New connection: {session_id} from {ip_address}")
        
        try:
            # Send welcome message with session ID
            welcome_msg = Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                content="Connected to chat server",
                message_type=MessageType.SYSTEM,
                timestamp=datetime.now().isoformat(),
            )
            await self.send_to_client(session_id, welcome_msg)
            
            # Handle messages from client
            async for message_data in websocket:
                await self._process_client_message(session_id, message_data)
                connection.last_activity = datetime.now()
                
        except ConnectionClosed:
            logger.info(f"Connection closed: {session_id}")
        except Exception as e:
            logger.error(f"Error handling client {session_id}: {e}")
        finally:
            # Cleanup
            await self._cleanup_connection(session_id)
    
    async def _process_client_message(self, session_id: str, message_data):
        """Process incoming message from client"""
        try:
            # Parse message
            if isinstance(message_data, bytes):
                # Handle binary data (files, voice)
                await self._handle_binary_message(session_id, message_data)
            else:
                # Handle JSON text messages
                data = json.loads(message_data)
                
                # Create message object
                message = Message(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    content=data.get("content", ""),
                    message_type=MessageType(data.get("type", "text")),
                    timestamp=datetime.now().isoformat(),
                    metadata=data.get("metadata", {}),
                )
                
                # Update session activity
                self.session_manager.update_session_activity(session_id)
                
                # Log message
                logger.info(f"Message from {session_id}: {message.content[:50]}...")
                
                # Send to Telegram (this would be implemented with your Telegram bot)
                await self.send_to_telegram(message)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {session_id}")
            error_msg = Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                content="Invalid message format",
                message_type=MessageType.ERROR,
                timestamp=datetime.now().isoformat(),
            )
            await self.send_to_client(session_id, error_msg)
        except Exception as e:
            logger.error(f"Error processing message from {session_id}: {e}")
    
    async def _handle_binary_message(self, session_id: str, binary_data: bytes):
        """Handle binary data (voice notes, images, files)"""
        try:
            # Process file based on metadata (first few bytes for type detection)
            file_type = await self.file_handler.detect_file_type(binary_data)
            file_path = await self.file_handler.save_temp_file(
                binary_data, 
                session_id, 
                file_type
            )
            
            # Create message for file
            message = Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                content=f"File upload: {file_type}",
                message_type=MessageType.FILE,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "file_path": file_path,
                    "file_type": file_type,
                    "file_size": len(binary_data),
                },
            )
            
            # Update session
            self.session_manager.update_session_activity(session_id)
            
            # Send to Telegram
            await self.send_to_telegram(message)
            
            # Notify client
            await self.send_to_client(session_id, Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                content="File uploaded successfully",
                message_type=MessageType.SYSTEM,
                timestamp=datetime.now().isoformat(),
            ))
            
        except Exception as e:
            logger.error(f"Error handling binary data from {session_id}: {e}")
            await self.send_to_client(session_id, Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                content="Failed to upload file",
                message_type=MessageType.ERROR,
                timestamp=datetime.now().isoformat(),
            ))
    
    async def send_to_client(self, session_id: str, message: Message):
        """Send message to specific client"""
        if session_id in self.connections:
            try:
                connection = self.connections[session_id]
                await connection.websocket.send(json.dumps(asdict(message)))
                return True
            except ConnectionClosed:
                await self._cleanup_connection(session_id)
            except Exception as e:
                logger.error(f"Error sending to {session_id}: {e}")
        return False
    
    async def broadcast(self, message: Message, exclude_session: Optional[str] = None):
        """Broadcast message to all connected clients"""
        disconnected = []
        
        for session_id, connection in self.connections.items():
            if session_id == exclude_session:
                continue
            
            try:
                await connection.websocket.send(json.dumps(asdict(message)))
            except ConnectionClosed:
                disconnected.append(session_id)
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
        
        # Cleanup disconnected clients
        for session_id in disconnected:
            await self._cleanup_connection(session_id)
    
    async def send_to_telegram(self, message: Message):
        """Send message to Telegram (to be implemented with Telegram bot)"""
        # This method will be called by the Telegram bot to forward messages
        # For now, just log it
        logger.info(f"Forwarding to Telegram: {message.content[:50]}...")
        
        # In the actual implementation, this would call Telegram bot's send method
        # await self.telegram_bot.send_message(message)
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, session_id: str):
        """Handle connection from FastAPI WebSocket endpoint"""
        await self._handle_client(websocket, f"/{session_id}")
    
    async def _cleanup_connection(self, session_id: str):
        """Cleanup connection resources"""
        if session_id in self.connections:
            connection = self.connections.pop(session_id)
            try:
                await connection.websocket.close()
            except:
                pass
            
            # Update session
            self.session_manager.end_session(session_id)
            logger.info(f"Cleaned up connection: {session_id}")
    
    def get_connection_stats(self):
        """Get connection statistics"""
        return {
            "total_connections": len(self.connections),
            "sessions": list(self.connections.keys()),
            "active_since": min(
                [conn.connected_at for conn in self.connections.values()], 
                default=None
            ),
          }
