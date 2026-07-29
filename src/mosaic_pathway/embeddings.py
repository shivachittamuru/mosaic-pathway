"""Local sentence-transformer embeddings for Mosaic records and queries."""

from sentence_transformers import SentenceTransformer

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 32


class LocalEmbeddingModel:
    """A locally executed embedding model that returns plain Python lists."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Load the sentence-transformer on first use rather than at import time."""

        if self._model is None:
            self._model = SentenceTransformer(self.model_name)

        return self._model

    @property
    def dimension(self) -> int:
        """Return the vector size produced by this model."""

        dimension = self.model.get_embedding_dimension()

        if dimension is None:
            raise RuntimeError(
                f"Embedding model '{self.model_name}' does not report a dimension."
            )

        return int(dimension)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed many texts in batches, normalized for cosine similarity."""

        if not texts:
            return []

        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return [[float(value) for value in vector] for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query with the same normalization as documents."""

        return self.embed_documents([text])[0]
