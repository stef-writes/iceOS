from uuid import uuid4

from fastapi import FastAPI, Response

app = FastAPI(title="Stub Chat UI Service")


@app.post("/chatbots")
async def create_chatbot(payload: dict):  # noqa: WPS110 – simple stub
    """Return deterministic <script> snippet for embed testing."""
    embed_id = uuid4().hex
    snippet = f"<script src='http://testserver/embed/{embed_id}.js'></script>"
    return {"embed_script": snippet}


@app.get("/embed/{embed_id}.js")
async def serve_embed(embed_id: str):  # noqa: WPS110 – simple stub
    """Serve a trivial JS bundle so browsers don't 404 during manual tests."""
    js = "console.log('stub chatbot', '%s');" % embed_id
    return Response(js, media_type="application/javascript")
