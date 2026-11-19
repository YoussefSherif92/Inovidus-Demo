import json
import os
from pathlib import Path

from qdrant_client import QdrantClient, models

from rag import (
    EMBEDDING_MODEL,
    EMBEDDING_SIZE,
    create_embedding,
)


collection_name = os.environ["QDRANT_COLLECTION"]

knowledge_file = Path("/app/knowledge/damage_types.json")
references = json.loads(
    knowledge_file.read_text(encoding="utf-8")
)

client = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
    timeout=10,
)

try:
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=EMBEDDING_SIZE,
                distance=models.Distance.COSINE,
            ),
        )

    collection = client.get_collection(collection_name)
    vector_config = collection.config.params.vectors

    if (
        not isinstance(vector_config, models.VectorParams)
        or vector_config.size != EMBEDDING_SIZE
        or vector_config.distance != models.Distance.COSINE
    ):
        raise ValueError(
            "Collection configuration does not match our embeddings."
        )

    points = []

    for reference in references:
        text = reference["title"] + "\n" + reference["description"]

        vector = create_embedding(
            text,
            task_type="RETRIEVAL_DOCUMENT",
        )

        point = models.PointStruct(
            id=reference["id"],
            vector=vector,
            payload={
                "category": reference["category"],
                "title": reference["title"],
                "description": reference["description"],
                "source": "demo_reference",
                "embedding_model": EMBEDDING_MODEL,
            },
        )

        points.append(point)

    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True,
    )

    print(f"Indexed {len(points)} reference descriptions.")

    query_vector = create_embedding(
        "Unter unserer Spüle läuft Wasser aus. "
        "Der Küchenunterschrank ist bereits aufgequollen.",
        task_type="RETRIEVAL_QUERY",
    )

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=3,
        with_payload=True,
    )

    print("\nSearch results:")

    for match in results.points:
        print(
            match.payload["title"],
            round(match.score, 3),
        )

finally:
    client.close()