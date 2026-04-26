#!/usr/bin/env python3
import json, time, subprocess, re, tempfile
from pathlib import Path
from datetime import datetime
KEY = ''
URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
LOG_DIR = Path.home() / 'chuck-guard' / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# ─── Config laden ──────────────────────────────────────────────────────────
cfg = Path.home() / 'chuck-guard' / '.env'
if cfg.exists():
    for line in open(cfg):
        line = line.strip()
        if line and not line.startswith('#'):
            k, _, v = line.partition('=')
            if k.strip() == 'DEEPSEEK_API_KEY': KEY = v.strip()

if not KEY or KEY.startswith('sk-xxx'):
    print('\n  KEIN KEY in .env. cp .env.example .env && nano .env\n')
    exit(1)

# ─── TTS via gTTS + mpv (KEINE Termux:API!) ────────────────────────────────
from gtts import gTTS

def speak(text):
    try:
        tts = gTTS(text=text, lang='de')
        tmp = '/data/data/com.termux/files/home/__chuck_tmp.mp3'
        tts.save(tmp)
        subprocess.run(['mpv', '--really-quiet', '--no-video', tmp], timeout=15)
    except Exception as e:
        print('  TTS fehler:', e)

# ─── Call-Status via dumpsys (KEINE Termux:API!) ───────────────────────────
def call_state():
    try:
        r = subprocess.run(['dumpsys', 'telephony.registry'],
                          capture_output=True, text=True, timeout=5).stdout
        if re.search(r'mCallState=1|CALL_STATE_RINGING', r): return 'ringing'
        if re.search(r'mCallState=2|CALL_STATE_OFFHOOK', r): return 'active'
    except: pass
    return 'idle'

def get_caller():
    try:
        r = subprocess.run(['dumpsys', 'telephony.registry'],
                          capture_output=True, text=True, timeout=5).stdout
        m = re.search(r'mCall(?:erNumber|Number|ingNumber)\"?\s*[=:]\s*\"?(\+?\d+)', r)
        return m.group(1) if m else 'unbekannt'
    except: return 'unbekannt'

# ─── DeepSeek ──────────────────────────────────────────────────────────────
def deepseek_chat():
    body = json.dumps({
        'model': MODEL,
        'messages': [
            {'role':'system','content':'Nerve Scammer. Stelle sinnlose Fragen. Tue verwirrt. Deutsch. Max 2 Saetze. Nur Text.'},
            {'role':'user','content':'Sag einen verwirrenden Satz.'}
        ],
        'max_tokens': 80, 'temperature': 0.9
    })
    try:
        r = subprocess.run(['curl','-s','--max-time','15',
            '-H','Authorization: Bearer '+KEY,
            '-H','Content-Type: application/json',
            '-d', body, URL], capture_output=True, text=True, timeout=20).stdout
        return json.loads(r)['choices'][0]['message']['content'].strip()
    except:
        return 'Hallo? Koennen Sie mich hoeren?'

# ─── Hauptschleife ─────────────────────────────────────────────────────────
print('\n  PRUEFUNG...')
r = subprocess.run(['input','keyevent','KEYCODE_HOME'], capture_output=True)
if r.returncode != 0:
    print('  input keyevent nicht verfuegbar -> Bedienungshilfen aktivieren')
    exit(1)
print('  OK - starte. Warte auf Anrufe.\n')

call_active = False
runden = 0

while True:
    state = call_state()
    
    if state == 'ringing' and not call_active:
        caller = get_caller()
        print(f'  ANRUF von {caller}')
        
        for i in range(20):
            time.sleep(1)
            if call_state() != 'ringing':
                print('  aufgelegt\n'); break
        else:
            subprocess.run(['input','keyevent','KEYCODE_CALL'])
            time.sleep(2)
            print('  angenommen. CHUCK: Hallo?')
            speak('Hallo? Guten Tag? Wer ist da?')
            call_active = True; runden = 0
    
    if state == 'active' and call_active:
        runden += 1
        antwort = deepseek_chat()
        print(f'  [{runden}] CHUCK: {antwort}')
        speak(antwort)
        
        for _ in range(10):
            time.sleep(1)
            if call_state() == 'idle': break
    
    if state == 'idle' and call_active:
        print(f'  AUFGELEGT - {runden} Runden\n')
        with open(LOG_DIR / f'call_{datetime.now():%Y%m%d_%H%M%S}.json','w') as f:
            json.dump({'runden':runden}, f)
        call_active = False; runden = 0
    
    time.sleep(2)
