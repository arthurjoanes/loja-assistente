import logging
from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from loja_assistente.assistant.routes import router as assistant_router
from loja_assistente.auth.routes import router as auth_router
from loja_assistente.conversations.routes import router as conversations_router
from loja_assistente.database import get_db
from loja_assistente.observability.routes import router as operations_router
from loja_assistente.request_limits import RequestBodyLimit

logging.basicConfig(level=logging.INFO, format="%(message)s")
app = FastAPI(
    title="Loja Assistente",
    version="0.1.0",
    description="Consulta indicadores de vendas. Entre pela interface local; mutações exigem Origin e X-CSRF-Token.",
)
for router in (auth_router, assistant_router, conversations_router, operations_router):
    app.include_router(router, prefix="/api")

# The context middleware declared below wraps rejections with the same public headers.
app.add_middleware(RequestBodyLimit)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request.state.request_id = str(uuid4())
    try:
        response = await call_next(request)
    except Exception as error:
        # Exception strings from database drivers can contain bound values. Log only its type.
        logging.getLogger("loja_assistente.errors").error(
            "request_id=%s status=error error_type=%s",
            request.state.request_id,
            type(error).__name__,
        )
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "Falha na consulta. Tente novamente.",
                "request_id": request.state.request_id,
            },
        )
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Entrada inválida. Confira os campos.",
            "request_id": request.state.request_id,
        },
    )


@app.get("/api/health", tags=["Infraestrutura"])
def health(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
