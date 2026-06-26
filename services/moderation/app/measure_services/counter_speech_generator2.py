import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

load_dotenv()

class CounterSpeechGenerator:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("LLMAPI_KEY"),
            base_url="https://hub.nhr.fau.de/api/llmgw/v1",
        )

    def generate(self, model_name: str, prompt_template: str, thread_context: str, diskussions_verlauf: str) -> str:
        # Wir fügen den Parent-Kontext und die 20 Kinder-Kommentare in das Template ein
        prompt = prompt_template.format(
            thread_context=thread_context, comment_text=diskussions_verlauf
        )

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7, #hier bissl rumprobieren!
        )

        return response.choices[0].message.content

if __name__ == "__main__":
    generator = CounterSpeechGenerator() # wenn nicht mehr lokal, dann wird klasse in moderation_warning_service aufgerufen --> dann das hier unnötig!

    PROMPTS = {
        "Deeskalations_Strategie": """
        *Rolle*
        Du bist ein Moderationsassistent zur Unterstützung der Erkennung und Deeskalation von Shitstorms. 
        Deine Aufgabe besteht darin, auf Grundlage eines Diskussionsverlaufs eine deeskalierende Gegenrede zu generieren.

        *Denke Schritt für Schritt nach*
        1. Analysiere die Dynamik und den Kontext um den es sich handelt
        2. erkenne die Emotionen
        3. Bewerte den Eskalationsgrad
        4. Entwerfe drei unterschiedliche deeskalierende Antwortstrategien
        5. Vergleiche die unterschiedlichen Strategien hinsichtlich Empathie, Neutralität, Sachlichkeit und Deeskalationspotenzial
        6. Leite daraus die am besten geeignetste Deeskalationsstrategie ab
        7. Generiere die finale Gegenrede

        *Anforderungen*
        - gebe NUR die finale Gegenrede aus
        - maximal 4 Sätze
        - neutral
        - sei nicht belehrend
        - keine Partei bevorzugen
        - empathisch und erklärend (situationsabhängig)
        - sachliche Diskussion fördern
        - Verwende einen natürlichen Sprachstil
        - Verzichte auf standardisierte Floskeln, Dankesformeln und generische Formulierungen
        
        CONTEXT (Ausgangskommentar des Parents):
        {thread_context}
        
        DISKUSSIONSVERLAUF (Die darauffolgenden Kinder-Kommentare):
        {comment_text}
        """,

        #bei CONTEXT wird der Root-Kommentar eingefügt, damit das Modell weiß, um was es geht
        #bei DISKUSSIONSVERLAUF werden die Replies auf den Root-Kommentar eingefügt
    }

    MODELS = [
        "gpt-oss-120b",
        "mistralai/Mistral-Medium-3.5-128B",
        "RedHatAI/Mistral-Small-3.2-24B-Instruct-2506-FP8", 
        "GaleneAI/Magistral-Small-2509-FP8-Dynamic",
        "RedHatAI/gemma-4-31B-it-FP8-block",
        "MiniMaxAI/MiniMax-M3-MXFP8", 
        "google/gemma-4-E4B-it",
        "Qwen/Qwen3.6-35B-A3B-FP8",
        "moonshotai/Kimi-K2.6",
        "deepseek-ai/DeepSeek-V4-Flash"
    ]

    # Daten werden geladen
    aktueller_ordner = Path(__file__).resolve().parent
    projekt_hauptordner = aktueller_ordner.parent.parent
    json_pfad = projekt_hauptordner / "testdata" / "synthetic_shitstorm_dataset_1.json"

    try:
        with open(json_pfad, "r", encoding="utf-8") as datei:
            datensatz = json.load(datei)
    except FileNotFoundError:
        print(f"\n FEHLER: Die Datei wurde unter '{json_pfad}' nicht gefunden!")
        exit()

    # im Hintergrund: Daten sammeln
    target_parent_id = None
    parent_text = ""
    gesammelte_kinder_texte = []
    MAX_KINDER = 20 #es werden nur 20 Kommentare reingenommen, um eine Gegenrede zu generieren

    # root-Kommentar (Parent=0) finden
    for thread in datensatz.get("threads", []):
        messages = thread.get("messages", [])
        for msg in messages:
            if msg.get("parent") == 0:
                target_parent_id = msg.get("id")
                parent_text = msg.get("text", "")
                break
        
        # die 20 "Kinder" sammeln, die zu Parent gehören --> richtige Reihenfolge sollte eigentlich schon passen
        if target_parent_id:
            for msg in messages:
                if msg.get("parent") == target_parent_id:
                    text = msg.get("text", "").strip()
                    if text:
                        gesammelte_kinder_texte.append(f"- {text}")
                    if len(gesammelte_kinder_texte) >= MAX_KINDER:
                        break
            break

    if not target_parent_id:
        #print(" FEHLER: Kein gültiger Parent-Kommentar gefunden.")
        exit()

    #die 20 Kommentare werden zu einem Textblock zusammenfügen --> ist das so richtig?
    verlaufs_text = "\n".join(gesammelte_kinder_texte)

    print()

    # output-Schleife
    # 1. nimm den Prompt
    # 2. schicke an jedes modell den root-Kommentar und die 20 dazugehörigen "Kinder"
    # 3. warten bis LLM antwortet und gebe Gegenree in Terminal aus
    # 4. falls modell nicht funktioniert, wird fehler geschmissen
    for prompt_name, prompt_template in PROMPTS.items():
        
        for model in MODELS:
            try:
                # Das Modell bekommt den root-Kommentar und 20 dazugehörige auf einmal geliefert (id von root ist parent von dazugehörigen)
                antwort = generator.generate(
                    model_name=model,
                    prompt_template=prompt_template,
                    thread_context=parent_text,
                    diskussions_verlauf=verlaufs_text
                )

                # Modell und finale Gegenrede werden ausgegeben
                print(f" Modell: {model}")
                print(antwort.strip())
                print()

            except Exception as e:
                print(f" Modell: {model} -> FEHLER: {e}\n")




