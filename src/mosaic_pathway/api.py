"""A small HTTP API over the existing grounded pathway workflow."""

from collections.abc import AsyncIterator, Callable, Iterator, Sequence
from contextlib import AbstractContextManager, asynccontextmanager, contextmanager
from typing import Annotated

from anthropic import (
    AnthropicError,
    APIConnectionError,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from mosaic_pathway.app_support import evidence_preview
from mosaic_pathway.embeddings import LocalEmbeddingModel
from mosaic_pathway.generation import ClaudePathwayGenerator
from mosaic_pathway.models import FamilyIntake, LearningPathway, RetrievedRecord
from mosaic_pathway.rag import GroundingError, MosaicPathwayService
from mosaic_pathway.retrieval import MosaicRetriever
from mosaic_pathway.settings import load_settings
from mosaic_pathway.vector_store import MosaicVectorStore

PREVIEW_CHARACTERS = 250
SCORE_DECIMALS = 4
DEFAULT_ALLOWED_ORIGINS = ("http://localhost:5173", "http://localhost:3000")
UNAVAILABLE_MESSAGE = (
    "The Mosaic pathway service is not available. Check the local setup and "
    "restart the API."
)

ServiceProvider = Callable[[], AbstractContextManager[MosaicPathwayService]]


class ApiSettings(BaseSettings):
    """API-only configuration, kept separate from the Anthropic Claude settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    allowed_origins: str = Field(default="", alias="MOSAIC_ALLOWED_ORIGINS")


class SourceSummary(BaseModel):
    """A retrieved passage reduced to what a frontend may safely display."""

    source_id: str
    title: str
    score: float
    preview: str


class PathwayApiResponse(BaseModel):
    pathway: LearningPathway
    sources: list[SourceSummary]


def parse_allowed_origins(value: str) -> list[str]:
    """Split, trim, and de-duplicate the configured CORS origins."""

    origins: list[str] = []

    for part in value.split(","):
        origin = part.strip()

        if origin and origin not in origins:
            origins.append(origin)

    return origins or list(DEFAULT_ALLOWED_ORIGINS)


def summarize_sources(records: Sequence[RetrievedRecord]) -> list[SourceSummary]:
    """Reduce retrieved records to previews, keeping retrieval rank order."""

    return [
        SourceSummary(
            source_id=retrieved.record.source_id,
            title=retrieved.record.title,
            score=round(retrieved.score, SCORE_DECIMALS),
            preview=evidence_preview(retrieved.record.text, PREVIEW_CHARACTERS),
        )
        for retrieved in records
    ]


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    """Build the single error shape this API returns for known failures."""

    return HTTPException(
        status_code=status_code, detail={"code": code, "message": message}
    )


def describe_setup_failure(error: Exception) -> str:
    """Turn a startup failure into one message that helps a local operator."""

    if isinstance(error, ValidationError):
        return (
            "Anthropic Claude settings are missing or invalid. Set "
            "ANTHROPIC_API_KEY and ANTHROPIC_MODEL."
        )

    if isinstance(error, RuntimeError):
        return str(error)

    return UNAVAILABLE_MESSAGE


def map_generation_error(error: Exception) -> HTTPException:
    """Map a failure from the pathway service onto an HTTP status and code."""

    if isinstance(error, GroundingError):
        return api_error(
            status.HTTP_502_BAD_GATEWAY,
            "pathway_not_grounded",
            "The generated pathway cited passages that were not retrieved.",
        )

    if "no mosaic records" in str(error).lower():
        return api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "no_sources_retrieved",
            "No Mosaic passages matched this family. Describe the family's goals "
            "in more detail and try again.",
        )

    if isinstance(error, AuthenticationError | PermissionDeniedError):
        return api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "anthropic_authentication_failed",
            "The Anthropic API rejected the credentials. Verify ANTHROPIC_API_KEY.",
        )

    if isinstance(error, RateLimitError):
        return api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "anthropic_rate_limited",
            "The Anthropic API is rate limiting requests. Try again shortly.",
        )

    if isinstance(error, APIConnectionError):
        return api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "anthropic_unreachable",
            "The Anthropic API could not be reached. Check connectivity and try again.",
        )

    if isinstance(error, AnthropicError | RuntimeError):
        return api_error(
            status.HTTP_502_BAD_GATEWAY,
            "pathway_generation_failed",
            "The pathway generator did not return a usable pathway.",
        )

    return api_error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error",
        "The pathway could not be created because of an unexpected error.",
    )


@contextmanager
def production_service() -> Iterator[MosaicPathwayService]:
    """Open the expensive local dependencies once and release them on shutdown."""

    settings = load_settings()

    with MosaicVectorStore() as store:
        if not store.collection_exists():
            raise RuntimeError(
                f"The local collection '{store.collection_name}' was not found at "
                f"{store.path}. Build it first with: "
                "uv run python -m mosaic_pathway.vector_store"
            )

        yield MosaicPathwayService(
            MosaicRetriever(LocalEmbeddingModel(), store),
            ClaudePathwayGenerator(settings),
        )


def get_service(request: Request) -> MosaicPathwayService:
    """Return the service built at startup, or report why it is unavailable."""

    service = getattr(request.app.state, "service", None)

    if service is None:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "service_unavailable",
            getattr(request.app.state, "setup_error", None) or UNAVAILABLE_MESSAGE,
        )

    return service


def create_app(
    service_provider: ServiceProvider = production_service,
    allowed_origins: Sequence[str] | None = None,
) -> FastAPI:
    """Build the application, letting tests supply a fake service provider."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.service = None
        app.state.setup_error = None

        try:
            provider = service_provider()
            app.state.service = provider.__enter__()
        except Exception as error:  # noqa: BLE001 - startup must not crash /health
            app.state.setup_error = describe_setup_failure(error)
            yield
            return

        try:
            yield
        finally:
            provider.__exit__(None, None, None)

    app = FastAPI(
        title="Mosaic Family Pathway API",
        version="0.1.0",
        lifespan=lifespan,
    )

    origins = (
        list(allowed_origins)
        if allowed_origins is not None
        else parse_allowed_origins(ApiSettings().allowed_origins)
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/pathways", response_model=PathwayApiResponse)
    def create_pathway(
        intake: FamilyIntake,
        service: Annotated[MosaicPathwayService, Depends(get_service)],
    ) -> PathwayApiResponse:
        try:
            result = service.generate_pathway(intake)
        except Exception as error:
            raise map_generation_error(error) from error

        return PathwayApiResponse(
            pathway=result.pathway,
            sources=summarize_sources(result.retrieved_records),
        )

    return app


app = create_app()
