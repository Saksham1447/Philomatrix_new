"""Small Mongo query helpers shared by converted route modules."""
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


def ids(docs: Iterable[Any], key: str = "id") -> list[Any]:
    return [doc.get(key) if isinstance(doc, Mapping) else getattr(doc, key) for doc in docs]


def index_by(docs: Iterable[Any], key: str = "id") -> dict[Any, Any]:
    return {doc.get(key) if isinstance(doc, Mapping) else getattr(doc, key): doc for doc in docs}


def group_by(docs: Iterable[Any], key: str) -> dict[Any, list[Any]]:
    grouped: dict[Any, list[Any]] = defaultdict(list)
    for doc in docs:
        value = doc.get(key) if isinstance(doc, Mapping) else getattr(doc, key)
        grouped[value].append(doc)
    return dict(grouped)


def regex_contains(text: str) -> dict[str, str]:
    pattern = "".join(".*" if char == "%" else "." if char == "_" else re.escape(char) for char in text)
    return {"$regex": pattern, "$options": "i"}


def in_(values: Iterable[Any]) -> dict[str, list[Any]]:
    return {"$in": list(values)}
