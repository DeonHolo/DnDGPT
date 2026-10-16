"""Disposable public UI probe. No campaign, database, credentials or inference access."""
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import (CallToolResult, ReadResourceRequest, ReadResourceResult,
                       ServerResult, TextContent, TextResourceContents, ToolAnnotations)
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route


def create_probe(origin=None):
    origin = origin or os.environ.get("DNDGPT_PROBE_ORIGIN", "http://127.0.0.1:8767")
    parsed = urlsplit(origin)
    if (parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/") or not parsed.hostname
            or (parsed.scheme != "https" and parsed.hostname not in ("127.0.0.1", "localhost"))):
        raise ValueError("Use an HTTPS origin or loopback HTTP origin")
    html = Path(__file__).with_suffix(".html").read_text(encoding="utf-8")
    # Share only static styling/navigation; never include engine/tool execution code.
    source = (Path(__file__).resolve().parents[1] / "app/index.html").read_text(encoding="utf-8")
    css = source.split("<style>", 1)[1].split("</style>", 1)[0]
    html = html.replace("/* SHARED_COMPANION_CSS */", css)
    nav = '<nav id="sectionNav"' + source.split('<nav id="sectionNav"', 1)[1].split("</nav>", 1)[0] + "</nav>"
    navigation = source.split('<script id="companionNavigation">', 1)[1].split("</script>", 1)[0]
    html = html.replace("<!-- SHARED_COMPANION_NAV -->", nav)
    html = html.replace("/* SHARED_COMPANION_NAVIGATION */", navigation)
    uri = "ui://dndgpt/pip-probe-" + hashlib.sha256(html.encode()).hexdigest()[:12] + ".html"
    server = FastMCP(
        "DnDGPT PiP compatibility test", stateless_http=True, json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[parsed.netloc, "127.0.0.1:*", "localhost:*"],
            allowed_origins=[origin.rstrip("/")] ))
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                           idempotentHint=True, openWorldHint=False)
    security = [{"type": "noauth"}]
    render_meta = {"securitySchemes": security,
                   "ui": {"resourceUri": uri}, "openai/outputTemplate": uri,
                   "openai/widgetAccessible": True}

    @server.tool(annotations=read, meta=render_meta)
    def render_pip_probe() -> CallToolResult:
        """Open the development-only PiP test card. Dummy data only; never starts gameplay.
        The user can request PiP and send a neutral test message. Do not claim PiP works
        until the actual client visibly grants it. Do not substitute Work for regular Chat.
        """
        return CallToolResult(content=[TextContent(type="text", text="Development-only PiP test; no game access.")],
                              structuredContent={"dummy_hp": 20, "campaign_access": False})

    @server.tool(annotations=read, meta={"securitySchemes": security,
                 "ui": {"visibility": ["app", "model"]}, "openai/widgetAccessible": True})
    def get_probe_status() -> CallToolResult:
        """Read the test server's UTC clock. No campaign, database, randomness or writes."""
        data = {"dummy_hp": 20, "source_utc": datetime.now(timezone.utc).isoformat(),
                "campaign_access": False}
        return CallToolResult(content=[TextContent(type="text", text=data["source_utc"])],
                              structuredContent=data)

    ui_meta = {"ui": {"prefersBorder": True, "csp": {"connectDomains": [], "resourceDomains": []}},
               "openai/widgetDescription": "Development-only PiP capability and button-to-chat test.",
               "openai/widgetCSP": {"connect_domains": [], "resource_domains": []}}

    @server.resource(uri, mime_type="text/html;profile=mcp-app", meta=ui_meta)
    def probe_html() -> str:
        return html

    async def read_resource(request):
        if str(request.params.uri) != uri:
            raise ValueError("Unknown UI resource")
        return ServerResult(ReadResourceResult(contents=[TextResourceContents(
            uri=uri, mimeType="text/html;profile=mcp-app", text=html, _meta=ui_meta)]))

    server._mcp_server.request_handlers[ReadResourceRequest] = read_resource

    @server._mcp_server.list_tools()
    async def list_tools_with_security():
        items = await server.list_tools()
        for item in items:
            item.securitySchemes = security
        return items

    app = server.streamable_http_app()

    async def health(request):
        return JSONResponse({"purpose": "temporary-static-ui-probe", "campaign_access": False})

    async def preview(request):
        return HTMLResponse(html)

    async def no_event_stream(request):
        return JSONResponse({"error": "This stateless probe uses JSON POST only"},
                            status_code=405, headers={"Allow": "POST"})

    app.router.routes.insert(0, Route("/mcp", no_event_stream, methods=["GET"]))
    app.add_route("/health", health)
    app.add_route("/preview", preview)
    return app


if __name__ == "__main__":
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    args = parser.parse_args()
    uvicorn.run(create_probe(args.origin), host="127.0.0.1", port=8767)
