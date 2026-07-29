# Mosaic Family Pathway MVP

A small, intentionally lean Retrieval-Augmented Generation project for Mosaic.

The MVP is designed to help families exploring self-directed learning receive a warm, practical, one-page learning pathway grounded in Mosaic’s materials.

## What this project does

The completed MVP will:

1. Collect structured information about a family and its learners.
2. Retrieve relevant guidance from Mosaic’s knowledge base.
3. Use an LLM to generate a personalized learning pathway.
4. Validate the generated response against a defined schema.
5. Present a concise pathway containing:

   * a reflection of the family’s values and intentions
   * a practical starting rhythm for the first two weeks
   * two or three grounded resources or activities
   * one community suggestion

The project intentionally avoids agents, complex orchestration frameworks, and unnecessary infrastructure.

## Current workflow

Slice 1 currently uses manually selected Mosaic context rather than automated retrieval.

```text
Synthetic family intake
        +
Manually selected Mosaic context
        |
        v
Azure OpenAI generation
        |
        v
Validated LearningPathway
        |
        v
Local JSON output
```

## Technology choices

Current:

* Python 3.12
* `uv` for dependency and environment management
* Pydantic for structured input and output validation
* Azure OpenAI for pathway generation
* Microsoft Entra ID for authentication
* Pytest for tests
* Ruff for formatting and linting
* Mypy for type checking

Planned for later slices:

* local document extraction and cleaning
* Sentence Transformers for local embeddings
* Qdrant local mode for vector retrieval
* Streamlit for a minimal user interface

## Setup

Clone the repository:

```powershell
git clone https://github.com/shivachittamuru/mosaic-pathway.git
cd mosaic-pathway
```

Install the project dependencies:

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

Configure the Azure OpenAI endpoint and deployment name in `.env`:

```dotenv
AZURE_OPENAI_BASE_URL=https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/
AZURE_OPENAI_CHAT_DEPLOYMENT=YOUR-DEPLOYMENT-NAME
```

Authenticate with Azure:

```powershell
az login
```

No API key should be stored in the repository.

## Add the private source materials

Place the supplied Mosaic PDFs and DOCX file under:

```text
data/raw/
```

These source files are private and intentionally excluded from Git.

Do not commit:

* original Mosaic source documents
* cleaned or extracted Mosaic content
* generated pathways based on private content
* `.env`
* real family information
* prompts or traces containing private content

## Run checks

Run the tests:

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

## Run Slice 1

Slice 1 generates a structured pathway from a synthetic family profile and manually curated Mosaic context.

The manual context file must exist locally at:

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

The manual context and generated output are excluded from Git.

## Current status

### Slice 0 — Complete

* Python project and Git repository initialized
* family intake schema defined
* learning pathway schema defined
* Mosaic source metadata schema defined
* synthetic family profiles created
* supplied Mosaic sources inventoried
* validation tests added

### Slice 1 — Complete

* Azure OpenAI integration added
* Microsoft Entra ID authentication configured
* manually selected Mosaic context supplied to the model
* structured `LearningPathway` generation implemented
* Pydantic output validation added
* generated output stored locally
* offline tests remain independent of Azure OpenAI

### Next

Slice 2 will extract, clean, and structure the supplied Mosaic PDF and DOCX content.

Automated retrieval is not yet implemented.

## Development slices

1. **Foundation and contracts** — complete
2. **Generation with manual context** — complete
3. **Content extraction and cleaning**
4. **Local embedding and retrieval**
5. **End-to-end RAG workflow**
6. **Lean evaluation**
7. **Minimal Streamlit interface**
8. **Final documentation and handoff**

Each slice is intentionally small and must work before the next capability is added.

## Privacy and scope boundaries

During development:

* use synthetic family profiles
* keep Mosaic materials local
* do not commit secrets
* do not use real child or family information
* do not provide medical, psychological, legal, or diagnostic advice
* generate suggestions only from supplied Mosaic context
* use warm, non-directive language
* do not recreate a full curriculum
* do not answer unrelated general-purpose questions

The MVP is limited to generating one grounded, practical family learning pathway.
