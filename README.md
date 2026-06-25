# 유사 한식 추천 데이터 매핑 (프로토타입)

국가별 대표 음식을 고르면 **재료·맛이 비슷한 한국 음식**을 추천하는 서비스의 PoC.

## 구조
```
data/                  수집된 데이터(생성됨)
  foreign_foods.json   THEMEALDB 해외 음식 671개 (37개국)
  korean_foods.json    식품안전나라 한식 1,051개
src/
  collect_foreign.py   THEMEALDB 수집 (search.php a~z 전수)
  collect_korean.py    식품안전나라 COOKRCP01 전체 수집 + 재료 파싱
  ingredients_map.py   ★한↔영 표준 재료 사전 + 맛 프로파일 (핵심)
  recommend.py         유사도 추천 엔진 (가중 Jaccard + 맛 프로파일)
app.py                 웹 데모 (표준 라이브러리만, 추가 설치 불필요)
```

## 실행
```bash
pip install requests pandas          # 수집 단계에만 필요
python src/collect_foreign.py        # 데이터 재수집(선택)
python src/collect_korean.py
python app.py                        # → http://localhost:8000
python src/recommend.py Pizza Curry  # CLI로 바로 추천 확인
```

## 핵심 아이디어
- **언어 장벽 해결**: 영어 재료(`Soy Sauce`)와 한글 재료(`간장`)를 하나의 표준
  토큰(`soy_sauce`)으로 모아 cross-language 매칭.
- **맛 방향 반영**: 양념(고추장/간장/참기름 등)에 가중치를 둔 Jaccard +
  spicy/savory/sweet/sour/nutty… 맛 프로파일 유사도를 결합.

## 관광 연계 (한국관광공사 TourAPI)
- 추천된 한식 → 그 음식의 **맛집(음식점)·특산물(전통시장/쇼핑)** 판매처 안내
- 레시피명에서 대표 요리 종류 키워드를 뽑아 검색 (`tour_api.py`)
- 키 설정: `config.example.json` → `config.json` 으로 복사 후 `tour_api_key`에
  data.go.kr **일반 인증키(Decoding)** 입력  (또는 환경변수 `TOUR_API_KEY`)
- ⚠️ `config.json`은 개인 인증키이므로 외부 공유/업로드 금지

## 홈 — 드래그 세계 지구본
- D3 orthographic 지구본을 드래그해 회전, 데이터 보유 37개국 클릭 → 음식 선택

## 배포 (Render 무료 플랜 예시)
1. 이 저장소를 GitHub에 push
2. Render 대시보드 → **New → Blueprint** → 저장소 선택 (`render.yaml` 자동 인식)
3. 환경변수 **`TOUR_API_KEY`** 에 data.go.kr TourAPI 키 입력 → Deploy
4. 발급된 `https://k-food-match.onrender.com` 형태의 URL로 접속

> 서버는 `PORT` 환경변수를 자동으로 사용하며, 데이터(`data/*.json`)가 포함돼 있어
> 별도 수집 없이 바로 구동된다. `config.json`은 `.gitignore`로 제외되므로
> 배포 환경에서는 **환경변수 `TOUR_API_KEY`** 로 키를 주입한다.
> 한식 데이터를 재수집하려면 환경변수 `FOOD_API_KEY`(식품안전나라 키)가 필요하다.

## 다음 단계 (고도화)
- `ingredients_map.py`의 규칙 기반 맛 추출 → **OpenAI 속성 추출**로 교체
- 음식 간 관계 **그래프 허브**화
