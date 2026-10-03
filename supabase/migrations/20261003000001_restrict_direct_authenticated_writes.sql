-- Supabase projects may grant table privileges through default ACLs.
-- Authenticated clients must not bypass domain services for workflow,
-- financial, approval, evidence, audit, or reliability writes.
revoke all on public.research_missions, public.research_tasks, public.source_snapshots,
    public.evidence_records, public.opportunities, public.research_reports,
    public.finance_assessments, public.evolver_assessments, public.enactor_executions,
    public.enactor_approvals, public.audit_events, public.operational_snapshots,
    public.reliability_incidents, public.sector_configurations
    from anon, authenticated;

grant select on public.research_missions, public.research_tasks, public.source_snapshots,
    public.evidence_records, public.opportunities, public.research_reports,
    public.finance_assessments, public.evolver_assessments, public.enactor_executions,
    public.enactor_approvals, public.audit_events, public.operational_snapshots,
    public.reliability_incidents, public.sector_configurations to authenticated;

revoke all on public.workspaces, public.workspace_members from anon, authenticated;
grant select on public.workspaces, public.workspace_members to authenticated;
