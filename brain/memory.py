"""Namespace-scoped memory and sensitivity-filtered context assembly."""

from __future__ import annotations

from copy import deepcopy
import json
import secrets
from threading import RLock

from .models import AgentDefinition, ContextItem, ContextPackage, DataSensitivity, MemoryRecord, utc_now


_SENSITIVITY = {
    DataSensitivity.PUBLIC: 0,
    DataSensitivity.INTERNAL: 1,
    DataSensitivity.SENSITIVE: 2,
    DataSensitivity.RESTRICTED: 3,
}


class MemoryStore:
    def __init__(self, persistence=None) -> None:
        self._records: dict[str, MemoryRecord] = {}
        self._lock = RLock()
        self._persistence = persistence

    def write(self, agent: AgentDefinition, record: MemoryRecord) -> MemoryRecord:
        if record.namespace not in agent.allowed_memory_namespaces:
            raise PermissionError("Agent cannot write to this memory namespace.")
        if _SENSITIVITY[record.sensitivity] > _SENSITIVITY[agent.maximum_sensitivity]:
            raise PermissionError("Agent cannot write memory at this sensitivity.")
        if record.expires_at is not None and record.expires_at <= utc_now():
            raise ValueError("Memory record is already expired.")
        with self._lock:
            if self._persistence is None:
                if record.memory_id in self._records:
                    raise ValueError(f"Memory record already exists: {record.memory_id}")
                self._records[record.memory_id] = self._copy(record)
            else:
                self._persistence.insert_record("brain_memory", record.memory_id, record)
        return self._copy(record)

    def retrieve(self, agent: AgentDefinition, *, namespace: str, query: str, top_k: int = 10) -> tuple[MemoryRecord, ...]:
        if not isinstance(query, str):
            raise ValueError("query must be a string.")
        if namespace not in agent.allowed_memory_namespaces:
            raise PermissionError("Agent cannot read this memory namespace.")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100.")
        terms = {term.casefold() for term in query.split() if term}
        now = utc_now()
        candidates = []
        with self._lock:
            stored_records = (
                tuple(self._records.values())
                if self._persistence is None
                else self._persistence.all_records("brain_memory", MemoryRecord)
            )
        for record in stored_records:
            if record.namespace != namespace or (record.expires_at is not None and record.expires_at <= now):
                continue
            if _SENSITIVITY[record.sensitivity] > _SENSITIVITY[agent.maximum_sensitivity]:
                continue
            content = json.dumps(record.content, ensure_ascii=False, default=str).casefold()
            score = sum(content.count(term) for term in terms)
            if terms and score == 0:
                continue
            candidates.append((score, record.created_at, record))
        candidates.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return tuple(self._copy(row[2]) for row in candidates[:top_k])

    def get(self, agent: AgentDefinition, memory_id: str) -> MemoryRecord:
        try:
            with self._lock:
                if self._persistence is None:
                    record = self._records[memory_id]
                else:
                    record = self._persistence.get_record(
                        "brain_memory", memory_id, MemoryRecord
                    )
        except KeyError as error:
            raise KeyError(f"Unknown memory record: {memory_id}") from error
        if record.namespace not in agent.allowed_memory_namespaces:
            raise PermissionError("Agent cannot read this memory namespace.")
        if _SENSITIVITY[record.sensitivity] > _SENSITIVITY[agent.maximum_sensitivity]:
            raise PermissionError("Agent cannot read memory at this sensitivity.")
        if record.expires_at is not None and record.expires_at <= utc_now():
            raise KeyError(f"Memory record has expired: {memory_id}")
        return self._copy(record)

    def forget(self, agent: AgentDefinition, memory_id: str) -> MemoryRecord:
        record = self.get(agent, memory_id)
        with self._lock:
            if self._persistence is None:
                del self._records[memory_id]
            else:
                self._persistence.delete_record("brain_memory", memory_id)
        return record

    @staticmethod
    def _copy(record: MemoryRecord) -> MemoryRecord:
        return MemoryRecord(
            record.memory_id, record.namespace, deepcopy(record.content), record.sensitivity,
            record.source_reference, record.created_at, record.expires_at,
        )


class ContextBuilder:
    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory

    def build(
        self,
        agent: AgentDefinition,
        *,
        task_id: str,
        references: tuple[str, ...],
        max_tokens: int,
        allowed_namespaces: frozenset[str] | None = None,
    ) -> ContextPackage:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 0:
            raise ValueError("Context token limit must be a non-negative integer.")
        items = []
        limitations = []
        total_tokens = 0
        seen = set()
        for reference in references:
            if reference in seen:
                continue
            seen.add(reference)
            record = self._memory.get(agent, reference)
            if record.namespace not in (agent.allowed_memory_namespaces if allowed_namespaces is None else allowed_namespaces):
                raise PermissionError("Session cannot read this memory namespace.")
            serialized = json.dumps(record.content, ensure_ascii=False, default=str)
            estimate = max(1, (len(serialized) + 3) // 4)
            if total_tokens + estimate > max_tokens:
                limitations.append(f"Context item omitted because the {max_tokens}-token limit would be exceeded.")
                continue
            items.append(ContextItem(reference, record.namespace, record.content, record.sensitivity, record.source_reference, record.created_at))
            total_tokens += estimate
        sensitivity = max((item.sensitivity for item in items), key=lambda item: _SENSITIVITY[item], default=DataSensitivity.PUBLIC)
        return ContextPackage(
            secrets.token_urlsafe(18), task_id, tuple(items), tuple(item.source_reference for item in items),
            sensitivity, total_tokens, tuple(limitations),
        )

    def search(
        self,
        agent: AgentDefinition,
        *,
        namespace: str,
        query: str,
        task_id: str,
        top_k: int,
        max_tokens: int,
        allowed_namespaces: frozenset[str] | None = None,
    ) -> ContextPackage:
        if allowed_namespaces is not None and namespace not in allowed_namespaces:
            raise PermissionError("Session cannot read this memory namespace.")
        records = self._memory.retrieve(agent, namespace=namespace, query=query, top_k=top_k)
        return self.build(
            agent, task_id=task_id, references=tuple(record.memory_id for record in records),
            max_tokens=max_tokens, allowed_namespaces=allowed_namespaces,
        )
