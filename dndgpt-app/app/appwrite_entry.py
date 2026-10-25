"""Appwrite's asynchronous function entrypoint for the existing ASGI service."""
import os
from functools import lru_cache
from urllib.parse import urlsplit

import httpx

from .appwrite_store import AppwriteAPI, AppwriteStore
from .auth import AuthConfig, JwtVerifier
from .engine import EngineError


@lru_cache(maxsize=2)
def verifier(config):
    return JwtVerifier(config)


async def dispatch(context, application, resource_url):
    origin = urlsplit(resource_url)
    path = context.req.path
    if not isinstance(path, str) or not path.startswith("/") or path.startswith("//"):
        return context.res.json({"detail": "Invalid request path"}, 400)
    host = context.req.headers.get("host", context.req.host)
    if host.lower() != origin.netloc.lower():
        return context.res.json({"detail": "Unrecognized service host"}, 421)
    body = context.req.body_binary
    if isinstance(body, str):
        body = body.encode()
    if not isinstance(body, (bytes, bytearray)) or len(body) > 2500000:
        return context.res.json({"detail": "Invalid or oversized request body"}, 413)
    headers = {key: value for key, value in context.req.headers.items()
               if key.lower() not in {"host", "content-length", "connection", "transfer-encoding"}
               and not key.lower().startswith("x-appwrite-")}
    query = context.req.query_string
    target = path + ("?" + query if query else "")
    async with application.router.lifespan_context(application):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application),
                                    base_url=origin.scheme + "://" + origin.netloc,
                                    follow_redirects=False) as client:
            response = await client.request(context.req.method, target, content=body, headers=headers)
    output_headers = {key: value for key, value in response.headers.items()
                      if key.lower() not in {"content-length", "connection", "transfer-encoding"}}
    return context.res.binary(response.content, response.status_code, output_headers)


async def main(context):
    client = httpx.Client(timeout=15, follow_redirects=False)
    try:
        api = AppwriteAPI(os.environ["APPWRITE_FUNCTION_API_ENDPOINT"],
                          os.environ["APPWRITE_FUNCTION_PROJECT_ID"],
                          context.req.headers.get("x-appwrite-key", ""), client=client)
        store = AppwriteStore(api, os.getenv("DNDGPT_APPWRITE_DATABASE", "dndgpt"),
                              os.getenv("DNDGPT_APPWRITE_TABLE", "records"))
        config = AuthConfig.from_env()
        if context.req.path == "/api/hosting-readiness" and context.req.method == "GET":
            store.initialize()
            return context.res.json({"hosting": "appwrite", "database": "configured",
                                     "oauth_configured": config.configured,
                                     "chatgpt_acceptance": "pending", "model_api_calls": False})
        if os.getenv("DNDGPT_ENV") != "production" or not config.configured:
            return context.res.json({"detail": "Hosted OAuth configuration is pending"}, 503)
        config.validate()
        from .server import create_app
        application = create_app(auth_config=config, token_verifier=verifier(config), store=store)
        return await dispatch(context, application, config.resource_url)
    except EngineError as error:
        if hasattr(error, "upstream_status") and callable(getattr(context, "error", None)):
            context.error(f"Hosted storage rejected request: status={error.upstream_status} type={error.upstream_type}")
        return context.res.json({"code": error.code, "detail": str(error)}, error.status)
    except (KeyError, ValueError):
        return context.res.json({"detail": "Hosted configuration is incomplete"}, 503)
    finally:
        client.close()
