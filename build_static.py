"""정적 사이트 빌드 → dist/  (GitHub Pages 배포용).

추천 결과와 맛집·특산물(TourAPI)을 빌드 시점에 미리 계산해 정적 JSON으로 굽는다.
→ 백엔드 없이 GitHub Pages만으로 완전 동작하며, 인증키는 빌드 시에만 쓰여 노출되지 않는다.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import app  # noqa: E402  (REC + payload 함수 로드, 서버는 시작 안 함)
from tour_api import DISH_TYPES, get_key, map_links, places_for  # noqa: E402


def best_keyword(name):
    """음식명에서 관광 데이터에 존재하는 대표 요리 종류만 추출(없으면 None)."""
    for d in DISH_TYPES:
        if d in name:
            return d
    return None

DIST = ROOT / "dist"
shutil.rmtree(DIST, ignore_errors=True)
(DIST / "api").mkdir(parents=True)


def dump(name, obj):
    (DIST / "api" / f"{name}.json").write_text(
        json.dumps(obj, ensure_ascii=False), encoding="utf-8")


# ── 프론트 자산 복사 (정적 모드 플래그 주입 + 절대경로→상대경로) ──
html = (ROOT / "web" / "index.html").read_text("utf-8")
html = html.replace('href="/style.css"', 'href="style.css"')
html = html.replace('src="/app.js"', 'src="app.js"')
html = html.replace("</head>", "<script>window.__STATIC__=true;</script>\n</head>")
(DIST / "index.html").write_text(html, encoding="utf-8")
shutil.copy(ROOT / "web" / "style.css", DIST / "style.css")
shutil.copy(ROOT / "web" / "app.js", DIST / "app.js")

# ── 국가 / 음식 ──
countries = app.countries_payload()
dump("countries", countries)
dump("foods", {c["id"]: app.foods_payload(c["id"]) for c in countries})
print(f"countries {len(countries)}")

# ── 추천 (해외 음식별) ──
reco, dishes = {}, set()
for f in app.REC.foreign:
    r = app.recommend_payload(f["id"])
    if r:
        reco[f["id"]] = r
        dishes.update(res["name"] for res in r["results"])
dump("reco", reco)
print(f"reco {len(reco)} / 추천 한식 종류 {len(dishes)}")

# ── 맛집·특산물 (추천된 한식별, TourAPI) ──
# 인식 가능한 요리 종류 키워드만 조회(키워드 단위 캐시) → 호출 수 최소화.
if not get_key():
    print("⚠️ TourAPI 키 없음 — places는 빈 값으로 빌드(지도검색 링크만).")
kw_cache, places = {}, {}
for i, d in enumerate(sorted(dishes)):
    kw = best_keyword(d)
    if kw is None:  # 인식 가능한 요리종류 없음 → 지도검색 링크만
        places[d] = {"needKey": False, "restaurants": [], "specialties": [], "links": map_links(d)}
        continue
    if kw not in kw_cache:
        kw_cache[kw] = places_for(kw)
        print(f"  [{len(kw_cache)}] '{kw}' 조회")
    pl = dict(kw_cache[kw])
    pl["links"] = map_links(d)  # 지도 링크는 실제 음식명 기준
    places[d] = pl
dump("places", places)
print(f"places {len(places)} (조회 키워드 {len(kw_cache)}종)")

print(f"\n✅ 빌드 완료 → {DIST}")
