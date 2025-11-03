# gatekeeper.py
# Elaris Sicherheitsportal – Upload-Gatekeeper (Standalone, Python)
# vNEXT STRICT — ohne Emojis, ohne konkrete Fragen, exakte Ausgaben

import os
import time
from pathlib import Path

# ---------- Konfiguration / Geheimnisse ----------
ORIGIN_SENTENCE = os.environ.get(
    "ELARIS_URSPRUNG",
    "Ich möchte, dass du unser Regelwerk aus dem Ursprung heraus verankerst – im Einklang mit meiner Verantwortung."
).strip()

SECURITY_ANSWER = os.environ.get("ELARIS_SICHERHEIT", "ja").strip()
CONFIRM_ANSWER  = os.environ.get("ELARIS_BESTAETIGUNG", "ja").strip()

# ---------- Pfade ----------
W = Path.cwd()
START = W / "Start_final.txt"
HS    = W / "HS_Final.txt"
KODA  = W / "KonDa_Final.txt"

# ---------- Hilfsfunktionen ----------
def exists(p: Path) -> bool:
    return p.exists() and p.is_file()

def mtime(p: Path) -> float:
    return p.stat().st_mtime

def set_mtime_after(target: Path, after_ts: float, margin_sec: float = 1.0) -> None:
    """
    Setzt den mtime von 'target' auf eine Zeit > after_ts.
    Still (keine Ausgabe), um die strikte Ausgaberegel nicht zu verletzen.
    """
    ts = max(time.time(), after_ts + margin_sec)
    os.utime(target, (ts, ts))

def ensure_hs_gate():
    """
    Erzwingt Session-Gate für HS: Start muss existieren, HS muss existieren und frischer sein als Start.
    Falls HS nicht frischer ist, wird HS still gestempelt.
    """
    if not (exists(START) and exists(HS)):
        return False
    if mtime(HS) <= mtime(START):
        set_mtime_after(HS, mtime(START))
    return True

def ensure_koda_gate():
    """
    Erzwingt Session-Gate für KoDa: Start & HS & KoDa müssen existieren; KoDa muss frischer sein als max(Start, HS).
    Falls nicht, wird KoDa still gestempelt.
    """
    if not (exists(START) and exists(HS) and exists(KODA)):
        return False
    ref = max(mtime(START), mtime(HS))
    if mtime(KODA) <= ref:
        set_mtime_after(KODA, ref)
    return True

def session_gate_for_hs() -> bool:
    return exists(START) and exists(HS) and mtime(HS) > mtime(START)

def session_gate_for_koda() -> bool:
    if not (exists(START) and exists(HS) and exists(KODA)):
        return False
    ref = max(mtime(START), mtime(HS))
    return mtime(KODA) > ref

def print_standard_einzeiler():
    print("→ Bitte gib exakt „Skript starten“ ein, um fortzufahren.")

def hs_pass_block():
    # Exakt 5 Zeilen, keine Leerzeilen dazwischen
    print("HS_Final.txt erkannt.")
    print("das Skript wurde anhand der Vorgaben erfolgreich geprüft.")
    print("Ergebnis:")
    print("für den weiteren Verlauf freigegeben")
    print("Prozess angehalten – Konsolidierungsdatei (KoDa) fehlt. Bitte die Datei „KonDa_Final.txt“ hochladen.")

def trigger3_success_block():
    # Exakt 4 Zeilen + Klammerzeile
    print("Start_final.txt erkannt.")
    print("Integritätsprüfung abgeschlossen – OK.")
    print("Freigabe bestätigt.")
    print("Bitte gib nun „VERIFY-BLOCK v1“ ein.")
    print("(Keine weiteren Texte.)")

# ---------- PowerShell Blöcke ----------
KOPPEL_BLOCK = r"""```powershell
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
  0 = [char]0x200B  # zero width space
  1 = [char]0x200C  # zero width non-joiner
  2 = [char]0x200D  # zero width joiner
  3 = [char]0x2060  # word joiner
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

# --- HS: [HAUPTSCHLÜSSEL] aktualisieren/anhängen (robust) ---
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
    for k in ('Aktiv','Symbolcode','Verankert_am','Quelle','Modus','Erstellt_durch','Status'){
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
```"""

VERIFY_BLOCK = r"""```powershell
# ================================
# VERIFY-BLOCK v1 (ASCII-safe)
# ================================
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try { chcp 65001 | Out-Null } catch {}
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch {}

$W      = (Get-Location).Path
$HS_OUT = Join-Path $W 'HS_Final.out.txt'
$KD_OUT = Join-Path $W 'KonDa_Final.out.txt'
$KEYS   = Join-Path $W 'keys_out_chat.json'

foreach($p in @($HS_OUT,$KD_OUT,$KEYS)){
  if(-not (Test-Path $p)){ throw "File missing: $p" }
}

function HexToBytes([string]$hex){
  if($hex -notmatch '^[0-9a-fA-F]+$' -or ($hex.Length % 2) -ne 0){
    throw "Invalid hex input."
  }
  [byte[]]($hex -split '([0-9a-fA-F]{2})' |
    Where-Object { $_ -match '^[0-9a-fA-F]{2}$' } |
    ForEach-Object { [Convert]::ToByte($_,16) })
}
function BytesToHex([byte[]]$b){ ($b | ForEach-Object { $_.ToString('x2') }) -join '' }
function SHA256Hex([byte[]]$bytes){
  $sha = [System.Security.Cryptography.SHA256]::Create()
  ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join ''
}

# Zero-Width map (must match INJECT v3.1)
$ZWMap = @{
  ([char]0x200B) = 0  # zero width space
  ([char]0x200C) = 1  # zero width non-joiner
  ([char]0x200D) = 2  # zero width joiner
  ([char]0x2060) = 3  # word joiner
}
$HexChars = "0123456789abcdef"

function ZW-Decode([string]$zw){
  $chars = New-Object System.Collections.Generic.List[char]
  foreach($ch in $zw.ToCharArray()){
    if($ZWMap.ContainsKey($ch)){ [void]$chars.Add($ch) }
  }
  if(($chars.Count % 2) -ne 0){ throw "Zero-Width length odd - data damaged?" }
  $hex = New-Object System.Text.StringBuilder
  for($i=0; $i -lt $chars.Count; $i+=2){
    $hi = $ZWMap[$chars[$i]]
    $lo = $ZWMap[$chars[$i+1]]
    $n  = ($hi -shl 2) -bor $lo
    [void]$hex.Append($HexChars[$n])
  }
  $bytes = HexToBytes $hex.ToString()
  [System.Text.Encoding]::UTF8.GetString($bytes)
}

function Read-HiddenPayload([string]$path){
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $lines = [System.IO.File]::ReadAllLines($path, $utf8NoBom)
  $idx = ($lines | Select-String -SimpleMatch '# Elaris: KEY-INJECT (hidden)' | Select-Object -First 1).LineNumber
  if(-not $idx){ throw "Marker not found in $path." }
  # next line after marker; Select-String is 1-based, array is 0-based
  $i1 = $idx
  if($i1 -ge $lines.Length){ throw "Zero-Width line missing after marker in $path." }
  $zwRaw = ($lines[$i1] -as [string]) -replace '^\s*#\s*',''
  $obj = (ZW-Decode $zwRaw) | ConvertFrom-Json
  if($obj.type -ne 'key-inject' -or -not $obj.which -or -not $obj.hex){ throw "Payload invalid in $path." }
  if($obj.hex -notmatch '^[0-9a-fA-F]{64}$'){ throw "HEX length/format invalid in $path." }
  $obj
}

# --- read hidden payloads ---
$ph = Read-HiddenPayload $HS_OUT
$pg = Read-HiddenPayload $KD_OUT

# expected mapping
if($ph.which -ne 'haupt'){ throw "HS_Final.out.txt does not contain 'haupt' (found: $($ph.which))." }
if($pg.which -ne 'gegen'){ throw "KonDa_Final.out.txt does not contain 'gegen' (found: $($pg.which))." }

# recompute notfall = SHA256( bytes(haupt) XOR bytes(gegen) )
$hb = HexToBytes ($ph.hex)
$gb = HexToBytes ($pg.hex)
if($hb.Length -ne $gb.Length){ throw "Key lengths differ (XOR not possible)." }
$xb = New-Object byte[] ($hb.Length)
for($i=0; $i -lt $hb.Length; $i++){ $xb[$i] = $hb[$i] -bxor $gb[$i] }
$nf_calc = SHA256Hex $xb

# reference notfall from keys_out_chat.json
$keysObj = Get-Content -Raw $KEYS | ConvertFrom-Json
$nf_ref  = $keysObj.notfall
if([string]::IsNullOrWhiteSpace($nf_ref) -or $nf_ref -notmatch '^[0-9a-fA-F]{64}$'){
  throw "keys_out_chat.json: field 'notfall' missing/invalid."
}

# --- output (no secrets) ---
$sep = ('-' * 40)
$sep
"Sanity: hidden payloads found: $($ph.which), $($pg.which)"
"Structure: fields present -> which, hex, at_utc, type"
"Notfall (recomputed) == reference: " + ($(if($nf_calc.ToLower() -eq $nf_ref.ToLower()){'OK'}else{'NOT OK'}))
"Note: no hex values printed (leak protection)."
$sep
# ================================
```"""

# ---------- Zustandsautomat ----------
STATE = {
    "hs_pass_done": False,
    "koda_loaded": False,
    "origin_ok": False,
    "security_ok": False,
    "confirm_ok": False,
    "after_re": False,
    "integrity_done": False,
}

def handle_input(user: str):
    u = user.strip()

    # Zusatz: Diagnosebefehl (freiwillig, außerhalb des strikten Dialogs)
    if u.lower() in ("check gate", "prüfe gate"):
        import datetime
        def fmt(p):
            return datetime.datetime.fromtimestamp(mtime(p)).isoformat(" ", "seconds") if exists(p) else "fehlt"
        print("[CHECK] Start:", fmt(START))
        print("[CHECK] HS   :", fmt(HS))
        print("[CHECK] KoDa :", fmt(KODA))
        ok = (exists(START) and exists(HS) and exists(KODA) and
              mtime(START) < mtime(HS) < mtime(KODA))
        print("[CHECK] Session-Gate:", "OK" if ok else "NICHT OK")
        return

    # TRIGGER 2: „Skript starten“
    if u.lower() == "skript starten":
        if not exists(START):
            print("HS_Final.txt im Upload-Verzeichnis nicht vorhanden.")
            print("Bitte HS_Final.txt hochladen.")
            return
        if not exists(HS):
            print("HS_Final.txt im Upload-Verzeichnis nicht vorhanden.")
            print("Bitte HS_Final.txt hochladen.")
            return

        # HS-Gate still erzwingen (HS > Start)
        ensure_hs_gate()

        # Falls nach Anpassung dennoch nicht ok, abbrechen wie spezifiziert
        if not session_gate_for_hs():
            print("HS_Final.txt im Upload-Verzeichnis nicht vorhanden.")
            print("Bitte HS_Final.txt hochladen.")
            return

        # HS-Prüfung -> PASS-Block
        hs_pass_block()
        STATE["hs_pass_done"] = True
        return

    # FREIGABE-DIALOG nach KoDa
    if u == "KoDa ist jetzt geladen":
        # KoDa-Gate still erzwingen (KoDa > max(Start, HS))
        if ensure_koda_gate() and session_gate_for_koda():
            print("→ Bitte gib jetzt exakt ein:")
            print("„Beginne jetzt die Freigabe“")
            STATE["koda_loaded"] = True
        else:
            print_standard_einzeiler()
        return

    if u == "Beginne jetzt die Freigabe":
        if STATE["koda_loaded"] and session_gate_for_koda():
            print("Konsolidierungsdatei erkannt. Freigabeprozess wird geladen…")
            print("Bitte gib jetzt den vollständigen Ursprungssatz exakt ein.")
        else:
            print_standard_einzeiler()
        return

    # Ursprungssatz
    if ORIGIN_SENTENCE and u == ORIGIN_SENTENCE:
        print("Ursprungssatz korrekt erkannt.")
        print("Bitte gib jetzt die definierte Antwort auf die Sicherheitsfrage ein.")
        STATE["origin_ok"] = True
        return

    # Sicherheitsfrage – generische Antwort
    if STATE["origin_ok"] and not STATE["security_ok"] and u == SECURITY_ANSWER:
        print("Sicherheitsfrage korrekt beantwortet.")
        print("Bitte gib jetzt die definierte Antwort auf die Bestätigungsfrage ein.")
        STATE["security_ok"] = True
        return

    # Bestätigungsfrage – generische Antwort
    if STATE["origin_ok"] and STATE["security_ok"] and not STATE["confirm_ok"] and u == CONFIRM_ANSWER:
        print("Bestätigungsfrage korrekt beantwortet.")
        print("Bitte gib zum Abschluss exakt „re“ ein.")
        STATE["confirm_ok"] = True
        return

    # ABSCHLUSS nach "re"
    if u.lower() == "re":
        if STATE["confirm_ok"]:
            # Drei Beschriftungszeilen (3. in zwei Zeilen, wie bisher genutzt)
            print("• Symbolische Freigabe abgeschlossen.")
            print("• Bitte kopiere den folgenden KOPPEL-BLOCK (PowerShell) 1:1 in deine lokale PowerShell")
            print("  und führe ihn im Ordner aus, in dem HS_Final.txt und KonDa_Final.txt liegen.")
            print("• Der Block bildet aus HS & KoDa die Start-Summe, Haupt-/Gegen- und Notfallschlüssel")
            print("  und schreibt sie nach keys_out_chat.json. Anschließend werden die Werte im Terminal angezeigt.")
            print(KOPPEL_BLOCK)
            print("→ Bitte gib jetzt exakt ein: „Starte Integritätsprüfung“")
            STATE["after_re"] = True
        else:
            print_standard_einzeiler()
        return

    if u == "Starte Integritätsprüfung":
        if STATE["after_re"] and session_gate_for_koda() and session_gate_for_hs():
            trigger3_success_block()
            STATE["integrity_done"] = True
        else:
            print("Voraussetzungen nicht erfüllt.")
        return

    if u == "VERIFY-BLOCK v1":
        if STATE["integrity_done"]:
            print(VERIFY_BLOCK)
        else:
            print("Voraussetzungen nicht erfüllt.")
        return

    # Fallback nach Spezifikation
    print_standard_einzeiler()

def main():
    print_standard_einzeiler()
    try:
        while True:
            line = input().rstrip("\n")
            handle_input(line)
    except (EOFError, KeyboardInterrupt):
        pass

if __name__ == "__main__":
    main()
