const $ = (s) => document.querySelector(s);
const api = (p) => fetch(p).then((r) => r.json());
const ph = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1' height='1'/%3E";
const flag = (iso, cls = "flag-img") =>
  iso ? `<img class="${cls}" src="https://flagcdn.com/w80/${iso}.png" alt="">` : "🍽";

/* 이미지 + 폴백(깨지거나 없으면 그라데이션 + 이모지) */
const thumb = (src, emoji, cls) =>
  `<div class="thumb ${cls}"><span class="thumb-fb">${emoji}</span>` +
  (src ? `<img loading="lazy" src="${src}" alt="" onerror="this.remove()">` : "") + `</div>`;

/* 로딩 스켈레톤 카드 */
const skel = (n, cls) =>
  Array.from({ length: n }, () => `<div class="${cls} sk"><div class="sk-img skel"></div>
    <div class="sk-line skel"></div><div class="sk-line short skel"></div></div>`).join("");

function goStep(n) {
  document.querySelectorAll(".panel").forEach((p) => p.classList.remove("is-active"));
  $(`#panel-${n}`).classList.add("is-active");
  document.querySelectorAll(".step").forEach((s) => {
    const d = +s.dataset.step;
    s.classList.toggle("is-active", d === n);
    s.classList.toggle("is-done", d < n);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* STEP 1 — 국가 */
async function loadCountries() {
  const list = await api("/api/countries");
  window._countries = list;
  $("#country-grid").innerHTML = list
    .map(
      (c) => `<div class="country" data-id="${c.id}">
        <div class="flag">${flag(c.iso)}</div>
        <div class="ko">${c.ko}</div>
        <div class="cnt">음식 ${c.count}종</div></div>`
    )
    .join("");
  document.querySelectorAll(".country").forEach((el) =>
    el.addEventListener("click", () => {
      const c = window._countries.find((x) => x.id === el.dataset.id);
      loadFoods(c);
    })
  );
}

/* STEP 2 — 음식 */
async function loadFoods(country) {
  $("#picked-country").innerHTML = `${flag(country.iso, "flag-inline")} ${country.ko},`;
  $("#food-grid").innerHTML = skel(8, "food");
  goStep(2);
  const foods = await api("/api/foods?country=" + encodeURIComponent(country.id));
  $("#food-grid").innerHTML = foods
    .map(
      (f, i) => `<div class="food pop" data-id="${f.id}" style="animation-delay:${i * 35}ms">
        ${thumb(f.thumb, "🍽", "food-thumb")}
        <div class="label">${f.name}
          ${f.category ? `<span class="chip">${f.category}</span>` : ""}</div></div>`
    )
    .join("");
  document.querySelectorAll(".food").forEach((el) =>
    el.addEventListener("click", () => recommend(el.dataset.id))
  );
}

/* STEP 3 — 추천 */
async function recommend(id) {
  $("#source-card").innerHTML = "";
  $("#result-grid").innerHTML = skel(6, "rcard");
  goStep(3);
  const d = await api("/api/recommend?id=" + id);
  const s = d.source;
  $("#source-card").innerHTML = `<div class="source-card pop">
      ${thumb(s.thumb, "🌍", "src-thumb")}
      <div><div class="src-eyebrow">${flag(s.iso, "flag-inline")} ${s.country_ko}에서 즐겨 먹는</div>
        <div class="nm">${s.name}</div>
        <div class="tags">${s.flavors.map((t) => `<span class="tag">${t}</span>`).join("")}</div>
      </div></div>`;
  const medals = ["①", "②", "③"];
  $("#result-grid").innerHTML = d.results
    .map(
      (r, i) => `<div class="rcard pop" style="animation-delay:${i * 60}ms">
        <div class="top">
          ${thumb(r.thumb, "🍲", "r-thumb")}
          ${i < 3 ? `<div class="rank rank${i + 1}">${medals[i]} ${i + 1}위</div>` : ""}
          <div class="badge">일치 ${r.score}%</div>
        </div>
        <div class="body">
          <div class="nm">${r.name}</div>
          <div class="cat">${[r.category, r.cook_method].filter(Boolean).join(" · ") || "한식"}</div>
          <div class="bar"><i style="width:${r.score}%"></i></div>
          <div class="tags">${r.flavors.map((t) => `<span class="tag">${t}</span>`).join("")}</div>
          <div class="shared">🤝 공통 재료: <b>${r.shared.join(", ") || "맛 프로파일 유사"}</b></div>
          <button class="place-btn" data-food="${r.name}">📍 맛집 · 특산물 찾기</button>
        </div></div>`
    )
    .join("");
  document.querySelectorAll(".place-btn").forEach((b) =>
    b.addEventListener("click", () => openPlaces(b.dataset.food))
  );
}

/* 맛집·특산물 (한국관광공사 TourAPI) */
async function openPlaces(food) {
  const ov = $("#places-overlay");
  $("#places-title").textContent = `📍 "${food}" 맛집 · 특산물`;
  $("#places-body").innerHTML = `<div class="place-section">` + skel(3, "place") + `</div>`;
  ov.classList.add("is-open");
  const d = await api("/api/places?food=" + encodeURIComponent(food));
  const links = (d.links || {});
  const linkRow = `<a class="maplink" target="_blank" href="${links.naver || "#"}">네이버 지도에서 보기</a>
    <a class="maplink kakao" target="_blank" href="${links.kakao || "#"}">카카오맵에서 보기</a>`;

  if (d.needKey) {
    $("#places-body").innerHTML = `<div class="notice">
      <b>한국관광공사 TourAPI</b> 연동 준비 완료 — data.go.kr 서비스키를 등록하면
      이 음식의 <b>실제 맛집·특산물 판매처</b>가 사진·주소와 함께 표시됩니다.<br>
      지금은 아래 지도 검색으로 확인하실 수 있어요.<div>${linkRow}</div></div>`;
    return;
  }
  const section = (title, items) =>
    !items || !items.length ? "" : `<div class="place-section"><h4>${title}</h4>` +
      items.map((p) => `<div class="place pop">
        ${thumb(p.image, "🏠", "p-thumb")}
        <div><div class="pn">${p.name}</div>
          <div class="pa">📍 ${p.addr || ""}</div>
          ${p.tel ? `<div class="pt">☎ ${p.tel}</div>` : ""}</div></div>`).join("") + `</div>`;

  const html = section("🍴 이 음식을 파는 맛집", d.restaurants) +
               section("🛍 관련 특산물 · 전통시장", d.specialties);
  $("#places-body").innerHTML =
    (html || `<div class="notice">검색 결과가 적어요. 지도에서 직접 찾아보세요.</div>`) +
    `<div style="margin-top:14px">${linkRow}</div>`;
}
$("#places-close").addEventListener("click", () => $("#places-overlay").classList.remove("is-open"));
$("#places-overlay").addEventListener("click", (e) => {
  if (e.target.id === "places-overlay") $("#places-overlay").classList.remove("is-open");
});

document.querySelectorAll(".back").forEach((b) =>
  b.addEventListener("click", () => goStep(+b.dataset.to))
);

/* ── 드래그 가능한 세계 지구본 (D3 orthographic) ── */
async function initGlobe() {
  if (!window.d3 || !window.topojson) return; // CDN 미로딩 시 목록 폴백 사용
  const byGeo = new Map((window._countries || []).map((c) => [c.geo, c]));
  const world = await d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json");
  const land = topojson.feature(world, world.objects.countries).features;

  const svg = d3.select("#globe");
  const size = Math.min(560, window.innerWidth * 0.92);
  svg.attr("viewBox", `0 0 ${size} ${size}`);
  const proj = d3.geoOrthographic().scale(size / 2 - 6).translate([size / 2, size / 2]).rotate([-10, -20]);
  const path = d3.geoPath(proj);
  const tip = $("#globe-tip");

  svg.append("circle").attr("class", "sphere")
    .attr("cx", size / 2).attr("cy", size / 2).attr("r", size / 2 - 6);
  svg.append("path").attr("class", "graticule").datum(d3.geoGraticule10());

  const paths = svg.selectAll("path.land").data(land).join("path")
    .attr("class", (d) => "land" + (byGeo.has(d.properties.name) ? " has-data" : ""));

  function redraw() {
    svg.select(".graticule").attr("d", path);
    paths.attr("d", path);
  }
  redraw();

  // 데이터 보유국: 클릭 → 음식, 호버 → 툴팁
  let dragged = false;
  paths.filter((d) => byGeo.has(d.properties.name))
    .on("click", (e, d) => { if (!dragged) loadFoods(byGeo.get(d.properties.name)); })
    .on("mousemove", (e, d) => {
      const c = byGeo.get(d.properties.name);
      tip.innerHTML = `${c.ko} · 음식 ${c.count}종`;
      tip.style.left = e.offsetX + "px"; tip.style.top = e.offsetY + "px"; tip.style.opacity = 1;
    })
    .on("mouseleave", () => (tip.style.opacity = 0));

  // 드래그로 회전
  let spin = d3.timer(() => { const r = proj.rotate(); proj.rotate([r[0] + 0.18, r[1]]); redraw(); });
  svg.call(d3.drag()
    .on("start", () => { dragged = false; spin.stop(); })
    .on("drag", (e) => {
      dragged = true;
      const r = proj.rotate();
      proj.rotate([r[0] + e.dx * 0.4, r[1] - e.dy * 0.4]);
      redraw();
    })
    .on("end", () => { setTimeout(() => (dragged = false), 50); }));
}

/* 딥링크: ?country=Thai 또는 ?food=th_123 으로 특정 단계 바로 진입(캡처/공유용) */
async function init() {
  await loadCountries();
  await initGlobe();
  const q = new URLSearchParams(location.search);
  if (q.get("food")) return recommend(q.get("food"));
  if (q.get("country")) {
    const c = (window._countries || []).find((x) => x.id === q.get("country"));
    if (c) loadFoods(c);
  }
}
init();
