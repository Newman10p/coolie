"""Bounded, auditable delegation requests; approval never executes external actions."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from .models import AgentDefinition, BrainOperation, Delegation, DelegationRequest


class DelegationManager:
    def __init__(self, *, maximum_children: int = 8) -> None:
        if isinstance(maximum_children, bool) or not isinstance(maximum_children, int) or maximum_children <= 0:
            raise ValueError("maximum_children must be a positive integer.")
        self._maximum_children = maximum_children
        self._records: dict[str, Delegation] = {}
        self._children: dict[str, int] = {}

    def create(self, parent: AgentDefinition, request: DelegationRequest, *, parent_depth: int = 0) -> Delegation:
        if request.requesting_agent_id != parent.agent_id:
            raise PermissionError("Delegation requester does not match the registered agent.")
        if BrainOperation.DELEGATE_TASK not in parent.allowed_operations:
            raise PermissionError("Agent is not authorized to delegate tasks.")
        if request.target_agent_type not in parent.allowed_delegate_types:
            raise PermissionError("Target agent type is not authorized for delegation.")
        if parent_depth >= parent.max_delegation_depth or request.max_depth > parent.max_delegation_depth:
            raise PermissionError("Delegation depth exceeds the agent policy.")
        if request.max_depth <= 0:
            raise ValueError("Delegation max_depth must be positive.")
        if request.deadline.tzinfo is None or request.deadline <= datetime.now(timezone.utc):
            raise ValueError("Delegation deadline must be a future timezone-aware time.")
        if request.budget.currency != parent.max_cost_per_task.currency or request.budget.amount <= 0 or request.budget.amount > parent.max_cost_per_task.amount:
            raise PermissionError("Delegation budget exceeds the agent policy.")
        if not request.task.strip() or not request.expected_schema.strip():
            raise ValueError("Delegation task and expected schema are required.")
        if request.delegation_id in self._records:
            raise ValueError(f"Delegation already exists: {request.delegation_id}")
        children = self._children.get(parent.agent_id, 0)
        if children >= self._maximum_children:
            raise PermissionError("Maximum concurrent delegation count reached.")
        delegation = Delegation(
            request.delegation_id, parent.agent_id, request.target_agent_type, request.task,
            request.context_refs, request.budget, request.deadline, parent_depth + 1,
            request.expected_schema,
            "awaiting_approval" if request.approval_required or parent.requires_approval_for_delegation else "approved",
            request.approval_required or parent.requires_approval_for_delegation,
        )
        self._records[delegation.delegation_id] = delegation
        self._children[parent.agent_id] = children + 1
        return delegation

    def approve(self, delegation_id: str, *, authority: str) -> Delegation:
        if not authority.strip():
            raise PermissionError("Delegation approval authority is required.")
        delegation = self.get(delegation_id)
        if delegation.status != "awaiting_approval":
            raise ValueError("Delegation is not awaiting approval.")
        approved = Delegation(
            delegation.delegation_id, delegation.parent_agent_id, delegation.target_agent_type,
            delegation.task, delegation.context_refs, delegation.budget, delegation.deadline,
            delegation.depth, delegation.expected_schema, "approved", delegation.approval_required,
        )
        self._records[delegation_id] = approved
        return approved

    def complete(self, delegation_id: str, *, target_agent_type: str, result: object) -> Delegation:
        delegation = self.get(delegation_id)
        if delegation.status != "approved":
            raise PermissionError("Delegation must be approved before completion.")
        if delegation.target_agent_type != target_agent_type:
            raise PermissionError("Result agent type does not match the delegation target.")
        if delegation.deadline <= datetime.now(timezone.utc):
            raise PermissionError("Delegation has expired.")
        completed = Delegation(
            delegation.delegation_id, delegation.parent_agent_id, delegation.target_agent_type,
            delegation.task, delegation.context_refs, delegation.budget, delegation.deadline,
            delegation.depth, delegation.expected_schema, "completed", delegation.approval_required, deepcopy(result),
        )
        self._records[delegation_id] = completed
        self._children[delegation.parent_agent_id] = max(0, self._children.get(delegation.parent_agent_id, 1) - 1)
        return completed

    def cancel(self, delegation_id: str, *, authority: str) -> Delegation:
        if not authority.strip():
            raise PermissionError("Delegation cancellation authority is required.")
        delegation = self.get(delegation_id)
        if delegation.status not in {"awaiting_approval", "approved"}:
            raise ValueError("Only pending delegations can be cancelled.")
        cancelled = Delegation(
            delegation.delegation_id, delegation.parent_agent_id, delegation.target_agent_type,
            delegation.task, delegation.context_refs, delegation.budget, delegation.deadline,
            delegation.depth, delegation.expected_schema, "cancelled", delegation.approval_required,
        )
        self._records[delegation_id] = cancelled
        self._children[delegation.parent_agent_id] = max(0, self._children.get(delegation.parent_agent_id, 1) - 1)
        return cancelled

    def get(self, delegation_id: str) -> Delegation:
        try:
            return deepcopy(self._records[delegation_id])
        except KeyError as error:
            raise KeyError(f"Unknown delegation: {delegation_id}") from error
