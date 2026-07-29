import json
from pathlib import Path
from typing import Any

from mosaic_pathway.generation import AzureOpenAIPathwayGenerator
from mosaic_pathway.models import FamilyIntake
from mosaic_pathway.settings import load_settings

FAMILY_PATH = Path("examples/family_nature.json")
CONTEXT_PATH = Path("data/manual/context.json")
OUTPUT_PATH = Path("data/manual/pathway_output.json")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    intake = FamilyIntake.model_validate(load_json(FAMILY_PATH))
    context = load_json(CONTEXT_PATH)

    generator = AzureOpenAIPathwayGenerator(load_settings())
    pathway = generator.generate(intake, context)

    output = pathway.model_dump_json(indent=2)

    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(output)
    print(f"\nSaved output to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
