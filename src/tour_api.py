"""관광 공공데이터 연동 — 한국관광공사 TourAPI (data.go.kr).

추천된 한식을 '어디서 먹고/살 수 있는지' 안내한다.
  - 음식점(contentTypeId=39): 해당 음식 키워드로 맛집 검색
  - 쇼핑/특산물(contentTypeId=38): 전통시장·특산물 판매처 검색

서비스키는 사용자가 data.go.kr에서 발급받아야 한다.
  · 환경변수 TOUR_API_KEY  또는  프로젝트 루트의 config.json {"tour_api_key": "..."}
키가 없으면 needKey=True 와 지도검색 링크를 반환한다(허위 데이터 생성 안 함).
"""
import json
import os
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://apis.data.go.kr/B551011/KorService2"


# 관광 데이터(맛집)에 실제로 존재하는 대표 요리 종류 키워드 (긴 것 우선 매칭)
DISH_TYPES = [
    "순두부찌개", "김치찌개", "된장찌개", "부대찌개", "콩나물국밥", "설렁탕", "갈비탕",
    "삼계탕", "감자탕", "칼국수", "수제비", "비빔밥", "볶음밥", "김치볶음밥", "떡볶이",
    "순대국", "돼지국밥", "소머리국밥", "보쌈", "족발", "삼겹살", "불고기", "갈비",
    "곱창", "막창", "닭갈비", "찜닭", "찜", "국밥", "찌개", "전골", "백반", "한정식",
    "냉면", "막국수", "국수", "만두", "꼬치", "구이", "회", "초밥", "물회", "해물탕",
    "아구찜", "낙지", "주꾸미", "장어", "추어탕", "메기", "새우", "굴", "전복",
    "파스타", "피자", "스테이크", "카레", "쌀국수", "짜장면", "짬뽕", "탕수육", "마라탕",
    "김밥", "라면", "우동", "돈까스", "튀김", "전", "죽", "샐러드", "샌드위치", "버거",
    "깍두기", "김치", "잡채", "탕", "국",
]


def tour_keyword(name: str) -> list[str]:
    """레시피명에서 관광 검색에 쓸 대표 키워드 후보(우선순위 순)."""
    cands = []
    for d in DISH_TYPES:               # 음식명에 포함된 요리 종류(긴 것 우선)
        if d in name and d not in cands:
            cands.append(d)
    # 그래도 없으면 마지막 어절(예: '바지락 볶음면'→'볶음면')
    last = name.split()[-1] if " " in name else name
    if last not in cands:
        cands.append(last)
    return cands[:4]


def get_key() -> str | None:
    key = os.environ.get("TOUR_API_KEY")
    if key:
        return key.strip()
    cfg = ROOT / "config.json"
    if cfg.exists():
        try:
            return json.loads(cfg.read_text("utf-8")).get("tour_api_key", "").strip() or None
        except Exception:
            return None
    return None


_SEARCH_CACHE: dict = {}


def _search(keyword: str, content_type_id: int, rows: int = 6) -> list[dict]:
    ck = (keyword, content_type_id, rows)
    if ck in _SEARCH_CACHE:
        return _SEARCH_CACHE[ck]
    key = get_key()
    params = {
        "serviceKey": key, "MobileOS": "ETC", "MobileApp": "KFoodMatch",
        "_type": "json", "arrange": "O",
        "keyword": keyword, "contentTypeId": content_type_id,
        "numOfRows": rows, "pageNo": 1,
    }
    r = requests.get(f"{BASE}/searchKeyword2", params=params, timeout=15)
    resp = r.json().get("response", {})
    if resp.get("header", {}).get("resultCode") != "0000":
        _SEARCH_CACHE[ck] = []
        return []
    body = resp.get("body", {})
    items = body.get("items")
    if not items or items == "":
        _SEARCH_CACHE[ck] = []
        return []
    rows_ = items["item"]
    if isinstance(rows_, dict):
        rows_ = [rows_]
    out = []
    for it in rows_:
        out.append({
            "name": it.get("title", ""),
            "addr": it.get("addr1", ""),
            "image": it.get("firstimage") or it.get("firstimage2") or "",
            "mapx": it.get("mapx"), "mapy": it.get("mapy"),
            "tel": it.get("tel", ""),
        })
    _SEARCH_CACHE[ck] = out
    return out


def map_links(keyword: str) -> dict:
    q = quote(keyword)
    return {
        "naver": f"https://map.naver.com/p/search/{q} 맛집",
        "kakao": f"https://map.kakao.com/?q={q} 맛집",
    }


def _search_first(candidates: list[str], content_type_id: int):
    """후보 키워드를 순서대로 검색해 결과가 나오는 첫 키워드 사용."""
    for kw in candidates:
        rows = _search(kw, content_type_id)
        if rows:
            return rows, kw
    return [], candidates[0] if candidates else ""


def places_for(food_name: str) -> dict:
    """추천 한식 이름으로 맛집/특산물 판매처 조회."""
    if not get_key():
        return {"needKey": True, "links": map_links(food_name)}
    try:
        cands = tour_keyword(food_name)
        restaurants, used = _search_first(cands, 39)
        specialties, _ = _search_first(cands, 38)
        return {"needKey": False, "keyword": used, "candidates": cands,
                "restaurants": restaurants, "specialties": specialties,
                "links": map_links(used or food_name)}
    except Exception as e:
        return {"error": str(e), "links": map_links(food_name)}


if __name__ == "__main__":
    import sys
    print("키 설정됨:", bool(get_key()))
    print(json.dumps(places_for(sys.argv[1] if len(sys.argv) > 1 else "불고기"),
                     ensure_ascii=False, indent=2))
