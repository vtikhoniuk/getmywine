"""Embedding service for generating text embeddings."""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI API."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "BAAI/bge-m3"
        self.dimensions = 1024

    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        """
        Generate embedding for a text string.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding, or None if API unavailable
        """
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set, returning None embedding")
            return None

        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def generate_embeddings_batch(
        self, texts: list[str]
    ) -> list[Optional[list[float]]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (or None for failures)
        """
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set, returning None embeddings")
            return [None] * len(texts)

        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.embeddings.create(
                model=self.model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [None] * len(texts)
