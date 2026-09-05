import http.server
import socketserver
import json
import os
import sys
import threading
import time
import urllib.request
import socketio
from pywebpush import webpush, WebPushException

PORT = int(os.environ.get("PORT", 8080))
SUBSCRIPTIONS_FILE = "subscriptions.json"
VAPID_FILE = "vapid_keys.json"
CACHE_FILE = "leagues_cache.json"

# Load VAPID keys
if not os.path.exists(VAPID_FILE):
    print("HATA: vapid_keys.json bulunamadı!")
    sys.exit(1)

with open(VAPID_FILE, "r") as f:
    vapid_keys = json.load(f)

# Load team names mapping from cache
match_names_map = {}
def load_match_names():
    global match_names_map
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            count = 0
            for lid, ldata in d.items():
                if isinstance(ldata, dict):
                    for w in ldata.get("weeks", []):
                        for m in w.get("matches", []):
                            mid = str(m.get("id", ""))
                            h = m.get("home_team", {}).get("name", "")
                            a = m.get("away_team", {}).get("name", "")
                            if mid and h and a:
                                match_names_map[mid] = (h, a)
                                count += 1
            print(f"✓ {count} maçın takım isimleri önbellekten yüklendi.")
        except Exception as e:
            print("Önbellek okuma hatası:", e)

load_match_names()

# Load subscriptions
def load_subscriptions():
    if os.path.exists(SUBSCRIPTIONS_FILE):
        try:
            with open(SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_subscriptions(subs):
    with open(SUBSCRIPTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(subs, f, indent=2, ensure_ascii=False)

def send_push_to_sub(sub, payload):
    try:
        webpush(
            subscription_info=sub,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=vapid_keys["private_key"],
            vapid_claims={"sub": "mailto:admin@iddaatakip.local"}
        )
        print(f"  ✓ Bildirim iletildi: {sub.get('endpoint', '')[:45]}...")
        return True
    except WebPushException as ex:
        status = getattr(ex.response, "status_code", None) if ex.response else None
        print(f"  ✗ Push Hatası ({status}): {ex}")
        if status in (404, 410):
            return "expired"
        return False
    except Exception as e:
        print(f"  ✗ Beklenmeyen hata: {e}")
        return False

# Send push ONLY to subscribers who favorited this match
def send_push_for_match(mid, payload):
    subs = load_subscriptions()
    if not subs:
        return 0

    s_mid = str(mid)
    # Target only subscribers who favorited this match
    target_subs = [s for s in subs if s_mid in [str(f) for f in s.get("favorites", [])]]
    if not target_subs:
        return 0

    print(f"[FAVORİ PUSH] Maç {s_mid} için {len(target_subs)} aboneye bildirim: {payload.get('title')} - {payload.get('body')}")
    expired_endpoints = set()
    sent_count = 0

    for sub in target_subs:
        res = send_push_to_sub(sub, payload)
        if res is True:
            sent_count += 1
        elif res == "expired":
            expired_endpoints.add(sub.get("endpoint"))

    if expired_endpoints:
        active_subs = [s for s in subs if s.get("endpoint") not in expired_endpoints]
        save_subscriptions(active_subs)

    return sent_count

# Send push to ALL subscribers (Test button / system)
def send_push_to_all(payload):
    subs = load_subscriptions()
    if not subs:
        print("[PUSH] Kayıtlı abone yok.")
        return 0

    print(f"[PUSH TÜMÜ] {len(subs)} aboneye test bildirimi: {payload.get('title')}")
    expired_endpoints = set()
    sent_count = 0

    for sub in subs:
        res = send_push_to_sub(sub, payload)
        if res is True:
            sent_count += 1
        elif res == "expired":
            expired_endpoints.add(sub.get("endpoint"))

    if expired_endpoints:
        active_subs = [s for s in subs if s.get("endpoint") not in expired_endpoints]
        save_subscriptions(active_subs)

    return sent_count

# Match state tracking
live_matches_state = {}

def process_match_update(update):
    if not update or not isinstance(update, dict):
        return

    mid = str(update.get("id") or update.get("match_id") or update.get("uuid") or "")
    if not mid:
        return

    cached_names = match_names_map.get(mid, ("Ev Sahibi", "Deplasman"))
    m = live_matches_state.setdefault(mid, {
        "home_team": update.get("home_team_name") or cached_names[0],
        "away_team": update.get("away_team_name") or cached_names[1],
        "home_score": None,
        "away_score": None,
        "ht_home": None,
        "ht_away": None,
        "status": "",
        "period": "",
        "minute": "",
        "rc_home": 0,
        "rc_away": 0,
        "notified_ht": False,
        "notified_ft": False
    })

    # Update names if found in cache and currently default
    if m["home_team"] == "Ev Sahibi" and cached_names[0] != "Ev Sahibi":
        m["home_team"] = cached_names[0]
        m["away_team"] = cached_names[1]

    if "home_team_name" in update and update["home_team_name"]:
        m["home_team"] = update["home_team_name"]
    if "away_team_name" in update and update["away_team_name"]:
        m["away_team"] = update["away_team_name"]
    if "minute" in update and update["minute"] is not None:
        m["minute"] = str(update["minute"])

    # 1. GOL KONTROLÜ
    new_home = update.get("fts_A")
    new_away = update.get("fts_B")

    goal_scored = False
    if new_home is not None:
        try:
            new_h = int(new_home)
            if m["home_score"] is not None and new_h > m["home_score"]:
                goal_scored = True
            m["home_score"] = new_h
        except ValueError:
            pass

    if new_away is not None:
        try:
            new_a = int(new_away)
            if m["away_score"] is not None and new_a > m["away_score"]:
                goal_scored = True
            m["away_score"] = new_a
        except ValueError:
            pass

    if goal_scored:
        min_str = f"{m['minute']}'" if m["minute"] else "Canlı"
        title = f"⚽ GOL! ({min_str})"
        body = f"{m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}"
        print(f"[GOL] {title} {body}")
        send_push_for_match(mid, {
            "title": title,
            "body": body,
            "icon": "icons/icon-192.png",
            "tag": f"goal-{mid}-{m['home_score']}-{m['away_score']}"
        })

    # 2. İLK YARI BİTTİ KONTROLÜ
    new_status = str(update.get("status") or "").strip()
    new_period = str(update.get("period") or "").strip()

    if update.get("hts_A") is not None:
        m["ht_home"] = update["hts_A"]
    if update.get("hts_B") is not None:
        m["ht_away"] = update["hts_B"]

    is_ht = new_period in ("Half Time", "Devre Arası", "HT") or new_status in ("Half Time", "Devre Arası", "HT")
    if is_ht and not m["notified_ht"]:
        m["notified_ht"] = True
        ht_h = m["ht_home"] if m["ht_home"] is not None else (m["home_score"] if m["home_score"] is not None else 0)
        ht_a = m["ht_away"] if m["ht_away"] is not None else (m["away_score"] if m["away_score"] is not None else 0)
        title = f"⏸️ İLK YARI BİTTİ (İY {ht_h}-{ht_a})"
        body = f"{m['home_team']} vs {m['away_team']}"
        print(f"[İY BİTTİ] {title} {body}")
        send_push_for_match(mid, {
            "title": title,
            "body": body,
            "icon": "icons/icon-192.png",
            "tag": f"ht-{mid}"
        })

    # 3. MAÇ BİTTİ KONTROLÜ
    is_ft = new_status.lower() in ("played", "ms", "ft", "finished", "bitti") or new_period.lower() in ("played", "ms", "ft", "finished")
    if is_ft and not m["notified_ft"]:
        m["notified_ft"] = True
        h = m["home_score"] if m["home_score"] is not None else 0
        a = m["away_score"] if m["away_score"] is not None else 0
        title = f"🏁 MAÇ BİTTİ (MS {h}-{a})"
        body = f"{m['home_team']} vs {m['away_team']}"
        print(f"[MAÇ BİTTİ] {title} {body}")
        send_push_for_match(mid, {
            "title": title,
            "body": body,
            "icon": "icons/icon-192.png",
            "tag": f"ft-{mid}"
        })

    # 4. KIRMIZI KART KONTROLÜ
    for kA in ("rc_A", "red_cards_A", "rcA", "redCardsA"):
        if kA in update and update[kA] is not None:
            try:
                new_rc_h = int(update[kA])
                if new_rc_h > m["rc_home"]:
                    m["rc_home"] = new_rc_h
                    min_str = f"{m['minute']}'" if m["minute"] else "Canlı"
                    title = f"🟥 KIRMIZI KART! ({min_str})"
                    body = f"{m['home_team']} kırmızı kart gördü! ({m['home_team']} {m.get('home_score',0)} - {m.get('away_score',0)} {m['away_team']})"
                    print(f"[KART] {title} {body}")
                    send_push_for_match(mid, {
                        "title": title,
                        "body": body,
                        "icon": "icons/icon-192.png",
                        "tag": f"rc-{mid}-{time.time()}"
                    })
            except ValueError:
                pass

    for kB in ("rc_B", "red_cards_B", "rcB", "redCardsB"):
        if kB in update and update[kB] is not None:
            try:
                new_rc_a = int(update[kB])
                if new_rc_a > m["rc_away"]:
                    m["rc_away"] = new_rc_a
                    min_str = f"{m['minute']}'" if m["minute"] else "Canlı"
                    title = f"🟥 KIRMIZI KART! ({min_str})"
                    body = f"{m['away_team']} kırmızı kart gördü! ({m['home_team']} {m.get('home_score',0)} - {m.get('away_score',0)} {m['away_team']})"
                    print(f"[KART] {title} {body}")
                    send_push_for_match(mid, {
                        "title": title,
                        "body": body,
                        "icon": "icons/icon-192.png",
                        "tag": f"rc-{mid}-{time.time()}"
                    })
            except ValueError:
                pass

# Live WebSocket Listener
def start_socket_listener():
    sio = socketio.Client(reconnection=True, reconnection_delay=2, reconnection_delay_max=10)

    @sio.on("connect")
    def on_connect():
        print("✓ Sahadan Canlı Socket Yayınına Bağlandı!")
        sio.emit("join-room", "soccer")

    @sio.on("disconnect")
    def on_disconnect():
        print("⚠ Socket bağlantısı koptu, yeniden bağlanılıyor...")

    @sio.on("matches")
    def on_matches(data):
        if not data:
            return
        content = data.get("content") if isinstance(data, dict) and "content" in data else data
        items = content if isinstance(content, list) else [content]
        for item in items:
            process_match_update(item)

    while True:
        try:
            sio.connect("https://socket.mackolikfeeds.com/mksh", socketio_path="/socket.io", transports=["websocket"], wait_timeout=10)
            sio.wait()
        except Exception as e:
            time.sleep(5)

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/vapid-key":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"public_key": vapid_keys["public_key"]}).encode("utf-8"))
            return

        if self.path == "/api/subscriptions":
            subs = load_subscriptions()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"count": len(subs)}).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/subscribe":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                sub_data = json.loads(body)
                subs = load_subscriptions()
                endpoint = sub_data.get("endpoint")
                
                # Check if endpoint already exists
                existing = next((s for s in subs if s.get("endpoint") == endpoint), None)
                if existing:
                    if "keys" in sub_data:
                        existing["keys"] = sub_data["keys"]
                    if "favorites" in sub_data:
                        existing["favorites"] = [str(f) for f in sub_data["favorites"]]
                else:
                    subs.append({
                        "endpoint": endpoint,
                        "keys": sub_data.get("keys", {}),
                        "favorites": [str(f) for f in sub_data.get("favorites", [])]
                    })
                save_subscriptions(subs)

                # Send welcome push only on initial subscription
                if not existing:
                    send_push_to_sub(sub_data, {
                        "title": "⭐ İddaa Takip",
                        "body": "✅ Bildirimler aktif! Sadece yıldızladığınız (★) maçların gol, devre, maç sonu ve kırmızı kart bildirimleri gelecek.",
                        "icon": "icons/icon-192.png",
                        "tag": "welcome"
                    })

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "subscribers": len(subs)}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/test-push":
            content_length = int(self.headers.get("Content-Length", 0))
            custom_payload = None
            if content_length > 0:
                try:
                    custom_payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                except Exception:
                    pass

            payload = custom_payload or {
                "title": "⭐ Test Bildirimi",
                "body": "İddaa Takip favori bildirim sistemi kusursuz çalışıyor! 🚀",
                "icon": "icons/icon-192.png",
                "tag": "test-push"
            }
            sent = send_push_to_all(payload)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "sent": sent}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def keep_alive_ping():
    time.sleep(60)
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL", "https://iddaatakip.onrender.com")
            ping_url = f"{url.rstrip('/')}/api/subscriptions"
            req = urllib.request.Request(ping_url, headers={"User-Agent": "RenderKeepAlive/1.0"})
            with urllib.request.urlopen(req, timeout=15) as res:
                if res.status == 200:
                    print("[KEEP-ALIVE] Ping başarılı, sunucu uyanık tutuluyor.")
        except Exception as e:
            print("[KEEP-ALIVE] Ping uyarısı:", e)
        time.sleep(540)  # 9 dakikada bir (15 dk sınırından önce)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    socketserver.TCPServer.allow_reuse_address = True

    # Start live socket listener thread
    sock_thread = threading.Thread(target=start_socket_listener, daemon=True)
    sock_thread.start()

    # Start keep-alive ping thread (Render Free Tier uyku önleyici)
    keepalive_thread = threading.Thread(target=keep_alive_ping, daemon=True)
    keepalive_thread.start()

    print(f"==================================================")
    print(f"🚀 İddaa Takip Web Push Sunucusu Başlatıldı")
    print(f"👉 Adres: http://localhost:{PORT}")
    print(f"👉 VAPID Public Key: {vapid_keys['public_key']}")
    print(f"👉 Kayıtlı Abone Cihaz: {len(load_subscriptions())}")
    print(f"==================================================")

    server = socketserver.TCPServer(("", PORT), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu kapatıldı.")
        server.server_close()
