import http.server
import socketserver
import json
import os
import sys
import threading
import time
import datetime
import urllib.request
import socketio
from pywebpush import webpush, WebPushException

PORT = int(os.environ.get("PORT", 8080))
SUBSCRIPTIONS_FILE = "subscriptions.json"
VAPID_FILE = "vapid_keys.json"
CACHE_FILE = "leagues_cache.json"

last_push_logs = []

def log_event(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    last_push_logs.append(entry)
    if len(last_push_logs) > 50:
        last_push_logs.pop(0)

# Load VAPID keys
if not os.path.exists(VAPID_FILE):
    log_event("HATA: vapid_keys.json bulunamadı!")
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
            log_event(f"{count} maçın takım isimleri önbellekten yüklendi.")
        except Exception as e:
            log_event(f"Önbellek okuma hatası: {e}")

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
    endpoint = sub.get("endpoint", "")
    try:
        claims = {"sub": "mailto:oktemonur7@gmail.com"}
        headers = {"Urgency": "high"}
        resp = webpush(
            subscription_info=sub,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=vapid_keys["private_key"],
            vapid_claims=claims,
            ttl=86400,
            headers=headers
        )
        status_code = getattr(resp, "status_code", 200)
        log_event(f"Push İletildi ({status_code}): {endpoint[:50]}...")
        return True, f"HTTP {status_code}"
    except WebPushException as ex:
        status = getattr(ex.response, "status_code", None) if ex.response else None
        body = getattr(ex.response, "text", str(ex)) if ex.response else str(ex)
        err_msg = f"WebPushException ({status}): {body}"
        log_event(f"Push Hatası: {err_msg}")
        if status in (404, 410):
            return "expired", err_msg
        return False, err_msg
    except Exception as e:
        err_msg = f"Beklenmeyen Hata: {type(e).__name__}: {e}"
        log_event(f"Push Hatası: {err_msg}")
        return False, err_msg

# Check if a match matches subscriber's favorites
def is_match_favorited(sub, match_identifiers):
    favs = sub.get("favorites", [])
    if not favs:
        return False
    fav_set = set(str(f).strip().lower() for f in favs)
    for ident in match_identifiers:
        if ident and str(ident).strip().lower() in fav_set:
            return True
    return False

# Send push ONLY to subscribers who favorited this match
def send_push_for_match(match_identifiers, payload):
    subs = load_subscriptions()
    if not subs:
        return 0

    target_subs = [s for s in subs if is_match_favorited(s, match_identifiers)]
    if not target_subs:
        return 0

    log_event(f"Maç bildirimi ({len(target_subs)} abone): {payload.get('title')} - {payload.get('body')}")
    expired_endpoints = set()
    sent_count = 0

    for sub in target_subs:
        ok, _ = send_push_to_sub(sub, payload)
        if ok is True:
            sent_count += 1
        elif ok == "expired":
            expired_endpoints.add(sub.get("endpoint"))

    if expired_endpoints:
        active_subs = [s for s in subs if s.get("endpoint") not in expired_endpoints]
        save_subscriptions(active_subs)

    return sent_count

# Send push to ALL subscribers (Test button / system)
def send_push_to_all(payload):
    subs = load_subscriptions()
    if not subs:
        log_event("Push gönderilemedi: Kayıtlı abone yok.")
        return 0, "Kayıtlı abone cihaz bulunamadı"

    log_event(f"Test bildirimi {len(subs)} aboneye iletiliyor...")
    expired_endpoints = set()
    sent_count = 0
    last_err = ""

    for sub in subs:
        ok, msg = send_push_to_sub(sub, payload)
        if ok is True:
            sent_count += 1
        else:
            last_err = msg
            if ok == "expired":
                expired_endpoints.add(sub.get("endpoint"))

    if expired_endpoints:
        active_subs = [s for s in subs if s.get("endpoint") not in expired_endpoints]
        save_subscriptions(active_subs)

    return sent_count, last_err

# Match state tracking
live_matches_state = {}

def process_match_update(update, is_initial=False):
    if not update or not isinstance(update, dict):
        return

    mid = str(update.get("id") or update.get("match_id") or update.get("uuid") or "")
    if not mid:
        return

    match_ids = [
        mid,
        str(update.get("id", "")),
        str(update.get("match_id", "")),
        str(update.get("uuid", "")),
        str(update.get("match_uuid", ""))
    ]
    match_ids = [i for i in match_ids if i]

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
        "notified_scores": set(),
        "notified_ht": False,
        "notified_ft": False
    })

    if "notified_scores" not in m:
        m["notified_scores"] = set()

    if m["home_team"] == "Ev Sahibi" and cached_names[0] != "Ev Sahibi":
        m["home_team"] = cached_names[0]
        m["away_team"] = cached_names[1]

    if "home_team_name" in update and update["home_team_name"]:
        m["home_team"] = update["home_team_name"]
    if "away_team_name" in update and update["away_team_name"]:
        m["away_team"] = update["away_team_name"]
    if "minute" in update and update["minute"] is not None:
        m["minute"] = str(update["minute"])

    all_identifiers = match_ids + [m["home_team"], m["away_team"]]

    new_home = update.get("fts_A")
    new_away = update.get("fts_B")

    new_status = str(update.get("status") or "").strip()
    new_period = str(update.get("period") or "").strip()
    is_ht = new_period in ("Half Time", "Devre Arası", "HT") or new_status in ("Half Time", "Devre Arası", "HT")
    is_ft = new_status.lower() in ("played", "ms", "ft", "finished", "bitti") or new_period.lower() in ("played", "ms", "ft", "finished")

    if is_initial:
        if new_home is not None:
            try: m["home_score"] = int(new_home)
            except ValueError: pass
        if new_away is not None:
            try: m["away_score"] = int(new_away)
            except ValueError: pass
        if m["home_score"] is not None and m["away_score"] is not None:
            m["notified_scores"].add((m["home_score"], m["away_score"]))
        if update.get("hts_A") is not None: m["ht_home"] = update["hts_A"]
        if update.get("hts_B") is not None: m["ht_away"] = update["hts_B"]
        m["status"] = new_status
        m["period"] = new_period
        if is_ht or is_ft:
            m["notified_ht"] = True
        if is_ft:
            m["notified_ft"] = True
        return

    # 1. GOL KONTROLÜ
    goal_team = ""
    goal_scored = False

    new_h = None
    new_a = None
    if new_home is not None:
        try: new_h = int(new_home)
        except ValueError: pass
    if new_away is not None:
        try: new_a = int(new_away)
        except ValueError: pass

    # Asla skoru geri düşürme (out-of-order delta veya çift event koruması)
    if new_h is not None and m["home_score"] is not None and new_h < m["home_score"]:
        new_h = m["home_score"]
    if new_a is not None and m["away_score"] is not None and new_a < m["away_score"]:
        new_a = m["away_score"]

    if new_h is not None:
        if m["home_score"] is not None and new_h > m["home_score"]:
            goal_scored = True
            goal_team = m["home_team"]
        m["home_score"] = new_h

    if new_a is not None:
        if m["away_score"] is not None and new_a > m["away_score"]:
            goal_scored = True
            goal_team = m["away_team"]
        m["away_score"] = new_a

    # DEDUPLICATION: Aynı skor için arka arkaya tekrar bildirim gitmesini engelle
    score_pair = (m["home_score"], m["away_score"])
    if goal_scored and score_pair not in m["notified_scores"]:
        m["notified_scores"].add(score_pair)
        min_str = f"{m['minute']}'" if m["minute"] else "Canlı"
        team_str = f" {goal_team}" if goal_team else ""
        title = f"⚽ GOL!{team_str} ({min_str})"
        body = f"{m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}"
        log_event(f"GOL TESPİT EDİLDİ: {title} -> {body}")
        send_push_for_match(all_identifiers, {
            "title": title,
            "body": body,
            "icon": "icons/icon-192.png",
            "tag": f"goal-{mid}-{m['home_score']}-{m['away_score']}"
        })

    # 2. İLK YARI BİTTİ KONTROLÜ
    if update.get("hts_A") is not None:
        m["ht_home"] = update["hts_A"]
    if update.get("hts_B") is not None:
        m["ht_away"] = update["hts_B"]

    if is_ht and not m["notified_ht"]:
        m["notified_ht"] = True
        ht_h = m["ht_home"] if m["ht_home"] is not None else (m["home_score"] if m["home_score"] is not None else 0)
        ht_a = m["ht_away"] if m["ht_away"] is not None else (m["away_score"] if m["away_score"] is not None else 0)
        title = "⏸️ İlk Yarı Bitti"
        body = f"{m['home_team']} {ht_h} - {ht_a} {m['away_team']}"
        log_event(f"İY BİTTİ: {title} -> {body}")
        send_push_for_match(all_identifiers, {
            "title": title,
            "body": body,
            "icon": "icons/icon-192.png",
            "tag": f"ht-{mid}"
        })

    # 3. MAÇ BİTTİ KONTROLÜ
    if is_ft and not m["notified_ft"]:
        m["notified_ft"] = True
        h = m["home_score"] if m["home_score"] is not None else 0
        a = m["away_score"] if m["away_score"] is not None else 0
        title = "🏁 Maç Bitti"
        body = f"{m['home_team']} {h} - {a} {m['away_team']}"
        log_event(f"MAÇ BİTTİ: {title} -> {body}")
        send_push_for_match(all_identifiers, {
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
                    title = f"🟥 Kırmızı Kart! {m['home_team']} ({min_str})"
                    body = f"{m['home_team']} {m.get('home_score',0)} - {m.get('away_score',0)} {m['away_team']}"
                    log_event(f"KIRMIZI KART: {title}")
                    send_push_for_match(all_identifiers, {
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
                    title = f"🟥 Kırmızı Kart! {m['away_team']} ({min_str})"
                    body = f"{m['home_team']} {m.get('home_score',0)} - {m.get('away_score',0)} {m['away_team']}"
                    log_event(f"KIRMIZI KART: {title}")
                    send_push_for_match(all_identifiers, {
                        "title": title,
                        "body": body,
                        "icon": "icons/icon-192.png",
                        "tag": f"rc-{mid}-{time.time()}"
                    })
            except ValueError:
                pass

# SAHADAN REAL-TIME HTTP SYNC ENGINE
latest_matches_summary = []
is_initial_sync = True

def sahadan_http_sync_worker():
    global is_initial_sync, latest_matches_summary
    log_event("🔄 Sahadan Canlı HTTP Senkronizasyon Servisi Başlatıldı.")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.sahadan.com/canli-sonuclar",
        "Accept": "application/json"
    }
    tz_tr = datetime.timezone(datetime.timedelta(hours=3))
    last_full_fetch = 0

    while True:
        now = time.time()

        # 1. Her 30 saniyede bir tüm maçların durumunu çek (soccer-live-e)
        if now - last_full_fetch >= 30:
            try:
                today = datetime.datetime.now(tz_tr).strftime("%Y-%m-%d")
                live_url = f"https://www.sahadan.com/api/index/soccer-live-e?a=bs&e=sams&add_playing=0&extended_period=1&date={today}&application=mackolik.com&language=tr"
                req = urllib.request.Request(live_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as res:
                    raw = json.loads(res.read().decode("utf-8"))
                    areas = raw.get("data", {}).get("areas", [])
                    new_summary = []
                    for a in areas:
                        for c in a.get("competitions", []):
                            for m in c.get("matches", []):
                                mid = m.get("id")
                                uuid = m.get("uuid")
                                t_a = m.get("team_A", {}).get("name", "")
                                t_b = m.get("team_B", {}).get("name", "")
                                if mid and t_a and t_b:
                                    match_names_map[str(mid)] = (t_a, t_b)
                                if uuid and t_a and t_b:
                                    match_names_map[str(uuid)] = (t_a, t_b)

                                match_dict = {
                                    "id": mid,
                                    "match_id": mid,
                                    "uuid": uuid,
                                    "match_uuid": uuid,
                                    "status": m.get("status"),
                                    "period": m.get("period"),
                                    "minute": m.get("minute"),
                                    "fts_A": m.get("fts_A"),
                                    "fts_B": m.get("fts_B"),
                                    "hts_A": m.get("hts_A"),
                                    "hts_B": m.get("hts_B"),
                                    "home_team_name": t_a,
                                    "away_team_name": t_b
                                }
                                new_summary.append(match_dict)
                                process_match_update(match_dict, is_initial=is_initial_sync)

                    latest_matches_summary = new_summary
                    last_full_fetch = now
                    if is_initial_sync:
                        is_initial_sync = False
                        live_cnt = len([x for x in new_summary if x.get("status") == "Playing"])
                        played_cnt = len([x for x in new_summary if x.get("status") == "Played"])
                        log_event(f"✓ Sahadan canlı maç tablosu yüklendi: Toplam {len(new_summary)} maç (Canlı: {live_cnt}, Biten: {played_cnt})")
            except Exception as e:
                log_event(f"Sahadan full sync hatası: {e}")

        # 2. Her 3 saniyede bir anlık olayları çek (soccer-sync-data)
        if not is_initial_sync:
            try:
                u = int(now / 2)
                sync_url = f"https://www.sahadan.com/api/index/soccer-sync-data?a=bs&e=sces&u={u}"
                req = urllib.request.Request(sync_url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as res:
                    changes = json.loads(res.read().decode("utf-8"))
                    if changes and isinstance(changes, list):
                        for item in changes:
                            mid = str(item.get("match_id") or item.get("id") or item.get("uuid") or "")
                            process_match_update(item, is_initial=False)
                            for existing in latest_matches_summary:
                                if str(existing.get("id")) == mid or str(existing.get("uuid")) == mid:
                                    if item.get("fts_A") is not None: existing["fts_A"] = item["fts_A"]
                                    if item.get("fts_B") is not None: existing["fts_B"] = item["fts_B"]
                                    if item.get("status"): existing["status"] = item["status"]
                                    if item.get("period"): existing["period"] = item["period"]
                                    if item.get("minute") is not None: existing["minute"] = item["minute"]
                                    break
            except Exception:
                pass

        time.sleep(3)

# Live WebSocket Listener (İkincil hızlı kanal)
def start_socket_listener():
    sio = socketio.Client(reconnection=True, reconnection_delay=2, reconnection_delay_max=10)

    @sio.on("connect")
    def on_connect():
        log_event("✓ Sahadan Canlı Socket Yayınına Bağlandı!")
        sio.emit("join-room", "soccer")

    @sio.on("disconnect")
    def on_disconnect():
        log_event("⚠ Socket bağlantısı koptu, yeniden bağlanılıyor...")

    @sio.on("matches")
    def on_matches(data):
        if not data:
            return
        content = data.get("content") if isinstance(data, dict) and "content" in data else data
        items = content if isinstance(content, list) else [content]
        for item in items:
            process_match_update(item, is_initial=False)

    while True:
        try:
            sio.connect("https://socket.mackolikfeeds.com/mksh", socketio_path="/socket.io", transports=["websocket"], wait_timeout=10)
            sio.wait()
        except Exception:
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
        if self.path.startswith("/api/live-sync") or self.path.startswith("/api/live-matches"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "count": len(latest_matches_summary),
                "matches": latest_matches_summary
            }, ensure_ascii=False).encode("utf-8"))
            return

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

        if self.path == "/api/diagnose":
            subs = load_subscriptions()
            safe_subs = []
            for s in subs:
                ep = s.get("endpoint", "")
                domain = ep.split("/")[2] if "//" in ep else "unknown"
                safe_subs.append({
                    "domain": domain,
                    "endpoint_preview": ep[:40] + "...",
                    "has_keys": bool(s.get("keys")),
                    "favorites_count": len(s.get("favorites", [])),
                    "favorites": s.get("favorites", [])[:10]
                })
            live_cnt = len([x for x in latest_matches_summary if x.get("status") == "Playing"])
            played_cnt = len([x for x in latest_matches_summary if x.get("status") == "Played"])
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "subscribers_count": len(subs),
                "sync_total_matches": len(latest_matches_summary),
                "sync_live_matches": live_cnt,
                "sync_played_matches": played_cnt,
                "subscribers": safe_subs,
                "recent_logs": last_push_logs
            }, indent=2, ensure_ascii=False).encode("utf-8"))
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
                
                favs = [str(f) for f in sub_data.get("favorites", [])]
                existing = next((s for s in subs if s.get("endpoint") == endpoint), None)
                if existing:
                    if "keys" in sub_data:
                        existing["keys"] = sub_data["keys"]
                    existing["favorites"] = favs
                    log_event(f"Abone favorileri güncellendi ({len(favs)} maç): {endpoint[:40]}...")
                else:
                    subs.append({
                        "endpoint": endpoint,
                        "keys": sub_data.get("keys", {}),
                        "favorites": favs
                    })
                    log_event(f"Yeni abone kaydedildi ({len(favs)} favori): {endpoint[:40]}...")
                    # Send welcome push
                    send_push_to_sub(sub_data, {
                        "title": "✅ Bildirimler Aktif!",
                        "body": "Yıldızladığınız (★) maçların gol, devre, maç sonu ve kırmızı kart bildirimleri gelecek.",
                        "icon": "icons/icon-192.png",
                        "tag": "welcome"
                    })

                save_subscriptions(subs)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "subscribers": len(subs)}).encode("utf-8"))
            except Exception as e:
                log_event(f"Subscribe hatası: {e}")
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
                "body": "Favori maç bildirim sisteminiz kusursuz çalışıyor! 🚀",
                "icon": "icons/icon-192.png",
                "tag": "test-push"
            }
            sent, err = send_push_to_all(payload)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "sent": sent, "error": err}).encode("utf-8"))
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
                    pass
        except Exception as e:
            pass
        time.sleep(540)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    socketserver.TCPServer.allow_reuse_address = True

    # Start Sahadan real-time HTTP sync thread
    http_sync_thread = threading.Thread(target=sahadan_http_sync_worker, daemon=True)
    http_sync_thread.start()

    # Start live socket listener thread
    sock_thread = threading.Thread(target=start_socket_listener, daemon=True)
    sock_thread.start()

    # Start keep-alive ping thread
    keepalive_thread = threading.Thread(target=keep_alive_ping, daemon=True)
    keepalive_thread.start()

    log_event(f"🚀 İddaa Takip Web Push Sunucusu Başlatıldı (Port: {PORT})")

    server = socketserver.TCPServer(("", PORT), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
