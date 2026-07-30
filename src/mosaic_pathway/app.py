"""A minimal local Streamlit interface for the Mosaic family pathway workflow."""

import streamlit as st
from pydantic import ValidationError

from mosaic_pathway.app_support import (
    ChildInput,
    GenerationError,
    IntakeFormInput,
    build_family_intake,
    clear_error,
    clear_pathway,
    describe_generation_failure,
    describe_validation_errors,
    evidence_preview,
    read_output_view,
    store_error,
    store_result,
    validate_form_input,
)
from mosaic_pathway.embeddings import LocalEmbeddingModel
from mosaic_pathway.generation import ClaudePathwayGenerator
from mosaic_pathway.models import FamilyIntake, GroundedPathwayResult
from mosaic_pathway.rag import MosaicPathwayService
from mosaic_pathway.retrieval import MosaicRetriever
from mosaic_pathway.settings import load_settings
from mosaic_pathway.vector_store import MosaicVectorStore

SECOND_CHILD_KEY = "include_second_child"


class SetupError(RuntimeError):
    """Raised when the local index or Anthropic configuration is not ready."""


@st.cache_resource(show_spinner="Loading the local Mosaic knowledge base...")
def load_service() -> MosaicPathwayService:
    """Build the production service once and keep it across widget reruns."""

    try:
        settings = load_settings()
    except ValidationError as error:
        raise SetupError(
            "Anthropic Claude settings are missing or invalid. Set "
            "ANTHROPIC_API_KEY and ANTHROPIC_MODEL in your .env file."
        ) from error

    store = MosaicVectorStore()

    if not store.collection_exists():
        store.close()
        raise SetupError(
            f"The local collection '{store.collection_name}' was not found at "
            f"{store.path}. Build it first with: "
            "uv run python -m mosaic_pathway.vector_store"
        )

    return MosaicPathwayService(
        MosaicRetriever(LocalEmbeddingModel(), store),
        ClaudePathwayGenerator(settings),
    )


def render_intro() -> None:
    st.title("Mosaic Family Pathway")
    st.write(
        "This tool creates a gentle starting pathway for a family exploring "
        "self-directed education, grounded in Mosaic's own materials."
    )
    st.info(
        "Privacy note: this is a local MVP. Enter synthetic or approved family "
        "information only. Nothing you type is saved to disk."
    )


def render_child_fields(
    number: int, default_label: str, default_age: int
) -> ChildInput:
    return ChildInput(
        label=st.text_input(
            "Label",
            value=default_label,
            key=f"child_{number}_label",
            help="A non-identifying label such as 'older child'.",
        ),
        age=int(
            st.number_input(
                "Age",
                min_value=2,
                max_value=21,
                value=default_age,
                step=1,
                key=f"child_{number}_age",
            )
        ),
        interests=st.text_input(
            "Interests (comma separated)",
            key=f"child_{number}_interests",
            placeholder="animals, drawing, being outdoors",
        ),
        learning_needs=st.text_input(
            "Learning needs (comma separated)",
            key=f"child_{number}_needs",
            placeholder="needs movement breaks",
        ),
    )


def render_form() -> IntakeFormInput | None:
    """Draw the intake form, returning the submitted values or None."""

    st.markdown("#### Learner")

    # Streamlit forms do not rerun on internal widget changes, so this toggle has
    # to sit outside the form to reveal the second learner's fields.
    include_second = st.checkbox("Include a second learner", key=SECOND_CHILD_KEY)

    with st.form("family_intake"):
        children = [render_child_fields(1, "older child", 10)]

        if include_second:
            st.markdown("#### Second learner")
            children.append(render_child_fields(2, "younger child", 7))

        st.markdown("#### Your family")
        leaving_behind = st.text_input(
            "Leaving behind (comma separated)",
            placeholder="rigid daily schedules, frequent worksheets",
        )
        wants_to_preserve = st.text_input(
            "Wants to preserve (comma separated)",
            placeholder="reading together",
        )
        wants_to_add = st.text_input(
            "Wants to add (comma separated)",
            placeholder="more outdoor learning, a calmer rhythm",
        )
        family_values = st.text_input(
            "Family values (comma separated)",
            placeholder="curiosity, connection",
        )
        practical_constraints = st.text_input(
            "Practical constraints (comma separated)",
            placeholder="one parent works full time, moderate budget",
        )
        additional_context = st.text_area(
            "Anything else you would like considered",
            placeholder="We are new to self-directed learning and feel overwhelmed.",
        )
        submitted = st.form_submit_button("Create pathway")

    if not submitted:
        return None

    return IntakeFormInput(
        children=children,
        leaving_behind=leaving_behind,
        wants_to_preserve=wants_to_preserve,
        wants_to_add=wants_to_add,
        family_values=family_values,
        practical_constraints=practical_constraints,
        additional_context=additional_context,
    )


def prepare_intake(form: IntakeFormInput) -> FamilyIntake | None:
    """Validate beside the form, returning None while anything needs fixing."""

    messages = validate_form_input(form)

    if messages:
        for message in messages:
            st.warning(message)

        return None

    try:
        return build_family_intake(form)
    except ValidationError as error:
        st.error("Please review these details before creating a pathway.")

        for message in describe_validation_errors(error):
            st.warning(message)

        return None


def run_generation(intake: FamilyIntake) -> None:
    """Generate once per submission, storing either the pathway or the failure."""

    try:
        service = load_service()
    except SetupError as error:
        store_error(st.session_state, str(error), error)
        return
    except Exception as error:  # noqa: BLE001 - the UI must never show a traceback
        store_error(
            st.session_state, "The local knowledge base could not be opened.", error
        )
        return

    with st.spinner("Finding relevant Mosaic guidance and creating your pathway..."):
        try:
            result = service.generate_pathway(intake)
        except Exception as error:  # noqa: BLE001 - the UI must never show a traceback
            store_error(st.session_state, describe_generation_failure(error), error)
            return

    store_result(st.session_state, result)


def render_placeholder() -> None:
    st.subheader("Your pathway will appear here")
    st.write(
        "Once your family profile is ready, a starting pathway drawn from Mosaic's "
        "guidance will be shown in this space."
    )
    st.markdown(
        "1. Complete the family profile on the left.\n"
        "2. Select **Create pathway**.\n"
        "3. Relevant Mosaic guidance is gathered, and a grounded starting pathway "
        "is written for your family."
    )


def render_failure(error: GenerationError) -> None:
    st.error(error.message)

    with st.expander("Technical details"):
        st.write(error.detail)


def render_pathway(result: GroundedPathwayResult) -> None:
    pathway = result.pathway

    st.header("Your Family Pathway")
    st.write(pathway.family_reflection)

    st.subheader("Your starting rhythm")

    for practice in pathway.starting_rhythm:
        with st.container(border=True):
            st.markdown(f"**{practice.timing}: {practice.practice}**")
            st.write(practice.why_it_fits)

    st.subheader("Resources and activities")

    for resource in pathway.resources:
        with st.container(border=True):
            st.markdown(f"**{resource.title}**")
            st.write(resource.why_it_fits)

            if resource.url:
                st.markdown(f"[Open this resource]({resource.url})")

    st.subheader("A way to connect")

    with st.container(border=True):
        st.markdown(f"**{pathway.community_suggestion.suggestion}**")
        st.write(pathway.community_suggestion.why_it_fits)

    st.subheader("Closing note")
    st.write(pathway.closing_note)


def render_sources(result: GroundedPathwayResult) -> None:
    with st.expander("Sources used"):
        for rank, retrieved in enumerate(result.retrieved_records, start=1):
            st.markdown(f"**{rank}. {retrieved.record.title}**")
            st.caption(
                f"{retrieved.record.source_id} | similarity {retrieved.score:.2f}"
            )
            st.write(evidence_preview(retrieved.record.text))


def render_method() -> None:
    with st.expander("How this pathway was created"):
        st.markdown(
            "1. Your intake was turned into a single search query.\n"
            "2. Relevant Mosaic passages were retrieved from the local index on "
            "this machine.\n"
            "3. Claude wrote the pathway using only those passages.\n"
            "4. Every cited source ID was checked against the retrieved records "
            "before the pathway was shown."
        )


def render_output() -> None:
    """Draw the placeholder, the stored pathway, or the latest failure."""

    view = read_output_view(st.session_state)

    if view.show_placeholder:
        render_placeholder()
        return

    if view.error is not None:
        render_failure(view.error)

    if view.result is None:
        return

    if view.shows_previous_result:
        st.info("The new pathway could not be generated. Showing the previous result.")

    if st.button("Clear pathway"):
        clear_pathway(st.session_state)
        st.rerun()

    render_pathway(view.result)
    render_sources(view.result)
    render_method()


def main() -> None:
    st.set_page_config(page_title="Mosaic Family Pathway", layout="wide")
    render_intro()

    input_column, output_column = st.columns([2, 3], gap="large")

    with input_column:
        form = render_form()
        intake = None

        if form is not None:
            clear_error(st.session_state)
            intake = prepare_intake(form)

    with output_column:
        if intake is not None:
            run_generation(intake)

        render_output()


if __name__ == "__main__":
    main()
