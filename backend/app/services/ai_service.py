from __future__ import annotations

import asyncio

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import settings

FALLBACK_MODELS = [
    settings.GEMINI_MODEL,
    "gemini-2.5-flash",
    "gemini-flash-latest",
]


class AIService:
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is missing. Add it to backend/.env")

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def _content_text(self, content: types.Content) -> str:
        parts = content.parts or []
        return "\n".join(part.text or "" for part in parts if getattr(part, "text", None)).strip()

    def _make_content(self, role: str, text: str) -> types.Content:
        return types.Content(
            role=role,
            parts=[types.Part.from_text(text=text)],
        )

    def _append_or_merge(self, contents: list[types.Content], role: str, text: str) -> None:
        clean = text.strip()
        if not clean:
            return

        if contents and contents[-1].role == role:
            merged = f"{self._content_text(contents[-1])}\n{clean}".strip()
            contents[-1] = self._make_content(role, merged)
            return

        contents.append(self._make_content(role, clean))

    def _history_to_contents(self, history: list, new_user_message: str) -> list[types.Content]:
        contents: list[types.Content] = []

        for item in history[-20:]:
            role = getattr(item, "role", None)
            content = getattr(item, "content", None)
            if isinstance(item, dict):
                role = item.get("role", role)
                content = item.get("content", content)

            text_content = str(content).strip() if content else ""
            if not text_content:
                continue

            gemini_role = "model" if str(role).lower() in {"assistant", "model"} else "user"
            self._append_or_merge(contents, gemini_role, text_content)

        self._append_or_merge(contents, "user", new_user_message)

        while contents and contents[0].role != "user":
            contents.pop(0)

        return contents

    def generate_ai_response(self, message: str) -> tuple[str, str]:
        last_error: APIError | None = None
        seen: set[str] = set()

        for model in FALLBACK_MODELS:
            if model in seen:
                continue
            seen.add(model)
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=message,
                )
                return response.text or "", model
            except APIError as exc:
                last_error = exc

        raise RuntimeError(f"Gemini API error: {last_error}")

    def _generate_chat_response_sync(self, user_message: str, history: list) -> str:
        contents = self._history_to_contents(history, user_message)
        last_error: Exception | None = None
        seen: set[str] = set()

        for model in FALLBACK_MODELS:
            if model in seen:
                continue
            seen.add(model)
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction="You are NeuraChat, an intelligent, helpful AI assistant.",
                        temperature=0.7,
                    ),
                )
                return response.text or ""
            except APIError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc

        raise RuntimeError(f"Gemini API error: {last_error}")

    async def generate_chat_response(self, user_message: str, history: list) -> str:
        return await asyncio.to_thread(
            self._generate_chat_response_sync,
            user_message,
            history,
        )


ai_service = AIService()
generate_ai_response = ai_service.generate_ai_response
