"""유사 한식 추천 — 백엔드 (JSON API + 정적 프론트 서빙).

실행:  python app.py   →  http://localhost:8000
API:
  GET /api/countries           국가 목록(국기/한글명/음식수)
  GET /api/foods?country=Thai  해당 국가 대표 음식
  GET /api/recommend?id=th_123 유사 한식 추천
프론트: web/ 폴더의 index.html / style.css / app.js
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from recommend import Recommender  # noqa: E402
from tour_api import places_for, get_key  # noqa: E402

REC = Recommender()
WEB = ROOT / "web"

# THEMEALDB 국가명 → (ISO코드, 한글명, 세계지도(world-atlas) 국가명)
COUNTRY_META = {
    "Algerian": ("dz", "알제리", "Algeria"), "Argentina": ("ar", "아르헨티나", "Argentina"),
    "Australian": ("au", "호주", "Australia"), "British": ("gb", "영국", "United Kingdom"),
    "Canadian": ("ca", "캐나다", "Canada"), "Chinese": ("cn", "중국", "China"),
    "Croatian": ("hr", "크로아티아", "Croatia"), "Egyptian": ("eg", "이집트", "Egypt"),
    "Filipino": ("ph", "필리핀", "Philippines"), "France": ("fr", "프랑스", "France"),
    "Greek": ("gr", "그리스", "Greece"), "India": ("in", "인도", "India"),
    "Irish": ("ie", "아일랜드", "Ireland"), "Italian": ("it", "이탈리아", "Italy"),
    "Jamaican": ("jm", "자메이카", "Jamaica"), "Japanese": ("jp", "일본", "Japan"),
    "Kenyan": ("ke", "케냐", "Kenya"), "Malaysian": ("my", "말레이시아", "Malaysia"),
    "Mexican": ("mx", "멕시코", "Mexico"), "Moroccan": ("ma", "모로코", "Morocco"),
    "Netherlands": ("nl", "네덜란드", "Netherlands"), "Norway": ("no", "노르웨이", "Norway"),
    "Polish": ("pl", "폴란드", "Poland"), "Portuguese": ("pt", "포르투갈", "Portugal"),
    "Russian": ("ru", "러시아", "Russia"), "Saudi Arabian": ("sa", "사우디아라비아", "Saudi Arabia"),
    "Slovakia": ("sk", "슬로바키아", "Slovakia"), "Spanish": ("es", "스페인", "Spain"),
    "Syrian": ("sy", "시리아", "Syria"), "Thai": ("th", "태국", "Thailand"),
    "Tunisian": ("tn", "튀니지", "Tunisia"), "Turkish": ("tr", "튀르키예", "Turkey"),
    "Ukrainian": ("ua", "우크라이나", "Ukraine"), "United States": ("us", "미국", "United States of America"),
    "Uruguayan": ("uy", "우루과이", "Uruguay"), "Venezuela": ("ve", "베네수엘라", "Venezuela"),
    "Vietnamese": ("vn", "베트남", "Vietnam"),
}

FLAVOR_KO = {"spicy": "매운맛", "savory": "감칠맛", "sweet": "단맛", "sour": "신맛",
             "nutty": "고소한맛", "creamy": "크리미", "herby": "허브향",
             "pungent": "알싸한맛"}


def countries_payload():
    out = []
    for c in sorted({f["country"] for f in REC.foreign if f["country"]}):
        iso, ko, geo = COUNTRY_META.get(c, ("", c, c))
        out.append({"id": c, "iso": iso, "ko": ko, "geo": geo,
                    "count": len(REC.list_by_country(c))})
    return sorted(out, key=lambda x: -x["count"])


def foods_payload(country):
    return [{"id": f["id"], "name": f["name"], "thumb": f["thumb"],
             "category": f["category"]}
            for f in sorted(REC.list_by_country(country), key=lambda f: f["name"])]


def _flavors_ko(tokens):
    return [FLAVOR_KO.get(t, t) for t in sorted(tokens)]


def recommend_payload(food_id):
    src = next((f for f in REC.foreign if f["id"] == food_id), None)
    if not src:
        return None
    results = REC.recommend_by_ingredients(src["_canon"], src["_flavor"], top=6)
    iso, ko, _geo = COUNTRY_META.get(src["country"], ("", src["country"], ""))
    return {
        "source": {"name": src["name"], "thumb": src["thumb"], "iso": iso,
                   "country_ko": ko, "flavors": _flavors_ko(src["_flavor"]),
                   "ingredients": sorted(src["_canon"])},
        "results": [{
            "name": k["name"], "thumb": k["thumb"], "category": k["category"],
            "cook_method": k["cook_method"], "score": round(score * 100),
            "flavors": _flavors_ko(k["_flavor"]),
            "shared": sorted(src["_canon"] & k["_canon"]),
        } for score, ing, fla, k in results],
    }


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, ctype):
        if not path.exists():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/countries":
            return self._json(countries_payload())
        if u.path == "/api/foods":
            return self._json(foods_payload(q.get("country", [""])[0]))
        if u.path == "/api/recommend":
            r = recommend_payload(q.get("id", [""])[0])
            return self._json(r) if r else self._json({"error": "not found"}, 404)
        if u.path == "/api/places":
            return self._json(places_for(q.get("food", [""])[0]))
        # 정적 파일
        if u.path in ("/", "/index.html"):
            return self._file(WEB / "index.html", "text/html; charset=utf-8")
        if u.path == "/style.css":
            return self._file(WEB / "style.css", "text/css; charset=utf-8")
        if u.path == "/app.js":
            return self._file(WEB / "app.js", "application/javascript; charset=utf-8")
        self.send_error(404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))      # 배포 플랫폼은 PORT를 주입함
    host = os.environ.get("HOST", "0.0.0.0")          # 외부 접속 허용(배포용)
    key_on = "TourAPI 연동됨" if get_key() else "TourAPI 키 없음(지도검색 폴백)"
    print(f"✅ http://localhost:{port}  (한식 {len(REC.korean)} / 해외 {len(REC.foreign)}) · {key_on}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
