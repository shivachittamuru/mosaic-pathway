import json
from pathlib import Path

from mosaic_pathway.models import SourceInventoryItem

INVENTORY_PATH = Path("data/inventory/sources.json")


def load_inventory() -> list[SourceInventoryItem]:
    raw_items = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    return [SourceInventoryItem.model_validate(item) for item in raw_items]


def test_inventory_contains_all_supplied_sources() -> None:
    inventory = load_inventory()

    assert len(inventory) == 9


def test_inventory_source_ids_are_unique() -> None:
    inventory = load_inventory()
    source_ids = [item.source_id for item in inventory]

    assert len(source_ids) == len(set(source_ids))


def test_inventory_filenames_are_unique() -> None:
    inventory = load_inventory()
    filenames = [item.filename for item in inventory]

    assert len(filenames) == len(set(filenames))


def test_inventory_has_core_sources() -> None:
    inventory = load_inventory()
    core_sources = [item for item in inventory if item.rag_priority == "core"]

    assert len(core_sources) >= 3


def test_all_sources_require_cleaning() -> None:
    inventory = load_inventory()

    assert all(item.requires_cleaning for item in inventory)
