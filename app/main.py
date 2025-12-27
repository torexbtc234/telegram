"""
Main FastAPI application with WebSocket and REST endpoints
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config.config import settings
from app.websocket_server import WebSocketManager
from app.telegram_bot import TelegramBot
from app.session_manager import SessionManager
from models.message import Message, MessageType

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
websocket_manager = None
telegram_bot = None
session_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    global websocket_manager, telegram_bot, session_manager
    
    # Startup
    logger.info("Starting Telegram WebSocket Bridge...")
    
    # Initialize managers
    session_manager = SessionManager()
    websocket_manager = WebSocketManager(session_manager)
    
    # Initialize Telegram bot
    telegram_bot = TelegramBot(websocket_manager, session_manager)
    
    # Start background tasks
    asyncio.create_task(websocket_manager.start())
    asyncio.create_task(telegram_bot.start())
    asyncio.create_task(session_manager.cleanup_old_sessions())
    
    logger.info(f"Server started on {settings.HOST}:{settings.PORT}")
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await websocket_manager.stop()
    await telegram_bot.stop()
    await session_manager.cleanup()

# Create FastAPI app
app = FastAPI(
    title="Telegram WebSocket Bridge",
    description="Real-time communication between website visitors and Telegram admins",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
if settings.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Telegram WebSocket Bridge",
        "version": "1.0.0",
        "active_sessions": len(session_manager.sessions) if session_manager else 0,
    }

@app.get("/health")
async def health_check():
    """Health check with detailed status"""
    status = {
        "websocket": websocket_manager.is_running if websocket_manager else False,
        "telegram_bot": telegram_bot.is_running if telegram_bot else False,
        "sessions": len(session_manager.sessions) if session_manager else 0,
        "uptime": session_manager.get_uptime() if session_manager else 0,
    }
    return JSONResponse(content=status)

@app.get("/stats")
async def get_stats():
    """Get server statistics"""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    stats = session_manager.get_statistics()
    return JSONResponse(content=stats)

@app.get("/sessions")
async def get_active_sessions():
    """Get active visitor sessions"""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    sessions = session_manager.get_active_sessions()
    return JSONResponse(content=sessions)

@app.post("/message")
async def send_message(message: Message):
    """Send a message from visitor (REST fallback)"""
    if not websocket_manager:
        raise HTTPException(status_code=503, detail="WebSocket manager not available")
    
    # Validate session
    if not session_manager.validate_session(message.session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Send to Telegram via WebSocket manager
    await websocket_manager.send_to_telegram(message)
    
    return {"status": "sent", "message_id": message.id}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication"""
    if not websocket_manager:
        await websocket.close(code=1011, reason="Server error")
        return
    
    # Validate origin
    origin = websocket.headers.get("origin")
    if origin not in settings.ALLOWED_ORIGINS.split(",") and not settings.DEBUG:
        await websocket.close(code=1008, reason="Origin not allowed")
        return
    
    await websocket_manager.handle_connection(websocket, session_id)

@app.post("/upload")
async def upload_file():
    """Handle file uploads (fallback for non-WebSocket clients)"""
    # Implementation for file upload handling
    return {"status": "File upload endpoint"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )
