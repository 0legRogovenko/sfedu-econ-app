import hashlib
import json

from fastapi import Request, Response


def json_with_etag(request: Request, response: Response, payload):
    """Отдаёт payload с ETag; на совпадающий If-None-Match — 304 без тела."""
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    etag = '"' + hashlib.sha256(body.encode()).hexdigest()[:32] + '"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)
    response.headers["ETag"] = etag
    return payload
