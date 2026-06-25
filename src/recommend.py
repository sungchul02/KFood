"""유사 한식 추천 엔진.

해외 음식(또는 임의 재료셋)을 받아, 표준 재료 토큰 + 맛 프로파일 유사도로
가장 가까운 한식을 추천한다.

유사도 = 0.7 * (재료 가중 Jaccard) + 0.3 * (맛 프로파일 Jaccard)
재료 가중: 양념/맛 핵심 토큰에 가중치를 둬서 '맛의 방향'이 비슷한 음식을 우대.
"""
import json
from pathlib import Path

from ingredients_map import canon_set, flavor_profile

DATA = Path(__file__).resolve().parent.parent / "data"

# 맛을 좌우하는 핵심 재료에 가중치
WEIGHTS = {
    "chili": 2.5, "gochujang": 2.5, "gochugaru": 2.5, "soy_sauce": 2.0,
    "doenjang": 2.0, "fish_sauce": 2.0, "sesame_oil": 1.8, "curry": 2.0,
    "cheese": 1.5, "cream": 1.5, "garlic": 1.3, "ginger": 1.3, "vinegar": 1.5,
}
DEFAULT_W = 1.0


def _w(token: str) -> float:
    return WEIGHTS.get(token, DEFAULT_W)


def weighted_jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = sum(_w(t) for t in a & b)
    union = sum(_w(t) for t in a | b)
    return inter / union if union else 0.0


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class Recommender:
    def __init__(self):
        self.korean = json.loads((DATA / "korean_foods.json").read_text("utf-8"))
        self.foreign = json.loads((DATA / "foreign_foods.json").read_text("utf-8"))
        for f in self.korean + self.foreign:
            f["_canon"] = canon_set(f["ingredients"])
            f["_flavor"] = flavor_profile(f["_canon"])
        # 빈 재료 한식 제외
        self.korean = [f for f in self.korean if f["_canon"]]

    def recommend_by_ingredients(self, canon: set[str], flavor: set[str], top=5):
        scored = []
        for k in self.korean:
            ing_sim = weighted_jaccard(canon, k["_canon"])
            fla_sim = jaccard(flavor, k["_flavor"])
            score = 0.7 * ing_sim + 0.3 * fla_sim
            if score > 0:
                scored.append((score, ing_sim, fla_sim, k))
        scored.sort(key=lambda x: -x[0])
        return scored[:top]

    def recommend_for_foreign(self, name: str, top=5):
        src = next((f for f in self.foreign
                    if f["name"].lower() == name.lower()), None)
        if not src:
            cand = [f for f in self.foreign if name.lower() in f["name"].lower()]
            if not cand:
                return None, []
            src = cand[0]
        return src, self.recommend_by_ingredients(src["_canon"], src["_flavor"], top)

    def list_by_country(self, country: str):
        return [f for f in self.foreign if f["country"].lower() == country.lower()]


def _fmt(src, results):
    shared = lambda k: ", ".join(sorted(src["_canon"] & k["_canon"])) or "-"
    lines = [f"\n🍽  [{src['country']}] {src['name']}",
             f"    재료토큰: {', '.join(sorted(src['_canon']))}",
             f"    맛: {', '.join(sorted(src['_flavor'])) or '-'}",
             "  → 유사 한식 추천:"]
    for i, (score, ing, fla, k) in enumerate(results, 1):
        lines.append(f"   {i}. {k['name']}  (유사도 {score:.2f} | 재료 {ing:.2f}, 맛 {fla:.2f})")
        lines.append(f"        공통재료: {shared(k)}  | 맛: {', '.join(sorted(k['_flavor'])) or '-'}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    rec = Recommender()
    print(f"로드: 한식 {len(rec.korean)}개 / 해외 {len(rec.foreign)}개")
    queries = sys.argv[1:] or ["Pizza", "Lasagne", "Sushi", "Curry", "Tacos", "Paella"]
    for q in queries:
        src, results = rec.recommend_for_foreign(q)
        if not src:
            print(f"\n❌ '{q}' 해당 해외 음식 없음")
            continue
        print(_fmt(src, results))
