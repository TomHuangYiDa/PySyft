import inspect
from inspect import signature
from typing import Any, Callable, Dict, Union, get_type_hints

from pydantic import BaseModel


def get_type_schema(type_hint: Any) -> Union[str, Dict[str, Any]]:
    """Get a schema representation of a type."""
    # Handle None
    if type_hint is None:
        return "null"

    # Handle Pydantic models
    if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
        return {
            "type": "model",
            "name": type_hint.__name__,
            "schema": type_hint.model_json_schema(),
        }

    # Handle Lists
    if getattr(type_hint, "__origin__", None) is list:
        return {"type": "array", "items": get_type_schema(type_hint.__args__[0])}

    # Handle Optional
    if getattr(type_hint, "__origin__", None) is Union:
        types = [t for t in type_hint.__args__ if t is not type(None)]
        if len(types) == 1:  # Optional[T] case
            return get_type_schema(types[0])
        return "union"  # General Union case

    # Handle basic types
    if isinstance(type_hint, type):
        return type_hint.__name__.lower()

    return "any"


def generate_schema(func: Callable) -> Dict[str, Any]:
    """Generate RPC schema from a function."""
    sig = signature(func)
    hints = get_type_hints(func)

    # Process parameters
    params = {}
    for name, param in sig.parameters.items():
        params[name] = {
            "type": get_type_schema(hints.get(name, Any)),
            "required": param.default is param.empty,
        }

    return {
        "description": inspect.getdoc(func),
        "args": params,
        "returns": get_type_schema(hints.get("return", Any)),
    }
