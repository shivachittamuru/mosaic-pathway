from conftest import FAKE_DIMENSION, FakeEmbeddingModel

from mosaic_pathway.embeddings import DEFAULT_EMBEDDING_MODEL, LocalEmbeddingModel


def test_local_embedding_model_does_not_load_at_construction() -> None:
    model = LocalEmbeddingModel()

    assert model.model_name == DEFAULT_EMBEDDING_MODEL
    assert model._model is None


def test_embed_documents_returns_one_plain_list_per_text(
    fake_embedding_model: FakeEmbeddingModel,
) -> None:
    vectors = fake_embedding_model.embed_documents(["first text", "second text"])

    assert len(vectors) == 2
    assert all(len(vector) == FAKE_DIMENSION for vector in vectors)
    assert all(isinstance(value, float) for vector in vectors for value in vector)


def test_embed_documents_handles_empty_input(
    fake_embedding_model: FakeEmbeddingModel,
) -> None:
    assert fake_embedding_model.embed_documents([]) == []


def test_embed_query_matches_document_embedding_for_same_text(
    fake_embedding_model: FakeEmbeddingModel,
) -> None:
    query_vector = fake_embedding_model.embed_query("shared text")

    assert query_vector == fake_embedding_model.embed_documents(["shared text"])[0]
