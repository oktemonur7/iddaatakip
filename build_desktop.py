import urllib.request
import json
import re
import os
import sys
import time
try:
    import requests
except ImportError:
    requests = None

LEAGUES = [
    {
        "id": "super-lig-tr",
        "name": "Trendyol Süper Lig",
        "country": "Türkiye",
        "url": "https://www.sahadan.com/lig/trendyol-super-lig/482ofyysbdbeoxauk19yg7tdt"
    },
    {
        "id": "trendyol-1-lig",
        "name": "Trendyol 1. Lig",
        "country": "Türkiye",
        "url": "https://www.sahadan.com/lig/trendyol-1-lig/2o9svokc5s7diish3ycrzk7jm?round_id=95268"
    },
    {
        "id": "sampiyonlar-ligi",
        "name": "Şampiyonlar Ligi",
        "country": "Avrupa",
        "url": "https://www.sahadan.com/lig/sampiyonlar-ligi/4oogyu6o156iphvdvphwpck10?round_id=95533"
    },
    {
        "id": "avrupa-ligi",
        "name": "Avrupa Ligi",
        "country": "Avrupa",
        "url": "https://www.sahadan.com/lig/avrupa-ligi/4c1nfi2j1m731hcay25fcgndq?round_id=94654"
    },
    {
        "id": "konferans-ligi",
        "name": "Konferans Ligi",
        "country": "Avrupa",
        "url": "https://www.sahadan.com/lig/konferans-ligi/c7b8o53flg36wbuevfzy3lb10?round_id=95377"
    },
    {
        "id": "premier-lig-en",
        "name": "Premier Lig",
        "country": "İngiltere",
        "url": "https://www.sahadan.com/lig/premier-lig/2kwbbcootiqqgmrzs6o5inle5?round_id=94794"
    },
    {
        "id": "championship",
        "name": "Championship",
        "country": "İngiltere",
        "url": "https://www.sahadan.com/lig/championship/7ntvbsyq31jnzoqoa8850b9b8?round_id=94876"
    },
    {
        "id": "laliga",
        "name": "LaLiga",
        "country": "İspanya",
        "url": "https://www.sahadan.com/lig/laliga/34pl8szyvrbwcmfkuocjm3r6t?round_id=95118"
    },
    {
        "id": "serie-a",
        "name": "Serie A",
        "country": "İtalya",
        "url": "https://www.sahadan.com/lig/serie-a/1r097lpxe0xn03ihb7wi98kao?round_id=95212"
    },
    {
        "id": "bundesliga",
        "name": "Bundesliga",
        "country": "Almanya",
        "url": "https://www.sahadan.com/lig/bundesliga/6by3h89i2eykc341oz7lv1ddd?round_id=94362"
    },
    {
        "id": "ligue-1",
        "name": "Ligue 1",
        "country": "Fransa",
        "url": "https://www.sahadan.com/lig/ligue-1/dm5ka0os1e3dxcp3vh05kmp33?round_id=95454"
    },
    {
        "id": "eredivisie",
        "name": "Eredivisie",
        "country": "Hollanda",
        "url": "https://www.sahadan.com/lig/eredivisie/akmkihra9ruad09ljapsm84b3?round_id=95210"
    },
    {
        "id": "premier-lig-pt",
        "name": "Primeira Liga",
        "country": "Portekiz",
        "url": "https://www.sahadan.com/lig/premier-lig/8yi6ejjd1zudcqtbn07haahg6?round_id=94364"
    },
    {
        "id": "pro-lig-be",
        "name": "Pro Lig",
        "country": "Belçika",
        "url": "https://www.sahadan.com/lig/pro-lig/4zwgbb66rif2spcoeeol2motx?round_id=95776"
    },
    {
        "id": "premiership-sc",
        "name": "Premiership",
        "country": "İskoçya",
        "url": "https://www.sahadan.com/lig/premiership/e21cf135btr8t3upw0vl6n6x0?round_id=94447"
    },
    {
        "id": "super-lig-dk",
        "name": "Superliga",
        "country": "Danimarka",
        "url": "https://www.sahadan.com/lig/super-lig/29actv1ohj8r10kd9hu0jnb0n?round_id=94865"
    },
    {
        "id": "super-lig-ch",
        "name": "Super League",
        "country": "İsviçre",
        "url": "https://www.sahadan.com/lig/super-lig/e0lck99w8meo9qoalfrxgo33o?round_id=94518"
    },
    {
        "id": "eliteserien",
        "name": "Eliteserien",
        "country": "Norveç",
        "url": "https://www.sahadan.com/lig/eliteserien/9ynnnx1qmkizq1o3qr3v0nsuk?round_id=92120"
    },
    {
        "id": "czech-liga",
        "name": "Chance Liga",
        "country": "Çekya",
        "url": "https://www.sahadan.com/lig/czech-liga/bu1l7ckihyr0errxw61p0m05?round_id=95226"
    }
]

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(APP_DIR, "leagues_cache.json")
DESKTOP_HTML = "/Users/onur/Desktop/futbol_ligleri.html"
TEMPLATE_HTML = os.path.join(APP_DIR, "index.html")
OUTPUT_HTML = os.path.join(APP_DIR, "dist", "index.html")  # GitHub Pages çıktısı

def parse_sahadan_league(target_url, max_retries=3):
    clean_url = target_url.strip().replace("\u2028", "").replace("\u2029", "")
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(clean_url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache"
            })
            html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
            
            for script in re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL):
                if "weeklyStandings" in script or "competition-main" in script:
                    data = json.loads(script)
                    memo = {}
                    def deep_resolve(val, depth=0):
                        if depth > 16: return None
                        if isinstance(val, int) and 0 <= val < len(data):
                            if val in memo: return memo[val]
                            raw = data[val]
                            if isinstance(raw, list) and len(raw) == 2 and raw[0] in ("ShallowReactive", "Reactive", "Set", "Map"):
                                res = deep_resolve(raw[1], depth + 1)
                                memo[val] = res
                                return res
                            if isinstance(raw, dict):
                                res = {k: deep_resolve(v, depth + 1) for k, v in raw.items()}
                                memo[val] = res
                                return res
                            if isinstance(raw, list):
                                res = [deep_resolve(item, depth + 1) for item in raw]
                                memo[val] = res
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

                    # Standings
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

                    # Weeks / Fixtures
                    clean_weeks = []
                    gamesets = comp_data.get("gamesets", [])
                    
                    for idx, gs in enumerate(gamesets):
                        week_num = gs.get("name")
                        matches = []
                        for m in gs.get("matches", []):
                            tA = m.get("team_A", {}) or {}
                            tB = m.get("team_B", {}) or {}
                            st = m.get("status", "")
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
                        clean_weeks.append({
                            "week": week_num,
                            "matches": matches
                        })

                    # Calculate real current active week:
                    # 1. Prefer week with 'Playing' or 'Live'
                    current_week_idx = 0
                    found_active = False
                    for idx, gs in enumerate(clean_weeks):
                        if any(m.get("status") in ("Playing", "Live") for m in gs.get("matches", [])):
                            current_week_idx = idx
                            found_active = True
                            break

                    # 2. If none live, find week with unplayed 'Fixture' matches closest to current date
                    if not found_active:
                        import datetime
                        today = datetime.datetime.now().date()
                        min_diff = 9999
                        for idx, gs in enumerate(clean_weeks):
                            unplayed = [m for m in gs.get("matches", []) if m.get("status") == "Fixture"]
                            for m in unplayed:
                                dt_str = (m.get("date_time") or "")[:10]
                                if dt_str:
                                    try:
                                        m_date = datetime.date.fromisoformat(dt_str)
                                        diff = abs((m_date - today).days)
                                        if diff < min_diff:
                                            min_diff = diff
                                            current_week_idx = idx
                                            found_active = True
                                    except:
                                        pass

                    # 3. Fallback: if no fixture matches, last week with played matches
                    if not found_active:
                        for idx, gs in enumerate(clean_weeks):
                            if any(m.get("status") == "Played" for m in gs.get("matches", [])):
                                current_week_idx = idx

                    return {
                        "success": True,
                        "competition_title": comp_data.get("competition", {}).get("name", ""),
                        "current_week_index": current_week_idx,
                        "standings": clean_standings,
                        "weeks": clean_weeks
                    }
        except Exception as e:
            time.sleep(1.0)
            
    return None

def fetch_live_scores_today():
    print(f"Sahadan.com üzerinden günün canlı maçları ({len(LEAGUES)} Lig/Kupa) taranıyor...")
    league_uuids = {}
    for l in LEAGUES:
        url_path = l["url"].split("?")[0]
        uuid = url_path.split("/")[-1]
        league_uuids[uuid] = l

    today_matches = []
    seen_match_ids = set()

    try:
        url = "https://www.sahadan.com/canli-sonuclar"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
            "Cache-Control": "no-cache"
        }
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8")
        m = re.search(r'<script[^>]*id=\"__NUXT_DATA__\"[^>]*>(.*?)</script>', html)
        if m:
            nuxt = json.loads(m.group(1))
            memo = {}
            def deep_resolve(val, depth=0):
                if depth > 40: return val
                if isinstance(val, int):
                    if val in memo: return memo[val]
                    if 0 <= val < len(nuxt):
                        raw = nuxt[val]
                        if isinstance(raw, (dict, list)):
                            memo[val] = raw
                            if isinstance(raw, dict):
                                res = {k: deep_resolve(v, depth+1) for k, v in raw.items()}
                            else:
                                if len(raw) == 2 and raw[0] == 'ShallowReactive':
                                    res = deep_resolve(raw[1], depth+1)
                                else:
                                    res = [deep_resolve(item, depth+1) for item in raw]
                            memo[val] = res
                            return res
                        return raw
                elif isinstance(val, dict):
                    return {k: deep_resolve(v, depth+1) for k, v in val.items()}
                elif isinstance(val, list):
                    if len(val) == 2 and val[0] == 'ShallowReactive':
                        return deep_resolve(val[1], depth+1)
                    return [deep_resolve(v, depth+1) for v in val]
                return val

            root = deep_resolve(2)
            for k, v in root.items():
                if isinstance(v, dict) and "data" in v and "areas" in v["data"]:
                    areas = v["data"]["areas"]
                    for a in areas:
                        for comp in a.get("competitions", []):
                            cuuid = comp.get("uuid")
                            if cuuid in league_uuids:
                                linfo = league_uuids[cuuid]
                                for m_item in comp.get("matches", []):
                                    mid = m_item.get("id")
                                    if mid in seen_match_ids:
                                        continue
                                    seen_match_ids.add(mid)
                                    tA = m_item.get("team_A", {}) or {}
                                    tB = m_item.get("team_B", {}) or {}
                                    raw_dt = m_item.get("date_time_utc")
                                    raw_time = m_item.get("match_time")
                                    local_time = raw_time
                                    if raw_dt and len(str(raw_dt)) >= 16:
                                        try:
                                            import datetime
                                            dt_utc = datetime.datetime.fromisoformat(str(raw_dt).replace(" ", "T"))
                                            dt_tr = dt_utc + datetime.timedelta(hours=3)
                                            local_time = dt_tr.strftime("%H:%M")
                                        except:
                                            pass
                                    elif raw_time and ":" in str(raw_time):
                                        try:
                                            parts = str(raw_time).split(":")
                                            hh = (int(parts[0]) + 3) % 24
                                            local_time = f"{hh:02d}:{parts[1]}"
                                        except:
                                            pass

                                    raw_st = str(m_item.get("status") or "").strip()
                                    raw_pr = str(m_item.get("period") or "").strip()
                                    is_m_ft = raw_st.lower() in ("played", "ms", "ft", "finished", "bitti") or raw_pr.lower() in ("played", "ms", "ft", "finished", "full time", "fulltime", "maç bitti")

                                    today_matches.append({
                                        "league_id": linfo["id"],
                                        "league_name": linfo["name"],
                                        "league_country": linfo["country"],
                                        "match_id": mid,
                                        "uuid": m_item.get("uuid"),
                                        "match_uuid": m_item.get("match_uuid") or m_item.get("uuid"),
                                        "date_time": raw_dt,
                                        "match_time": local_time,
                                        "status": "Played" if is_m_ft else raw_st,
                                        "period": raw_pr,
                                        "minute": m_item.get("minute"),
                                        "minute_extra": m_item.get("minute_extra"),
                                        "home_team": tA.get("name") if isinstance(tA, dict) else str(tA),
                                        "away_team": tB.get("name") if isinstance(tB, dict) else str(tB),
                                        "home_score": m_item.get("fts_A"),
                                        "away_score": m_item.get("fts_B"),
                                        "half_time_home": m_item.get("hts_A"),
                                        "half_time_away": m_item.get("hts_B"),
                                    })
            print(f" ✓ Canlı skor bülteninden {len(LEAGUES)} lige ait toplam {len(today_matches)} maç listelendi.")
    except Exception as e:
        print(f" ! Canlı sonuçlar taranırken hata: {e}")

    return today_matches

import html as html_parser
from concurrent.futures import ThreadPoolExecutor

def norm_team_name(s):
    if not s:
        return ""
    s = html_parser.unescape(s).replace("İ", "i").replace("I", "i").lower()
    # Normalize common abbreviations and prefixes
    s = re.sub(r"\bo\.?\s*h\.?\s*", "oh ", s)
    s = re.sub(r"\bfatih\s+", "f ", s)
    abbr_map = {
        r"\br\.\s*": "real ",
        r"\be\.\s*": "eintracht ",
        r"\bv\.\s*": "vitoria ",
        r"\bfortuna\s+": "f ",
        r"\bf\.\s*": "f ",
        r"\bh\.\s*kralove\b": "hradec kralove",
        r"\bman\.\s*": "manchester ",
        r"\bman\s+": "manchester ",
        r"\bdep\.\s*": "deportivo ",
        r"\bath\.\s*": "athletic ",
        r"\batl\.\s*": "atletico "
    }
    for pattern, repl in abbr_map.items():
        s = re.sub(pattern, repl, s)

    # Remove common club suffixes/prefixes
    s = re.sub(r"\b(sk|fk|fc|cf|cd|sc|as|w)\b\.?", " ", s)

    ch_map = {'ü': 'u', 'ö': 'o', 'ı': 'i', 'ş': 's', 'ç': 'c', 'ğ': 'g', 'é': 'e', 'è': 'e', 'á': 'a', 'à': 'a', 'ä': 'a', 'ø': 'o', 'æ': 'ae', 'í': 'i', 'ó': 'o', 'ú': 'u'}
    for ch in [' ', '.', '-', '\t', '\'', '’', 'ü', 'ö', 'ı', 'ş', 'ç', 'ğ', 'é', 'è', 'á', 'à', 'ä', 'ø', 'æ', 'í', 'ó', 'ú', 'club', 'de']:
        s = s.replace(ch, ch_map.get(ch, ''))
    return s

def fetch_iddaa_odds(all_target_teams=None):
    print("İddaa bülteninden (Sahadan & iddaa.com) tüm maçların güncel oranları (MS, 2.5 Alt/Üst, KG Var/Yok) taranıyor...")
    all_odds = {}

    headers_sahadan = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache"
    }
    headers_iddaa = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Origin": "https://www.iddaa.com",
        "Referer": "https://www.iddaa.com/"
    }

    # 1. Sahadan.com Nuxt Programı (600+ maç)
    try:
        req_s = urllib.request.Request("https://www.sahadan.com/iddaa-programi", headers=headers_sahadan)
        html_s = urllib.request.urlopen(req_s, timeout=12).read().decode("utf-8")
        m = re.search(r'<script[^>]*id=\"__NUXT_DATA__\"[^>]*>(.*?)</script>', html_s)
        if m:
            nuxt_data = json.loads(m.group(1))
            def resolve(val):
                if isinstance(val, int) and 0 <= val < len(nuxt_data):
                    return nuxt_data[val]
                return val

            for item in nuxt_data:
                if isinstance(item, dict) and "team_A" in item and "team_B" in item and "markets" in item:
                    tA = resolve(item["team_A"])
                    tB = resolve(item["team_B"])
                    if not isinstance(tA, str) or not isinstance(tB, str):
                        continue
                    markets = resolve(item["markets"])
                    odds = {}
                    if isinstance(markets, list):
                        for m_idx in markets:
                            m_val = resolve(m_idx)
                            if not isinstance(m_val, dict):
                                continue
                            mi = resolve(m_val.get("i"))
                            o_list = resolve(m_val.get("o"))
                            if isinstance(o_list, list):
                                for opt_idx in o_list:
                                    opt = resolve(opt_idx)
                                    if isinstance(opt, dict):
                                        lines = resolve(opt.get("l"))
                                        if isinstance(lines, list):
                                            for line_idx in lines:
                                                line_d = resolve(line_idx)
                                                if isinstance(line_d, dict):
                                                    name = resolve(line_d.get("n"))
                                                    val = resolve(line_d.get("v"))
                                                    if mi == 1:
                                                        if name == "1": odds["ms1"] = str(val)
                                                        elif name in ("0", "X", "x"): odds["ms0"] = str(val)
                                                        elif name == "2": odds["ms2"] = str(val)
                                                    elif mi == 10:
                                                        if name == "Alt": odds["alt"] = str(val)
                                                        elif name == "Üst": odds["ust"] = str(val)
                                                    elif mi == 6:
                                                        if name == "Var": odds["kg_var"] = str(val)
                                                        elif name == "Yok": odds["kg_yok"] = str(val)
                    if "ms1" in odds:
                        all_odds[(tA, tB)] = odds
            print(f" ✓ Sahadan bülteninden {len(all_odds)} maçlık İddaa oranları toplandı.")
    except Exception as e:
        print(f" ! Sahadan bülteni okunurken hata: {e}")

    # 2. iddaa.com Resmi Sportsbook API (Tüm resmi bülten & oranlar)
    try:
        req_i = urllib.request.Request("https://sportsbookv2.iddaa.com/sportsbook/events?type=1&sportId=1", headers=headers_iddaa)
        events = json.loads(urllib.request.urlopen(req_i, timeout=12).read().decode("utf-8")).get("data", {}).get("events", [])

        target_events = []
        for e in events:
            if e.get("sid") == 1:
                hn = e.get("hn", "")
                an = e.get("an", "")
                norm_h = norm_team_name(hn)
                norm_a = norm_team_name(an)
                
                # Check if matches target teams
                is_relevant = True
                if all_target_teams:
                    h_ok = any(t in norm_h or norm_h in t for t in all_target_teams)
                    a_ok = any(t in norm_a or norm_a in t for t in all_target_teams)
                    is_relevant = (h_ok and a_ok)

                if is_relevant:
                    # Target id is preferably mpi if present, or i
                    target_id = e.get("mpi") or e.get("i")
                    target_events.append((target_id, hn, an))

        print(f" ✓ iddaa.com üzerinden {len(target_events)} maçın canlı oran detayları çekiliyor...")
        def fetch_single_event(item):
            eid, hn, an = item
            url = f"https://sportsbookv2.iddaa.com/sportsbook/event/{eid}"
            try:
                data = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=headers_iddaa), timeout=6).read().decode("utf-8"))
                ev = data.get("data", {})
                odds = {}
                for m in ev.get("m", []):
                    st = m.get("st")
                    sov = str(m.get("sov") or "")
                    o_dict = {str(o.get("n")): str(o.get("wodd") or o.get("odd")) for o in m.get("o", [])}
                    if st in (1, 4) and "1" in o_dict and "0" in o_dict and "2" in o_dict:
                        odds["ms1"] = o_dict["1"]
                        odds["ms0"] = o_dict["0"]
                        odds["ms2"] = o_dict["2"]
                    elif st in (14, 101) and sov == "2.5":
                        if "Alt" in o_dict and "Üst" in o_dict:
                            odds["alt"] = o_dict["Alt"]
                            odds["ust"] = o_dict["Üst"]
                    elif st in (89, 131):
                        if "Var" in o_dict and "Yok" in o_dict:
                            odds["kg_var"] = o_dict["Var"]
                            odds["kg_yok"] = o_dict["Yok"]
                if "ms1" in odds:
                    return hn, an, odds
            except:
                pass
            return hn, an, None

        with ThreadPoolExecutor(max_workers=25) as executor:
            for hn, an, odds in executor.map(fetch_single_event, target_events):
                if odds:
                    # Update or merge
                    if (hn, an) in all_odds:
                        all_odds[(hn, an)].update(odds)
                    else:
                        all_odds[(hn, an)] = odds

        print(f" ✓ iddaa.com senkronizasyonu tamamlandı. Toplam havuz: {len(all_odds)} maç.")
    except Exception as e:
        print(f" ! iddaa.com taranırken hata: {e}")

    # Build clean lookup dictionary
    clean_dict = {}
    for (tA, tB), odds in all_odds.items():
        clean_dict[f"{norm_team_name(tA)}__{norm_team_name(tB)}"] = odds

    return clean_dict

def match_odds(tA, tB, clean_dict):
    if not clean_dict:
        return None
    nA = norm_team_name(tA)
    nB = norm_team_name(tB)
    k = f"{nA}__{nB}"
    if k in clean_dict:
        return clean_dict[k]
    # Fuzzy match
    for ok, ov in clean_dict.items():
        okA, okB = ok.split("__")
        if (nA in okA or okA in nA) and (nB in okB or okB in nB):
            return ov
def fetch_tv_broadcasts():
    print("Sahadan.com TV Programı (Canlı Yayın Akışı) taranıyor...")
    tv_map = {}
    try:
        url = "https://www.sahadan.com/tv-programi"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
            "Cache-Control": "no-cache"
        }
        html_text = ""
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                html_text = response.read().decode("utf-8")
        except:
            if requests:
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code == 200:
                    html_text = resp.text
        if html_text:
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', html_text, re.DOTALL)
            for s in scripts:
                s_strip = s.strip()
                if s_strip.startswith('[["ShallowReactive"') and "tv-broadcasts" in s_strip:
                    data = json.loads(s_strip)
                    memo = {}
                    def deep_resolve(val, depth=0):
                        if depth > 40: return None
                        if isinstance(val, int):
                            if 0 <= val < len(data):
                                if val in memo: return memo[val]
                                raw = data[val]
                                if isinstance(raw, list) and len(raw) == 2 and raw[0] in ('ShallowReactive', 'Reactive', 'Set', 'Map'):
                                    res = deep_resolve(raw[1], depth + 1)
                                    memo[val] = res
                                    return res
                                if isinstance(raw, dict):
                                    res = {k: deep_resolve(v, depth + 1) for k, v in raw.items()}
                                    memo[val] = res
                                    return res
                                if isinstance(raw, list):
                                    res = [deep_resolve(item, depth + 1) for item in raw]
                                    memo[val] = res
                                    return res
                                return raw
                        elif isinstance(val, dict):
                            return {k: deep_resolve(v, depth + 1) for k, v in val.items()}
                        elif isinstance(val, list):
                            return [deep_resolve(v, depth + 1) for v in val]
                        return val

                    resolved = deep_resolve(2)
                    broadcasts = resolved.get("tv-broadcasts", {}).get("data", {}).get("broadcasts", [])
                    for b in broadcasts:
                        chs = [c.get("name") for c in (b.get("channels") or []) if c.get("name")]
                        if not chs:
                            continue
                        m = b.get("match") or {}
                        mid = m.get("id")
                        muuid = m.get("uuid")
                        mname = m.get("name") or b.get("name") or ""

                        if mid:
                            tv_map[mid] = chs
                            tv_map[str(mid)] = chs
                        if muuid:
                            tv_map[muuid] = chs
                        if " - " in mname:
                            parts = mname.split(" - ")
                            h = norm_team_name(parts[0].strip())
                            a = norm_team_name(parts[1].strip())
                            if h and a:
                                tv_map[f"{h}___{a}"] = chs
                    break
        print(f" ✓ Sahadan TV Programından {len(tv_map)} anahtar ile yayın kanalları toplandı.")
    except Exception as e:
        print(f" ! TV Programı taranırken hata: {e}")
    return tv_map

def build_desktop_html():
    print(f"Sahadan.com üzerinden {len(LEAGUES)} ligin verileri taranıyor...")
    cached_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
        except:
            cached_data = {}

    for l in LEAGUES:
        lid = l["id"]
        name = l["name"]
        country = l["country"]
        url = l["url"]

        data = parse_sahadan_league(url)
        if data and len(data.get("standings", [])) > 0:
            cached_data[lid] = data
            s_count = len(data["standings"])
            w_count = len(data["weeks"])
            print(f" ✓ {name} ({country}): {s_count} Takım, {w_count} Hafta")
        else:
            if lid in cached_data:
                print(f" ! {name} ({country}): Canlı bağlantı gecikti, kayıtlı veri korundu.")
            else:
                print(f" ✗ {name} ({country}): Alınamadı!")
        time.sleep(0.3)

    # Collect all team names across leagues to optimize iddaa querying
    all_target_teams = set()
    for lid, ldata in cached_data.items():
        for s in ldata.get("standings", []):
            all_target_teams.add(norm_team_name(s.get("name", "")))

    # İddaa oranlarını çek ve eşleştir
    clean_odds_dict = fetch_iddaa_odds(all_target_teams)
    matched_odds = 0
    if clean_odds_dict:
        for lid, ldata in cached_data.items():
            for w in ldata.get("weeks", []):
                for m in w.get("matches", []):
                    o = match_odds(m["home_team"]["name"], m["away_team"]["name"], clean_odds_dict)
                    if o:
                        m["odds"] = o
                        matched_odds += 1
        print(f" ✓ Toplam {matched_odds} maça İddaa oranları (MS, 2.5 Alt/Üst, KG) eksiksiz eşleştirildi.")

    # Canlı Skorlar (Bugün liglerde oynanacak/oynanan tüm maçlar)
    today_live_matches = fetch_live_scores_today()
    if clean_odds_dict and today_live_matches:
        for tm in today_live_matches:
            o = match_odds(tm["home_team"], tm["away_team"], clean_odds_dict)
            if o:
                tm["odds"] = o

    # TV Yayın Akışı (Hangi kanal veriyor?)
    tv_map = fetch_tv_broadcasts()
    if tv_map:
        matched_tv_live = 0
        if today_live_matches:
            for tm in today_live_matches:
                mid = tm.get("match_id")
                muuid = tm.get("uuid") or tm.get("match_uuid")
                h_norm = norm_team_name(tm.get("home_team", ""))
                a_norm = norm_team_name(tm.get("away_team", ""))
                pair_key = f"{h_norm}___{a_norm}"

                chs = None
                if mid and mid in tv_map:
                    chs = tv_map[mid]
                elif muuid and muuid in tv_map:
                    chs = tv_map[muuid]
                elif pair_key in tv_map:
                    chs = tv_map[pair_key]

                if chs:
                    tm["tv_channels"] = chs
                    matched_tv_live += 1
        print(f" ✓ Toplam {matched_tv_live} canlı maça TV yayın kanalları eşleştirildi.")

        # Fikstür maçlarına da TV kanallarını bağla
        matched_tv_fix = 0
        for lid, ldata in cached_data.items():
            for w in ldata.get("weeks", []):
                for m in w.get("matches", []):
                    mid = m.get("id")
                    muuid = m.get("uuid")
                    h_norm = norm_team_name(m.get("home_team", {}).get("name", ""))
                    a_norm = norm_team_name(m.get("away_team", {}).get("name", ""))
                    pair_key = f"{h_norm}___{a_norm}"

                    chs = None
                    if mid and mid in tv_map:
                        chs = tv_map[mid]
                    elif muuid and muuid in tv_map:
                        chs = tv_map[muuid]
                    elif pair_key in tv_map:
                        chs = tv_map[pair_key]

                    if chs:
                        m["tv_channels"] = chs
                        matched_tv_fix += 1
        print(f" ✓ Fikstür maçlarından toplam {matched_tv_fix} maça TV yayın kanalları eşleştirildi.")

    # Cache yaz
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cached_data, f, ensure_ascii=False)

    payload = {
        "leagues_list": [
            {"id": l["id"], "name": l["name"], "country": l["country"]}
            for l in LEAGUES
        ],
        "default_league": "super-lig-tr",
        "live_scores_today": today_live_matches,
        "data": cached_data
    }

    with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
        template = f.read()

    # Socket.io v2 client kütüphanesini doğrudan HTML içine göm (Sıfır CDN bağımlılığı)
    socket_js_path = os.path.join(os.path.dirname(__file__), "socket.io.v2.slim.js")
    if os.path.exists(socket_js_path):
        with open(socket_js_path, "r", encoding="utf-8") as sf:
            socket_code = sf.read()
        template = re.sub(
            r'<script\s+src=[\'\"][^\'\"]*socket\.io[^\'\"]*[\'\"]>\s*</script>',
            lambda _: f'<script>\n{socket_code}\n</script>',
            template
        )

    injected_js = f"window.INITIAL_ALL_LEAGUES = {json.dumps(payload, ensure_ascii=False)};\n"
    modified_html = template.replace("// EMBEDDED_DATA_PLACEHOLDER", injected_js)

    # Desktop'a yaz (sadece macOS'ta)
    if os.path.isdir("/Users/onur/Desktop"):
        with open(DESKTOP_HTML, "w", encoding="utf-8") as f:
            f.write(modified_html)
        with open("/Users/onur/Desktop/premier_lig.html", "w", encoding="utf-8") as f:
            f.write(modified_html)

    # GitHub Pages çıktısı
    dist_dir = os.path.dirname(OUTPUT_HTML)
    os.makedirs(dist_dir, exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(modified_html)

    # PWA dosyalarını dist/ klasörüne kopyala
    import shutil
    for fname in ["manifest.json", "sw.js"]:
        src = os.path.join(APP_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dist_dir, fname))
    icons_src = os.path.join(APP_DIR, "icons")
    icons_dst = os.path.join(dist_dir, "icons")
    if os.path.isdir(icons_src):
        shutil.copytree(icons_src, icons_dst, dirs_exist_ok=True)

    print(f"\nİşlem başarıyla tamamlandı! Standalone Neon Lig Tablosu:")
    print(f"1. {DESKTOP_HTML}")
    print(f"2. /Users/onur/Desktop/premier_lig.html")
    print(f"3. {OUTPUT_HTML} (GitHub Pages)")

    print(f"\nİşlem tamamlandı! {len(cached_data)}/{len(LEAGUES)} lig ve turnuva hazır:")
    print(f"- {DESKTOP_HTML}")

if __name__ == "__main__":
    build_desktop_html()
