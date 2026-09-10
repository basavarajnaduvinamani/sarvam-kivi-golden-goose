from .models import Memory
from .schemas import MemoryEvidenceRead, MemoryRead


def present_memory(memory: Memory) -> MemoryRead:
    return MemoryRead(
        id=memory.id,
        project_id=memory.project_id,
        memory_type=memory.memory_type,
        subject=memory.subject,
        predicate=memory.predicate,
        object_value=memory.object_value,
        epistemic_status=memory.epistemic_status,
        lifecycle_status=memory.lifecycle_status,
        valid_from=memory.valid_from,
        valid_to=memory.valid_to,
        confidence=memory.confidence,
        extraction_method=memory.extraction_method,
        extraction_model=memory.extraction_model,
        schema_version=memory.schema_version,
        supersedes_memory_id=memory.supersedes_memory_id,
        evidence=[
            MemoryEvidenceRead(
                take_id=link.take_id,
                span_start=link.span_start,
                span_end=link.span_end,
                evidence_role=link.evidence_role,
                is_required=link.is_required,
                sufficiency_contribution=link.sufficiency_contribution,
            )
            for link in memory.evidence_links
        ],
    )

