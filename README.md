# Mosaic Family Pathway MVP

A lean Retrieval-Augmented Generation application for Mosaic.

The MVP helps families exploring self-directed learning receive a warm, practical, one-page learning pathway grounded in Mosaic’s materials.

## What this project does

The system:

1. Collects structured information about a family and its learners.
2. Retrieves relevant guidance from Mosaic’s knowledge base.
3. Uses an LLM to generate a personalized learning pathway.
4. Validates the generated response and its source references.
5. Evaluates the pathway using deterministic checks and human review.
6. Produces a concise pathway containing:

   * a reflection of the family’s values and intentions
   * a practical starting rhythm
   * two or three grounded resources or activities
   * one community suggestion

The project intentionally avoids agents, orchestration frameworks, cloud databases, and unnecessary infrastructure.

## Current workflow

```text
Structured family intake
          |
          v
Deterministic retrieval query
          |
          v
Local semantic retrieval
          |
          v
Relevant Mosaic passages
          |
          v
Anthropic Claude generation
          |
          v
Validated GroundedPathwayResult
          |
          v
Deterministic checks + human review
```

The local knowledge base is prepared separately:

```text
Private Mosaic PDF and DOCX files
              |
              v
     Extract and clean text
              |
              v
    Validated SourceRecords
              |
              v
 Local embeddings and Qdrant
```

## Technology choices

* Python 3.12
* `uv` for dependency and environment management
* Pydantic for structured data validation
* PyMuPDF for PDF text extraction
* `python-docx` for DOCX extraction
* Sentence Transformers for local embeddings
* `all-MiniLM-L6-v2` as the initial embedding model
* Qdrant local mode for vector storage and similarity search
* Anthropic Claude for pathway generation
* An Anthropic API key for authentication
* Pytest for tests
* Ruff for formatting and linting
* Mypy for type checking

A minimal Streamlit interface and a lean FastAPI service are both implemented. The demo checklist below lists the commands that run them.

## Generation provider

This branch calls the Anthropic Claude API directly through the official `anthropic` package. Generation uses Claude's native structured outputs, so the `LearningPathway` model is passed as the output format and the parsed result is validated by Pydantic before anything reaches a family.

## Architecture and handoff

Three documents support a developer taking the project over:

* [docs/architecture.md](docs/architecture.md) explains the design principles, components, contracts, retrieval and grounding behavior, privacy boundaries, and known limitations.
* [docs/demo-checklist.md](docs/demo-checklist.md) is an ordered checklist for setting up a machine and demonstrating the project end to end.
* [docs/pathway-review-rubric.md](docs/pathway-review-rubric.md) is the rubric for the human review that the deterministic checks cannot replace.

## Setup

Clone the repository:

```powershell
git clone https://github.com/shivachittamuru/mosaic-pathway.git
cd mosaic-pathway
```

Install the dependencies:

```powershell
uv sync
```

Confirm the Python version:

```powershell
uv run python --version
```

The project uses Python 3.12.

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Configure the Anthropic API key and the Claude model:

```dotenv
ANTHROPIC_API_KEY=YOUR-ANTHROPIC-API-KEY
ANTHROPIC_MODEL=YOUR-CLAUDE-MODEL
```

Create the key in the Anthropic Console under API keys. Choose a Claude 4.5 or later model that supports structured outputs.

An optional third variable caps the generated response:

```dotenv
ANTHROPIC_MAX_TOKENS=
```

Leave it blank to use the project default.

No API key should be stored in the repository. `.env` is excluded from Git.

## Add the private source materials

Place the supplied Mosaic PDFs and DOCX file under:

```text
data/raw/
```

The source files are private and excluded from Git.

Do not commit:

* original Mosaic source documents
* extracted or cleaned Mosaic content
* local vector-store files
* generated pathways based on private content
* evaluation outputs containing retrieved Mosaic passages
* `.env`
* real family information
* prompts or traces containing private content

## Run checks

Run all tests:

```powershell
uv run pytest
```

Run linting:

```powershell
uv run ruff check .
```

Check formatting:

```powershell
uv run ruff format --check .
```

Run type checking:

```powershell
uv run mypy src
```

## Run Slice 1: Structured generation

Slice 1 generates a structured pathway from a synthetic family profile and manually selected Mosaic context.

The local context file must exist at:

```text
data/manual/context.json
```

Run:

```powershell
uv run python -m mosaic_pathway.slice1_demo
```

The validated output is printed to the terminal and saved locally at:

```text
data/manual/pathway_output.json
```

## Run Slice 2A: Build the knowledge base

Slice 2A extracts, cleans, chunks, and validates the private Mosaic source documents.

Run:

```powershell
uv run python -m mosaic_pathway.knowledge_base
```

The processor:

* reads nine PDF and DOCX source files
* preserves document order
* removes conservative, explicitly defined noise
* creates paragraph-aware chunks
* assigns stable record IDs
* validates every record with Pydantic
* writes the resulting records locally

The generated knowledge base is saved at:

```text
data/processed/source_records.json
```

The current source set produces 807 validated records. Processed content remains excluded from Git.

## Run Slice 2B: Index and retrieve

Slice 2B embeds the validated source records locally and stores them in a persistent Qdrant collection.

Build or rebuild the local vector index:

```powershell
uv run python -m mosaic_pathway.vector_store
```

Run the retrieval demonstration:

```powershell
uv run python -m mosaic_pathway.slice2b_demo
```

The demo runs synthetic family-oriented queries and displays:

* similarity score
* source-record ID
* source title
* a truncated passage preview

Retrieval uses a configurable per-source cap so the much larger Mosaic website source does not occupy every result.

Run the retrieval baseline evaluation:

```powershell
uv run python -m mosaic_pathway.retrieval_evaluation
```

The initial synthetic evaluation produced:

* 10 queries evaluated
* 8 hits within the top five
* 80% hit rate at five
* misses for family criticism and educator-to-parent transition queries

This is a small human-authored baseline rather than a complete retrieval benchmark.

## Run Slice 3: End-to-end RAG generation

Slice 3 connects structured family intake, local retrieval, and Anthropic Claude generation.

Build the knowledge base and vector index first:

```powershell
uv run python -m mosaic_pathway.knowledge_base
uv run python -m mosaic_pathway.vector_store
```

Run the complete workflow:

```powershell
uv run python -m mosaic_pathway.slice3_demo
```

The workflow:

1. Loads a synthetic `FamilyIntake`.
2. Converts the intake into a deterministic retrieval query.
3. Retrieves relevant Mosaic records from local Qdrant.
4. Expands the candidate window when source diversification initially under-fills the requested result count.
5. Sends only the retrieved passages to Anthropic Claude.
6. Validates the generated `LearningPathway`.
7. Confirms that structured source references belong to the retrieved record set.
8. Preserves the intake, query, retrieved evidence, and pathway in one result.

The complete grounded result is saved locally at:

```text
data/manual/grounded_pathway_output.json
```

Structured source IDs are stored in dedicated `source_id` fields rather than being displayed inside family-facing prose.

## Run Slice 4: Evaluate pathway quality

Slice 4 evaluates complete grounded pathways using deterministic checks and a human-review rubric.

Ensure the knowledge base and vector index already exist:

```powershell
uv run python -m mosaic_pathway.knowledge_base
uv run python -m mosaic_pathway.vector_store
```

Run the six-case end-to-end evaluation:

```powershell
uv run python -m mosaic_pathway.slice4_evaluation
```

The evaluation:

1. Loads six synthetic family cases.
2. Runs the complete RAG workflow for every case.
3. Saves each private grounded result locally.
4. Applies deterministic structural, citation, length, scope, and weak personalization checks.
5. Produces a combined evaluation report.
6. Supports a separate human review of usefulness, evidence support, practicality, tone, and scope adherence.

Generated evaluation artifacts are written under:

```text
data/evaluation/
```

This directory is excluded from Git because the results contain retrieved Mosaic content.

### Slice 4 baseline

The initial deterministic evaluation produced:

```text
Cases evaluated: 6
Cases passed: 6
Checks passed: 60/60
Check pass rate: 100%
```

The six synthetic cases cover:

* gentle transition away from rigid schooling
* neurodivergent teen autonomy and community
* limited time and budget
* educator-parent unlearning classroom habits
* college exploration without rankings pressure
* recovery from school harm

Human review was also completed using the project rubric.

The deterministic checks validate structure and known failure patterns. They do not prove semantic faithfulness, strong personalization, or overall usefulness. Those dimensions remain part of the human review.

## Run Slice 6: Serve the pathway API

Slice 6 exposes the existing workflow over HTTP so a React or other frontend can call it.

Ensure the knowledge base and vector index already exist:

```powershell
uv run python -m mosaic_pathway.knowledge_base
uv run python -m mosaic_pathway.vector_store
```

Start the service:

```powershell
uv run uvicorn mosaic_pathway.api:app --reload
```

The API provides:

| Method | Path                | Purpose                                            |
|--------|---------------------|----------------------------------------------------|
| GET    | `/health`           | Confirms the API process is running                |
| POST   | `/api/v1/pathways`  | Accepts a `FamilyIntake` and returns a pathway     |

FastAPI serves its generated interfaces locally at `/docs`, `/redoc`, and `/openapi.json`.

The response contains the validated pathway plus truncated source summaries. Complete retrieved passages are never returned. Browser origins allowed to call the API are configured through `MOSAIC_ALLOWED_ORIGINS`.

Requests and responses are not persisted or logged.

## Current status

### Slice 0 — Complete

* project foundation created
* family intake schema defined
* learning pathway schema defined
* source-record and inventory schemas defined
* synthetic family examples created
* supplied Mosaic sources inventoried
* validation tests added

### Slice 1 — Complete

* Anthropic Claude integration added
* Anthropic API key authentication configured
* structured `LearningPathway` generation implemented
* manually selected Mosaic context supplied to the model
* Pydantic output validation added
* generated output stored locally
* offline tests remain independent of the Anthropic API

### Slice 2A — Complete

* nine private Mosaic documents processed
* PDF and DOCX extraction implemented
* conservative text cleaning implemented
* paragraph-aware chunking added
* stable source-record IDs generated
* 807 validated knowledge records produced
* processed content kept outside Git

### Slice 2B — Complete

* local embedding model added
* persistent local Qdrant collection added
* all 807 source records indexed
* semantic retrieval implemented
* configurable source-diversity behavior added
* synthetic retrieval queries created
* hit-rate and ranking evaluation added
* retrieval runs without any generation provider

### Slice 3 — Complete

* structured family intake converted into a deterministic retrieval query
* relevant Mosaic records retrieved from local Qdrant
* retrieval candidate expansion added to reduce under-filled result sets
* retrieved evidence passed to the existing generator
* validated `LearningPathway` produced
* structured citations checked against the retrieved record set
* citation markers excluded from family-facing prose
* intake, retrieval query, evidence, and pathway preserved together
* generated output kept outside Git

### Slice 4 — Complete

* six synthetic family evaluation cases added
* complete RAG workflow evaluated across all cases
* deterministic pathway checks implemented
* citation, structure, length, scope, and weak personalization indicators added
* private grounded results and reports stored outside Git
* 6 of 6 cases passed deterministic evaluation
* 60 of 60 deterministic checks passed
* human-review rubric created and completed
* known limits of deterministic evaluation documented

### Slice 5 — Complete

- minimal local Streamlit interface added
- family intake form supports one or two learners
- comma-separated family and learner fields converted into validated domain models
- existing `MosaicPathwayService` reused without duplicating RAG logic
- embedding model, vector store, and generation service cached across UI reruns
- pathway rendered as a readable family-facing document
- retrieved source evidence exposed through a collapsed transparency section
- wide two-column input and output layout added
- stale UI error behavior corrected
- previous pathway can be cleared without rebuilding cached resources
- submitted family information is not persisted
- UI helper tests remain independent of the Anthropic API and the production vector store

### Slice 6 — Complete

- lean FastAPI service added over the existing workflow
- `GET /health` and `POST /api/v1/pathways` exposed
- `FamilyIntake` reused as the request contract
- expensive dependencies built once through a lifespan handler
- application factory allows a fake service to be injected in tests
- retrieved evidence reduced to truncated source summaries
- domain failures mapped to explicit 422, 502, 503, and 500 responses
- configurable CORS origins added for local frontend development
- API tests remain offline and independent of the Anthropic API and Qdrant
- requests and responses are not persisted or logged

### Next

The final slice will focus on project handoff:

- concise final documentation
- architecture explanation
- reproducible setup and demo checklist
- educational notebooks
- final repository cleanup

## Development slices

1. **Foundation and contracts** — complete
2. **Generation with manual context** — complete
3. **Content extraction and cleaning** — complete
4. **Local embeddings and retrieval** — complete
5. **End-to-end RAG pathway generation** — complete
6. **Pathway and retrieval evaluation** — complete
7. **Minimal Streamlit interface** — complete
8. **Lean FastAPI backend** — complete
9. **Final documentation, notebooks, and handoff**

Each slice is intentionally small and must work before the next capability is added.

## Known limitations

* The Mosaic website source contains approximately 82% of all records.
* Some nonconsecutive duplicate website sections remain in the processed data.
* Embedding similarity scores are not probabilities.
* Retrieval quality is evaluated using a small synthetic query set.
* Retrieval uses semantic vector search only.
* There is no keyword search, reranking, or hybrid retrieval.
* Citation validation confirms that an ID was retrieved, not that every generated claim is semantically supported.
* Personalization indicators use lexical matching and can reward keyword repetition.
* Prohibited-phrase checks use a small substring list and are not comprehensive safety validation.
* Word-count checks detect empty or runaway sections, not vagueness or repetition.
* Exact duplicate detection does not identify semantic near-duplicates.
* Deterministic checks use hard pass or fail outcomes without severity weighting.
* Anthropic API keys are account-scoped and rate limited, so repeated evaluation runs can be throttled.
* No real family data should be used during development.

These limitations are retained until evidence shows that additional complexity is necessary.

## Privacy and scope boundaries

During development:

* use synthetic family profiles
* keep Mosaic materials local
* keep processed records, vectors, and evaluations local
* do not commit secrets
* do not use real child or family information
* do not provide medical, psychological, legal, or diagnostic advice
* generate suggestions only from supplied Mosaic context
* use warm, non-directive language
* do not recreate a full curriculum
* do not answer unrelated general-purpose questions

The MVP is limited to generating one grounded, practical family learning pathway.
