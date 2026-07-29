# Mosaic Family Pathway MVP

A small, intentionally simple Retrieval-Augmented Generation (RAG) project for Mosaic.

The goal is to build a working MVP that:

1. Accepts structured information about a family.
2. Retrieves relevant guidance from Mosaic’s materials.
3. Uses an LLM to generate a personalized one-page learning pathway.
4. Keeps the workflow understandable, testable, and inexpensive.

This project intentionally avoids unnecessary infrastructure and frameworks.

## MVP principles

* Keep the architecture simple.
* Use ordinary Python instead of agent frameworks.
* Use local and free tooling where practical.
* Use synthetic family profiles during development.
* Add one capability at a time.
* Do not add features unless they are required for the MVP.

## Planned workflow

```text
Mosaic source documents
        ↓
Extract and clean content
        ↓
Create local embeddings
        ↓
Store content in a local vector database
        ↓

Family intake
        ↓
Retrieve relevant Mosaic passages
        ↓
Send intake and retrieved context to an LLM
        ↓
Generate a structured one-page pathway
        ↓
Validate and display the result
```

## Initial technology choices

The project will begin with:

* Python 3.12
* `uv` for Python environments and dependency management
* Pydantic for data models and validation
* Pytest for tests
* Ruff for formatting and linting
* Mypy for type checking

Later slices may add:

* Azure OpenAI or Anthropic Claude for generation
* Sentence Transformers for local embeddings
* Qdrant local mode for vector storage
* Document parsers for PDF and DOCX files
* Streamlit for a minimal user interface

These later dependencies should not be installed until the project reaches the slice that needs them.

---

# Prerequisites

Install the following tools before starting.

## 1. Install Git

Download and install Git for Windows.

After installation, open PowerShell and confirm:

```powershell
git --version
```

## 2. Install `uv`

Open PowerShell and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell.

Confirm the installation:

```powershell
uv --version
```

## 3. Configure Git identity

Run these commands using your own name and email address:

```powershell
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

---

# Create the project

Choose a folder where you normally keep development projects.

For example:

```powershell
cd C:\Users\YourName\Documents
```

Create the project folder:

```powershell
mkdir mosaic-pathway
cd mosaic-pathway
```

Initialize the Python project:

```powershell
uv init --package
```

Initialize Git:

```powershell
git init
```

---

# Set the Python version

This project uses Python 3.12.

Run:

```powershell
uv python pin 3.12
uv sync
```

Confirm the version:

```powershell
uv run python --version
```

Expected output:

```text
Python 3.12.x
```

The first `uv sync` command creates:

* `.venv`
* `uv.lock`

Do not manually activate the virtual environment. Use `uv run` when running project commands.

---

# Install the initial dependencies

Install the application dependencies:

```powershell
uv add pydantic pydantic-settings
```

Install the development dependencies:

```powershell
uv add --dev pytest ruff mypy
```

Do not install AI, vector database, document parsing, or UI packages yet.

---

# Create the project folders

Run:

```powershell
mkdir data
mkdir data\raw
mkdir data\inventory
mkdir examples
mkdir tests
```

The project should now look similar to:

```text
mosaic-pathway/
├── data/
│   ├── inventory/
│   └── raw/
├── examples/
├── src/
│   └── mosaic_pathway/
│       └── __init__.py
├── tests/
├── .gitignore
├── .python-version
├── README.md
├── pyproject.toml
└── uv.lock
```

---

# Configure `.gitignore`

Open `.gitignore` and add:

```gitignore
# Local Mosaic source materials
data/raw/*
!data/raw/.gitkeep

# Generated local data
data/processed/
data/qdrant/

# Environment variables and secrets
.env

# Python and development caches
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
```

Create an empty placeholder inside the raw-data folder:

```powershell
New-Item data\raw\.gitkeep -ItemType File
```

This allows Git to preserve the folder without committing the private source documents.

---

# Add the Mosaic source materials

Copy the provided Mosaic PDFs and DOCX file into:

```text
data/raw/
```

For example:

```text
data/raw/
├── Resources_Mosaic.docx
├── podcast-transcript-01.pdf
├── podcast-transcript-02.pdf
└── ...
```

These source files should remain local and must not be committed to Git.

Before every commit, verify that they are not staged.

---

# Run the initial checks

Run:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

At this stage, Pytest may report that no tests were collected. That is expected because the project does not contain tests yet.

The Ruff and Mypy commands should finish without errors.

---

# Create the first Git commit

Review the files that Git sees:

```powershell
git status
```

Make sure that the PDFs and DOCX file under `data/raw/` are not listed as staged files.

Stage the project files:

```powershell
git add .
```

Check again:

```powershell
git status
```

Create the first commit:

```powershell
git commit -m "Initialize lean Mosaic pathway project"
```

---

# Verify the setup

Run:

```powershell
Get-ChildItem -Recurse -Depth 3
git status
uv run python --version
```

Expected results:

* Python reports version 3.12.x.
* Git reports a clean working tree.
* The project structure contains `src`, `tests`, `examples`, and `data`.
* The Mosaic source files exist locally under `data/raw`.
* The source files are ignored by Git.

---

# Development plan

The project will be built in small slices.

## Slice 0 — Foundation and contracts

* Create the project structure.
* Inventory the Mosaic content.
* Define the family intake schema.
* Define the one-page pathway schema.
* Create synthetic family profiles.

## Slice 1 — Generation without RAG

Use a synthetic family intake and manually selected Mosaic excerpts to generate a structured pathway with an LLM.

This validates the prompt and output design before retrieval is introduced.

## Slice 2 — Content preparation

* Extract PDF and DOCX text.
* Remove navigation, footers, repeated content, and other noise.
* Create clean content records.
* Add basic metadata.

## Slice 3 — Local retrieval

* Generate local embeddings.
* Store them in local Qdrant.
* Test retrieval separately from generation.

## Slice 4 — End-to-end RAG

Connect:

```text
Family intake
   ↓
Retrieval
   ↓
Mosaic context
   ↓
LLM generation
   ↓
Validated pathway
```

## Slice 5 — Lean evaluation

* Use synthetic test profiles.
* Add deterministic validation checks.
* Use a short human-review rubric.
* Record latency and token usage.

## Slice 6 — Minimal Streamlit app

* Family intake form.
* Generate button.
* One-page pathway result.
* Source references.
* Simple feedback fields.

## Slice 7 — Documentation and handoff

* Setup guide.
* Architecture summary.
* User-testing guide.
* Known limitations.
* Optional Anthropic Claude adapter.

---

# Explicitly out of scope for the lean MVP

Do not add the following unless a later requirement clearly demands them:

* AI agents
* LangChain
* LangGraph
* long-term conversational memory
* authentication
* user accounts
* WordPress integration
* cloud-hosted vector databases
* Docker
* Kubernetes
* CI/CD
* Redis
* PostgreSQL
* background jobs
* production monitoring platforms
* complex administrative dashboards
* automated web search
* a 100-day learning planner
* a general-purpose chatbot

The MVP should remain focused on generating one useful, grounded learning pathway.

---

# Security and privacy

During development:

* Use synthetic family data.
* Do not commit source documents.
* Do not commit API keys.
* Store secrets in a local `.env` file.
* Confirm authorization before sending real Mosaic or family data to any external API.
* Avoid collecting names or identifying information unless required.
* Do not use real child medical or learning information during early testing.

---

# Common commands

Install or synchronize dependencies:

```powershell
uv sync
```

Run tests:

```powershell
uv run pytest
```

Run Ruff:

```powershell
uv run ruff check .
```

Check formatting:

```powershell
uv run ruff format --check .
```

Format the project:

```powershell
uv run ruff format .
```

Run Mypy:

```powershell
uv run mypy src
```

Run all initial quality checks:

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

View Git status:

```powershell
git status
```

---

# Troubleshooting

## `uv` is not recognized

Close and reopen PowerShell after installation.

Then run:

```powershell
uv --version
```

If it still fails, restart the computer or verify that the `uv` installation directory is on the system `PATH`.

## Python 3.12 is unavailable

Run:

```powershell
uv python install 3.12
uv python pin 3.12
uv sync
```

## PowerShell blocks the `uv` installation command

Run the installation command exactly as shown:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Mosaic files appear in `git status`

Check that `.gitignore` contains:

```gitignore
data/raw/*
!data/raw/.gitkeep
```

If a source file was already added to Git, remove it from Git tracking without deleting the local file:

```powershell
git rm --cached data\raw\<filename>
```

Then check:

```powershell
git status
```

## Pytest says no tests were collected

That is normal during the initial setup. Tests will be added in the next implementation step.

---

# Current status

The project foundation is complete when:

* `uv` manages the Python environment.
* Python 3.12 is configured.
* Git is initialized.
* Initial dependencies are installed.
* The source documents are stored locally and ignored by Git.
* The first commit has been created.
* Ruff and Mypy run successfully.

The next step is to define the family intake and one-page pathway data contracts.
