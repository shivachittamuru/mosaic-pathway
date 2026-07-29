from mosaic_pathway.models import ChildProfile, FamilyIntake
from mosaic_pathway.query_builder import build_retrieval_query


def full_intake() -> FamilyIntake:
    return FamilyIntake(
        children=[
            ChildProfile(
                label="younger child",
                age=7,
                interests=["animals", "drawing"],
                learning_needs=["extra movement breaks"],
            ),
            ChildProfile(
                label="older child",
                age=12,
                interests=["robotics"],
            ),
        ],
        leaving_behind=["rigid daily schedules"],
        wants_to_preserve=["reading together"],
        wants_to_add=["more outdoor learning"],
        family_values=["curiosity", "connection"],
        practical_constraints=["moderate budget"],
        additional_context="The family feels overwhelmed by the options.",
    )


def minimal_intake() -> FamilyIntake:
    return FamilyIntake(
        children=[ChildProfile(label="only child", age=9, interests=["music"])],
        leaving_behind=["worksheets"],
        wants_to_add=["more choice"],
        family_values=["creativity"],
    )


def test_query_includes_every_populated_intake_dimension() -> None:
    query = build_retrieval_query(full_intake())

    assert "younger child (age 7) interested in animals, drawing" in query
    assert "learning needs: extra movement breaks" in query
    assert "older child (age 12) interested in robotics" in query
    assert "Leaving behind: rigid daily schedules." in query
    assert "Wants to preserve: reading together." in query
    assert "Wants to add: more outdoor learning." in query
    assert "Family values: curiosity, connection." in query
    assert "Practical constraints: moderate budget." in query
    assert "Additional context: The family feels overwhelmed by the options." in query


def test_empty_optional_fields_are_omitted() -> None:
    query = build_retrieval_query(minimal_intake())

    assert "Wants to preserve" not in query
    assert "Practical constraints" not in query
    assert "Additional context" not in query
    assert "learning needs" not in query
    assert "Leaving behind: worksheets." in query


def test_blank_additional_context_is_omitted() -> None:
    intake = minimal_intake().model_copy(update={"additional_context": "   "})

    assert "Additional context" not in build_retrieval_query(intake)


def test_query_is_deterministic_for_identical_input() -> None:
    assert build_retrieval_query(full_intake()) == build_retrieval_query(full_intake())


def test_children_appear_in_intake_order() -> None:
    query = build_retrieval_query(full_intake())

    assert query.index("younger child") < query.index("older child")
