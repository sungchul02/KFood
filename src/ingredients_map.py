"""한↔영 재료 정규화 + 표준 재료 사전 + 맛 프로파일.

이 모듈이 프로젝트의 핵심: 영어 재료(THEMEALDB)와 한글 재료(식품안전나라)를
하나의 '표준 토큰(canonical token)'으로 모아 cross-language 매칭을 가능하게 한다.
또한 재료로부터 맛(spicy/savory/sweet/sour/herby/creamy 등) 프로파일을 추정한다.
(향후 이 단계를 OpenAI 속성 추출로 고도화할 수 있다.)
"""
import re

# ── 표준 재료 사전 ──────────────────────────────────────────────
# canonical token : [한/영 변형들(부분일치 키워드)]
CANON: dict[str, list[str]] = {
    # 단백질
    "beef":      ["소고기", "쇠고기", "우둔", "사태", "양지", "불고기", "beef", "steak", "mince"],
    "pork":      ["돼지", "삼겹", "목살", "pork", "bacon", "ham", "lardon", "chorizo"],
    "chicken":   ["닭", "계육", "chicken"],
    "egg":       ["달걀", "계란", "egg"],
    "shrimp":    ["새우", "shrimp", "prawn"],
    "fish":      ["생선", "고등어", "명태", "북어", "동태", "대구", "연어", "fish", "cod", "salmon", "tuna", "haddock"],
    "squid":     ["오징어", "낙지", "squid", "calamari", "octopus"],
    "tofu":      ["두부", "tofu"],
    # 채소
    "onion":     ["양파", "onion", "shallot", "challot"],
    "green_onion": ["대파", "쪽파", "실파", "scallion", "spring onion"],
    "garlic":    ["마늘", "garlic"],
    "ginger":    ["생강", "ginger"],
    "carrot":    ["당근", "carrot"],
    "potato":    ["감자", "potato"],
    "tomato":    ["토마토", "tomato"],
    "mushroom":  ["버섯", "표고", "느타리", "팽이", "mushroom"],
    "cabbage":   ["배추", "양배추", "cabbage"],
    "cucumber":  ["오이", "cucumber"],
    "chili":     ["고추", "홍고추", "청고추", "풋고추", "페페론", "chilli", "chili", "jalapeno", "pul biber", "cayenne", "red pepper paste"],
    "bell_pepper": ["파프리카", "피망", "bell pepper", "paprika", "capsicum"],
    "spinach":   ["시금치", "spinach"],
    "bean_sprout": ["콩나물", "숙주", "bean sprout"],
    "radish":    ["무", "radish"],
    "leek":      ["부추", "leek", "chive"],
    "perilla":   ["깻잎", "들깨", "perilla"],
    "eggplant":  ["가지", "aubergine", "eggplant"],
    # 곡물/면
    "rice":      ["쌀", "밥", "rice"],
    "flour":     ["밀가루", "부침가루", "튀김가루", "flour"],
    "noodle":    ["국수", "면", "당면", "소면", "noodle", "pasta", "spaghetti", "macaroni"],
    # 양념/맛 핵심
    "soy_sauce": ["간장", "조선간장", "저염간장", "양조간장", "soy sauce"],
    "doenjang":  ["된장", "쌈장"],
    "gochujang": ["고추장"],
    "gochugaru": ["고춧가루", "고추가루"],
    "fish_sauce": ["액젓", "멸치액젓", "까나리", "fish sauce", "anchovy"],
    "sesame_oil": ["참기름", "들기름", "sesame oil"],
    "sesame":    ["깨", "통깨", "참깨", "sesame"],
    "vinegar":   ["식초", "vinegar"],
    "sugar":     ["설탕", "올리고당", "물엿", "조청", "매실", "sugar", "syrup", "honey"],
    "salt":      ["소금", "salt"],
    "pepper":    ["후추", "후춧가루", "pepper", "peppercorn"],
    "oil":       ["식용유", "올리브", "포도씨", "카놀라", "oil"],
    "butter":    ["버터", "butter"],
    "milk":      ["우유", "milk"],
    "cream":     ["생크림", "휘핑", "cream"],
    "cheese":    ["치즈", "cheese", "mozzarella", "parmesan"],
    "yogurt":    ["요거트", "요구르트", "yogurt", "yoghurt"],
    "coconut":   ["코코넛", "coconut"],
    "curry":     ["카레", "커리", "curry", "turmeric", "cumin", "garam"],
    "herb":      ["바질", "파슬리", "고수", "민트", "로즈마리", "타임", "오레가노", "basil", "parsley", "coriander", "cilantro", "mint", "thyme", "rosemary", "oregano", "bay leaf"],
    "wine":      ["와인", "맛술", "미림", "청주", "소주", "wine", "mirin", "sake"],
    "stock":     ["육수", "다시", "stock", "broth"],
    "lemon":     ["레몬", "라임", "유자", "lemon", "lime"],
    "bean":      ["콩", "팥", "강낭", "bean", "lentil", "chickpea"],
    "corn":      ["옥수수", "corn", "maize"],
    "nut":       ["땅콩", "아몬드", "호두", "잣", "peanut", "almond", "walnut", "cashew", "pine nut"],
}

# 빠른 역색인: 키워드 → canonical (긴 키워드 우선)
_INDEX: list[tuple[str, str]] = sorted(
    ((kw.lower(), canon) for canon, kws in CANON.items() for kw in kws),
    key=lambda x: -len(x[0]),
)

# 재료가 아닌 잡음(무시)
_STOPWORDS = {"물", "water", "적당량", "약간", "조금", "기타", "고명", "양념", "소스", "재료"}

# 맛 프로파일: canonical token → 맛 태그
_FLAVOR = {
    "chili": "spicy", "gochujang": "spicy", "gochugaru": "spicy", "curry": "spicy",
    "soy_sauce": "savory", "doenjang": "savory", "fish_sauce": "savory", "stock": "savory",
    "mushroom": "savory", "cheese": "savory",
    "sugar": "sweet", "coconut": "sweet",
    "vinegar": "sour", "lemon": "sour", "yogurt": "sour",
    "sesame_oil": "nutty", "sesame": "nutty", "nut": "nutty", "perilla": "nutty",
    "cream": "creamy", "butter": "creamy", "milk": "creamy",
    "herb": "herby", "ginger": "herby",
    "garlic": "pungent", "green_onion": "pungent", "onion": "pungent",
}


def _normalize_kr(s: str) -> str:
    s = re.sub(r"\(.*?\)", "", s)          # 괄호(용량) 제거
    s = re.sub(r"[\d]+.*", "", s)          # 숫자 이후 제거
    s = re.sub(r"(적당량|약간|조금|간것|다진|채썬|송송|곱게)", "", s)
    return s.strip(" ·:[]●*\t")


def _normalize_en(s: str) -> str:
    return re.sub(r"\(.*?\)", "", s).strip().lower()


def to_canon(ingredient: str) -> str | None:
    """재료 문자열 → 표준 토큰(없으면 정규화된 원문, 잡음이면 None)."""
    raw = ingredient.strip()
    has_kr = bool(re.search(r"[가-힣]", raw))
    norm = _normalize_kr(raw) if has_kr else _normalize_en(raw)
    if not norm or norm in _STOPWORDS:
        return None
    low = norm.lower()
    for kw, canon in _INDEX:          # 부분일치(긴 키워드 우선)
        if kw in low:
            return canon
    return norm  # 사전에 없으면 정규화 원문 유지(동일 언어끼리는 매칭됨)


def canon_set(ingredients: list[str]) -> set[str]:
    out = set()
    for ing in ingredients:
        c = to_canon(ing)
        if c:
            out.add(c)
    return out


def flavor_profile(canon_tokens: set[str]) -> set[str]:
    return {_FLAVOR[t] for t in canon_tokens if t in _FLAVOR}


if __name__ == "__main__":
    # 매핑 동작 확인
    tests = ["양파(50g)", "다진 마늘", "고춧가루", "Soy Sauce", "Garlic Clove", "Olive Oil", "소금적당량"]
    for t in tests:
        print(f"{t:20s} → {to_canon(t)}")
