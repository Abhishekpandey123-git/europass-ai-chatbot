import sys
from unittest.mock import MagicMock

# Prevent tests from requiring a real Gemini API key.
mock_genai = MagicMock()
sys.modules["google.genai"] = mock_genai

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_chat_start():
    response = client.get("/api/chat/start")
    assert response.status_code == 200


def test_chat_message_validation():
    response = client.post("/api/chat/message", json={})
    assert response.status_code in (400, 422)


def test_generate_pdf_missing_session():
    response = client.get("/api/generate-pdf/nonexistent-session")
    assert response.status_code in (404, 400)
