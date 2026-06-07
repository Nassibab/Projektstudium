

async def moderate(payload: dict):

    print("Kommentar empfangen:")
    print(payload)

    return {
        "status": "ok"
    }