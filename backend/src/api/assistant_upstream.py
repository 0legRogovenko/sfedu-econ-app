import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.schemas import AskRequest

router = APIRouter(prefix="/assistant")
ASSISTANT_ORIGIN = "https://econ-yufu-api.vercel.app"


def request_assistant(method: str, path: str, *, payload=None, params=None):
    try:
        response = requests.request(
            method,
            f"{ASSISTANT_ORIGIN}/api/assistant/{path}",
            json=payload,
            params=params,
            timeout=(4, 48),
            allow_redirects=False,
        )
        if response.status_code in (200, 422, 429):
            return JSONResponse(response.json(), status_code=response.status_code)
    except (requests.RequestException, ValueError):
        pass
    raise HTTPException(503, detail="Помощник временно недоступен")


@router.post("/ask")
def ask(payload: AskRequest):
    return request_assistant("POST", "ask", payload=payload.model_dump())


@router.delete("/data")
def forget_device(device_id: str | None = Query(default=None, max_length=64)):
    return request_assistant("DELETE", "data", params={"device_id": device_id})
