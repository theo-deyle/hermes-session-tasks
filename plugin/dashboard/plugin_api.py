"""Board routes for the Desktop pane.

The Hermes dashboard host loads this file by path with no package. It holds no relative
import and reaches the core package through `load_core`. Logic stays in core; each
handler only maps a core reply to a JSON response.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

CORE_KEY = "hermes_session_tasks_core"
SESSION_ID_MAX = 256

router = APIRouter()


def load_core() -> ModuleType:
    """Load `session_tasks` by path under a fixed key. The same module serves every request."""
    cached = sys.modules.get(CORE_KEY)
    if cached is not None:
        return cached
    init = Path(__file__).resolve().parent.parent / "session_tasks" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        CORE_KEY, init, submodule_search_locations=[str(init.parent)]
    )
    if spec is None or spec.loader is None:
        raise ImportError("cannot load the session_tasks core package")
    module = importlib.util.module_from_spec(spec)
    sys.modules[CORE_KEY] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(CORE_KEY, None)
        raise
    return module


def core_module(name: str) -> ModuleType:
    load_core()
    return importlib.import_module(f"{CORE_KEY}.{name}")


def get_api() -> Any:
    """Build the board api. It holds no state, so each request gets new objects."""
    return core_module("board_api").build()


ApiDep = Annotated[Any, Depends(get_api)]


@router.get("/board")
def read_board(
    session_id: Annotated[str, Query(min_length=1, max_length=SESSION_ID_MAX)],
    api: ApiDep,
) -> JSONResponse:
    reply = api.read(session_id)
    return JSONResponse(reply.body, status_code=reply.status)
