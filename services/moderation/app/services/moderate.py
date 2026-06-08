from app.services.llm import test_llm

async def moderate(payload: dict):

    print("Kommentar empfangen und LLM testen:")
    
    #llm test
    llm_answer = test_llm()

    return {
        "status": "ok",
        "received": payload,
        "llm_answer": llm_answer,
    }