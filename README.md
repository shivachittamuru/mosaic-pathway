# Mosaic Family Pathway MVP

A small, intentionally lean Retrieval-Augmented Generation project for Mosaic.

The MVP helps families exploring self-directed learning receive a warm, practical, one-page learning pathway grounded in Mosaic’s materials.

## What this project does

The system:

1. Collects structured information about a family and its learners.
2. Retrieves relevant guidance from Mosaic’s knowledge base.
3. Uses an LLM to generate a personalized learning pathway.
4. Validates the response against a defined schema.
5. Produces a concise pathway containing:

   * a reflection of the family’s values and intentions
   * a practical starting rhythm
   * two or three grounded resources or activities
   * one community suggestion

The project intentionally avoids agents, orchestration frameworks, cloud databases, and unnecessary infrastructure.

## Current workflow

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
              |
              v
 Relevant Mosaic passages
              |
              v
 Azure OpenAI generation
              |
              v
 Validated LearningPathway
```

Slices 1 and 2 currently work independently:

* Slice 1 generates a pathway using manually selected context.
* Slice 2 prepares the Mosaic knowledge base and retrieves context automatically.
* The next slice will connect retrieval to generation.

## Technology choices

* Python 3.12
* `uv` for dependency and environment management
* Pydantic for structured data validation
* PyMuPDF for PDF text extraction
* `python-docx` for DOCX extraction
* Sentence Transformers for local embeddings
* `all-MiniLM-L6-v2` as the initial embedding model
* Qdrant local mode for vector storage and similarity search
* Azure OpenAI for pathway generation
* Microsoft Entra ID for Azure authentication
* Pytest for tests
* Ruff for formatting and linting
* Mypy for type checking

A minimal Streamlit interface is planned for a later slice.

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

The source files are private and excluded from Git.

Do not commit:

* original Mosaic source documents
* extracted or cleaned Mosaic content
* local vector-store files
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

The current source set produces 807 records:

```text
Mosaic website resources:                    664
Navigating self-directed learning alone:      12
Affording a different path:                   21
Permission to choose:                         14
College applications:                         25
Making the college process human again:       20
Neurodivergence:                              17
School harm and racism:                       16
Educators becoming parents:                   18
```

Processed content remains excluded from Git.

## Run Slice 2B: Index and retrieve

Slice 2B embeds the validated source records locally and stores them in a persistent Qdrant collection.

Build or rebuild the local vector index:

```powershell
uv run python -m mosaic_pathway.vector_store
```

The index contains one vector and payload for every validated `SourceRecord`.

Run the retrieval demonstration:

```powershell
uv run python -m mosaic_pathway.slice2b_demo
```

The demo runs synthetic family-oriented queries and displays:

* similarity score
* source-record ID
* source title
* a truncated passage preview

Retrieval requests additional candidates and applies a configurable per-source cap. This prevents the much larger Mosaic website source from occupying every result while preserving semantic-score order.

Run the retrieval baseline evaluation:

```powershell
uv run python -m mosaic_pathway.retrieval_evaluation
```

The evaluator reports:

* hit rate at five
* mean reciprocal rank
* first expected-source rank
* retrieved source IDs
* queries that missed their expected sources

This is an initial human-authored baseline rather than a complete retrieval benchmark.

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

* Azure OpenAI integration added
* Microsoft Entra ID authentication configured
* structured `LearningPathway` generation implemented
* manually selected Mosaic context supplied to the model
* Pydantic output validation added
* generated output stored locally
* offline tests remain independent of Azure OpenAI

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
* source-diversity behavior added
* synthetic retrieval queries created
* hit-rate and ranking evaluation added
* retrieval runs without Azure OpenAI

### Next

The next slice will connect automatic retrieval from Slice 2 with structured pathway generation from Slice 1.

## Development slices

1. **Foundation and contracts** — complete
2. **Generation with manual context** — complete
3. **Content extraction and cleaning** — complete
4. **Local embeddings and retrieval** — complete
5. **End-to-end RAG pathway generation**
6. **Pathway and retrieval evaluation**
7. **Minimal Streamlit interface**
8. **Final documentation, notebooks, and handoff**

Each slice is intentionally small and must work before the next capability is added.

## Known limitations

* The Mosaic website source contains approximately 82% of all records.
* Some nonconsecutive duplicate website sections remain in the processed data.
* Embedding similarity scores are not probabilities.
* Retrieval quality is currently evaluated using a small synthetic query set.
* Retrieval uses semantic vector search only.
* There is no keyword search, reranking, or hybrid retrieval.
* Retrieval and pathway generation have not yet been connected.
* No real family data should be used during development.

These limitations are retained intentionally until evaluation demonstrates that additional complexity is necessary.

## Privacy and scope boundaries

During development:

* use synthetic family profiles
* keep Mosaic materials local
* keep processed records and vectors local
* do not commit secrets
* do not use real child or family information
* do not provide medical, psychological, legal, or diagnostic advice
* generate suggestions only from supplied Mosaic context
* use warm, non-directive language
* do not recreate a full curriculum
* do not answer unrelated general-purpose questions

The MVP is limited to generating one grounded, practical family learning pathway.
