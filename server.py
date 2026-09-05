import http.server
import socketserver
import urllib.request
import json
import re
import os
import sys

PORT = 8080
TARGET_URL = "https://www.sahadan.com/lig/premier-lig/2kwbbcootiqqgmrzs6o5inle5?round_id=94794"

def fetch_sahadan():
    try:
        req = urllib.request.Request(TARGET_URL, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache"
        })
        html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8")
        
        for script in re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL):
            if "weeklyStandings" in script or "competition-main" in script:
                data = json.loads(script)
                
                memo = {}
                def deep_resolve(val, depth=0):
                    if depth > 16:
                        return None
                    if isinstance(val, int) and 0 <= val < len(data):
                        if val in memo:
                            return memo[val]
                        raw = data[val]
                        if isinstance(raw, list) and len(raw) == 2 and raw[0] in ("ShallowReactive", "Reactive", "Set", "Map"):
                            res = deep_resolve(raw[1], depth + 1)
                            memo[val] = res
                            return res
                        if isinstance(raw, dict):
                            res = {}
                            memo[val] = res
                            for k, v in raw.items():
                                res[k] = deep_resolve(v, depth + 1)
                            return res
                        if isinstance(raw, list):
                            res = []
                            memo[val] = res
                            for item in raw:
                                res.append(deep_resolve(item, depth + 1))
                            return res
                        return raw
                    elif isinstance(val, dict):
                        return {k: deep_resolve(v, depth + 1) for k, v in val.items()}
                    elif isinstance(val, list):
                        return [deep_resolve(v, depth + 1) for v in val]
                    return val

                root_data = deep_resolve(2)
                comp_keys = [k for k in root_data.keys() if "competition" in k]
                if not comp_keys:
                    continue
                comp_data = root_data[comp_keys[0]]

                # Puan Tablosu
                rankings = comp_data.get("rankings", {})
                total_table = rankings.get("total", [{}])[0].get("table", [])
                clean_standings = []
                for row in total_table:
                    team = row.get("team", {}) or {}
                    pro = row.get("pro", 0) or 0
                    against = row.get("against", 0) or 0
                    clean_standings.append({
                        "rank": row.get("rank"),
                        "team_id": team.get("id"),
                        "team_uuid": team.get("uuid"),
                        "name": team.get("name"),
                        "display_name": team.get("display_name", team.get("name")),
                        "played": row.get("played", 0),
                        "win": row.get("win", 0),
                        "draw": row.get("draw", 0),
                        "lost": row.get("lost", 0),
                        "pro": pro,
                        "against": against,
                        "diff": pro - against,
                        "pts": row.get("pts", 0),
                        "serie": row.get("serie", ""),
                        "zone": row.get("zone", {})
                    })

                # Fikstür / Haftalar
                clean_weeks = []
                current_week_idx = 0
                gamesets = comp_data.get("gamesets", [])
                
                for idx, gs in enumerate(gamesets):
                    week_num = gs.get("name")
                    matches = []
                    has_active = False
                    for m in gs.get("matches", []):
                        tA = m.get("team_A", {}) or {}
                        tB = m.get("team_B", {}) or {}
                        st = m.get("status", "")
                        if st in ("Played", "Playing", "Live"):
                            has_active = True
                        matches.append({
                            "id": m.get("id"),
                            "date_time": m.get("date_time_utc"),
                            "match_time": m.get("match_time"),
                            "status": st,
                            "home_team": {
                                "id": tA.get("id"),
                                "uuid": tA.get("uuid"),
                                "name": tA.get("name"),
                                "display_name": tA.get("display_name", tA.get("name"))
                            },
                            "away_team": {
                                "id": tB.get("id"),
                                "uuid": tB.get("uuid"),
                                "name": tB.get("name"),
                                "display_name": tB.get("display_name", tB.get("name"))
                            },
                            "home_score": m.get("fts_A"),
                            "away_score": m.get("fts_B"),
                            "half_time_home": m.get("hts_A"),
                            "half_time_away": m.get("hts_B")
                        })
                    if has_active:
                        current_week_idx = idx
                    clean_weeks.append({
                        "week": week_num,
                        "matches": matches
                    })

                return {
                    "success": True,
                    "competition": comp_data.get("competition", {}).get("name", "Premier Lig"),
                    "source": TARGET_URL,
                    "current_week_index": current_week_idx,
                    "standings": clean_standings,
                    "weeks": clean_weeks
                }
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {"success": False, "error": "Veri bulunamadı"}

from urllib.parse import urlparse

class PremierLeagueHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/data":
            data = fetch_sahadan()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        elif parsed.path == "/" or parsed.path == "":
            self.path = "/index.html"
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PremierLeagueHandler) as httpd:
        print(f"Server çalışıyor: http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer durduruldu.")
