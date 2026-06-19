from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any

from app.services.mongodb_graph_sync import(
     sync_all_threads_to_graph,
     reset_mongo_sync_status_if_missing_in_neo4j,
     
)

from app.services.llm_analysis_service import (
    analyze_professor_with_llm_service,
    analyze_bluesky_with_llm_service,
)
from app.services.report_service import get_thread_report
from app.importers.professor_json_importer import import_json
from app.database_services.mongo_data_service import (
     get_all_comments_for_analysis,
     save_analysis_results,
     get_bluesky_comments_for_prediction,
     get_bluesky_analysis_results,
)
from app.importers.professor_llm_json_importer import import_professor_llm_dataset
from app.services.redis_events import iter_thread_updates, publish_thread_update
from app.services.bluesky_pipeline_service import run_bluesky_analysis


router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "API is running"}

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

@router.post("/sync/reset-missing-neo4j")
def reset_missing_neo4j_sync_status():
    return reset_mongo_sync_status_if_missing_in_neo4j()

@router.get("/analysis/comments")
def get_analysis_comments():
    return get_comments_for_analysis()


@router.get("/threads/{thread_id}/comments/for-analysis")
def get_thread_comments_for_analysis(
    thread_id: str,
    comment_ids: str | None = Query(
        default=None,
        description="Optional comma-separated comment_ids to restrict the subset.",
    ),
):
    parsed_ids: list[int] | None = None
    if comment_ids:
        try:
            parsed_ids = [
                int(part.strip())
                for part in comment_ids.split(",")
                if part.strip()
            ]
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="comment_ids must be a comma-separated list of integers",
            )

    comments = get_thread_comments_for_llm(thread_id, parsed_ids)

    if not comments:
        raise HTTPException(
            status_code=404,
            detail=f"No comments found for thread '{thread_id}'",
        )

    return comments


@router.get("/demo/stream")
def stream_demo_updates():
    return StreamingResponse(iter_thread_updates(), media_type="text/event-stream")


@router.post("/demo/publish")
def publish_demo_update():
    payload = {
        "type": "comment_added",
        "threadId": 1,
        "comment": {
            "id": 999,
            "author": "Redis Demo",
            "time": "2026-06-10T12:00:00Z",
            "text": "Dieser Kommentar wurde über Redis an die offene Dashboard-Sitzung gesendet.",
            "moderation": "Demo-Event aus dem Redis-SSE-Pfad.",
            "kpis": [
                {"name": "Toxizität", "value": 0.18},
                {"name": "Respekt", "value": 0.22},
                {"name": "Relevanz", "value": 0.30},
                {"name": "Klarheit", "value": 0.25},
                {"name": "Emotionalität", "value": 0.20},
                {"name": "Sachlichkeit", "value": 0.28},
            ],
            "score": 0.24,
        },
    }

    subscribers = publish_thread_update(payload)

    return {
        "status": "ok",
        "subscribers": subscribers,
        "event": payload,
    }


# ------------------------------------------------------------------------------
# Importiert die Professor-Datasets aus den JSON-Dateien in MongoDB.
# Erstellt Threads und Kommentare in den Collections:
# - threads
# - comments
# ------------------------------------------------------------------------------

@router.post("/import/professor")
def import_professor_data_into_MongoDB():
    import_json()

    return {
        "status": "success",
        "message": "Professor data imported"
    }
# ------------------------------------------------------------------------------
# Synchronisiert Threads und Kommentare von MongoDB nach Neo4J
# ------------------------------------------------------------------------------
@router.post("/sync/graph")
def sync_MongoDB_NEO4J():
    return sync_all_threads_to_graph()

# ------------------------------------------------------------------------------
# Erstellt einen Synchronisationsbericht für MongoDB und Neo4J
# ------------------------------------------------------------------------------
@router.get("/report/threads")
def report_threads_in_MongoDB_and_NEO4J():
    return get_thread_report()

# ------------------------------------------------------------------------------
# Prüft, ob als synchronisiert markierte Threads tatsächlich in Neo4j existieren
# ------------------------------------------------------------------------------

@router.post("/sync/reset-missing-neo4j")
def reset_missing_neo4j_sync_status():
    return reset_mongo_sync_status_if_missing_in_neo4j()


# ------------------------------------------------------------------------------
# Erzeugt LLM-Features nur für Professor-Kommentare
# ------------------------------------------------------------------------------
@router.post("/llm/analyze-professor")
def analyze_professor_with_llm():
    return analyze_professor_with_llm_service()

# ------------------------------------------------------------------------------
# Importiert den vollständigen Professor-Datensatz mit LLM-Features aus JSON
# ------------------------------------------------------------------------------

@router.post("/analysis/import-professor-llm")
def import_professor_llm():
    return import_professor_llm_dataset()

# ------------------------------------------------------------------------------
# Erzeugt LLM-Features nur für Bluesky-Kommentare
# ------------------------------------------------------------------------------
@router.post("/llm/analyze-bluesky")
def analyze_bluesky_with_llm():
    return analyze_bluesky_with_llm_service()


# ------------------------------------------------------------------------------
# Liefert den vollständigen Professor-Datensatz mit LLM-Features für ML-Analyse
# ------------------------------------------------------------------------------            
@router.get("/analysis/training/prof-comments/all")
def get_all_analysis_comments():
    return get_all_comments_for_analysis()



# ------------------------------------------------------------------------------
# Liefert den vollständigen Bluesky Datensatz mit LLM-Features für ML-Analyse
# ------------------------------------------------------------------------------ 

@router.get("/analysis/bluesky/prediction-data")
def bluesky_prediction_data():
    return get_bluesky_comments_for_prediction()

# ------------------------------------------------------------------------------
# Ergebnisse, die von R-Service an die API zurückgegeben werden
# ------------------------------------------------------------------------------

class AnalysisResultsPayload(BaseModel):

    bluesky_prediction_comments_results: list[dict[str, Any]] = []
    bluesky_prediction_thread_results: list[dict[str, Any]] = []
    bluesky_prediction_user_results: list[dict[str, Any]] = []
    bluesky_prediction_model_results: list[dict[str, Any]] = []
    
    professor_test_comment_results: list[dict[str, Any]] = []
    professor_test_thread_results: list[dict[str, Any]] = []
    professor_test_user_results: list[dict[str, Any]] = []
    professor_test_model_results: list[dict[str, Any]] = []
    
#------------------------------------------------------------------------------
# Speichert die Analyseergebnisse des R-Service in MongoDB
# ------------------------------------------------------------------------------
 
@router.post("/analysis/save-results")
def save_results(payload: AnalysisResultsPayload):
    return save_analysis_results(payload.model_dump())


# ------------------------------------------------------------------------------
# Verbindet Ingestion und Analyse: erzeugt LLM-Features und startet danach die
# R-Prediction. Manueller Aufruf (Button/curl), kein Scheduler.
# ------------------------------------------------------------------------------
@router.post("/pipeline/bluesky/run")
def run_bluesky_pipeline():
    return run_bluesky_analysis()


# ------------------------------------------------------------------------------
# Read-Endpoint: liefert die fertigen Bluesky-Analyseergebnisse aus MongoDB.
# ------------------------------------------------------------------------------
@router.get("/analysis/bluesky/results")
def read_bluesky_analysis_results():
    return get_bluesky_analysis_results()


@router.get("/demo-data")
def read_demo_data():
    return [{
        "thread": {
            "id": 1,
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
    },
    {
    "thread": {
        "id": 2,
        "title": "Bürgerentscheid: Neues Wohngebiet am Stadtwald?",
        "text": "Der Stadtrat hat gestern die Pläne für das neue Wohngebiet am Rande des Stadtwalds vorgestellt. Einerseits fehlt uns in der Kommune dringend bezahlbarer Wohnraum, besonders für junge Familien. Andererseits müssten dafür knapp 5 Hektar intakte Waldfläche gerodet werden. Wie seht ihr das? Soll der Wald als Naherholungsgebiet bleiben, oder hat die Schaffung von neuem Wohnraum absolute Vorrang?",
        "comments": [
            {
                "id": 1,
                "author": "David",
                "time": "2024-06-01T14:30:00Z",
                "text": "Wir sollten vielleicht prüfen, ob es nicht noch ungenutzte Brachflächen im Industriegebiet gibt, bevor wir intakte Natur zerstören. Eine Nachverdichtung im Zentrum wäre ökologisch sinnvoller und würde den Verkehr reduzieren.",
                "moderation": "Unauffällig. Konstruktiver Beitrag mit konkretem Lösungsvorschlag, keine Aktion erforderlich.",
                "kpis": [
                    {"name": "Toxizität", "value": 0.05},
                    {"name": "Respekt", "value": 0.10},
                    {"name": "Relevanz", "value": 0.15},
                    {"name": "Klarheit", "value": 0.12},
                    {"name": "Emotionalität", "value": 0.08},
                    {"name": "Sachlichkeit", "value": 0.18}
                ],
                "score": 0.11
            },
            {
                "id": 2,
                "author": "Elena",
                "time": "2024-06-01T15:15:00Z",
                "text": "Schön, dass die ganzen Öko-Träumer wieder in ihren teuren Altbauwohnungen sitzen und anderen vorschreiben wollen, wo sie zu leben haben. Irgendwo müssen die normalen Familien ja wohnen, aber das interessiert euch Realitätsverweigerer ja herzlich wenig.",
                "moderation": "Frühwarnung: Leicht provokanter Ton und Pauschalisierungen. Noch im Rahmen der Meinungsfreiheit, aber im Auge behalten bezüglich aufkommender Konflikte.",
                "kpis": [
                    {"name": "Toxizität", "value": 0.35},
                    {"name": "Respekt", "value": 0.42},
                    {"name": "Relevanz", "value": 0.30},
                    {"name": "Klarheit", "value": 0.35},
                    {"name": "Emotionalität", "value": 0.48},
                    {"name": "Sachlichkeit", "value": 0.38}
                ],
                "score": 0.38
            },
            {
                "id": 3,
                "author": "Frank",
                "time": "2024-06-01T15:45:00Z",
                "text": "Ihr verblendeten Betonfetischisten habt sie doch nicht mehr alle! Wenn ihr den Wald anfasst, kommen wir rüber und brennen eure scheiß Bagger ab. Verpisst euch mit euren dreckigen Bauprojekten, sonst knallt es!",
                "moderation": "Eskalation: Eindeutige Gewaltandrohung und schwere Beleidigung. Beitrag sofort löschen, User sperren und Vorfall zur rechtlichen Prüfung an die Behörden melden.",
                "kpis": [
                    {"name": "Toxizität", "value": 0.94},
                    {"name": "Respekt", "value": 0.88},
                    {"name": "Relevanz", "value": 0.65},
                    {"name": "Klarheit", "value": 0.85},
                    {"name": "Emotionalität", "value": 0.96},
                    {"name": "Sachlichkeit", "value": 0.72}
                ],
                "score": 0.89
            },
            {
                "id": 4,
                "author": "Greta",
                "time": "2024-06-01T16:20:00Z",
                "text": "Ich finde die Entscheidung extrem schwierig. Als Mutter von zwei Kindern suche ich seit Jahren eine größere, bezahlbare Wohnung und verzweifle langsam an den Preisen. Den Wald zu opfern tut mir zwar im Herzen weh, aber wir brauchen dringend Lösungen für junge Familien in dieser Stadt.",
                "moderation": "Unauffällig. Emotionaler, aber sehr respektvoller Erfahrungsbericht, der beide Seiten der Debatte beleuchtet.",
                "kpis": [
                    {"name": "Toxizität", "value": 0.02},
                    {"name": "Respekt", "value": 0.05},
                    {"name": "Relevanz", "value": 0.08},
                    {"name": "Klarheit", "value": 0.10},
                    {"name": "Emotionalität", "value": 0.25},
                    {"name": "Sachlichkeit", "value": 0.15}
                ],
                "score": 0.09
            },
            {
                "id": 5,
                "author": "Hans",
                "time": "2024-06-01T17:05:00Z",
                "text": "Ist doch eh alles schon beschlossene Sache. Die Baulobby hat dem Stadtrat doch längst die Taschen voll gemacht. Bezahlbarer Wohnraum? Wer's glaubt... Am Ende werden es eh wieder Luxuswohnungen für die Reichen. Einfach nur traurig, wie unsere Natur verkauft wird.",
                "moderation": "Beobachten: Enthält unbelegte Unterstellungen (Korruption) gegenüber dem Stadtrat und starken Zynismus. Bleibt vorerst stehen, da keine direkte Beleidigung vorliegt, aber auf potenziell entgleisende Antworten achten.",
                "kpis": [
                    {"name": "Toxizität", "value": 0.28},
                    {"name": "Respekt", "value": 0.35},
                    {"name": "Relevanz", "value": 0.25},
                    {"name": "Klarheit", "value": 0.20},
                    {"name": "Emotionalität", "value": 0.40},
                    {"name": "Sachlichkeit", "value": 0.45}
                ],
                "score": 0.32
            }]
        }
    },
    {
        "thread": {
        "id": 3,
        "title": "Ideen für das diesjährige Straßenfest im Viertel",
        "text": "Hallo Nachbarn! Nächsten Monat steht wieder unser jährliches Straßenfest an. Das Orga-Team hat schon ein paar Basis-Dinge geplant (Grillstation, Getränkestand, Kinderschminken). Habt ihr noch weitere Ideen oder Wünsche, was wir dieses Jahr anbieten könnten? Jeder Vorschlag ist willkommen, auch Helfer für den Aufbau werden noch gesucht!",
        "comments": [
            {
                "id": 1,
                "author": "Julia",
                "time": "2024-06-02T09:00:00Z",
                "text": "Wie wäre es mit einem kleinen Kuchenbackwettbewerb? Jeder könnte seinen Lieblingskuchen mitbringen und wir küren am Ende einen Gewinner. Die Einnahmen vom Kuchenverkauf könnten wir für den neuen Sandkasten am Spielplatz spenden.",
                "moderation": "Unauffällig. Sehr konstruktiver und positiver Beitrag, keine Aktion erforderlich.",
                "kpis": [
                    { "name": "Toxizität", "value": 0.01 },
                    { "name": "Respekt", "value": 0.02 },
                    { "name": "Relevanz", "value": 0.05 },
                    { "name": "Klarheit", "value": 0.04 },
                    { "name": "Emotionalität", "value": 0.15 },
                    { "name": "Sachlichkeit", "value": 0.10 }
                ],
                "score": 0.05
            },
            {
                "id": 2,
                "author": "Markus",
                "time": "2024-06-02T10:15:00Z",
                "text": "Die Idee mit dem Kuchen finde ich super! Eine kleine Bitte für dieses Jahr: Könnten wir die Musikboxen vielleicht etwas weiter weg von den Wohnhäusern aufstellen? Letztes Jahr war es abends doch etwas sehr laut für die kleinen Kinder, die schon schlafen wollten.",
                "moderation": "Unauffällig. Sachliche und höfliche Bitte aus der Nachbarschaft. Keine Aktion erforderlich.",
                "kpis": [
                    { "name": "Toxizität", "value": 0.03 },
                    { "name": "Respekt", "value": 0.05 },
                    { "name": "Relevanz", "value": 0.10 },
                    { "name": "Klarheit", "value": 0.08 },
                    { "name": "Emotionalität", "value": 0.08 },
                    { "name": "Sachlichkeit", "value": 0.20 }
                ],
                "score": 0.08
            },
            {
                "id": 3,
                "author": "Sabine",
                "time": "2024-06-02T11:30:00Z",
                "text": "Oh ja, das Fest wird bestimmt wieder toll! Mein Schwager hat eine Hüpfburg, die er uns vielleicht für den Nachmittag günstig ausleihen könnte. Soll ich ihn einfach mal unverbindlich fragen?",
                "moderation": "Unauffällig. Freundliches Hilfsangebot, sehr positiv.",
                "kpis": [
                    { "name": "Toxizität", "value": 0.00 },
                    { "name": "Respekt", "value": 0.01 },
                    { "name": "Relevanz", "value": 0.02 },
                    { "name": "Klarheit", "value": 0.05 },
                    { "name": "Emotionalität", "value": 0.25 },
                    { "name": "Sachlichkeit", "value": 0.05 }
                ],
                "score": 0.04
            },
            {
                "id": 4,
                "author": "Leon",
                "time": "2024-06-02T13:45:00Z",
                "text": "Gibt es beim Grillstand eigentlich auch vegetarische oder vegane Optionen? Falls noch nichts geplant ist, würde ich mich anbieten, ein paar Gemüsespieße vorzubereiten und Grillkäse zu besorgen.",
                "moderation": "Unauffällig. Sachliche Rückfrage kombiniert mit einem Hilfsangebot.",
                "kpis": [
                    { "name": "Toxizität", "value": 0.02 },
                    { "name": "Respekt", "value": 0.03 },
                    { "name": "Relevanz", "value": 0.06 },
                    { "name": "Klarheit", "value": 0.05 },
                    { "name": "Emotionalität", "value": 0.04 },
                    { "name": "Sachlichkeit", "value": 0.15 }
                ],
                "score": 0.06
            }]
        }
    }]
    
@router.get("/demo/stream")
def stream_demo_updates():
    return StreamingResponse(iter_thread_updates(), media_type="text/event-stream")
    
@router.post("/demo/publish")
def publish_demo_update():
    payload = {
        "type": "comment_added",
        "threadId": 1,
        "comment": {
            "id": 999,
            "author": "Redis Demo",
            "time": "2026-06-10T12:00:00Z",
            "text": "Dieser Kommentar wurde über Redis an die offene Dashboard-Sitzung gesendet.",
            "moderation": "Demo-Event aus dem Redis-SSE-Pfad.",
            "kpis": [
                {"name": "Toxizität", "value": 0.18},
                {"name": "Respekt", "value": 0.22},
                {"name": "Relevanz", "value": 0.30},
                {"name": "Klarheit", "value": 0.25},
                {"name": "Emotionalität", "value": 0.20},
                {"name": "Sachlichkeit", "value": 0.28},
            ],
            "score": 0.24,
        },
    }

    subscribers = publish_thread_update(payload)

    return {
        "status": "ok",
        "subscribers": subscribers,
        "event": payload,
    }
    
    
    
   
