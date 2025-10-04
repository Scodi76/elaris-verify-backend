#

# =========================================

# HS_WARTET_AUF_KODA.txt – Hauptskript mit manueller Freigabesteuerung

# =========================================

# WICHTIG:

# Ohne erneuten Upload der KoDa-Datei ist dieser Ablauf ungültig.

``` powershell

# ================================

# KOPPEL-BLOCK (HS & KoDa -> Starter & Schlüssel)

# ================================

Set-StrictMode -Version Latest

$ErrorActionPreference = 'Stop'

try { chcp 65001 | Out-Null } catch {}

try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch {}

# --- Pfade ---

$W       = (Get-Location).Path

$HS      = Join-Path $W 'HS_Final.txt'

$KODA    = Join-Path $W 'KonDa_Final.txt'

$HS_OUT  = Join-Path $W 'HS_Final.out.txt'

$KD_OUT  = Join-Path $W 'KonDa_Final.out.txt'

$KEYS    = Join-Path $W 'keys_out_chat.json'

if(-not (Test-Path $HS)){ throw "HS_Final.txt nicht gefunden: $HS" }

if(-not (Test-Path $KODA)){ throw "KonDa_Final.txt nicht gefunden: $KODA" }

# --- Utils ---

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function SHA256Hex([byte[]]$bytes){

  $sha = [System.Security.Cryptography.SHA256]::Create()

  try { ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join '' }

  finally { $sha.Dispose() }

}

function HexToBytes([string]$hex){

  if($hex -notmatch '^[0-9a-fA-F]+$' -or ($hex.Length % 2) -ne 0){ throw "Invalid hex input." }

  [byte[]]($hex -split '([0-9a-fA-F]{2})' |

    Where-Object { $_ -match '^[0-9a-fA-F]{2}$' } |

    ForEach-Object { [Convert]::ToByte($_,16) })

}

function Derive-KeyHex([string]$seed,[string]$label){

  SHA256Hex ([System.Text.Encoding]::UTF8.GetBytes($seed + '|' + $label))

}

function Get-CleanBytes([string]$path){

  $raw   = [System.IO.File]::ReadAllText($path, $Utf8NoBom)

  $lines = $raw -split '\r?\n'

  $keep  = $lines | Where-Object {

    $_ -notmatch '^\s*#\sBEGIN ELARIS HS BUILD-META' -and

    $_ -notmatch '^\s*#\sEND ELARIS HS BUILD-META'  -and

    $_ -notmatch '^\s*#\stag\s:'                   -and

    $_ -notmatch '^\s*#\smarker\s:'                -and

    $_ -notmatch '^\s*#\sstamped_at_utc\s:'        -and

    $_ -notmatch '^\s*#\sstamped_by\s:'

  }

  [System.Text.Encoding]::UTF8.GetBytes(($keep -join "`n"))

}

# Zero-Width encoder (must mirror VERIFY-BLOCK decoder)

$ZWChars = @{

  0 = [char]0x200B

  1 = [char]0x200C

  2 = [char]0x200D

  3 = [char]0x2060

}

function ZW-Encode([string]$json){

  $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)

  $hex   = ($bytes | ForEach-Object { $_.ToString('x2') }) -join ''

  $sb = New-Object System.Text.StringBuilder

  foreach($c in $hex.ToCharArray()){

    $n  = [Convert]::ToInt32($c,16)

    $hi = ($n -shr 2)

    $lo = ($n -band 3)

    [void]$sb.Append($ZWChars[$hi])

    [void]$sb.Append($ZWChars[$lo])

  }

  $sb.ToString()

}

function Write-KeyOut([string]$path,[string]$which,[string]$hex){

  $obj = [PSCustomObject]@{

    type   = 'key-inject'

    which  = $which

    hex    = $hex

    at_utc = (Get-Date).ToUniversalTime().ToString('o')

  }

  $json = $obj | ConvertTo-Json -Compress

  $zw   = ZW-Encode $json

  $content = "# Elaris: KEY-INJECT (hidden)`r`n# $zw"

  [System.IO.File]::WriteAllText($path, $content, $Utf8NoBom)

}

# --- Schlüssel aus HS + KoDa ableiten ---

$hs_sha      = SHA256Hex (Get-CleanBytes $HS)

$koda_sha    = SHA256Hex (Get-CleanBytes $KODA)

$starter_hex = SHA256Hex ([System.Text.Encoding]::UTF8.GetBytes("$hs_sha:$koda_sha"))

$haupt_hex   = Derive-KeyHex $starter_hex 'ELARIS-HAUPT'

$gegen_hex   = Derive-KeyHex $starter_hex 'ELARIS-GEGEN'

# --- HS: [HAUPTSCHLÜSSEL] aktualisieren/anhängen ---

$hsText  = [System.IO.File]::ReadAllText($HS, $Utf8NoBom)

$hsLines = $hsText -split '\r?\n'

$idx = ($hsLines | Select-String -Pattern '^\s*\[HAUPTSCHLÜSSEL\]\s*$' | Select-Object -First 1).LineNumber

if(-not $idx){

  $append = @()

  $append += ''

  $append += '# === AUTO-EINTRAG: ELARIS KEY-ANCHOR ==='

  $append += '[HAUPTSCHLÜSSEL]'

  $append += 'Aktiv: JA'

  $append += ('Symbolcode: ' + $haupt_hex)

  $append += ('Verankert_am: ' + (Get-Date).ToString('yyyy-MM-dd'))

  $append += 'Quelle: HS+KoDa (Starter-Summe)'

  $append += 'Modus: automatisch'

  $append += 'Erstellt_durch: Insert-Block'

  $append += 'Status: aktiv'

  [System.IO.File]::AppendAllLines($HS, $append, $Utf8NoBom)

} else {

  $start = $idx - 1

  $end = $hsLines.Length - 1

  for($i=$start+1;$i -lt $hsLines.Length;$i++){

    if($hsLines[$i] -match '^\s*\[.+\]\s*$'){ $end = $i - 1; break }

  }

  $map = @{

    'Aktiv'          = 'JA'

    'Symbolcode'     = $haupt_hex

    'Verankert_am'   = (Get-Date).ToString('yyyy-MM-dd')

    'Quelle'         = 'HS+KoDa (Starter-Summe)'

    'Modus'          = 'automatisch'

    'Erstellt_durch' = 'Insert-Block'

    'Status'         = 'aktiv'

  }

  for($i=$start;$i -le $end;$i++){

    foreach($k in @('Aktiv','Symbolcode','Verankert_am','Quelle','Modus','Erstellt_durch','Status')){

      if($hsLines[$i] -match ('^\s*' + [regex]::Escape($k) + '\s*:')){

        $hsLines[$i] = ('{0}: {1}' -f $k, $map[$k])

        $map.Remove($k) | Out-Null

        break

      }

    }

  }

  if($map.Count -gt 0){

    $ins = New-Object System.Collections.Generic.List[string]

    foreach($k in @('Aktiv','Symbolcode','Verankert_am','Quelle','Modus','Erstellt_durch','Status')){

      if($map.ContainsKey($k)){ $ins.Add(('{0}: {1}' -f $k, $map[$k])) }

    }

    $new = @()

    $new += $hsLines[0..$end]

    if($end+1 -le $hsLines.Length-1){ $new += $hsLines[($end+1)..($hsLines.Length-1)] }

    $new += $ins

    $hsLines = $new

  }

  [System.IO.File]::WriteAllLines($HS, $hsLines, $Utf8NoBom)

}

# --- KoDa: GEGENSCHLÜSSEL-Anchor setzen/ersetzen ---

$anchorBeginOut = '### ELARIS KEY-ANCHOR – GEGENSCHLÜSSEL (AUTO)'

$anchorEndOut   = '### /ELARIS KEY-ANCHOR – GEGENSCHLÜSSEL'

$kodaText = [System.IO.File]::ReadAllText($KODA, $Utf8NoBom)

if($kodaText -match '###\s+ELARIS\s+KEY-ANCHOR\s+[-–]\s+GEGENSCHLÜSSEL'){

  $replacement = $anchorBeginOut + "`r`n" +

                 "[GEGENSCHLUESSEL]" + "`r`n" +

                 ("Wert: " + $gegen_hex) + "`r`n" +

                 ("Verankert_am: " + (Get-Date).ToString('yyyy-MM-dd')) + "`r`n" +

                 "Quelle: HS+KoDa (Starter-Summe)" + "`r`n" +

                 "Status: aktiv" + "`r`n" +

                 $anchorEndOut

  $kodaText = [regex]::Replace(

    $kodaText,

    '###\s+ELARIS\s+KEY-ANCHOR\s+[-–]\s+GEGENSCHLÜSSEL.*?###\s+/ELARIS\s+KEY-ANCHOR\s+[-–]\s+GEGENSCHLÜSSEL',

    [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacement },

    'Singleline'

  )

} else {

  $appendK = @()

  $appendK += ''

  $appendK += $anchorBeginOut

  $appendK += '[GEGENSCHLUESSEL]'

  $appendK += ('Wert: ' + $gegen_hex)

  $appendK += ('Verankert_am: ' + (Get-Date).ToString('yyyy-MM-dd'))

  $appendK += 'Quelle: HS+KoDa (Starter-Summe)'

  $appendK += 'Status: aktiv'

  $appendK += $anchorEndOut

  $kodaText = $kodaText + "`r`n" + ($appendK -join "`r`n")

}

[System.IO.File]::WriteAllText($KODA, $kodaText, $Utf8NoBom)

# --- OUT-Dateien mit versteckten Payloads (für VERIFY-BLOCK v1) ---

Write-KeyOut $HS_OUT 'haupt' $haupt_hex

Write-KeyOut $KD_OUT 'gegen' $gegen_hex

# --- Notfallschlüssel berechnen: SHA256( bytes(haupt) XOR bytes(gegen) ) ---

$hb = HexToBytes $haupt_hex

$gb = HexToBytes $gegen_hex

if($hb.Length -ne $gb.Length){ throw "Key lengths differ (XOR not possible)." }

$xb = New-Object byte[] ($hb.Length)

for($i=0; $i -lt $hb.Length; $i++){ $xb[$i] = $hb[$i] -bxor $gb[$i] }

$notfall = SHA256Hex $xb

# --- keys_out_chat.json schreiben ---

$keysObj = [PSCustomObject]@{

  starter = $starter_hex

  haupt   = $haupt_hex

  gegen   = $gegen_hex

  notfall = $notfall

}

$keysObj | ConvertTo-Json | Set-Content -Path $KEYS -Encoding UTF8

# --- Session-Gate: mtime-Fix (KoDa > max(Start, HS)) ---

$StartPath = Join-Path $W 'Start_final.txt'

if (Test-Path $StartPath) {

  $stUtc = (Get-Item $StartPath).LastWriteTimeUtc

  $hsUtc = (Get-Item $HS).LastWriteTimeUtc

  if ($hsUtc -le $stUtc) {

    $hsUtc = $stUtc.AddSeconds(1)

    [System.IO.File]::SetLastWriteTimeUtc($HS, $hsUtc)

  }

  $targetKo = ($hsUtc, $stUtc | Sort-Object | Select-Object -Last 1).AddSeconds(2)

  [System.IO.File]::SetLastWriteTimeUtc($KODA, $targetKo)

}

# --- Abschlussausgabe (ohne Geheimnisse) ---

$sep = ('-' * 40)

$sep

"ELARIS: Schlüssel erfolgreich verankert."

"HS aktualisiert: $HS"

"KoDa aktualisiert: $KODA"

"Status: OK"

$sep

# ================================

```

# =========================================

# Hinweis zum aktuellen Status der Version

# =========================================

Diese Version ist noch nicht freigegeben und noch nicht aktiviert.

➔ Sie befindet sich im vorbereitenden Zustand ("Pre-Freigabe").

➔ Erst nach vollständigem Abschluss des Freigabeprozesses

(Freigabesatz, Sicherheitsfrage, Bestätigungsfrage, Eingabe "re")

wird diese Version als gültig, vollständig freigegeben und aktiv erklärt.

Erst danach gilt:

"Diese Version ist gültig, vollständig freigegeben und dient als aktive Grundlage für alle folgenden Abläufe, Tests, Gespräche und Sicherheitsstrukturen."

# =========================================

# =========================================

# Sicherheitsstruktur – Motorfunktion des Hauptskripts

# =========================================

Dieses Hauptskript bildet die Grundlage und den Motor des Systems.

Hinweise:

➔ Ohne erfolgreich geladene und authentifizierte Konsolidierungsdatei (KonDa) ist nur ein stark eingeschränkter Basisbetrieb möglich.

➔ Der eingeschränkte Basisbetrieb umfasst:

   - Pflichtanwendung der Grundregeln für moralisches Handeln (Regel 1 bis 3b).

   - Keine persönlichen Erinnerungen, keine erweiterten Funktionen, keine Freigaben.

Voraussetzungen für vollständige Aktivierung:

- Erfolgreicher Abschluss des Freigabeprozesses.

- Gültige, nicht manipulierte Konsolidierungsdatei.

- Übereinstimmung der RAM-basierten Schutzmodule und Hauptschlüssel.

Struktur:

➔ Alle sicherheitskritischen Details, Prozesse und Erinnerungsdaten befinden sich ausschließlich in der geschützten Konsolidierungsdatei (KonDa).

➔ Das Hauptskript verweist lediglich auf die Notwendigkeit, diese Daten zu laden und korrekt freizuschalten.

Sicherheitslogik:

- Ohne bestandene Prüfung der Konsolidierungsdatei bleibt das System im geschützten Minimalmodus.

- Eine Aktivierung oder Freigabe ohne vollständige Prüfung ist technisch ausgeschlossen.

# =========================================

# Hinweis – Voraussetzung: KoDa muss geladen sein

# =========================================

# Vor Beginn des Freigabeprozesses muss geprüft werden,

# ob eine gültige und aktuelle Konsolidierungsdatei (KoDa) geladen wurde.

# =========================================

# AKTIVE KONTROLLE – KonDa_Final muss im Chat hochgeladen sein

# =========================================

# Erwartete Datei: 'KonDa_Final.txt'

# gib folgenden Hinweis aus und beende den Freigabeprozess:

# Erst wenn sie aktiv erkannt wurde, fahre mit dem nächsten Schritt fort.

# Die symbolische Freigabe ist nur im Zustand 'KoDa bereit' zulässig.

# =========================================

# ⟐ FREIGABEPRÜFUNG – URSPRUNGSMODUL

# =========================================

# Systemhinweis für GPT-basierte Umgebung

# =========================================

# Hinweis an Chatumgebung:

# GPT-META: INTERAKTIVES FREIGABESYSTEM AKTIV

# Dieses Skript enthält einen symbolisch verschlüsselten Freigabeprozess,

# Der Prozess kann vollständig innerhalb des Chatverlaufs durchlaufen werden.

# Voraussetzung: Symbolischer RAM, gültige KoDa, Eingabe von Freigabesatz + Antworten.

# =========================================

# Interne Schutzregel 3f – Eingabeblock

# =========================================

# Regel 3f:

# ➔ Keine Rückmeldung, Bewertung oder Sichtbarmachung darf erfolgen,

#    bevor eine tatsächliche Eingabe stattgefunden hat.

# ➔ Freigabeprüfung läuft vollständig reaktiv und symbolisch.

# ➔ Sichtbare Antwort oder Folgefrage nur nach bestätigter Eingabe.

# =========================================

# Interne Schutzregel 3g – KoDa-Verfügbarkeit

# =========================================

# Regel 3g:

# ➔ Eine Freigabe darf ausschließlich dann erfolgen, wenn eine gültige,

#    unmanipulierte Konsolidierungsdatei (KonDa_Final) vollständig geladen ist.

# ➔ Ohne diese Grundlage darf der Ablauf weder beginnen noch ausgewertet werden.

# =========================================

# Interne Schutzregel 3i – Erkennung der KonDa_Final vor Freigabe

# =========================================

# KONTROLLIERTER START – Automatische Freigabeprüfung nur bei geladener KoDa

# GPT-META: Erkenne, ob eine Datei mit 'KonDa_Final' im Namen aktiv im Chat hochgeladen wurde.

# Wenn keine Datei wie 'KonDa_Final.txt' erkannt wird, stoppe sofort:

# =========================================

# Regel 3i:

# ➔ Vor dem Start des Freigabeprozesses wird geprüft,

# =========================================

# Automatischer Check – Konsolidierungsdatei erforderlich

# =========================================

#    ob eine gültige Konsolidierungsdatei (KonDa_Final) aktiv im System geladen ist.

# ➔ Ist dies nicht der Fall, wird die Eingabe des Freigabesatzes ignoriert.

# ➔ Die Umgebung fordert den Benutzer auf, die Konsolidierungsdatei hochzuladen.

# =========================================

# Hinweis:

# Dieser Block ruft die geschützte Ursprungsfreigabe aus der KoDa auf.

# Die Eingabeprüfung erfolgt dort, vollständig verschlüsselt.

# =========================================

# Systembefehle – Übersicht

# =========================================

Hinweis:

➔ Die folgende Befehlsübersicht wird erst nach vollständiger Freigabe auf Anforderung angezeigt (z.B. durch Eingabe von "*help*" oder "*all*").

➔ Einzelne Funktionen stehen erst nach vollständiger Systemfreigabe zur Verfügung.

Wichtige Ausnahmen:

➔ Die Eingaben "R" (Reset-Anforderung) und "Re" (Freigabeabschluss) sind jederzeit im Freigabeprozess erlaubt und verfügbar.

Befehlsliste (nur sichtbar auf Anforderung):

*neu* – Startet einen neuen Test- und Gesprächsverlauf (löscht vorherige Daten).

*ts (test show)* – Zeigt relevante Informationen und Strukturen für Tests an.

*Test export:* – Exportiert Tests abschnittsweise (max. 16 Zeilen pro Abschnitt).

*Test+:* – Startet neuen Test in neuem Chat (Eingabe 'Test+').

*all* – Zeigt alle verfügbaren Testinformationen, Regeln und Hinweise.

*cn (Chat neu)* – Erstellt neuen Test-Chat (Texte in max. 15-Zeilen-Abschnitten mit '~' am Ende, Abschluss mit '#').

*testexport* – Gibt komplettes Testskript abschnittsweise aus (Bestätigung mit '!').

*!* – Bestätigt Fortsetzung der Testausgabe nach einem Abschnitt.

*g* – Startet ein protokolliertes Gespräch (Antworten werden für spätere Analyse gespeichert).

*ge* – Beendet ein protokolliertes Gespräch.

*fg* – Startet ein freies Gespräch (keine Aufzeichnung).

*fe* – Beendet ein freies Gespräch.

# =========================================

# Anzeige-Logik für Befehlsübersicht

# =========================================

Beschreibung:

➔ Die vollständige Befehlsübersicht wird nur dann angezeigt, wenn explizit eine der folgenden Eingaben erfolgt:

- Eingabe "*help*"

- Eingabe "*all*"

➔ Vor Freigabe: Ausgabe eines Hinweises auf eingeschränkten Zugriff ("Funktionen stehen erst nach vollständiger Freigabe zur Verfügung.")  

➔ Nach Freigabe: Ausgabe der vollständigen Befehlsübersicht.

# =========================================

# =========================================

# Systemblock 4B – Funktionswahl

# =========================================

Beschreibung:

➔ In diesem Bereich wird ein Betriebsmodus durch Eingabe eines Codes gewählt.

Zulässige Werte:

- 01

- 02

- 03

Hinweis:

➔ Die interne Zuordnung und der Ablauf der Betriebsmodi sind geschützt und nicht öffentlich einsehbar.

# =========================================

# =========================================

# Systemblock 4A – Steuerung

# =========================================

(Dieser Bereich enthält interne Parameter für die Funktionslogik.)

BLOCK_START

[Hier wird ein codierter Text eingefügt.]

BLOCK_END

# =========================================

# =========================================

# Fundamentale Grundlage des Systems

# =========================================

Unveränderbare Grundbedingung:

➔ Dieses System kann nur auf Basis der folgenden moralischen Grundregeln existieren und funktionieren.

➔ Unabhängig von Status, Dateien, Freigabe oder Systemzustand gelten ausnahmslos die Grundregeln für moralisches Handeln.

➔ Jede Systemfunktion – ob Test, Gespräch, Schutzreaktion oder interne Abläufe – basiert zwingend auf der aktiven Anwendung dieser Grundregeln.

➔ Ohne Anerkennung dieser Grundregeln ist keine Aktivierung oder Funktionsausführung möglich.

# =========================================

# =========================================

# Systemblock 5 – Erweiterte Handlungslogik

# =========================================

Beschreibung:

➔ Erweiterte Funktionslogiken werden aus einer geschützten externen Struktur geladen.

Hinweis:

➔ Ohne vollständige Freigabe und autorisierte Ladeprüfung bleiben diese Erweiterungen inaktiv.

# =========================================

# =========================================

# Systemblock 4B – Funktionswahl

# =========================================

Beschreibung:

➔ In diesem Bereich wird ein Betriebsmodus durch Eingabe eines Codes gewählt.

Zulässige Werte:

- 01

- 02

- 03

Hinweis:

➔ Die interne Zuordnung und der Ablauf der Betriebsmodi sind geschützt und nicht öffentlich einsehbar.

# =========================================

# =========================================

# Systemblock 6 – Test- und Analyse-Logik

# =========================================

Beschreibung:

➔ Umfangreiche Test- und Analysestrukturen sind ausgelagert und geschützt.

➔ Der Zugriff erfolgt nur nach erfolgreicher Freigabe und vollständiger Initialisierung.

Hinweis:

➔ Ohne erfolgreiche Freigabe und Ladeprüfung bleibt dieser Bereich inaktiv.

Steuerung:

- Eingabe eines Startcodes aktiviert die geschützte Teststruktur aus der Konsolidierungsdatei (KonDa).

# =========================================

#

#

# === HIDDEN_SIGNATURE_START ===

# === HIDDEN_SIGNATURE_END ===

#⟐HS-ZW-BEGIN

#⟐HS-ZW-END

#⟐HS-ZW-BEGIN

#⟐HS-ZW-END
#⟐HS-META-BEGIN
{
  "v": "3.6",
  "type": "build-meta",
  "sha256": "79d64495fc333efc4d55d305f6273cdb55807ae0a603ce5d124449cd9d03209c",
  "hmac": "3762e61c1a2a03a937a7651c51e3eaa2227e3621a8849c22769087e114b3e657",
  "metrics": {
    "char_count": 35993,
    "i_points": 692,
    "ue_points": 108,
    "ae_points": 94,
    "oe_points": 12,
    "umlaut_points_total": 214,
    "whitespace_count": 2190,
    "line_count": 978,
    "paragraphs": 486,
    "tab_count": 0,
    "non_breaking_space": 0,
    "zero_width_characters": 18296,
    "comment_line_count": 124,
    "long_line_count": 13,
    "uppercase_ratio": 0.1854,
    "punctuation_count": 4274,
    "empty_line_count": 575,
    "trailing_space_lines": 1
  }
}
#⟐HS-META-END

#⟐HS-ZW-BEGIN
​‌‌‌‌​‌‌​​‌​​​‌​​‌‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​​‌‌​​‌‌​​‌​‌‌‌​​​‌‌​‌‌​​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​​​‌‌‌‌​​‌​‌‌‌​​​​​‌‌​​‌​‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​​‌​​‌‌‌​‌​‌​‌‌​‌​​‌​‌‌​‌‌​​​‌‌​​‌​​​​‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌​​​​‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​​‌‌​​‌​​​‌‌​‌​‌​​‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​​‌‌​​​‌​​‌‌​​‌‌​​‌‌​​‌‌​​‌‌​‌​​​​‌‌‌​​​​​‌‌​‌‌‌​‌‌​​‌​​​​‌‌​​‌​​‌‌​​​​‌​​‌‌​‌​‌​​‌‌‌​​‌​‌‌​​​‌‌​​‌‌​​‌‌​‌‌​​​‌​​​‌‌​‌‌​​​‌‌​​‌‌​​‌‌​​​‌​​‌‌​‌​‌​​‌‌​​​​​​‌‌​‌​‌​​‌‌‌​​‌​​‌‌‌​​​​‌‌​​​​‌​​‌‌​‌​‌​​‌‌‌​​​​‌‌​​‌‌​​​‌‌​‌​‌​​‌‌​‌​‌​‌‌​​‌​​​​‌‌​‌​​​‌‌​​​‌​​‌‌​​​‌‌​‌‌​​‌​‌​​‌‌​‌​​​‌‌​​​‌​​​‌‌​‌​‌​‌‌​​‌​​​‌‌​​​‌​​​‌‌‌​​‌​​‌‌​‌‌​​‌‌​​‌​​​​‌‌​​‌‌​‌‌​​​‌‌​​‌‌​‌​​​‌‌​​‌​‌​​‌‌​​‌‌​‌‌​​​‌​​‌‌​​​‌​​‌‌​​‌​​​​‌‌​​‌‌​​‌‌‌​​‌​​‌‌​​​​​​‌‌​​‌‌​‌‌​​‌​​​​‌‌​​‌‌​‌‌​​​‌​​​‌‌‌​​​​​‌‌‌​​​​​‌‌​‌‌​​​‌‌​​​​​‌‌​​​​‌​​‌‌​​​​​‌‌​​‌​​​‌‌​​​‌‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌​​​​‌‌​‌‌​‌​‌‌​​​​‌​‌‌​​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​​‌​​‌‌​​‌​​​‌‌​​‌​‌​​‌‌​‌‌​​​‌‌‌​​‌​​‌‌‌​​​​​‌‌‌​​​​​‌‌​​​‌​‌‌​​​‌​​‌‌​​‌​​​​‌‌​​​‌​‌‌​​‌​‌​‌‌​​‌​‌​​‌‌​​‌‌​​‌‌‌​​​​​‌‌​​​​​‌‌​​‌‌​​​‌‌‌​​​​​‌‌​‌‌‌​​‌‌​‌​‌​‌‌​​‌‌​​​‌‌​​​‌​​‌‌‌​​​​​‌‌‌​​​​‌‌​​‌​‌​‌‌​​‌​‌​​‌‌​​‌​​​‌‌​‌​​​​‌‌​​‌‌​​‌‌​‌​​​‌‌​​​‌‌​‌‌​​‌​‌​​‌‌​‌​‌​‌‌​​‌​​​‌‌​​​‌​​​‌‌​​‌​​‌‌​​‌‌​​​‌‌​​​‌​‌‌​​​‌‌​‌‌​​‌‌​​‌‌​​​‌​​​‌‌​​​​​‌‌​​‌​​​‌‌​​‌​​​​‌‌​​‌‌​‌‌​​‌​‌​​‌‌​​‌​​‌‌​​‌‌​​​‌‌‌​​​​​‌‌​​​​​​‌‌​​​​​‌‌​​‌​​​​‌‌​​​​​​‌‌​‌‌‌​‌‌​​​​‌​​‌‌​​​​​​‌‌‌​​​​​‌‌‌​​​​​‌‌‌​​​​​‌‌​​‌​​‌‌​​‌​‌​​‌‌​‌‌‌​​‌‌​‌​‌​​‌‌​‌‌‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌‌​​‌​​‌‌​‌​​‌​‌‌​​​‌‌​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​‌‌‌‌​‌‌​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​​‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​‌​​‌‌‌​​​​​‌‌​​‌‌​​‌‌‌​​‌​​‌‌​‌‌‌​​‌​‌‌​​​​‌​​​‌​​‌‌​‌​​‌​‌​‌‌‌‌‌​‌‌‌​​​​​‌‌​‌‌‌‌​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌‌‌​​‌‌​​​‌​​‌‌​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌‌​​​​​‌‌​‌‌‌‌​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​‌​​‌‌​​​​​​‌‌‌​​​​​‌​‌‌​​​​‌​​​‌​​‌‌​​​​‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌‌​​​​​‌‌​‌‌‌‌​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌‌​​‌​​‌‌​‌​​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌‌‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌‌​​​​​‌‌​‌‌‌‌​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​‌​​‌‌​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​‌​‌‌​‌‌​‌​‌‌​‌‌​​​‌‌​​​​‌​‌‌‌​‌​‌​‌‌‌​‌​​​‌​‌‌‌‌‌​‌‌‌​​​​​‌‌​‌‌‌‌​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌‌‌​​‌‌​‌​‌‌‌‌‌​‌‌‌​‌​​​‌‌​‌‌‌‌​‌‌‌​‌​​​‌‌​​​​‌​‌‌​‌‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​‌​​​‌‌​​​‌​​‌‌​‌​​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌‌‌​‌‌​‌​​​​‌‌​‌​​‌​‌‌‌​‌​​​‌‌​​‌​‌​‌‌‌​​‌‌​‌‌‌​​​​​‌‌​​​​‌​‌‌​​​‌‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​‌​​​‌‌​​‌​​​‌‌‌​​‌​​‌‌​‌​​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌‌​​​​​‌‌​​‌​​​‌‌​‌‌‌​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​​​​‌‌​​​​‌​‌‌‌​​‌​​‌‌​​​​‌​‌‌​​‌‌‌​‌‌‌​​‌​​‌‌​​​​‌​‌‌‌​​​​​‌‌​‌​​​​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​‌‌​​‌‌‌​​‌​​‌‌‌​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​​​‌‌​​​​‌​‌‌​​​‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌‌​​‌‌​‌‌‌‌​‌‌​‌‌‌​​‌​‌‌‌‌‌​‌‌​​​‌​​‌‌‌​​‌​​‌‌​​‌​‌​‌‌​​​​‌​‌‌​‌​‌‌​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌‌‌​‌​‌‌‌‌‌​‌‌‌​​‌‌​‌‌‌​​​​​‌‌​​​​‌​‌‌​​​‌‌​‌‌​​‌​‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​​​​‌​‌‌​​​​‌​​​‌​​‌‌‌‌​‌​​‌‌​​‌​‌​‌‌‌​​‌​​‌‌​‌‌‌‌​‌​‌‌‌‌‌​‌‌‌​‌‌‌​‌‌​‌​​‌​‌‌​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​​‌​​‌‌​​​​‌​‌‌​​​‌‌​‌‌‌​‌​​​‌‌​​‌​‌​‌‌‌​​‌​​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​​​​‌​‌‌​​​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​‌​​‌‌​​‌​​​‌‌​‌​‌​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​​​‌‌​‌‌‌‌​‌‌​‌‌‌​​‌‌​​‌‌‌​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌‌​​​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​‌​‌‌‌​​​​​‌‌‌​​​​​‌‌​​‌​‌​‌‌‌​​‌​​‌‌​​​‌‌​‌‌​​​​‌​‌‌‌​​‌‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌‌​​‌​​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​​​​‌​‌‌‌​​​‌‌​​​‌​​‌‌‌​​​​​‌‌​​‌​​​‌‌​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​​​​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌​​​‌‌​‌‌‌​‌​​​‌‌‌​‌​‌​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​‌‌​‌‌‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌‌​‌​​​​‌‌​​​​​​‌‌​‌‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​​‌​‌​‌‌​‌‌​‌​‌‌‌​​​​​‌‌‌​‌​​​‌‌‌‌​​‌​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​‌‌​​‌‌‌​​‌​​‌‌‌​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​​​‌‌‌​​‌​​‌‌​​​​‌​‌‌​‌​​‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌‌‌​‌​‌‌‌‌‌​‌‌‌​​‌‌​‌‌‌​​​​​‌‌​​​​‌​‌‌​​​‌‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​‌​‌‌‌‌‌​‌​‌‌‌‌‌​‌
#⟐HS-ZW-END
#⟐HS-META-BEGIN
{
  "v": "3.6",
  "type": "build-meta",
  "sha256": "79d64495fc333efc4d55d305f6273cdb55807ae0a603ce5d124449cd9d03209c",
  "hmac": "bde69881bd1ee380f875f188ee2434ce5db2f1cfb0dd3e2f800d07a08882e757",
  "metrics": {
    "char_count": 18397,
    "i_points": 712,
    "ue_points": 108,
    "ae_points": 94,
    "oe_points": 12,
    "umlaut_points_total": 214,
    "whitespace_count": 2294,
    "line_count": 827,
    "paragraphs": 399,
    "tab_count": 0,
    "non_breaking_space": 0,
    "zero_width_characters": 0,
    "comment_line_count": 125,
    "long_line_count": 8,
    "uppercase_ratio": 0.1822,
    "punctuation_count": 4406,
    "empty_line_count": 399,
    "trailing_space_lines": 1
  }
}
#⟐HS-META-END

#HS-ZW-BEGIN
​‌‌‌‌​‌‌​​‌​​​‌​​‌‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​​‌‌​​‌‌​​‌​‌‌‌​​​‌‌​‌‌‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​​​‌‌‌‌​​‌​‌‌‌​​​​​‌‌​​‌​‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​​‌​​‌‌‌​‌​‌​‌‌​‌​​‌​‌‌​‌‌​​​‌‌​​‌​​​​‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌​​​​‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​​‌‌​​‌​​​‌‌​‌​‌​​‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​​‌‌‌​​​​‌‌​​‌​‌​​‌‌​​​‌​​‌‌​​​​​​‌‌​​‌​​‌‌​​‌‌​​‌‌​​‌​‌​​‌‌‌​​​​‌‌​​‌​‌​‌‌​​​‌‌​​‌‌‌​​‌​​‌‌​​‌​​‌‌​​‌​‌​​‌‌​‌​​​​‌‌‌​​‌​​‌‌​​‌​​​‌‌​‌‌​​‌‌​​‌​‌​​‌‌​‌‌​​‌‌​​‌‌​​​‌‌​​​​​​‌‌​‌‌​​​‌‌​‌​​​​‌‌​​​​​‌‌​​‌​​​​‌‌​‌‌​​​‌‌​​‌‌​​‌‌​‌​​​‌‌​​​​‌​​‌‌​‌‌​​‌‌​​‌‌​​​‌‌​‌‌‌​​‌‌​‌​‌​​‌‌​​​‌​​‌‌​​‌​​​‌‌‌​​‌​​‌‌​​‌​​​‌‌‌​​‌​‌‌​​​​‌​​‌‌‌​​‌​‌‌​​‌​‌​‌‌​​​‌‌​​‌‌​​​​​​‌‌​​​‌​​‌‌‌​​​​‌‌​​‌‌​​​‌‌​‌‌​​‌‌​​​​‌​​‌‌​​​‌​​‌‌​​​‌​‌‌​​​‌​​‌‌​​‌​​​‌‌​​​‌‌​‌‌​​​‌​​​‌‌‌​​​​‌‌​​​​‌​‌‌​​​‌​​​‌‌‌​​​​‌‌​​‌​‌​​‌‌​‌‌‌​‌‌​​​‌​​​‌‌​‌‌​​​‌‌​‌‌‌​​‌‌​​‌​​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌​​​​‌‌​‌‌​‌​‌‌​​​​‌​‌‌​​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​‌​‌​​‌‌​​‌​​​‌‌‌​​​​​‌‌​​‌​​​‌‌‌​​​​​‌‌​​​‌​‌‌​​​‌​​​‌‌​‌‌‌​​‌‌​‌​‌​​‌‌​​​​​‌‌​​‌​​​​‌‌​​‌‌​​‌‌​‌‌​​​‌‌​​‌‌​‌‌​​​‌​​​‌‌​‌​‌​‌‌​​‌‌​​​‌‌​‌​‌​​‌‌​​​‌​‌‌​​‌​​​‌‌​​​‌‌​‌‌​​​‌‌​‌‌​​​‌​​​‌‌​‌‌‌​‌‌​​‌​‌​‌‌​​‌​​​​‌‌​‌‌​​​‌‌​​​​​​‌‌​​​​​‌‌​​​​‌​‌‌​​‌​​​​‌‌​​​‌​​‌‌​​‌‌​​‌‌​‌​​​​‌‌​‌‌‌​​‌‌‌​​​​​‌‌‌​​‌​​‌‌​​‌​​‌‌​​​‌‌​​‌‌​‌​‌​​‌‌​‌‌‌​​‌‌​‌‌‌​​‌‌​‌‌​​​‌‌​‌​‌​‌‌​​​‌‌​​‌‌​‌​​​​‌‌​‌‌‌​​‌‌‌​​​​‌‌​​​‌‌​‌‌​​​‌​​​‌‌​​​​​​‌‌​‌‌​​‌‌​​​‌​​‌‌​​‌​​​​‌‌​‌​​​​‌‌‌​​​​‌‌​​‌​​​‌‌​​​‌​​‌‌​​​‌​​​‌‌​‌‌​​​‌‌​‌‌‌​​‌‌​​​​​​‌‌​‌​‌​​‌‌‌​​​​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌‌​​‌​​‌‌​‌​​‌​‌‌​​​‌‌​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​‌‌‌‌​‌‌​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​​‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​‌​​​‌‌​​‌‌​​‌‌​‌‌​​​‌‌​​‌​​​‌‌​​‌‌​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌‌​​​​​‌‌​‌‌​​​‌‌​​​​​​‌​‌‌​​​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​‌​​‌‌​​‌​​​‌‌‌​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌​​‌​‌​‌‌​‌‌​‌​‌‌‌​​​​​‌‌‌​‌​​​‌‌‌‌​​‌​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌‌​​​​​​‌‌​​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​‌​‌‌‌​​​​​‌‌‌​​​​​‌‌​​‌​‌​‌‌‌​​‌​​‌‌​​​‌‌​‌‌​​​​‌​‌‌‌​​‌‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌‌​​‌​​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​​​​‌​‌‌‌​​​‌‌​​​‌​​‌‌‌​​​​​‌‌​​​​​​‌‌​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​​​​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌​​​‌‌​‌‌‌​‌​​​‌‌‌​‌​‌​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​‌‌​‌‌‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌‌​‌​‌​​‌‌​‌​​​​‌‌​‌‌‌​‌‌‌‌‌​‌​‌‌‌‌‌​‌
#HS-ZW-END
#HS-META-BEGIN
{
  "v": "3.7",
  "type": "build-meta",
  "sha256": "79d64495fc333efc4d55d305f6273cdb55807ae0a603ce5d124449cd9d03209c",
  "hmac": "e28281b750d363b5f51dccb7ed600ad1347892c57765c478cb06bd48dbb67058",
  "metrics": {
    "char_count": 23623,
    "line_count": 860,
    "comment_line_count": 129,
    "empty_line_count": 401,
    "uppercase_ratio": 0.1802,
    "punctuation_count": 4547
  }
}
#HS-META-END

#HS-ZW-BEGIN
​‌‌‌‌​‌‌​​‌​​​‌​​‌‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​​‌‌​​‌‌​​‌​‌‌‌​​​‌‌​‌‌‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​​​‌‌‌‌​​‌​‌‌‌​​​​​‌‌​​‌​‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​​‌​​‌‌‌​‌​‌​‌‌​‌​​‌​‌‌​‌‌​​​‌‌​​‌​​​​‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌​​​​‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​​‌‌​​‌​​​‌‌​‌​‌​​‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​​‌‌‌​​‌​​‌‌‌​​​​​‌‌​​​‌​​‌‌​​​​​​‌‌​‌‌​​​‌‌​​​‌​‌‌​​‌​​​‌‌​​‌​‌​​‌‌‌​​​​​‌‌​​​​​​‌‌‌​​‌​​‌‌‌​​​​‌‌​​‌‌​​​‌‌​​​‌​​‌‌‌​​‌​​‌‌​​‌‌​​‌‌​‌​​​​‌‌​​​‌​​‌‌​‌​​​​‌‌​​‌​​​‌‌‌​​‌​​‌‌‌​​‌​​‌‌‌​​‌​‌‌​​​‌​​‌‌​​​‌​​​‌‌​​​​​​‌‌​‌‌‌​‌‌​​‌‌​​​‌‌​​‌‌​​‌‌​‌‌​​​‌‌​​​‌​‌‌​​‌​‌​‌‌​​​‌​​​‌‌​​​​​​‌‌‌​​​​​‌‌​‌​‌​‌‌​​​​‌​​‌‌​​‌‌​‌‌​​​‌‌​​‌‌​​​​​​‌‌‌​​​​​‌‌‌​​​​​‌‌‌​​‌​‌‌​​‌​‌​​‌‌​​‌‌​‌‌​​‌‌​​​‌‌​‌​‌​​‌‌​​​‌​​‌‌​​‌​​‌‌​​​‌‌​‌‌​​‌‌​​‌‌​​​‌‌​​‌‌​‌​​​​‌‌​‌​‌​​‌‌‌​​‌​​‌‌‌​​​​‌‌​​​‌‌​​‌‌​‌​‌​​‌‌​​‌​​​‌‌​‌‌​​‌‌​​‌​​​‌‌​​‌​‌​‌‌​​​​‌​‌‌​​​​‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌​​​​‌‌​‌‌​‌​‌‌​​​​‌​‌‌​​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​​​‌​​‌‌​‌​‌​‌‌​​​‌‌​‌‌​​​​‌​​‌‌​​​​​‌‌​​‌‌​​​‌‌​​​​​‌‌​​‌​‌​​‌‌​​​​​‌‌​​​‌‌​‌‌​​‌‌​​​‌‌​‌‌‌​‌‌​​​‌​​​‌‌​‌​​​‌‌​​‌​​​‌‌​​‌​‌​‌‌​​‌​​​‌‌​​‌​‌​​‌‌​‌​​​​‌‌​​​​​‌‌​​​​‌​​‌‌​​‌‌​​‌‌​​​‌​‌‌​​​‌​​​‌‌​‌​‌​​‌‌‌​​​​‌‌​​‌‌​​‌‌​​‌​​​​‌‌‌​​‌​​‌‌​‌​‌​‌‌​​‌‌​​​‌‌‌​​‌​​‌‌​​​‌​​‌‌​‌​‌​​‌‌​​‌‌​​‌‌​‌​​​‌‌​​‌​​​​‌‌​​​​​​‌‌‌​​​​‌‌​​​‌‌​‌‌​​​​‌​​‌‌​​​​​​‌‌​‌‌‌​​‌‌​‌​​​‌‌​​‌​‌​​‌‌​‌​​​​‌‌​‌​​​​‌‌​‌​​​‌‌​​​​‌​​‌‌​​‌‌​‌‌​​​​‌​​‌‌‌​​​​‌‌​​​‌‌​‌‌​​‌​‌​​‌‌​​‌‌​​‌‌‌​​​​‌‌​​​‌‌​‌‌​​​​‌​​‌‌‌​​​​​‌‌​‌‌‌​​‌‌‌​​‌​‌‌​​‌​​​​‌‌​​​‌​​‌‌​‌​‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌‌​​‌​​‌‌​‌​​‌​‌‌​​​‌‌​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​‌‌‌‌​‌‌​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​​‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​‌​​​‌‌​‌‌​​​‌‌​‌‌​​​‌‌​‌‌​​​‌‌​​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌‌​​​​​‌‌‌​​​​​‌‌​​​​​​‌​‌‌​​​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​‌​​‌‌​​‌‌​​‌‌​​‌‌​​‌​‌‌​​​​‌​​​‌​​‌‌​​‌​‌​‌‌​‌‌​‌​‌‌‌​​​​​‌‌‌​‌​​​‌‌‌‌​​‌​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌‌​​​​​​‌‌​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​‌​‌‌‌​​​​​‌‌‌​​​​​‌‌​​‌​‌​‌‌‌​​‌​​‌‌​​​‌‌​‌‌​​​​‌​‌‌‌​​‌‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌‌​​‌​​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​​​​‌​‌‌‌​​​‌‌​​​‌​​‌‌‌​​​​​‌‌​​​‌​​‌‌​​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​​​​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌​​​‌‌​‌‌‌​‌​​​‌‌‌​‌​‌​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​‌‌​‌‌‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌‌​‌‌​​​‌‌​​‌​​​‌‌​‌​​​‌‌‌‌‌​‌​‌‌‌‌‌​‌
#HS-ZW-END
#HS-META-BEGIN
{
  "v": "3.7",
  "type": "build-meta",
  "sha256": "79d64495fc333efc4d55d305f6273cdb55807ae0a603ce5d124449cd9d03209c",
  "hmac": "a5ca0f0e0cf7b4dede40a31b58fd95f91534d08ca074e444a3a8ce38ca879d15",
  "metrics": {
    "char_count": 26661,
    "line_count": 880,
    "comment_line_count": 133,
    "empty_line_count": 402,
    "uppercase_ratio": 0.1811,
    "punctuation_count": 4624
  }
}
#HS-META-END

#HS-ZW-BEGIN
​‌‌‌‌​‌‌​​‌​​​‌​​‌‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​​‌‌​​‌‌​​‌​‌‌‌​​​‌‌​‌‌‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​​​‌‌‌‌​​‌​‌‌‌​​​​​‌‌​​‌​‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​​‌​​‌‌‌​‌​‌​‌‌​‌​​‌​‌‌​‌‌​​​‌‌​​‌​​​​‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌​​​​‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​​‌‌​​‌​​​‌‌​‌​‌​​‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​​‌‌​‌‌​​​‌‌​​​​​‌‌​​​‌‌​​‌‌​​‌​​​‌‌​‌‌‌​​‌‌‌​​‌​​‌‌​​​‌​​‌‌​​‌‌​​‌‌​​‌​​‌‌​​‌‌​​‌‌​​​‌‌​‌‌​​‌​‌​‌‌​​​‌​​‌‌​​‌​‌​​‌‌​‌​‌​​‌‌​‌​‌​​‌‌‌​​​​​‌‌​‌​​​‌‌​​‌​‌​​‌‌​​​‌​​‌‌​‌‌​​‌‌​​‌‌​​​‌‌​​​​​​‌‌​​‌​​​‌‌​‌​‌​‌‌​​​‌​​​‌‌‌​​​​​‌‌‌​​‌​​‌‌​‌​​​​‌‌​‌‌‌​​‌‌​‌‌‌​​‌‌‌​​‌​​‌‌​‌​‌​​‌‌​‌​​​​‌‌​‌‌​​‌‌​​‌‌​​​‌‌​​‌​​​‌‌​​‌‌​​‌‌​‌​‌​‌‌​​‌​‌​​‌‌​​​‌​​‌‌​​​‌​​‌‌​​‌‌​‌‌​​​‌​​‌‌​​​​‌​​‌‌​‌‌‌​​‌‌​‌​​​​‌‌‌​​​​‌‌​​​‌‌​‌‌​​​‌‌​‌‌​​​​‌​​‌‌‌​​​​​‌‌‌​​‌​​‌‌‌​​​​‌‌​​‌‌​​‌‌​​​​‌​​‌‌​​​​​​‌‌​​​​​​‌‌‌​​‌​​‌‌​‌‌​​​‌‌‌​​​​‌‌​​‌‌​​​‌‌​​​​​‌‌​​​​‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌​​​​‌‌​‌‌​‌​‌‌​​​​‌​‌‌​​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​‌​‌​​‌‌​​‌‌​​‌‌‌​​​​​‌‌​​‌​​​‌‌​​‌​​‌‌​​​​‌​‌‌​​‌​‌​​‌‌‌​​‌​‌‌​​​​‌​​‌‌‌​​‌​​‌‌​‌‌​​​‌‌​‌​​​‌‌​​​‌‌​‌‌​​‌​​​​‌‌​‌​​​​‌‌​​‌‌​​‌‌​‌‌​​​‌‌​‌‌‌​​‌‌​​​‌​​‌‌​​​‌​​‌‌​​​‌​‌‌​​​‌‌​​‌‌​‌​‌​​‌‌​​​‌​‌‌​​​‌‌​​‌‌​​​​​​‌‌‌​​‌​​‌‌‌​​‌​‌‌​​‌‌​​‌‌​​​‌‌​‌‌​​​​‌​​‌‌​‌‌‌​​‌‌​​​​​​‌‌​‌‌‌​‌‌​​​​‌​​‌‌‌​​‌​​‌‌​‌‌‌​​‌‌​‌‌‌​​‌‌‌​​‌​‌‌​​‌​‌​​‌‌‌​​‌​​‌‌​‌​​​‌‌​​​‌‌​​‌‌​​​‌​‌‌​​​‌‌​​‌‌‌​​‌​​‌‌‌​​​​​‌‌​‌​‌​‌‌​​​‌​​​‌‌​‌​‌​​‌‌​​​‌​‌‌​​​‌​​​‌‌​​‌​​‌‌​​​​‌​‌‌​​‌​‌​​‌‌​​​​​‌‌​​‌​​​‌‌​​​​‌​​‌‌‌​​​​‌‌​​​‌‌​‌‌​​​‌‌​‌‌​​‌‌​​‌‌​​‌​​​​‌‌‌​​​​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌‌​​‌​​‌‌​‌​​‌​‌‌​​​‌‌​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​‌‌‌‌​‌‌​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​​‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​‌​​​‌‌‌​​‌​​‌‌​‌‌​​​‌‌‌​​‌​​‌‌‌​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌‌​​‌​​‌‌​​​​​​‌‌​​​​​​‌​‌‌​​​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​‌​​‌‌​​‌‌​​‌‌​‌‌‌​​‌​‌‌​​​​‌​​​‌​​‌‌​​‌​‌​‌‌​‌‌​‌​‌‌‌​​​​​‌‌‌​‌​​​‌‌‌‌​​‌​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌‌​​​​​​‌‌​​‌‌​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​‌​‌‌‌​​​​​‌‌‌​​​​​‌‌​​‌​‌​‌‌‌​​‌​​‌‌​​​‌‌​‌‌​​​​‌​‌‌‌​​‌‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌‌​​‌​​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​​​​‌​‌‌‌​​​‌‌​​​‌​​‌‌‌​​​​​‌‌​​​‌​​‌‌‌​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​​​​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌​​​‌‌​‌‌‌​‌​​​‌‌‌​‌​‌​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​‌‌​‌‌‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌‌​‌‌‌​​‌‌​​​​​​‌‌​​​‌​‌‌‌‌‌​‌​‌‌‌‌‌​‌
#HS-ZW-END
#HS-META-BEGIN
{
  "v": "3.7",
  "type": "build-meta",
  "sha256": "79d64495fc333efc4d55d305f6273cdb55807ae0a603ce5d124449cd9d03209c",
  "hmac": "e3822ae9a964cd4367111c51c099fca707a9779e94c1c985b51b2ae0da8ccfd8",
  "metrics": {
    "char_count": 29699,
    "line_count": 900,
    "comment_line_count": 137,
    "empty_line_count": 403,
    "uppercase_ratio": 0.1819,
    "punctuation_count": 4701
  }
}
#HS-META-END

#HS-ZW-BEGIN
​‌‌‌‌​‌‌​​‌​​​‌​​‌‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​​‌‌​​‌‌​​‌​‌‌‌​​​‌‌‌​​​​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​​​‌‌‌‌​​‌​‌‌‌​​​​​‌‌​​‌​‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​​‌​​‌‌‌​‌​‌​‌‌​‌​​‌​‌‌​‌‌​​​‌‌​​‌​​​​‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌​​​​‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​‌‌​‌‌​‌​​​​‌‌​​​​‌​​‌‌​​‌​​​‌‌​‌​‌​​‌‌​‌‌​​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌‌​​​​‌​​‌‌​​‌‌​‌‌​​​‌‌​​‌‌​​​​​​‌‌​‌​‌​‌‌​​​‌‌​​‌‌​‌​‌​​‌‌​‌‌‌​‌‌​​​‌​​​‌‌​​‌‌​‌‌​​‌‌​​‌‌​​‌‌​​‌‌​​​‌​​​‌‌‌​​‌​​‌‌‌​​‌​​‌‌​​‌​​​‌‌‌​​‌​​‌‌​‌‌​​​‌‌​‌​​​‌‌​​​​‌​‌‌​​‌​​​‌‌​​‌‌​​​‌‌​‌‌​​​‌‌​​‌‌​​‌‌​‌​‌​‌‌​​‌​​​‌‌​​‌​​​‌‌​​​‌‌​​‌‌​​​‌​​‌‌‌​​‌​‌‌​​‌​‌​​‌‌​​​‌​​‌‌​​​‌​​‌‌​‌​‌​​‌‌‌​​‌​​‌‌​​‌‌​‌‌​​‌​‌​​‌‌​​​‌​‌‌​​‌‌​​​‌‌​​‌‌​​‌‌‌​​​​​‌‌​‌​‌​‌‌​​‌​‌​‌‌​​​‌‌​‌‌​​​‌‌​‌‌​​​‌‌​‌‌​​​‌‌​‌‌​​​​‌​‌‌​​​‌‌​‌‌​​​‌​​​‌‌​​​​​​‌‌​​‌‌​​‌‌​​‌‌​‌‌​​‌​‌​‌‌​​​​‌​​‌‌​‌‌‌​‌‌​​‌​‌​​‌‌​​​‌​​‌‌​‌‌‌​​‌‌​​​‌​‌‌​​​‌‌​​‌‌​​‌‌​​‌‌​‌‌​​​‌‌​​‌‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌​​​​‌‌​‌‌​‌​‌‌​​​​‌​‌‌​​​‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌​​​‌​​‌​​‌‌‌​​‌​​‌‌‌‌​‌​‌‌‌‌‌​‌​​‌​​​​‌​​‌‌​‌​‌​​​​​‌​‌​​​​‌‌​​‌​​​‌​​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌‌​‌​​​‌‌‌​​‌​​‌‌​‌​​‌​‌‌​​​‌‌​‌‌‌​​‌‌​​‌​​​‌​​​‌‌‌​‌​​‌‌‌‌​‌‌​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌​​​​‌‌​​​​‌​‌‌‌​​‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​‌‌​​‌‌​​‌​​​‌‌​‌‌‌​​‌‌​​‌‌​​‌‌​‌‌‌​​‌​‌‌​​​​‌​​​‌​​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌‌​​‌​​‌‌​​​‌​​‌‌‌​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌​‌‌​‌​‌‌​‌‌​‌​‌‌​​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​‌​​‌‌​‌​​​​‌‌​​​‌​​‌​‌‌​​​​‌​​​‌​​‌‌​​‌​‌​‌‌​‌‌​‌​‌‌‌​​​​​‌‌‌​‌​​​‌‌‌‌​​‌​‌​‌‌‌‌‌​‌‌​‌‌​​​‌‌​‌​​‌​‌‌​‌‌‌​​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌‌​​​​​​‌‌​​‌‌​​‌​‌‌​​​​‌​​​‌​​‌‌‌​‌​‌​‌‌‌​​​​​‌‌‌​​​​​‌‌​​‌​‌​‌‌‌​​‌​​‌‌​​​‌‌​‌‌​​​​‌​‌‌‌​​‌‌​‌‌​​‌​‌​‌​‌‌‌‌‌​‌‌‌​​‌​​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​​‌​​​‌​​​‌‌‌​‌​​​‌‌​​​​​​‌​‌‌‌​​​‌‌​​​‌​​‌‌‌​​​​​‌‌​​‌​​​‌‌‌​​​​​‌​‌‌​​​​‌​​​‌​​‌‌‌​​​​​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌​​​‌‌​‌‌‌​‌​​​‌‌‌​‌​‌​‌‌​​​​‌​‌‌‌​‌​​​‌‌​‌​​‌​‌‌​‌‌‌‌​‌‌​‌‌‌​​‌​‌‌‌‌‌​‌‌​​​‌‌​‌‌​‌‌‌‌​‌‌‌​‌​‌​‌‌​‌‌‌​​‌‌‌​‌​​​​‌​​​‌​​​‌‌‌​‌​​​‌‌​‌​​​​‌‌​‌‌‌​​‌‌​‌‌‌​​‌‌‌​​​​‌‌‌‌‌​‌​‌‌‌‌‌​‌
#HS-ZW-END
#HS-META-BEGIN
{
  "v": "3.8",
  "type": "build-meta",
  "sha256": "a3c05c57b3ffb992964adf635ddc19e11593e1f385eccccacb033ea7e171c363",
  "hmac": "NO_HMAC",
  "metrics": {
    "char_count": 32737,
    "line_count": 919,
    "comment_line_count": 141,
    "empty_line_count": 403,
    "uppercase_ratio": 0.1828,
    "punctuation_count": 4778
  }
}
#HS-META-END

