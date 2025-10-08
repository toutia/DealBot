# dealbot_server.py
from fastapi import FastAPI
from pydantic import BaseModel
from llama_cpp import Llama
import uvicorn
"""
 curl -X POST http://localhost:8080/compose -H "Content-Type: application/json" -d '{"title":"Vélo électrique","price":900,"location":"Lyon","offer":700}'

"""
app = FastAPI()

# Load local model (adjust path)
llm = Llama(
    model_path="/home/touti/models/gpt-oss-20b-fp16.gguf",
    n_ctx=4096,
    n_gpu_layers=999,  # number of layers to offload to GPU
    use_mlock=True,
    n_threads= 12
)

class NegotiationRequest(BaseModel):
    title: str
    price: float
    location: str
    offer: float

@app.post("/compose")
async def compose(req: NegotiationRequest):
    prompt = f"""
Tu es un négociateur poli et efficace pour un acheteur sur Leboncoin.
Titre de l'annonce : {req.title}
Prix demandé : {req.price} €
Localisation : {req.location}
Proposition initiale : {req.offer} €

Écris un message court (2 à 3 phrases) en français, poli et naturel, pour demander si l'objet est disponible
et proposer {req.offer} €, tout en montrant que tu es prêt à venir rapidement.
"""

    output = llm.create_completion(
        prompt=prompt,
        max_tokens=2000,     # ou 1000, voire 2000 selon ta RAM
        temperature=0.5,
        repeat_penalty=1.1,
        top_p=0.9,
        stop=["\n"]
    )

    message = output["choices"][0]["text"].strip()
    return {"message": message}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)