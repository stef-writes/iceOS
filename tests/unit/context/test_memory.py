import pytest

from ice_sdk.context.memory import SQLiteVectorMemory


@pytest.mark.asyncio
async def test_similarity_search_basic():
    mem = SQLiteVectorMemory(":memory:")
    # Add corpus
    await mem.add("Hello world")
    await mem.add("Goodbye world")
    await mem.add("Hello there, friend")

    # Query should retrieve sentence containing 'Hello'
    results = await mem.retrieve("Hello", k=2)

    # Ensure we got 2 results and top one is most similar
    assert len(results) == 2
    top_text, top_score = results[0]
    assert "Hello" in top_text
    # Score should not increase as we go down the list
    if len(results) > 1:
        assert top_score >= results[1][1]
