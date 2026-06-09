from app.services.llm import test_llm

from app.services.aggregate import analyze_frequency

async def moderate(payload: dict):

    print("Kommentar empfangen und LLM testen:")

    #Kommentar kommt an und wird in der Frequenzanalyse analysiert
    result = analyze_frequency(payload)

    # Für einen bestimmten thread wird eine Warnung herausgegeben
    # Für die sich darin enthalten Kommentare soll Gegenrede erzeugt werden


    #llm test
    llm_answer = test_llm()

    return {
        "status": "ok",
        "received": payload,
        "llm_answer": llm_answer,
    }