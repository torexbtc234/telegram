"""
Telegram bot handler for admin communication
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, List

from telegram import Update, Bot, Message as TelegramMessage
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackContext,
)
from telegram.constants import ParseMode

from config.config import settings
from models.message import Message, MessageType
from app.websocket_server import WebSocketManager
from app.session_manager import SessionManager
from app.file_handler import FileHandler

logger = logging.getLogger(__name__)

class TelegramBot:
    """Handles Telegram bot communication with admin group"""
    
    def __init__(self, websocket_manager: WebSocketManager, session_manager: SessionManager):
        self.websocket_manager = websocket_manager
        self.session_manager = session_manager
        self.file_handler = FileHandler()
        self.application: Optional[Application] = None
        self.is_running = False
        
        # Store message mapping for replies
        self.message_map: Dict[int, str] = {}  # telegram_message_id -> session_id
        
    async def start(self):
        """Start the Telegram bot"""
        try:
            # Create application
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
            
            # Add handlers
            self._setup_handlers()
            
            # Start polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            logger.info("Telegram bot started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            raise
    
    async def stop(self):
        """Stop the Telegram bot"""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        self.is_running = False
        logger.info("Telegram bot stopped")
    
    def _setup_handlers(self):
        """Setup Telegram bot command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("sessions", self._sessions_command))
        self.application.add_handler(CommandHandler("stats", self._stats_command))
        self.application.add_handler(CommandHandler("broadcast", self._broadcast_command))
        
        # Message handlers
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_text_message
            )
        )
        
        # Voice message handler
        self.application.add_handler(
            MessageHandler(
                filters.VOICE,
                self._handle_voice_message
            )
        )
        
        # Photo handler
        self.application.add_handler(
            MessageHandler(
                filters.PHOTO,
                self._handle_photo_message
            )
        )
        
        # Document handler
        self.application.add_handler(
            MessageHandler(
                filters.DOCUMENT,
                self._handle_document_message
            )
        )
        
        # Reply handler (for replying to visitor messages)
        self.application.add_handler(
            MessageHandler(
                filters.REPLY,
                self._handle_reply_message
            )
        )
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "🤖 *Website Chat Bridge Bot*\n\n"
            "I bridge website visitors with this Telegram group.\n\n"
            "*Available commands:*\n"
            "/sessions - Show active visitor sessions\n"
            "/stats - Show server statistics\n"
            "/broadcast - Send message to all visitors\n"
            "/help - Show this help message\n\n"
            "To reply to a visitor, simply reply to their message in this group.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            "💡 *How to use this bot:*\n\n"
            "1. Visitors connect via website\n"
            "2. Their messages appear here\n"
            "3. Reply to any message to respond to that visitor\n"
            "4. Use /broadcast to message all visitors\n"
            "5. Use /sessions to see who's online\n\n"
            "*Tip:* You can send text, voice notes, photos, and files!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _sessions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sessions command - show active sessions"""
        sessions = self.session_manager.get_active_sessions()
        
        if not sessions:
            await update.message.reply_text("No active visitor sessions.")
            return
        
        response = "👥 *Active Visitor Sessions:*\n\n"
        for session in sessions[:10]:  # Limit to 10
            duration = self.session_manager.get_session_duration(session["session_id"])
            response += f"• Session: `{session['session_id'][:8]}...`\n"
            response += f"  Duration: {duration}\n"
            response += f"  Messages: {session.get('message_count', 0)}\n"
            if session.get('user_agent'):
                response += f"  Browser: {session['user_agent'][:30]}...\n"
            response += "\n"
        
        if len(sessions) > 10:
            response += f"... and {len(sessions) - 10} more sessions"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show statistics"""
        stats = self.session_manager.get_statistics()
        
        response = (
            "📊 *Server Statistics:*\n\n"
            f"• Active sessions: {stats['active_sessions']}\n"
            f"• Total sessions today: {stats['total_sessions_today']}\n"
            f"• Messages today: {stats['messages_today']}\n"
            f"• Uptime: {stats['uptime']}\n"
            f"• Memory usage: {stats['memory_usage_mb']} MB\n"
        )
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
    
    async def _broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command - send to all visitors"""
        if not context.args:
            await update.message.reply_text(
                "Usage: /broadcast Your message here\n"
                "Sends message to all connected visitors."
            )
            return
        
        message_text = " ".join(context.args)
        
        # Create broadcast message
        broadcast_msg = Message(
            id=str(uuid.uuid4()),
            session_id="broadcast",
            content=f"📢 Admin Broadcast: {message_text}",
            message_type=MessageType.ADMIN,
            timestamp=datetime.now().isoformat(),
            metadata={"from_admin": update.effective_user.username or "Admin"}
        )
        
        # Send to all connected clients
        await self.websocket_manager.broadcast(broadcast_msg)
        
        # Count recipients
        active_count = len(self.websocket_manager.connections)
        
        await update.message.reply_text(
            f"Broadcast sent to {active_count} active visitor(s)."
        )
    
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages (not replies)"""
        # Check if message is in admin group
        if update.effective_chat.id != int(settings.TELEGRAM_GROUP_ID):
            return
        
        # This is a new message (not a reply), treat as general admin message
        message_text = update.message.text
        
        # Create message for all visitors
        broadcast_msg = Message(
            id=str(uuid.uuid4()),
            session_id="admin_broadcast",
            content=f"💬 Admin: {message_text}",
            message_type=MessageType.ADMIN,
            timestamp=datetime.now().isoformat(),
            metadata={
                "from_admin": update.effective_user.username or "Admin",
                "telegram_message_id": update.message.message_id
            }
        )
        
        # Store mapping for potential replies
        self.message_map[update.message.message_id] = "broadcast"
        
        # Send to all visitors
        await self.websocket_manager.broadcast(broadcast_msg)
    
    async def _handle_reply_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle reply messages to visitor messages"""
        if not update.message.reply_to_message:
            return
        
        replied_message = update.message.reply_to_message
        session_id = self.message_map.get(replied_message.message_id)
        
        if not session_id:
            await update.message.reply_text(
                "⚠️ Cannot identify which visitor to reply to. "
                "Please reply directly to a visitor's message."
            )
            return
        
        # Create response message
        response_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            content=update.message.text or "📎 File/Media message",
            message_type=MessageType.ADMIN,
            timestamp=datetime.now().isoformat(),
            metadata={
                "from_admin": update.effective_user.username or "Admin",
                "in_reply_to": replied_message.message_id,
                "telegram_message_id": update.message.message_id
            }
        )
        
        # Send to specific visitor
        if session_id == "broadcast":
            await self.websocket_manager.broadcast(response_msg)
        else:
            await self.websocket_manager.send_to_client(session_id, response_msg)
        
        # Log the reply
        logger.info(f"Admin reply to {session_id}: {update.message.text[:50]}...")
    
    async def _handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages from admin"""
        voice = update.message.voice
        
        # Download voice file
        voice_file = await voice.get_file()
        voice_data = await voice_file.download_as_bytearray()
        
        # Store mapping for replies
        if update.message.reply_to_message:
            replied_id = update.message.reply_to_message.message_id
            session_id = self.message_map.get(replied_id, "broadcast")
        else:
            session_id = "broadcast"
        
        self.message_map[update.message.message_id] = session_id
        
        # Create message
        voice_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            content="🎤 Voice message from admin",
            message_type=MessageType.VOICE,
            timestamp=datetime.now().isoformat(),
            metadata={
                "from_admin": update.effective_user.username or "Admin",
                "voice_duration": voice.duration,
                "file_size": len(voice_data),
                "telegram_message_id": update.message.message_id
            }
        )
        
        # Send to visitor(s)
        if session_id == "broadcast":
            await self.websocket_manager.broadcast(voice_msg)
        else:
            await self.websocket_manager.send_to_client(session_id, voice_msg)
    
    async def _handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages from admin"""
        photo = update.message.photo[-1]  # Get highest resolution
        
        # Download photo
        photo_file = await photo.get_file()
        photo_data = await photo_file.download_as_bytearray()
        
        # Determine session
        if update.message.reply_to_message:
            replied_id = update.message.reply_to_message.message_id
            session_id = self.message_map.get(replied_id, "broadcast")
        else:
            session_id = "broadcast"
        
        self.message_map[update.message.message_id] = session_id
        
        # Create message
        photo_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            content="🖼️ Photo from admin",
            message_type=MessageType.IMAGE,
            timestamp=datetime.now().isoformat(),
            metadata={
                "from_admin": update.effective_user.username or "Admin",
                "file_size": len(photo_data),
                "telegram_message_id": update.message.message_id
            }
        )
        
        # Send to visitor(s)
        if session_id == "broadcast":
            await self.websocket_manager.broadcast(photo_msg)
        else:
            await self.websocket_manager.send_to_client(session_id, photo_msg)
    
    async def _handle_document_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document/file messages from admin"""
        document = update.message.document
        
        # Download document
        doc_file = await document.get_file()
        doc_data = await doc_file.download_as_bytearray()
        
        # Determine session
        if update.message.reply_to_message:
            replied_id = update.message.reply_to_message.message_id
            session_id = self.message_map.get(replied_id, "broadcast")
        else:
            session_id = "broadcast"
        
        self.message_map[update.message.message_id] = session_id
        
        # Create message
        doc_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            content=f"📎 {document.file_name} from admin",
            message_type=MessageType.FILE,
            timestamp=datetime.now().isoformat(),
            metadata={
                "from_admin": update.effective_user.username or "Admin",
                "file_name": document.file_name,
                "file_size": document.file_size,
                "mime_type": document.mime_type,
                "telegram_message_id": update.message.message_id
            }
        )
        
        # Send to visitor(s)
        if session_id == "broadcast":
            await self.websocket_manager.broadcast(doc_msg)
        else:
            await self.websocket_manager.send_to_client(session_id, doc_msg)
    
    async def send_to_telegram_group(self, message: Message):
        """Send visitor message to Telegram group"""
        if not self.application:
            logger.error("Telegram bot not initialized")
            return None
        
        try:
            bot = self.application.bot
            
            # Format message based on type
            if message.message_type == MessageType.TEXT:
                formatted_msg = (
                    f"👤 *Visitor Message*\n\n"
                    f"`{message.content}`\n\n"
                    f"*Session:* `{message.session_id[:8]}...`\n"
                    f"*Time:* {message.timestamp}"
                )
                
                sent_message = await bot.send_message(
                    chat_id=settings.TELEGRAM_GROUP_ID,
                    text=formatted_msg,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Store mapping for replies
                self.message_map[sent_message.message_id] = message.session_id
                return sent_message.message_id
                
            elif message.message_type == MessageType.VOICE:
                # For voice, we would send the actual voice file
                # This requires the file path in metadata
                formatted_msg = (
                    f"🎤 *Visitor Voice Message*\n\n"
                    f"*Session:* `{message.session_id[:8]}...`\n"
                    f"*Time:* {message.timestamp}"
                )
                
                sent_message = await bot.send_message(
                    chat_id=settings.TELEGRAM_GROUP_ID,
                    text=formatted_msg,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                self.message_map[sent_message.message_id] = message.session_id
                return sent_message.message_id
                
            elif message.message_type == MessageType.IMAGE:
                formatted_msg = (
                    f"🖼️ *Visitor Image*\n\n"
                    f"*Session:* `{message.session_id[:8]}...`\n"
                    f"*Time:* {message.timestamp}"
                )
                
                sent_message = await bot.send_message(
                    chat_id=settings.TELEGRAM_GROUP_ID,
                    text=formatted_msg,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                self.message_map[sent_message.message_id] = message.session_id
                return sent_message.message_id
                
            else:
                formatted_msg = (
                    f"📎 *Visitor File*\n\n"
                    f"`{message.content}`\n\n"
                    f"*Session:* `{message.session_id[:8]}...`\n"
                    f"*Time:* {message.timestamp}"
                )
                
                sent_message = await bot.send_message(
                    chat_id=settings.TELEGRAM_GROUP_ID,
                    text=formatted_msg,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                self.message_map[sent_message.message_id] = message.session_id
                return sent_message.message_id
                
        except Exception as e:
            logger.error(f"Failed to send message to Telegram: {e}")
            return None
