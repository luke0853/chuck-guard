#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chuck Guard - Anti Scam Call Agent
Läuft direkt auf Android via Termux.
Kein PC, kein Tasker, kein Abo.

Installation:
  pkg install python termux-api -y
  Termux:API App aus F-Droid installieren
  Berechtigungen: Telefon, Akku-Optimierung AUS, Bedienungshilfen AN

Start:
  python termux_guard.py
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# ─── Konfiguration ─────────────────────────────────────────────────────────

CONFIG_FILE = Path(__file__).parent / '.env'
KEY = ""
MODEL = "deepseek-chat"
URL = "https://api.deepseek.com/chat/completions"

# Config laden
if CONFIG_FILE.exists():
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                k, _, v = line.partition("=")
                k = k.strip()
                if k == "DEEPSEEK_API_KEY":
                    KEY = v.strip()
                elif k == "DEEPSEEK_MODEL":
                    MODEL = v.strip()

if not KEY or KEY.startswith("sk-xxx"):
    print()
    print("  ╔══════════════════════════════════╗")
    print("  ║   ❌  KEIN API-KEY GEFUNDEN       ║")
    print("  ╚══════════════════════════════════╝")
    print()
    print("  Erstelle .env und trage deinen DeepSeek-Key ein:")
    print("    cp .env.example .env")
    print("    nano .env")
    print("  Dann: DEEPSEEK_API_KEY=sk-dein_echter_key")
    print()
    sys.exit(1)

# ─── Termux-API prüfen ─────────────────────────────────────────────────────

def check_termux_api():
    """Prüft ob termux-telephony-device-info verfügbar ist."""
    try:
        r = subprocess.run(["termux-telephony-device-info"],
                          capture_output=True, text=True, timeout=5)
        return True
    except FileNotFoundError:
        return False

def check_accessibility():
    """Prüft ob input keyevent funktioniert (Accessibility)."""
    try:
        r = subprocess.run(["input", "keyevent", "KEYCODE_HOME"],
                          capture_output=True, timeout=3)
        return True
    except:
        return False

# ─── Termux-Funktionen ─────────────────────────────────────────────────────

def get_call_state():
    """Ermittelt Telefon-Status: idle | ringing | active"""
    try:
        info = subprocess.run(["termux-telephony-device-info"],
                             capture_output=True, text=True, timeout=5).stdout
        if "CALL_STATE_RINGING" in info:
            return "ringing"
        elif "CALL_STATE_OFFHOOK" in info:
            return "active"
    except:
        pass
    return "idle"

def get_caller():
    """Eingehende Rufnummer auslesen."""
    try:
        info = subprocess.run(["termux-telephony-device-info"],
                             capture_output=True, text=True, timeout=5).stdout
        for line in info.split("\n"):
            if "callNumber" in line or "incomingNumber" in line:
                num = line.split(":")[-1].strip().strip('", ')
                return num
    except:
        pass
    return "unbekannt"

def answer_call():
    """Anruf annehmen."""
    subprocess.run(["input", "keyevent", "KEYCODE_CALL"],
                   capture_output=True, timeout=3)

def end_call():
    """Auflegen."""
    subprocess.run(["input", "keyevent", "KEYCODE_ENDCALL"],
                   capture_output=True, timeout=3)

def speak(text):
    """Text-to-Speech."""
    try:
        subprocess.run(["termux-tts-speak", "-n", "de-DE", "--", text],
                       capture_output=True, timeout=30)
    except Exception as e:
        print(f"  ⚠️ TTS-Fehler: {e}")

def notify(title, msg):
    """Benachrichtigung."""
    try:
        subprocess.run(["termux-notification", "-t", title, "-c", msg],
                       capture_output=True, timeout=5)
    except:
        pass

# ─── DeepSeek Chat via curl ────────────────────────────────────────────────

def deepseek_chat():
    """Holt einen Satz von DeepSeek zum Verwirren des Scammers."""
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content":
                "Du bist Chuck Guard, ein Anti-Scam-Agent. "
                "Deine Aufgabe: Scammer mit sinnlosen Fragen aufhalten. "
                "Tue aelter und verwirrt. Stelle dumme Fragen. "
                "Antworte auf DEUTSCH, max 2 Saetze. "
                "Nur Text, keine Emojis, keine Formatierung."},
            {"role": "user", "content":
                "Der Scamer ruft an. Sag einen Satz der verwirrt."}
        ],
        "max_tokens": 80,
        "temperature": 0.9
    })

    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "15",
             "-H", "Authorization: Bearer " + KEY,
             "-H", "Content-Type: application/json",
             "-d", body, URL],
            capture_output=True, text=True, timeout=20
        )
        data = json.loads(r.stdout)
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠️ DeepSeek-Fehler: {e}")
        return "Hallo? Hallo? Koennen Sie mich hoeren?"

# ─── Logging ───────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

def log_call(caller, runden, log_text):
    """Speichert Anruf-Log."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = LOG_DIR / f"call_{ts}.json"
    with open(logfile, "w", encoding="utf-8") as f:
        json.dump({
            "zeit": ts,
            "anrufer": caller,
            "runden": runden,
            "log": log_text
        }, f, ensure_ascii=False, indent=2)
    return logfile

# ─── Hauptschleife ─────────────────────────────────────────────────────────

def main():
    print()
    print("  ╔══════════════════════════════════╗")
    print("  ║    🛡️  CHUCK GUARD AKTIV         ║")
    print("  ║    wartet auf Scammer...          ║")
    print("  ╚══════════════════════════════════╝")
    print()

    call_active = False
    runden = 0
    caller = "unbekannt"
    log_text = []

    while True:
        state = get_call_state()

        # ── Anruf erkannt ──────────────────────────────────────────
        if state == "ringing" and not call_active:
            caller = get_caller()
            print(f"  📞 Anruf von: {caller}")
            print(f"  ⏱  Warte 20s (4. Klingeln)...")
            notify("🛡️ Anruf erkannt", f"Von: {caller}")

            # Warten - aber nur, wenn noch klingelt
            aufgelegt = False
            for _ in range(20):
                time.sleep(1)
                if get_call_state() != "ringing":
                    aufgelegt = True
                    break

            if aufgelegt:
                print("  ❌ Scamer hat aufgelegt\n")
                continue

            # Annehmen
            print(f"  📞 4. Klingeln -> nehme an!")
            answer_call()
            call_active = True
            runden = 0
            log_text = []

            time.sleep(2)
            speak("Hallo? Guten Tag? Wer ist da?")
            print("  🤖 Chuck: Hallo? Guten Tag?")
            log_text.append("START: Hallo? Guten Tag?")

        # ── Gespräch aktiv ─────────────────────────────────────────
        if state == "active" and call_active:
            runden += 1

            # Antwort von DeepSeek holen
            antwort = deepseek_chat()
            print(f"  🤖 Chuck [{runden}]: {antwort}")
            log_text.append(f"Chuck: {antwort}")

            # Sprechen
            speak(antwort)

            # Warten auf Scamer-Antwort (max 10s)
            for _ in range(10):
                time.sleep(1)
                if get_call_state() == "idle":
                    break

        # ── Aufgelegt ──────────────────────────────────────────────
        if state == "idle" and call_active:
            print(f"\n  📵 Aufgelegt - {runden} Runden")
            logfile = log_call(caller, runden, log_text)
            print(f"  📝 Geloggt: {logfile}")
            notify("🛡️ Aufgelegt", f"{runden} Runden, {caller}")
            print()
            call_active = False
            print("  Warte auf nächsten Anruf...\n")

        time.sleep(2)

# ─── Start mit Prüfung ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("  Prüfe System...")

    # 1. Termux:API prüfen
    if not check_termux_api():
        print("  ❌ termux-telephony-device-info nicht gefunden!")
        print()
        print("  So beheben:")
        print("    1. pkg install termux-api")
        print("    2. Termux:API aus F-Droid installieren")
        print("    3. Termux neustarten")
        print("    4. Berechtigungen: Telefon ERLAUBEN")
        print()
        input("  Enter drücken zum Beenden...")
        sys.exit(1)

    print("  ✅ Termux:API gefunden")

    # 2. Accessiblity prüfen
    if not check_accessibility():
        print("  ⚠️  input keyevent nicht verfügbar!")
        print("  (Anruf autom. annehmen braucht Bedienungshilfen)")
        print()
        print("  So beheben:")
        print("    Einstellungen -> Bedienungshilfen -> Termux AN")
        print()
        input("  Enter drücken zum Fortfahren trotzdem...")

    print("  ✅ System bereit")
    print()

    try:
        main()
    except KeyboardInterrupt:
        print("\n  🛡️ Chuck Guard beendet. Tschüss Scammer!")
