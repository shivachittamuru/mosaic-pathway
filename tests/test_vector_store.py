import json
from pathlib import Path

from conftest import FAKE_DIMENSION, FakeEmbeddingModel, make_source_record

from mosaic_pathway.models import SourceRecord
from mosaic_pathway.vector_store import (
    MosaicVectorStore,
    build_index,
    load_source_records,
    point_id_for,
)


def test_point_id_is_deterministic_and_unique() -> None:
    assert point_id_for("mosaic-web-resources-0001") == point_id_for(
        "mosaic-web-resources-0001"
    )
    assert point_id_for("mosaic-web-resources-0001") != point_id_for(
        "mosaic-web-resources-0002"
    )


def test_create_collection_and_index_records(
    tmp_path: Path, fake_embedding_model: FakeEmbeddingModel
) -> None:
    records = [
        make_source_record(f"synthetic-source-{index:04d}") for index in range(5)
    ]

    with MosaicVectorStore(tmp_path / "store") as store:
        assert not store.collection_exists()

        store.create_collection(fake_embedding_model.dimension)

        assert store.collection_exists()
        assert store.index_records(records, fake_embedding_model, batch_size=2) == 5
        assert store.count() == 5


def test_search_returns_payloads_that_validate_as_source_records(
    tmp_path: Path, fake_embedding_model: FakeEmbeddingModel
) -> None:
    records = [
        make_source_record(f"synthetic-source-{index:04d}") for index in range(3)
    ]

    with MosaicVectorStore(tmp_path / "store") as store:
        store.create_collection(fake_embedding_model.dimension)
        store.index_records(records, fake_embedding_model)

        results = store.search(fake_embedding_model.embed_query(records[1].text), 3)

    assert len(results) == 3

    payloads = [SourceRecord.model_validate(payload) for payload, _ in results]

    assert payloads[0] == records[1]
    assert {payload.source_id for payload in payloads} == {
        record.source_id for record in records
    }


def test_recreate_collection_clears_existing_points(
    tmp_path: Path, fake_embedding_model: FakeEmbeddingModel
) -> None:
    records = [
        make_source_record(f"synthetic-source-{index:04d}") for index in range(3)
    ]

    with MosaicVectorStore(tmp_path / "store") as store:
        store.create_collection(fake_embedding_model.dimension)
        store.index_records(records, fake_embedding_model)

        store.recreate_collection(fake_embedding_model.dimension)

        assert store.count() == 0


def test_build_index_reports_indexed_record_count(tmp_path: Path) -> None:
    records = [
        make_source_record(f"synthetic-source-{index:04d}") for index in range(7)
    ]
    records_path = tmp_path / "source_records.json"
    records_path.write_text(
        json.dumps([record.model_dump() for record in records]), encoding="utf-8"
    )

    indexed = build_index(
        records_path=records_path,
        store_path=tmp_path / "store",
        embedding_model=FakeEmbeddingModel(),
    )

    assert indexed == 7
    assert load_source_records(records_path) == records


def test_indexing_is_idempotent_for_repeated_record_ids(
    tmp_path: Path, fake_embedding_model: FakeEmbeddingModel
) -> None:
    records = [
        make_source_record(f"synthetic-source-{index:04d}") for index in range(4)
    ]

    with MosaicVectorStore(tmp_path / "store") as store:
        store.create_collection(FAKE_DIMENSION)
        store.index_records(records, fake_embedding_model)
        store.index_records(records, fake_embedding_model)

        assert store.count() == 4
