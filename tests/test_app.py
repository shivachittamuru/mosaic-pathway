from mosaic_pathway import app
from mosaic_pathway.generation import ClaudePathwayGenerator


def test_importing_the_app_does_not_build_any_service() -> None:
    assert app.SECOND_CHILD_KEY == "include_second_child"
    assert callable(app.main)
    assert callable(app.render_form)
    assert callable(app.prepare_intake)
    assert callable(app.run_generation)
    assert callable(app.render_output)


def test_the_service_factory_is_cached() -> None:
    assert hasattr(app.load_service, "clear")


def test_the_app_builds_the_claude_generator() -> None:
    assert app.ClaudePathwayGenerator is ClaudePathwayGenerator


def test_setup_error_is_a_runtime_error() -> None:
    assert issubclass(app.SetupError, RuntimeError)
