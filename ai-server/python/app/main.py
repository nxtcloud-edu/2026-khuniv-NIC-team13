"""Port of ``pertineo.agent.AgentApplication`` (FastAPI entrypoint)."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.container import Container
from app.controllers import agent_controller, career_controller, parse_controller
from app.repository.dynamodb_local_init import initialize_tables

# pydantic-settings reads .env for the Settings model itself, but does NOT
# export those values into the process's os.environ. LOG_LEVEL is read via
# plain os.environ (logging has to be configured before Settings/Container
# exist), so it needs its own explicit .env load here.
load_dotenv()

# LOG_LEVEL=DEBUG (in .env or the shell) turns on verbose per-node /
# per-LLM-call logging (full prompts, raw completion, parsed output) for
# THIS APP'S code only (everything under the "app" logger namespace, i.e.
# every module using logging.getLogger(__name__) under app/).
#
# Root logger stays at INFO regardless, so noisy third-party libraries
# (botocore, urllib3, httpcore, openai's own client) don't flood the
# output with connection/signing/retry internals. Set VERBOSE_LIBS=1 too
# if you specifically need that (e.g. debugging a raw HTTP/AWS SDK issue).
_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
_VERBOSE_LIBS = os.environ.get("VERBOSE_LIBS", "0") == "1"

logging.basicConfig(
    level=logging.DEBUG if _VERBOSE_LIBS else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("app").setLevel(_LOG_LEVEL)

logger = logging.getLogger(__name__)
logger.info("App log level set to %s (library logs verbose=%s)", _LOG_LEVEL, _VERBOSE_LIBS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = Container()
    app.state.container = container

    # mirrors @Profile("local") DynamoDBLocalTableInitializer
    if container.settings.is_local_profile:
        await initialize_tables(container.dynamodb_client, container.settings.dynamodb_tables)

    try:
        yield
    finally:
        await container.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="pertineo-agent", version="0.0.1", lifespan=lifespan)
    app.include_router(agent_controller.router)
    app.include_router(parse_controller.router)
    app.include_router(career_controller.router)
    return app


app = create_app()
