"""Operações de escrita associadas a um único turno em memória."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import copy
import re
from threading import Lock
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class PendingOperation:
    operation_id: str
    tool_name: str
    arguments: dict[str, Any]
    tool: Any


_current_holder: ContextVar[ToolHolder | None] = ContextVar("tool_holder", default=None)


class ToolHolder:
    def __init__(self):
        self._operations: list[PendingOperation] = []
        self._closed = False
        self._lock = Lock()

    def prepare(self, tool: Any, arguments: dict[str, Any]) -> PendingOperation:
        with self._lock:
            if self._closed:
                raise RuntimeError("O lote deste turno já foi finalizado.")
            operation = PendingOperation(uuid4().hex, tool.name, copy.deepcopy(arguments), tool)
            self._operations.append(operation)
            return operation

    def has_operations(self) -> bool:
        with self._lock:
            return bool(self._operations)

    def discard(self) -> None:
        with self._lock:
            self._closed = True
            self._operations.clear()

    def commit(self) -> list[dict[str, Any]]:
        with self._lock:
            if self._closed:
                raise RuntimeError("O lote deste turno já foi finalizado.")
            self._closed = True
            operations, self._operations = self._operations, []
        operations.sort(key=lambda op: op.tool_name == "add_google_event")
        results = []
        stopped = False
        for operation in operations:
            if stopped:
                result = {"status": "skipped", "message": "Não executada após falha anterior."}
            else:
                try:
                    result = operation.tool.invoke(operation.arguments)
                except Exception:
                    result = {"status": "error", "message": "Falha ao executar a operação."}
                if not isinstance(result, dict) or result.get("status") != "ok":
                    stopped = True
            results.append({"operation_id": operation.operation_id, "tool_name": operation.tool_name, "result": result})
        return results


@contextmanager
def holder_context():
    holder = ToolHolder()
    token = _current_holder.set(holder)
    try:
        yield holder
    finally:
        holder.discard()
        _current_holder.reset(token)


def current_holder() -> ToolHolder | None:
    return _current_holder.get()

def juiz_aprovou(decisao: str) -> bool:
    match = re.fullmatch(r"juiz:apoiada noul=(0\.[0-9]{2}|1\.00)", decisao)
    return bool(match and float(match.group(1)) >= 0.70)
