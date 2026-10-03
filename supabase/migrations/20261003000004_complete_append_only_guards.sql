-- Close delete gaps in tables whose application contracts are append-only.
drop trigger if exists audit_events_append_only on public.audit_events;
create trigger audit_events_append_only
    before update or delete on public.audit_events
    for each row execute function public.reject_immutable_record_change();

drop trigger if exists evidence_records_append_only on public.evidence_records;
create trigger evidence_records_append_only
    before update or delete on public.evidence_records
    for each row execute function public.reject_immutable_record_change();

drop trigger if exists research_reports_append_only on public.research_reports;
create trigger research_reports_append_only
    before update or delete on public.research_reports
    for each row execute function public.reject_immutable_record_change();

drop trigger if exists enactor_artifacts_append_only on public.enactor_artifacts;
create trigger enactor_artifacts_append_only
    before update or delete on public.enactor_artifacts
    for each row execute function public.reject_immutable_record_change();

drop trigger if exists research_mission_transitions_append_only
    on public.research_mission_transitions;
create trigger research_mission_transitions_append_only
    before update or delete on public.research_mission_transitions
    for each row execute function public.reject_immutable_record_change();
