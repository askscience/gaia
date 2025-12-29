"""
Chat storage module for auto-saving and loading chat conversations.
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class ChatStorage:
    """Handles auto-saving and loading of chat conversations."""
    
    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            # Default to XDG data directory
            xdg_data = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
            self.storage_dir = Path(xdg_data) / 'gaia' / 'chats'
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def create_chat(self, title: str = "New Chat") -> dict:
        """Create a new chat with a unique ID."""
        chat_id = str(uuid.uuid4())
        chat = {
            'id': chat_id,
            'title': title,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'history': []
        }
        self.save_chat(chat)
        return chat
    
    def save_chat(self, chat: dict) -> None:
        """Save a chat to disk."""
        chat['updated_at'] = datetime.now().isoformat()
        file_path = self.storage_dir / f"{chat['id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(chat, f, indent=2, ensure_ascii=False)
    
    def load_chat(self, chat_id: str, limit_messages: Optional[int] = None) -> Optional[dict]:
        """Load a single chat by ID. If limit_messages is provided, only load the most recent messages."""
        file_path = self.storage_dir / f"{chat_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                chat = json.load(f)
                # If limit is set, truncate history to the most recent messages
                if limit_messages and 'history' in chat and len(chat['history']) > limit_messages:
                    chat['history'] = chat['history'][-limit_messages:]
                return chat
        return None
    
    def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat file."""
        file_path = self.storage_dir / f"{chat_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def list_chats(self) -> list[dict]:
        """List all saved chats with metadata only (no history), sorted by updated_at (newest first)."""
        chats = []
        for file_path in self.storage_dir.glob('*.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chat = json.load(f)
                    # Only return metadata, not full history for better performance
                    chats.append({
                        'id': chat['id'],
                        'title': chat.get('title', 'New Chat'),
                        'created_at': chat.get('created_at', ''),
                        'updated_at': chat.get('updated_at', ''),
                        '_history_length': len(chat.get('history', []))
                    })
            except (json.JSONDecodeError, KeyError):
                # Skip corrupted files
                continue
        
        # Sort by updated_at, newest first
        chats.sort(key=lambda c: c.get('updated_at', ''), reverse=True)
        return chats
    
    def update_chat_title(self, chat_id: str, title: str) -> None:
        """Update a chat's title."""
        chat = self.load_chat(chat_id)
        if chat:
            chat['title'] = title
            self.save_chat(chat)
    
    def add_message(self, chat_id: str, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Add a message to a chat and save."""
        chat = self.load_chat(chat_id)
        if chat:
            message = {
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            if metadata:
                message['metadata'] = metadata
                
            chat['history'].append(message)
            
            # Auto-generate title from first user message if still "New Chat"
            if chat['title'] == "New Chat" and role == 'user':
                # Use first 30 chars of first message as title
                chat['title'] = content[:30] + ('...' if len(content) > 30 else '')
            self.save_chat(chat)
