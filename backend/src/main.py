import os
import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.config.rate_limiter import limiter
from src.routes.connection_routes import connection_router
from src.routes.agent_routes import agent_router
from src.routes.document_routes import document_router
from src.routes.calendar_routes import calendar_router
from src.mcp.mount import mount_mcp_server

app = FastAPI(title="Cadence Backend")

app_url = os.getenv("APP_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[app_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting — keyed by client IP. 120/min default on every route; the chat and
# upload endpoints carry their own tighter per-route limits (see their routers).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


@app.get("/health")
def health_check():
    db_url = os.getenv("DATABASE_URL")
    try:
        conn = psycopg2.connect(db_url)
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


app.include_router(connection_router)
app.include_router(agent_router)
app.include_router(document_router)
app.include_router(calendar_router)

# MCP server — external MCP clients (Claude Desktop, Cursor, etc.) reuse the same
# calendar tools as the in-app agent, authenticated via the same Descope session.
mount_mcp_server(app)