# Mosaic Family Pathway Architecture

This document explains how the MVP works today. Every statement describes code that
exists in this repository on the `aoai-generation-branch` branch. Planned or possible
future work is marked as conditional.

## 1. Problem and MVP objective

Families exploring self-directed education arrive with a mix of hopes, constraints, and
worries. Mosaic has written a great deal of guidance for them, but a family cannot read
all of it, and generic advice does not reflect their particular children.

The MVP accepts structured information about one family and produces a one-page learning
pathway grounded in Mosaic's own materials. The pathway contains a reflection of the
family's values, a light starting rhythm for the first two weeks, two or three
recommended resources or activities, and one low-pressure community suggestion. Every
recommendation carries the identifier of the Mosaic passage it came from.

The objective is a working, inspectable, inexpensive system that a small team can
understand end to end. It is not a production service.

## 2. Design principles

* Deterministic workflow rather than an agent. `MosaicPathwayService.generate_pathway`
  runs a fixed sequence: build query, retrieve, generate, verify. There is no planner,
  no tool selection, and no loop that decides what to do next.
* Local-first knowledge processing and retrieval. Extraction, cleaning, chunking,
  embedding, and vector search all run on the developer's machine. Only the retrieved
  passages and the intake leave the machine, and only at generation time.
* Structured Pydantic contracts. Every boundary in the system passes validated models
  rather than loose dictionaries, including the model response itself.
* Inspectable intermediate artifacts. The processed records, the retrieval query, the
  retrieved evidence, and the generated pathway are all readable JSON, which makes
  failures diagnosable without a debugger.
* Minimal frameworks and infrastructure. Plain Python modules, one embedding library,
  one local vector store, one HTTP framework. No orchestration layer, no dependency
  injection container, no message queue, no container build.
* Synthetic data during development. Every committed family profile and evaluation case
  is invented. No real family information is used.
* Private Mosaic content kept outside Git. Raw documents, processed chunks, vectors,
  generated pathways, and evaluation outputs are all ignored by Git.

## 3. High-level architecture

The request path runs when a family submits an intake:

```text
Family intake (FamilyIntake)
        |
        v
Deterministic query builder (query_builder.build_retrieval_query)
        |
        v
Local embedding model (embeddings.LocalEmbeddingModel)
        |
        v
Local Qdrant retrieval (vector_store.MosaicVectorStore + retrieval.MosaicRetriever)
        |
        v
Retrieved SourceRecords (list[RetrievedRecord])
        |
        v
Azure OpenAI structured generation (generation.AzureOpenAIPathwayGenerator)
        |
        v
Grounding validation (rag.MosaicPathwayService)
        |
        v
LearningPathway inside a GroundedPathwayResult
        |
        v
Streamlit (app.py) or FastAPI (api.py)
```

The knowledge base is prepared separately and offline, before any request can be served:

```text
Private PDF and DOCX files in data/raw/
        |
        v
Extraction (extraction.extract_paragraphs)
        |
        v
Cleaning (cleaning.clean_paragraphs)
        |
        v
Paragraph-aware chunking (knowledge_base.chunk_paragraphs)
        |
        v
Validated SourceRecords in data/processed/source_records.json
        |
        v
Local embeddings (embeddings.LocalEmbeddingModel.embed_documents)
        |
        v
Qdrant collection "mosaic_sources" in data/vector_store/
```

The two pipelines meet only through the processed records file and the Qdrant
collection. The request path never reads the raw documents.

## 4. Component responsibilities

| Module | Responsibility |
|--------|----------------|
| `models.py` | Every validated contract in the system, from `ChildProfile` through `EvaluationCase`. Nothing else defines domain shapes. |
| `settings.py` | `Settings` reads `AZURE_OPENAI_BASE_URL` and `AZURE_OPENAI_CHAT_DEPLOYMENT` from the environment or `.env`. `load_settings()` is the single entry point. |
| `extraction.py` | Turns one PDF or DOCX file into ordered raw paragraphs. PDFs are read block by block with PyMuPDF; DOCX paragraphs are read in document order. Unsupported suffixes raise `UnsupportedFileTypeError`. |
| `cleaning.py` | Normalizes whitespace, drops an explicit list of navigation and footer lines, applies a few footer patterns, and removes consecutive duplicate paragraphs. The noise list is deliberately literal and easy to edit. |
| `knowledge_base.py` | Owns `PROJECT_ROOT` and the data paths. Loads the reviewed inventory, extracts and cleans each included source, groups paragraphs into chunks of roughly 1,500 characters with a 2,000 character ceiling, assigns stable IDs of the form `<inventory-source-id>-0001`, validates each record, and writes `data/processed/source_records.json`. |
| `embeddings.py` | Wraps `all-MiniLM-L6-v2`. Loads the model lazily on first use, embeds documents in batches, normalizes vectors, and returns plain Python lists so no numpy types leak into the rest of the system. |
| `vector_store.py` | Owns the persistent local Qdrant collection: creation with cosine distance, deterministic point IDs, batched upserts, exact counts, and similarity search. `build_index` rebuilds the collection and verifies the written count. |
| `retrieval.py` | Combines the embedding model and the store. Over-fetches candidates, caps results per inventory source, widens the candidate window when the cap under-fills the request, and returns a `RetrievalResult`. |
| `query_builder.py` | Converts a `FamilyIntake` into one deterministic block of searchable prose, omitting empty fields. No model call is involved. |
| `prompts.py` | Holds `SYSTEM_PROMPT`, which carries the thirteen behavioral rules, and `build_generation_prompt`, which serializes the intake and the retrieved context into the user message. |
| `generation.py` | `AzureOpenAIPathwayGenerator` authenticates with Entra ID, calls the Azure OpenAI structured-output API with `LearningPathway` as the response format, and raises on refusal or an unparsed response. |
| `rag.py` | `MosaicPathwayService` is the composition point for the whole request path, and the only place that verifies citations. Raises `GroundingError` when a pathway cites an identifier that retrieval did not return. |
| `pathway_evaluation.py` | Ten deterministic checks over one generated pathway, plus the aggregation into an `EvaluationReport`. |
| `retrieval_evaluation.py` | Baseline retrieval metrics over the synthetic query set: hit rate at five and mean reciprocal rank. |
| `app.py` | The Streamlit interface. Builds the form, calls the service, and renders the pathway, the source evidence, and the method explanation. |
| `app_support.py` | The pure helpers behind the interface: parsing, validation messages, session state access, and `evidence_preview`. Keeping these free of Streamlit calls is what makes the interface testable offline. |
| `api.py` | The FastAPI application: settings, CORS, a lifespan handler that builds expensive dependencies once, error mapping, and the two routes. |
| `slice1_demo.py`, `slice2b_demo.py`, `slice3_demo.py`, `slice4_evaluation.py` | Command-line entry points that demonstrate one capability each. They are the recommended reading order for a new developer. |

## 5. Contracts and data flow

* `ChildProfile` describes one learner: a non-identifying label, an age between 2 and 21,
  at least one interest, and optional learning needs. Labels rather than names keep
  identifying information out of the system by construction.
* `FamilyIntake` is the request contract for the whole application. It holds the
  children plus what the family wants to leave behind, preserve, and add, their values,
  their practical constraints, and free-text context. The Streamlit form, the API
  request body, and the evaluation cases all produce this same model.
* `SourceRecord` is one cleaned, retrievable chunk of Mosaic knowledge, carrying its
  stable `source_id`, title, originating filename, content and authority types, topics,
  optional age range, and the text itself. It is stored as the Qdrant payload, so
  retrieval reconstructs it by validating the payload rather than by a second lookup.
* `RetrievedRecord` pairs a `SourceRecord` with its similarity score, and
  `RetrievalResult` pairs the query with the ranked records.
* `LearningPathway` is the generated artifact and also the schema handed to Azure
  OpenAI: a family reflection, two to six `RhythmPractice` entries, two or three
  `ResourceRecommendation` entries each carrying a `source_id`, one
  `CommunitySuggestion` with an optional `source_id`, and a closing note.
* `GroundedPathwayResult` binds a pathway to the evidence that produced it: the intake,
  the retrieval query, the retrieved records, and the pathway. This is what makes an
  after-the-fact review possible, and it is what the evaluation consumes.
* The API source-summary response, `PathwayApiResponse`, contains the validated pathway
  plus a list of `SourceSummary` objects. Each summary carries only the source
  identifier, the title, the score rounded to four decimal places, and a preview of at
  most 250 characters. The complete `GroundedPathwayResult` never crosses the HTTP
  boundary.

## 6. Retrieval

* Embeddings come from `sentence-transformers/all-MiniLM-L6-v2`, executed locally. The
  model is downloaded once by the sentence-transformers cache and then runs offline.
* Vectors are normalized at encode time for both documents and queries, so the cosine
  distance configured in Qdrant behaves as a plain dot product.
* Qdrant runs in local persistent mode against `data/vector_store/`. There is no server
  process and no network call.
* The collection `mosaic_sources` is created with `Distance.COSINE` and the dimension
  reported by the embedding model.
* A configurable per-source cap, `max_per_source`, defaults to 2. It applies to the
  inventory-level source derived by `inventory_source_id`, which strips the trailing
  chunk number from a record ID.
* Two different defaults for `top_k` coexist deliberately. `retrieval.DEFAULT_TOP_K` is
  5 and governs the demos and the retrieval evaluation, while `rag.DEFAULT_TOP_K` is 6
  and governs generation, which benefits from one extra passage. A request through
  Streamlit or the API therefore returns six sources, and the reported hit rate at five
  describes the evaluation setting rather than the serving one.
* Candidate expansion is adaptive. The first window is `max(top_k * 4, 20)` candidates.
  If the per-source cap leaves fewer than `top_k` results, the window doubles and the
  search repeats until the request is satisfied or the whole collection has been
  considered.
* Identifiers are stable in both directions. A record ID is derived from its inventory
  source plus a zero-padded chunk number, and `point_id_for` maps that ID through a
  fixed UUID5 namespace, so rebuilding the index reuses the same point IDs rather than
  creating duplicates.
* The current corpus holds 807 validated records built from nine source documents.
* The corpus is imbalanced. Roughly 82 percent of records come from the Mosaic website
  export, which is why the per-source cap exists. Without it, one source fills the
  entire result window.

## 7. Generation and grounding

* Query construction is deterministic. `build_retrieval_query` renders the intake as
  prose using the family's own wording. The same intake always produces the same query,
  which makes retrieval reproducible and cheap to debug.
* The model receives only the retrieved context. `build_context` reduces each retrieved
  record to its chunk ID, inventory source ID, title, and text, and the system prompt
  forbids inventing organizations, programs, books, websites, or activities that are
  absent from those passages.
* Generation uses the Azure OpenAI structured-output API. The client is the OpenAI SDK
  pointed at the Azure base URL, authenticated with a bearer token provider built from
  `DefaultAzureCredential`. The call passes `LearningPathway` directly as the response
  format.
* Pydantic validates the result twice over: the SDK parses the response into
  `LearningPathway`, and the model's own field constraints reject a pathway with too few
  practices or the wrong number of resources. A refusal or an unparsed response raises
  rather than returning a partial object.
* Source identifiers live in dedicated structured fields. The prompt explicitly forbids
  citation markers inside family-facing prose, and a deterministic check enforces this
  afterwards.
* Runtime verification closes the loop. `MosaicPathwayService.generate_pathway` collects
  every non-empty cited identifier and subtracts the set of retrieved identifiers. Any
  remainder raises `GroundingError`, so a pathway citing a passage that was never
  retrieved is never returned to a caller.
* Identifier validity is not claim support. This check proves that a citation points at
  a passage the model was actually shown. It does not prove that the passage says what
  the recommendation claims. Assessing that remains a human judgment, which is why the
  review rubric exists.

## 8. Evaluation

Retrieval is measured against ten human-authored synthetic queries in
`examples/retrieval_queries.json`, each listing the inventory sources a good answer
should surface.

* Hit rate at five counts the queries where an expected source appears in the top five
  results. The initial baseline was 8 hits from 10 queries, or 0.80.
* Mean reciprocal rank is computed over the successful queries only, so it describes how
  highly the first correct source ranked when retrieval succeeded rather than blending
  in the misses.
* The two recorded misses concerned family criticism and the educator-to-parent
  transition.

Generated pathways are measured by `slice4_evaluation`, which runs the complete workflow
over the six synthetic cases in `examples/evaluation/` and applies ten deterministic
checks to each: required sections populated, resource count in range, resource citations
grounded, community citation grounded, no citation markers in prose, no duplicate
recommendations, word-count guardrails, no prohibited phrases, and two weak
personalization indicators. The initial run passed 6 of 6 cases and 60 of 60 checks.

A human review was completed for the same cases using
[docs/pathway-review-rubric.md](pathway-review-rubric.md), scoring personalization,
evidence support, practicality, tone, and scope adherence from 1 to 3.

These results describe a small, self-authored baseline and nothing more. The query set
and the case set are tiny and were written by the same person who built the system. The
personalization checks are lexical, so repeating a stated interest satisfies them
without producing a genuinely tailored suggestion. The prohibited-phrase list is a short
substring match, not safety validation. Every check is a hard pass or fail with no
severity weighting. None of this constitutes scientific measurement or production-grade
validation.

## 9. Presentation boundaries

* Streamlit calls the Python service directly. `app.py` imports `MosaicPathwayService`
  and holds it in `st.cache_resource`, so there is no HTTP hop and no serialization
  between the interface and the workflow. The Streamlit process owns the vector store
  for as long as it runs.
* FastAPI exposes the same service to external frontends. `api.py` builds the identical
  object graph inside a lifespan handler and serves `GET /health` and
  `POST /api/v1/pathways`. A React or other browser client would use this path.
* The two interfaces differ in what they reveal. Streamlit runs on the operator's own
  machine and shows a 250-character preview of each retrieved passage in a collapsed
  expander. The API returns `SourceSummary` objects only, so complete private chunks
  never leave the process over HTTP.
* No submitted family information is persisted by either interface. Streamlit keeps the
  latest result in session state, which disappears when the browser session ends. The
  API writes nothing to disk and logs only request lines. The evaluation script is the
  one component that writes generated pathways to disk, and it writes them into an
  ignored directory.

## 10. Privacy and trust boundaries

| Artifact | Location | Status |
|----------|----------|--------|
| Private raw documents | `data/raw/` | Local only, ignored by Git except for `.gitkeep` |
| Processed chunks | `data/processed/source_records.json` | Local only, ignored by Git |
| Vector store | `data/vector_store/` | Local only, ignored by Git |
| Generated pathways | `data/manual/` | Local only, ignored by Git |
| Evaluation outputs | `data/evaluation/` | Local only, ignored by Git |
| Source inventory | `data/inventory/sources.json` | Committed: metadata and filenames only, no source text |
| Synthetic families and queries | `examples/` | Committed: invented data only |
| Credentials | `.env` | Local only, ignored by Git. `.env.example` holds placeholders |

Two boundaries carry private content out of the process:

* The Azure OpenAI request boundary. Each generation sends the family intake and the
  retrieved Mosaic passages to the configured Azure OpenAI deployment. This is the only
  place Mosaic source text leaves the machine, and it is the boundary to review with
  Mosaic before any wider use.
* The API response boundary. Responses carry the generated pathway plus truncated
  source summaries. This boundary is deliberately narrower than the Streamlit one
  because an HTTP client is assumed to be less trusted than the operator's own screen.

Everything else stays on the machine that ran it.

## 11. Azure OpenAI provider boundary

Azure-specific code is confined to two modules and one configuration file:

* `generation.py` holds `AzureOpenAIPathwayGenerator`, which builds the Entra ID token
  provider against the `https://ai.azure.com/.default` scope and calls the structured
  output API with the deployment name as the model.
* `settings.py` defines the two required variables, `AZURE_OPENAI_BASE_URL` and
  `AZURE_OPENAI_CHAT_DEPLOYMENT`.
* `.env` supplies those values locally, and `.env.example` documents them.

Nothing else imports the `openai` or `azure.identity` packages except `api.py`, which
imports `OpenAIError` purely to classify failures. `MosaicPathwayService` depends on the
generator object, not on Azure.

The branch `aoai-generation-branch` preserves this working Azure OpenAI implementation.
It is the reference point to return to if a provider experiment goes badly.

A reasonable future swap would introduce a small protocol describing the single method
`generate(intake, context) -> LearningPathway`, keep `AzureOpenAIPathwayGenerator` as
one implementation, add a sibling implementation for another provider, and select
between them with one setting. `MosaicPathwayService` would not change, because it
already depends only on that method.

That swap is not free, and the providers are not interchangeable. Azure OpenAI, OpenAI,
and Anthropic Claude differ in how they express structured output, in how strictly they
guarantee schema conformance, and in how they authenticate. This project uses Entra ID
token authentication and the OpenAI SDK's parse helper, which returns an already
validated `LearningPathway`. Another provider may require an explicit tool or schema
definition, a different error surface, a separate parsing and validation step, and API
key handling instead of federated credentials. Any migration should be measured against
the existing evaluation rather than assumed to be equivalent.

## 12. Runtime limitations

* The local Qdrant database uses an exclusive file lock. Exactly one process may own
  `data/vector_store/` at a time, so the Streamlit app, the API, and any command-line
  demo cannot run concurrently. Starting a second one raises a storage lock error.
* Generation is synchronous. A request occupies its worker for the full duration of the
  Azure OpenAI call, which is typically several seconds. There is no streaming, no
  queue, and no progress reporting beyond the Streamlit spinner.
* The API is for local development only. It binds to localhost, allows a small list of
  configured browser origins, and assumes a trusted caller.
* There is no authentication, no authorization, no persistence layer, no rate limiting,
  no background job runner, and no deployment configuration. There is no Dockerfile and
  no CI pipeline.
* Azure authentication is tenant-sensitive. `DefaultAzureCredential` resolves the Azure
  CLI default tenant, which may not be the tenant that owns the Azure OpenAI resource.
  When they differ, set `AZURE_TENANT_ID` in the shell session before running. Setting
  it in `.env` has no effect, because that file is read by the settings model rather
  than exported into the process environment.
* The first run of any command that touches embeddings pays a one-time model download,
  and every process start pays several seconds of sentence-transformers import time.

## 13. Evolution path

None of the following is implemented, and none of it should be built without a reason
that comes from evidence rather than ambition.

* A provider-specific generator implementation behind a shared protocol, if a second
  model provider becomes necessary.
* A React frontend against the existing API, if the Streamlit interface proves too
  limited for real use.
* Hybrid retrieval or reranking, only if evaluation shows that semantic search alone
  misses material a family needed. The current misses would be the place to start.
* Stronger semantic evaluation, such as human-scored faithfulness on a larger case set,
  if the deterministic checks stop catching real problems.
* Production vector infrastructure, if the corpus outgrows local Qdrant or more than one
  process must read it concurrently.
* Authentication, authorization, and deployment controls, if the API is ever exposed
  beyond a developer machine. That step is a prerequisite for any real family data, not
  an optional extra.

The corpus imbalance and the small evaluation sets are the two weaknesses most likely to
matter first. Both are cheaper to address than any of the infrastructure above.
