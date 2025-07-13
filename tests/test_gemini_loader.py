#!/usr/bin/env python3
"""Tests for the Gemini conversation loader."""

import tempfile
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from ccsm.core.gemini_loader import (
    load_gemini_conversations,
    load_gemini_conversation,
    parse_gemini_message,
    parse_timestamp,
    generate_title,
)
from ccsm.core.models import Conversation, Message, MessageRole

class TestGeminiLoader:
    """Test the Gemini loader functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def create_gemini_checkpoint(self, temp_dir):
        """Helper to create a dummy Gemini checkpoint file."""
        def _creator(session_id, checkpoint_name, messages_data):
            session_path = temp_dir / session_id
            session_path.mkdir(exist_ok=True)
            file_path = session_path / checkpoint_name
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(messages_data, f)
            return file_path
        return _creator

    def test_load_empty_directory(self, temp_dir):
        """Test loading from an empty directory."""
        conversations = load_gemini_conversations(str(temp_dir))
        assert conversations == []

    def test_load_single_valid_checkpoint(self, create_gemini_checkpoint):
        """Test loading a single valid Gemini checkpoint file."""
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        messages_data = [
            {"role": "user", "parts": [{"text": "Hello Gemini!"}], "timestamp": timestamp},
            {"role": "model", "parts": [{"text": "Hi there!"}], "timestamp": timestamp},
        ]
        file_path = create_gemini_checkpoint("session1", "checkpoint-000000.json", messages_data)

        conversations = load_gemini_conversations(str(file_path))
        assert len(conversations) == 1
        conv = conversations[0]
        assert conv.id == "session1"
        assert conv.title == "Hello Gemini!"
        assert len(conv.messages) == 2
        assert conv.messages[0].role == MessageRole.USER
        assert conv.messages[0].content == "Hello Gemini!"
        assert conv.messages[1].role == MessageRole.ASSISTANT
        assert conv.messages[1].content == "Hi there!"
        assert conv.create_time is not None
        assert conv.update_time is not None
        assert conv.metadata["source"] == "gemini"
        assert conv.metadata["file"] == str(file_path)

    def test_load_directory_with_multiple_checkpoints(self, create_gemini_checkpoint, temp_dir):
        """Test loading from a directory with multiple valid Gemini checkpoint files."""
        timestamp1 = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        timestamp2 = datetime(2023, 1, 2, 11, 0, 0, tzinfo=timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

        create_gemini_checkpoint("sessionA", "checkpoint-000000.json", [
            {"role": "user", "parts": [{"text": "First session query"}], "timestamp": timestamp1}
        ])
        create_gemini_checkpoint("sessionB", "checkpoint-000000.json", [
            {"role": "user", "parts": [{"text": "Second session query"}], "timestamp": timestamp2}
        ])
        create_gemini_checkpoint("sessionC", "checkpoint-000000.json", [
            {"role": "user", "parts": [{"text": "Third session query"}], "timestamp": timestamp1}
        ])

        conversations = load_gemini_conversations(str(temp_dir))
        assert len(conversations) == 3
        # Should be sorted by create_time (newest first)
        assert conversations[0].title == "Second session query"
        assert conversations[1].title == "First session query" or conversations[1].title == "Third session query"
        assert conversations[2].title == "First session query" or conversations[2].title == "Third session query"

    def test_load_malformed_json(self, temp_dir):
        """Test handling of malformed JSON files."""
        session_path = temp_dir / "bad_session"
        session_path.mkdir()
        file_path = session_path / "checkpoint-000000.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("{invalid json")

        conversations = load_gemini_conversations(str(file_path))
        assert conversations == []

    def test_parse_gemini_message_user_role(self):
        """Test parsing a user message."""
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        data = {"role": "user", "parts": [{"text": "User input here"}], "timestamp": timestamp}
        message = parse_gemini_message(data)
        assert message is not None
        assert message.role == MessageRole.USER
        assert message.content == "User input here"
        assert message.create_time is not None
        assert isinstance(message.id, str)

    def test_parse_gemini_message_assistant_role(self):
        """Test parsing an assistant message."""
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        data = {"role": "model", "parts": [{"text": "Assistant response"}], "timestamp": timestamp}
        message = parse_gemini_message(data)
        assert message is not None
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Assistant response"

    def test_parse_gemini_message_with_message_field(self):
        """Test parsing a message with 'message' field instead of 'parts'."""
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        data = {"role": "user", "message": "Legacy message content", "timestamp": timestamp}
        message = parse_gemini_message(data)
        assert message is not None
        assert message.content == "Legacy message content"

    def test_parse_gemini_message_empty_content(self):
        """Test parsing a message with empty content."""
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        data = {"role": "user", "parts": [], "timestamp": timestamp}
        message = parse_gemini_message(data)
        assert message is None

        data = {"role": "user", "message": "", "timestamp": timestamp}
        message = parse_gemini_message(data)
        assert message is None

    def test_parse_gemini_message_unsupported_type(self):
        """Test parsing a message with an unsupported type."""
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        data = {"role": "system", "parts": [{"text": "System message"}], "timestamp": timestamp}
        message = parse_gemini_message(data)
        assert message is None

    def test_parse_timestamp_valid(self):
        """Test parsing a valid ISO timestamp."""
        timestamp_str = "2023-10-27T10:00:00.123Z"
        timestamp_float = parse_timestamp(timestamp_str)
        assert timestamp_float == datetime(2023, 10, 27, 10, 0, 0, 123000, tzinfo=timezone.utc).timestamp()

    def test_parse_timestamp_invalid(self):
        """Test parsing an invalid timestamp string."""
        assert parse_timestamp("invalid-date") is None
        assert parse_timestamp(None) is None
        assert parse_timestamp("") is None

    def test_generate_title_from_user_message(self):
        """Test title generation from the first user message."""
        messages = [
            Message(id="1", role=MessageRole.ASSISTANT, content="Hello!"),
            Message(id="2", role=MessageRole.USER, content="My query is about Python."),
            Message(id="3", role=MessageRole.ASSISTANT, content="Okay."),
        ]
        title = generate_title(messages)
        assert title == "My query is about Python."

    def test_generate_title_from_long_user_message(self):
        """Test title generation from a long user message, truncated."""
        long_content = "A very long user query that should be truncated because it exceeds the maximum length allowed for a conversation title in the UI."
        messages = [
            Message(id="1", role=MessageRole.USER, content=long_content),
        ]
        title = generate_title(messages)
        assert len(title) <= 80
        assert title == long_content[:80]

    def test_generate_title_from_create_time(self):
        """Test title generation from create time if no user message."""
        create_time = datetime(2023, 5, 15, 14, 30, 0, tzinfo=timezone.utc).timestamp()
        messages = [
            Message(id="1", role=MessageRole.ASSISTANT, content="Only assistant messages.", create_time=create_time),
        ]
        title = generate_title(messages)
        assert title == "Gemini session 2023-05-15 14:30"

    def test_generate_title_default(self):
        """Test default title generation if no user message or create time."""
        messages = []
        title = generate_title(messages)
        assert title == "Gemini conversation"

        messages_no_time = [
            Message(id="1", role=MessageRole.ASSISTANT, content="No user message, no time."),
        ]
        title = generate_title(messages_no_time)
        assert title == "Gemini conversation"
