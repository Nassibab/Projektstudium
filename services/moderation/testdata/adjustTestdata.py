import json

# JSON laden
with open("test_labeled_ranger_structure (1).json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Alle tfidf_* Felder entfernen
for item in data:
    keys_to_remove = [key for key in item if key.startswith("tfidf_")]
    for key in keys_to_remove:
        del item[key]

# Bereinigtes JSON speichern
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Alle tfidf_* Attribute wurden entfernt.")