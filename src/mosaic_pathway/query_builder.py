"""Turn a structured family intake into a deterministic retrieval query."""

from mosaic_pathway.models import ChildProfile, FamilyIntake


def describe_child(child: ChildProfile) -> str:
    """Describe one child in the family's own wording."""

    description = f"{child.label} (age {child.age})"

    if child.interests:
        description += f" interested in {', '.join(child.interests)}"

    if child.learning_needs:
        description += f"; learning needs: {', '.join(child.learning_needs)}"

    return description


def build_retrieval_query(intake: FamilyIntake) -> str:
    """Build concise searchable prose from the intake, omitting empty fields."""

    lines = [f"- {describe_child(child)}" for child in intake.children]
    sections: list[tuple[str, list[str]]] = [
        ("Leaving behind", intake.leaving_behind),
        ("Wants to preserve", intake.wants_to_preserve),
        ("Wants to add", intake.wants_to_add),
        ("Family values", intake.family_values),
        ("Practical constraints", intake.practical_constraints),
    ]

    if lines:
        lines.insert(0, "Children:")

    for label, values in sections:
        if values:
            lines.append(f"{label}: {', '.join(values)}.")

    if intake.additional_context and intake.additional_context.strip():
        lines.append(f"Additional context: {intake.additional_context.strip()}")

    return "\n".join(lines)
