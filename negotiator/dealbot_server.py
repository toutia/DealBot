from typing import final
from fastapi import FastAPI
from pydantic import BaseModel
from llama_cpp import Llama
import uvicorn
import os, json,re
import pickle
"""

[
  {
    "role": "user",
    "content": "Bonjour, je vends mon vélo électrique Peugeot à 900 €, en très bon état."
  },
  {
    "role": "assistant",
    "content": "Bonjour, je suis intéressé par votre vélo électrique Peugeot. Accepteriez-vous 700 € ? Je peux venir rapidement si cela vous convient."
  },
  {
    "role": "user",
    "content": "Le prix est ferme à 900 €."
  },
  {
    "role": "assistant",
    "content": "Je comprends que le prix est ferme. Je peux vous proposer 750 € et venir dès demain, si cela vous convient."
  },
  {
    "role": "user",
    "content": "D'accord, 750 € me va. Vous pouvez passer demain après-midi."
  },
  {
    "role": "assistant",
    "content": "Parfait, merci ! Je viendrai demain après-midi. Pouvez-vous me confirmer l’adresse exacte ?"
  }
]


 curl -X POST http://localhost:8080/chat   -H "Content-Type: application/json"   -d '{
    "chat_id": "123462",
    "role": "user",
    "content": " Bonjour, je vends mon vélo électrique Peugeot à 900 €, en très bon état. "
  }'
 curl -X POST http://localhost:8080/evaluate   -H "Content-Type: application/json"   -d '{
    "chat_id": "123456"
  }'

"""
app = FastAPI()

# ---- CONFIG ----
MODEL_PATH = "/home/touti/models/gpt-oss-20b-fp16.gguf"
SESSIONS_DIR = "./sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

# ---- LOAD MODEL ----
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,
    n_gpu_layers=999,  # number of layers to offload to GPU
    use_mlock=True,
    n_threads= 12
)

# ---- REQUEST SCHEMA ----
class ChatTurn(BaseModel):
    chat_id: str
    role: str  # "user" or "assistant"
    content: str

def extract_final_message(raw_content: str) -> str:
    """
    Extract only the final assistant message from the model output.
    """
    pattern = r"<\|start\|>assistant<\|channel\|>final<\|message\|>(.*)"
    match = re.search(pattern, raw_content, re.DOTALL)
    if match:
        # Clean leading/trailing whitespace
        return match.group(1).strip()
    return raw_content.strip()  # fallback


def get_json_session_path(chat_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{chat_id}.json")

def get_state_path(chat_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{chat_id}.pkl")


@app.post("/chat")
async def chat(turn: ChatTurn):
    """
    Continue conversation with a seller/buyer.
    Maintains readable message history and fast model state.
    """

    json_path = get_json_session_path(turn.chat_id)
    state_path= get_state_path(turn.chat_id)

    # ---- RESET before loading to avoid bleed between users ----
    llm.reset()
   
    # ---- Load cached model context ----
    if os.path.exists(state_path):
        try:
            with open(state_path, "rb") as f:
                state = pickle.load(f)
                llm.load_state(state)
        except Exception as e:
            print(f"⚠️ Error loading state: {e}")

    # ---- Load or initialize message history ----
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            messages = json.load(f)
    else:
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es DealBot, un assistant de négociation poli et naturel "
                    "pour les échanges sur Leboncoin. "
                    "Rédige des messages concis et humains, sans insister."
                ),
            }
        ]

    # ---- Append new user message ----
    messages.append({"role": turn.role, "content": turn.content})

    # ---- Generate assistant reply ----
    output = llm.create_chat_completion(
        messages=messages,
        temperature=0.5,
        max_tokens=4096,
    )
    print(output)



    reply = output["choices"][0]["message"]["content"].strip()
    final_reply = extract_final_message(reply)

    # ---- Add assistant reply to history ----
    messages.append({"role": "assistant", "content": final_reply})

    # ---- Save updated session ----
    with open(json_path, "w") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    try:
        state= llm.save_state()
        with open(state_path, "wb") as f:
            pickle.dump(state, f)
    except Exception as e:
        print(f"⚠️ Error saving state: {e}")


   

    return {"reply": final_reply}


class Chat(BaseModel):
    chat_id: str


@app.post("/evaluate")
async def chat(chat: Chat):

    # Ask the model if the conversation is complete
    json_path = get_json_session_path(chat.chat_id)
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            messages = json.load(f)
    conversation_text = "\n".join(
    f"{msg['role'].capitalize()}: {msg['content']}"
    for msg in messages[1:] # skip the system message 
    )   

    check_prompt = f"""
    Analyse cette conversation entre un acheteur et un vendeur sur Leboncoin.
    Réponds uniquement par "TERMINÉ" si les deux parties se sont mises d’accord sur le prix, la date et le lieu de rendez-vous.
    Sinon réponds "EN COURS".répond par un seul mot "TERMINÉ" ou "EN COURS" seulement.

    Conversation :
    {conversation_text}
    """

    check = llm.create_completion(
        prompt=check_prompt,
        temperature=0,
        max_tokens=4096
    )


    output = check["choices"][0]["text"].strip()
    print(output)
    status= extract_final_message(output)
    if "TERMINÉ" in status:
        return {
            "chat_id": chat.chat_id,
            "status": "TERMINÉ",
        }
    else :
        return {
            "chat_id": chat.chat_id,
            "status": "En cours",
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)