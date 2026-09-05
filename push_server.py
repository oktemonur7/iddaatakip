import http.server
import socketserver
import json
import os
import sys
import threading
import time
import socketio
from pywebpush import webpush, WebPushException

PORT = int(os.environ.get("PORT", 8080))
SUBSCRIPTIONS_FILE = "subscriptions.json"
VAPID_FILE = "vapid_keys.json"

# Load VAPID keys
if not os.path.exists(VAPID_FILE):
    print("HATA: vapid_keys.json bulunamadı!")
    sys.exit(1)

with open(VAPID_FILE, "r") as f:
    vapid_keys = json.load(f)

# Load subscriptions
def load_subscriptions():
    if os.path.exists(SUBSCRIPTIONS_FILE):
        try:
            with open(SUBSCRIPTIONS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_subscriptions(subs):
    with open(SUBSCRIPTIONS_FILE, "w") as f:
        json.dump(subs, f, indent=2)

def send_push_to_all(payload):
    subs = load_subscriptions()
    if not subs:
        print("[PUSH] Kayıtlı abone yok.")
        return 0

    print(f"[PUSH] {len(subs)} aboneye bildirim gönderiliyor: {payload.get('title')} - {payload.get('body')}")
    active_subs = []
    sent_count = 0

    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps(payload),
                vapid_private_key=vapid_keys["private_key"],
                vapid_claims={"sub": "mailto:admin@iddaatakip.local"}
            )
            active_subs.append(sub)
            sent_count += 1
            print(f"  ✓ Bildirim iletildi: {sub.get('endpoint', '')[:45]}...")
        except WebPushException as ex:
            status = getattr(ex.response, "status_code", None) if ex.response else None
            print(f"  ✗ Push Hatası ({status}): {ex}")
            # 404 / 410 ise cihaz aboneliği kapatmış, listeden çıkar
            if status not in (404, 410):
                active_subs.append(sub)
        except Exception as e:
            print(f"  ✗ Beklenmeyen hata: {e}")
            active_subs.append(sub)

    if len(active_subs) != len(subs):
        save_subscriptions(active_subs)

    return sent_count

# Match tracker memory
live_matches_state = {}

def process_match_update(update):
    if not update or not isinstance(update, dict):
        return

    mid = str(update.get("id") or update.get("match_id") or update.get("uuid") or "")
    if not mid:
        return

    m = live_matches_state.setdefault(mid, {
        "home_team": update.get("home_team_name") or "Ev Sahibi",
        "away_team": update.get("away_team_name") or "Deplasman",
        "home_score": None,
        "away_score": None,
        "minute": ""
    })

    if "home_team_name" in update:
        m["home_team"] = update["home_team_name"]
    if "away_team_name" in update:
        m["away_team"] = update["away_team_name"]
    if "minute" in update and update["minute"] is not None:
        m["minute"] = str(update["minute"])

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
        print(f"[GOL TESPİT EDİLDİ] {title} {body}")
        send_push_to_all({
            "title": title,
            "body": body,
            "icon": "icons/icon-192.png",
            "tag": f"goal-{mid}"
        })

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
                # Deduplicate by endpoint
                subs = [s for s in subs if s.get("endpoint") != sub_data.get("endpoint")]
                subs.append(sub_data)
                save_subscriptions(subs)

                # Send welcome push
                try:
                    webpush(
                        subscription_info=sub_data,
                        data=json.dumps({
                            "title": "🔔 İddaa Takip",
                            "body": "✅ Bildirimler aktif! Canlı maçlarda gol olduğunda kilit ekranınıza bildirim gelecek.",
                            "icon": "icons/icon-192.png",
                            "tag": "welcome"
                        }),
                        vapid_private_key=vapid_keys["private_key"],
                        vapid_claims={"sub": "mailto:admin@iddaatakip.local"}
                    )
                except Exception as e:
                    print("Welcome push error:", e)

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
                "title": "⚽ Test Bildirimi",
                "body": "İddaa Takip bildirim sistemi kusursuz çalışıyor! 🚀",
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

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    socketserver.TCPServer.allow_reuse_address = True

    # Start live socket listener thread
    sock_thread = threading.Thread(target=start_socket_listener, daemon=True)
    sock_thread.start()

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
