import random
from fastapi import APIRouter

from app.services.mongodb_graph_sync import sync_all_threads_to_graph
from app.services.report_service import get_thread_report
from app.importers.professor_json_importer import import_json


router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "API is running"}


@router.get("/demo-data")
def read_demo_data():
    return {
        "thread": {
            "title": "Diskussion zum neuen Mobilitätsbericht: Autofreie Innenstädte?",
            "text": (
                "Die Stadtverwaltung hat gestern den neuen Bericht zur Verkehrsentwicklung veröffentlicht. Laut den neuesten Statistiken hat sich die Luftqualität in den Testzonen deutlich verbessert, während Teile des Einzelhandels über Umsatzrückgänge klagen. Was ist eure Meinung zu diesen Zahlen? Sollen wir den Weg der autofreien Innenstädte weitergehen oder schadet das der Wirtschaft zu sehr?"
            ),
            "comments": [
                {
                    "id": 1,
                    "author": "Anna",
                    "time": "2024-06-01T12:00:00Z",
                    "text": "Ich verstehe den Punkt, aber meiner Meinung nach sollten wir die aktuellen Statistiken aus dem Bericht von letzter Woche berücksichtigen, bevor wir voreilige Schlüsse ziehen.",
                    "moderation": "Unauffällig. Sachlicher Beitrag, keine Aktion erforderlich.",
                    "kpis": [
                    {"name": "Toxizität", "value": 0.08},
                    {"name": "Respekt", "value": 0.18},
                    {"name": "Relevanz", "value": 0.12},
                    {"name": "Klarheit", "value": 0.15},
                    {"name": "Emotionalität", "value": 0.10},
                    {"name": "Sachlichkeit", "value": 0.20}
                    ],
                    "score": 0.14
                },
                {
                    "id": 2,
                    "author": "Ben",
                    "time": "2024-06-01T12:10:00Z",
                    "text": "Das ist doch völliger Unsinn. Wer das wirklich glaubt, hat die letzten Jahre komplett geschlafen. Typisch, dass hier wieder nur einseitig argumentiert wird.",
                    "moderation": "Frühwarnung: Der Ton wird schärfer und unsachlich. Im Auge behalten, Eskalationsgefahr.",
                    "kpis": [
                    {"name": "Toxizität", "value": 0.32},
                    {"name": "Respekt", "value": 0.38},
                    {"name": "Relevanz", "value": 0.35},
                    {"name": "Klarheit", "value": 0.40},
                    {"name": "Emotionalität", "value": 0.30},
                    {"name": "Sachlichkeit", "value": 0.42}
                    ],
                    "score": 0.36
                },
                {
                    "id": 3,
                    "author": "Clara",
                    "time": "2024-06-01T12:20:00Z",
                    "text": "Ihr seid doch alle komplett gehirngewaschen und dumm! Es kotzt mich an, wie hier andauernd Lügen verbreitet werden. Haltet einfach die Klappe, wenn ihr keine Ahnung habt!",
                    "moderation": "Eskalation: Hohe Toxizität und klare Richtlinienverletzung (Beleidigung). Beitrag verbergen und User verwarnen.",
                    "kpis": [
                    {"name": "Toxizität", "value": 0.72},
                    {"name": "Respekt", "value": 0.68},
                    {"name": "Relevanz", "value": 0.75},
                    {"name": "Klarheit", "value": 0.60},
                    {"name": "Emotionalität", "value": 0.80},
                    {"name": "Sachlichkeit", "value": 0.65}
                    ],
                    "score": 0.70
                },
            ],
        },
    }


@router.post("/import/professor")
def import_professor_data_into_MongoDB():
    import_json()

    return {
        "status": "success",
        "message": "Professor data imported"
    }

@router.post("/sync/graph")
def sync_MongoDB_NEO4J():
    return sync_all_threads_to_graph()

@router.get("/report/threads")
def report_threads_in_MongoDB_and_NEO4J():
    return get_thread_report()
