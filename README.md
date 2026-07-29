# Mosaic Family Pathway MVP

## What this project does

## Current workflow

```text
Synthetic family intake + manually selected Mosaic context
					|
					v
				LLM generation
					|
					v
		    Validated one-page pathway
```

## Technology choices

## Setup

## Add the private source materials

## Run checks

Run the tests:

```powershell
uv run pytest
```

Run and validate the Slice 1 family example:

```powershell
uv run python -c "from pathlib import Path; from mosaic_pathway.models import FamilyIntake; print(FamilyIntake.model_validate_json(Path('examples/family_nature.json').read_text()).model_dump_json(indent=2))"
```

## Current status

Slice 1 is complete. The project has validated family intake and learning pathway
models, synthetic family examples, and an inventory of the supplied Mosaic sources.
LLM generation currently uses context selected and supplied manually; automated
retrieval is not part of this slice.

## Development slices

## Privacy and scope boundaries