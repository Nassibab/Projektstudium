from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class CounterSpeechGenerator:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("LLMAPI_KEY"),
            base_url="https://hub.nhr.fau.de/api/llmgw/v1",
        )

    def generate(
        self,
        comment: dict,
        model_name: str,          # Dynamisches Modell
        prompt_template: str,      # Dynamischer Prompt
        thread_context: str = ""
    ) -> str:
        
        # Hier werden Kontext und Kommentar flexibel in das jeweilige Prompt-Template eingesetzt
        prompt = prompt_template.format(
            thread_context=thread_context,
            comment_text=comment.get("text", "")
        )

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3, # Niedrige Temperatur sorgt für vergleichbarere Ergebnisse
        )

        return response.choices[0].message.content

# Benchmarking (Test-Szenarien)
if __name__ == "__main__":
    generator = CounterSpeechGenerator()

    # Testprompts (Erweiterung möglich)
    # {thread_context} und {comment_text} als Platzhalter nutzen
    PROMPTS = {
        "Prompt_1_Standard_EN": """
        You are a moderation assistant. Generate a constructive counter speech response.
        Requirements:
        - Remain polite and respectful.
        - De-escalate the discussion.
        - Maximum 3 sentences.
        Thread context: {thread_context}
        Comment: {comment_text}
        """,
        
        "Prompt_2_Fakten_DE": """
        Du bist ein sachlicher Faktenprüfer. Reagiere auf den Kommentar höflich, aber korrigiere 
        Fehlinformationen direkt und fordere den Nutzer auf, Quellen zu nennen. Maximal 2 Sätze.
        Thema: {thread_context}
        Kommentar: {comment_text}
        """,
        
        "Prompt_3_Empathisch_DE": """
        Reagiere auf den folgenden Kommentar mit maximaler Empathie. Versuche die Sorgen des Nutzers 
        aufzugreifen, ohne ihm inhaltlich zuzustimmen, und lenke das Gespräch auf eine konstruktive Ebene. Maximal 3 Sätze.
        Kontext: {thread_context}
        User-Kommentar: {comment_text}
        """
    }

    # Definition der LLMs, auf die wir Zugriff haben von der FAU --> wird noch angepasst, weil einige Modelle nicht zu unserem Anwendungsbeispiel passen oder keine Antworten geben können
    MODELS = [
        "gpt-oss-120b", 
        "RedHatAI/Mistral-Small-3.2-24B-Instruct-2506-FP8", 
        "GaleneAI/Magistral-Small-2509-FP8-Dynamic",
        "llamaindex/vdr-2b-multi-v1",
        "lightonai/LightOnOCR-2-1B",
        "google/gemma-4-E4B-it",
        "Qwen/Qwen3.6-35B-A3B-FP8",
        "intfloat/multilingual-e5-large",
        "moonshotai/Kimi-K2.6",
        "deepseek-ai/DeepSeek-V4-Flash",
        "ibm-granite/granite-4.1-3b",
        "Microsoft/Phi-4-mini-instruct",
        "mistralai/Mistral-Medium-3.5-128B",
        "RedHatAI/gemma-4-31B-it-FP8-block",
        "MiniMaxAI/MiniMax-M3-MXFP8"
    ]

    # hier sind die Testdaten für die LLMs (Input bleibt immer gleich) --> hier wäre es ja sinnvoll testdaten von uns reinzupacken oder?? also die output_30.json oder?
    test_kommentar = {"text": "Klimawandel ist doch eine Erfindung der Medien! Alles Fake!"}
    test_kontext = "Umwelt & Wissenschaft"

    print(f"Test-Kommentar: '{test_kommentar['text']}'\n")

    # Verschachtelte Schleife (jeder Prompt wird an jedes Modell geschickt)
    for prompt_name, prompt_template in PROMPTS.items():
        print(f"\n TESTE: {prompt_name}")
        print("=" * 60)
        
        for model in MODELS:
            print(f"-> Modell: [{model}] generiert Antwort...")
            
            try:
                antwort = generator.generate(
                    comment=test_kommentar,
                    model_name=model,
                    prompt_template=prompt_template,
                    thread_context=test_kontext
                )
                
                print(f"\n Antwort von {model}")
                print(antwort.strip())
                print("-" * 60)
                
            except Exception as e:
                print(f"Fehler bei Modell {model}: {e}\n")
