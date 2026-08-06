import json


# Eingabedatei laden
with open("test_labeled_ranger_structure (1).json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Erste 30 Objekte auswählen
first_30 = data[:30]

# In neue Datei speichern
with open("output_30.json", "w", encoding="utf-8") as f:
    json.dump(first_30, f, ensure_ascii=False, indent=2)

print("Die ersten 30 Objekte wurden in 'output_30.json' gespeichert.")