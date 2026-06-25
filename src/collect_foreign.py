"""해외 음식 수집 — THEMEALDB.

search.php?f=<a-z> 를 모두 호출하면 DB 전체 음식을 '재료 포함' 풀데이터로 받을 수 있다.
(filter.php는 재료를 안 주므로 letter 검색이 더 효율적이다.)
"""
import json
import requests
from pathlib import Path

BASE = "https://www.themealdb.com/api/json/v1/1"
OUT = Path(__file__).resolve().parent.parent / "data" / "foreign_foods.json"


def extract_ingredients(meal: dict) -> list[str]:
    out = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}")
        if ing and ing.strip():
            out.append(ing.strip())
    return out


def fetch_all() -> list[dict]:
    seen = {}
    for c in "abcdefghijklmnopqrstuvwxyz":
        meals = requests.get(f"{BASE}/search.php?f={c}", timeout=30).json().get("meals")
        if not meals:
            continue
        for m in meals:
            mid = m["idMeal"]
            if mid in seen:
                continue
            seen[mid] = {
                "id": f"th_{mid}",
                "name": m["strMeal"],
                "source": "foreign",
                "country": m.get("strArea") or "",
                "category": m.get("strCategory") or "",
                "ingredients": extract_ingredients(m),
                "thumb": m.get("strMealThumb") or "",
            }
        print(f"  '{c}': 누적 {len(seen)}개")
    return list(seen.values())


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    foods = fetch_all()
    OUT.write_text(json.dumps(foods, ensure_ascii=False, indent=2), encoding="utf-8")
    # 국가별 분포
    from collections import Counter
    dist = Counter(f["country"] for f in foods)
    print(f"\n저장 완료: {OUT}  ({len(foods)}개)")
    print("국가 수:", len(dist))
    print("상위 국가:", dist.most_common(10))
