from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from app.services.ai_service import generate_ai_response

router = APIRouter(tags=["AI"])


class AIRequest(BaseModel):
    prompt: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def require_text(self):
        if not (self.prompt or self.message):
            raise ValueError("Either prompt or message is required")
        return self

    @property
    def text(self) -> str:
        return self.prompt or self.message or ""


def _run_ai_test(request: AIRequest) -> dict:
    try:
        response, model = generate_ai_response(request.text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "success": True,
        "model": model,
        "prompt": request.text,
        "message": request.text,
        "response": response,
    }


@router.post("/test-ai")
def test_ai(request: AIRequest):
    return _run_ai_test(request)


@router.post("/ai/test")
def test_ai_legacy(request: AIRequest):
    return _run_ai_test(request)