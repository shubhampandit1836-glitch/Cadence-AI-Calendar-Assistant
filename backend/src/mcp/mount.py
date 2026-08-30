from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from src.mcp.calendar_tools import MCP_CALENDAR_TOOLS, handle_mcp_tool_call
from src.middleware.require_session import require_session

def mount_mcp_server(app: FastAPI):
    @app.get("/mcp")
    async def get_mcp_manifest():
        """Public capability manifest — no user data here, so no auth required."""
        return {
            "server": {"name": "cadence-calendar-mcp", "version": "1.0.0"},
            "tools": MCP_CALENDAR_TOOLS,
        }

    @app.post("/mcp/messages")
    async def post_mcp_message(request: Request, auth=Depends(require_session)):
        """Runs tool calls as the authenticated Descope session's user — never a
        hardcoded identity, so one MCP client can never read another user's calendar."""
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})

        if method == "tools/list":
            return {"tools": MCP_CALENDAR_TOOLS}
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            try:
                result = handle_mcp_tool_call(tool_name, auth["oauth_user_id"], args)
                return result
            except ValueError as e:
                return JSONResponse(status_code=404, content={"error": str(e)})
            except Exception as e:
                return JSONResponse(status_code=500, content={"error": f"MCP tool call failed: {e}"})

        return JSONResponse(status_code=400, content={"error": "Unsupported MCP method"})