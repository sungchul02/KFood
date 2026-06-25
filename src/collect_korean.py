"""한식 레시피 수집 — 식품안전나라 COOKRCP01 (전체 ~1,146개).

음식명, 조리방식, 재료원문, 카테고리, 영양정보, 썸네일을 저장한다.
"""
import json
import os
import re
import requests
from pathlib import Path

# 식품안전나라 인증키 — 공개 데이터용. 환경변수로 덮어쓸 수 있다.
API_KEY = os.environ.get("FOOD_API_KEY", "sample_key")
BASE = "https://openapi.foodsafetykorea.go.kr/api"
OUT = Path(__file__).resolve().parent.parent / "data" / "korean_foods.json"


def parse_ingredients(text: str) -> list[str]:
    """RCP_PARTS_DTLS 원문에서 재료명만 추출(용량/구획어 제거)."""
    if not text:
        return []
    text = text.replace("\n", ",")
    out = []
    for p in text.split(","):
        ing = re.sub(r"\d+.*", "", p)          # 숫자(용량) 이후 제거
        ing = ing.strip(" ·:[]●*\t")
        # 구획어/섹션 헤더 제거
        if "양념" in ing or "소스" in ing or "고명" in ing or "재료" in ing:
            # '양념장 : 저염간장' → 콜론 뒤만 남김
            if ":" in ing:
                ing = ing.split(":")[-1].strip()
            else:
                continue
        ing = ing.strip()
        if 1 < len(ing) < 12:
            out.append(ing)
    # 중복 제거(순서 유지)
    return list(dict.fromkeys(out))


def fetch_all() -> list[dict]:
    # 총개수 먼저 확인
    head = requests.get(f"{BASE}/{API_KEY}/COOKRCP01/json/1/1", timeout=30).json()
    total = int(head["COOKRCP01"]["total_count"])
    print(f"총 한식 레시피: {total}")

    rows = []
    step = 100
    for start in range(1, total + 1, step):
        end = min(start + step - 1, total)
        url = f"{BASE}/{API_KEY}/COOKRCP01/json/{start}/{end}"
        chunk = requests.get(url, timeout=60).json()["COOKRCP01"].get("row", [])
        rows.extend(chunk)
        print(f"  {start}-{end}: {len(chunk)}개 (누적 {len(rows)})")

    foods = []
    for r in rows:
        foods.append({
            "id": f"kr_{r.get('RCP_SEQ')}",
            "name": (r.get("RCP_NM") or "").strip(),
            "source": "korean",
            "category": r.get("RCP_PAT2") or "",       # 반찬/국/밥 등
            "cook_method": r.get("RCP_WAY2") or "",     # 찌기/볶기 등
            "ingredients_raw": r.get("RCP_PARTS_DTLS") or "",
            "ingredients": parse_ingredients(r.get("RCP_PARTS_DTLS") or ""),
            "hashtag": r.get("HASH_TAG") or "",
            "thumb": r.get("ATT_FILE_NO_MAIN") or r.get("ATT_FILE_NO_MK") or "",
            "nutrition": {
                "kcal": r.get("INFO_ENG"), "carb": r.get("INFO_CAR"),
                "protein": r.get("INFO_PRO"), "fat": r.get("INFO_FAT"),
                "sodium": r.get("INFO_NA"),
            },
        })
    return foods


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    foods = [f for f in fetch_all() if f["name"]]
    OUT.write_text(json.dumps(foods, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장 완료: {OUT}  ({len(foods)}개)")
    print("예시:", foods[0]["name"], "→", foods[0]["ingredients"])
