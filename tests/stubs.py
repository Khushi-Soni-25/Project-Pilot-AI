"""Minimal stand-ins for FastAPI and pydantic.

Used ONLY when the real packages are not installed (for example in an offline
sandbox). They let the handler functions in ``backend/app.py`` execute so that
wiring errors (wrong field names, missing imports) are caught, but they do NOT
validate types or serve HTTP. With the real packages installed, nothing here is
used and the same tests run against real pydantic models.
"""

from __future__ import annotations

import sys
import types


def real_packages_available() -> bool:
    try:
        import fastapi  # noqa: F401
        import pydantic  # noqa: F401
    except ImportError:
        return False
    return True


def install_if_needed() -> bool:
    """Install stubs when needed. Returns True if stubs are active."""
    if real_packages_available():
        return False
    if "fastapi" in sys.modules and getattr(sys.modules["fastapi"], "_is_stub", False):
        return True

    class _Missing:
        pass

    MISSING = _Missing()

    def Field(default=MISSING, **_kwargs):
        return default

    class BaseModel:
        def __init__(self, **data):
            fields: dict = {}
            for klass in reversed(type(self).__mro__):
                for name in getattr(klass, "__annotations__", {}):
                    fields[name] = getattr(klass, name, MISSING)
            unknown = set(data) - set(fields)
            if unknown:  # stricter than pydantic (which ignores extras): catch typos
                raise TypeError(f"{type(self).__name__}: unexpected fields {sorted(unknown)}")
            for name, default in fields.items():
                if name in data:
                    value = data[name]
                elif default is not MISSING:
                    value = default
                else:
                    raise TypeError(f"{type(self).__name__}: missing field {name!r}")
                setattr(self, name, value)

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail=None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class FastAPI:
        def __init__(self, *args, **kwargs):
            self.routes = {}

        def add_middleware(self, *args, **kwargs):
            pass

        def on_event(self, _name):
            return lambda fn: fn

        def _route(self, method):
            def decorator_factory(path, **_kwargs):
                def decorator(fn):
                    self.routes[(method, path)] = fn
                    return fn

                return decorator

            return decorator_factory

        def __getattr__(self, name):
            if name in ("get", "post", "put", "delete"):
                return self._route(name.upper())
            raise AttributeError(name)

    class CORSMiddleware:
        pass

    pydantic = types.ModuleType("pydantic")
    pydantic.BaseModel, pydantic.Field = BaseModel, Field
    fastapi = types.ModuleType("fastapi")
    fastapi.FastAPI, fastapi.HTTPException = FastAPI, HTTPException
    fastapi._is_stub = True
    middleware = types.ModuleType("fastapi.middleware")
    cors = types.ModuleType("fastapi.middleware.cors")
    cors.CORSMiddleware = CORSMiddleware
    sys.modules.update(
        {
            "pydantic": pydantic,
            "fastapi": fastapi,
            "fastapi.middleware": middleware,
            "fastapi.middleware.cors": cors,
        }
    )
    return True
