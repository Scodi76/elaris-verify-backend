# Elaris Verify Backend

Dieses Backend dient als kryptologische Prüfstelle und Status-Manager für die Elaris-KI.

## 🧠 Funktionen

- Prüft und speichert, ob HS_Final.txt und KoDa_Final.txt erfolgreich verifiziert wurden
- Stellt API-Endpunkte für Abfrage, Aktualisierung und Zurücksetzen des Systemstatus bereit
- Wird genutzt, um bei einem Neustart die vorherige Freigabe fortzusetzen

## 🚀 API-Endpunkte

| Methode | Pfad         | Beschreibung                         |
|----------|--------------|--------------------------------------|
| GET      | `/status`    | Liefert den aktuellen Prüfstatus     |
| POST     | `/verify`    | Aktualisiert den Status (z. B. `hs_verified: true`) |
| POST     | `/reset`     | Setzt alle Werte zurück              |

## 💡 Beispiel

```bash
curl -X POST https://<DEIN-BACKEND>.onrender.com/verify \
  -H "Content-Type: application/json" \
  -d '{"hs_verified": true, "koda_verified": true}'
