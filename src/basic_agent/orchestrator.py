import requests
from typing import TypedDict
from langgraph.graph import StateGraph, END

# 1. Definiamo lo stato del Grafo. 
# Questo dizionario passerà i dati da un nodo all'altro.
class AgentState(TypedDict):
    input_query: str
    system_prompt: str
    response_message: str
    reasoning: str

# 2. Definiamo la funzione del Nodo (il motore che parla con LM Studio)
def call_lm_studio_node(state: AgentState) -> AgentState:
    url = "http://localhost:1234/api/v1/chat"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "model": "google/gemma-4-12b",
        "system_prompt": state.get("system_prompt", "You are a helpful assistant."),
        "input": state.get("input_query"),
    }
    
    # Invio della richiesta
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    # Estraiamo i dati dall'output di LM Studio
    message_content = ""
    reasoning_content = ""
    
    for output in data.get("output", []):
        if output.get("type") == "message":
            message_content = output.get("content")
        elif output.get("type") == "reasoning":
            reasoning_content = output.get("content")
            
    # Aggiorniamo lo stato restituendo i nuovi valori
    return {
        **state,
        "response_message": message_content,
        "reasoning": reasoning_content
    }

# 3. Costruiamo il Grafo
workflow = StateGraph(AgentState)

# Aggiungiamo il singolo nodo al grafo
workflow.add_node("llm_call", call_lm_studio_node)

# Definiamo il punto di ingresso e le transizioni (in questo caso va subito alla fine)
workflow.set_entry_point("llm_call")
workflow.add_edge("llm_call", END)

# Compiliamo il grafo per renderlo eseguibile
orchestrator_app = workflow.compile()