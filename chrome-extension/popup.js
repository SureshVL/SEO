/* global omnirankInspect, chrome */
const scoreEl = document.getElementById("scoreBadge");
const metaEl = document.getElementById("meta");
const checksEl = document.getElementById("checks");

const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function scored(status) { return status === "ok" ? 1 : status === "warn" ? 0.5 : 0; }

function buildChecks(d) {
  const checks = [];
  const add = (label, status, val, weight = 1) => checks.push({ label, status, val, weight });

  add("Title tag",
    !d.title ? "bad" : d.titleLen >= 30 && d.titleLen <= 60 ? "ok" : "warn",
    d.title ? `<b>${d.titleLen} chars</b> — ${esc(d.title)}` : "Missing", 2);

  add("Meta description",
    !d.description ? "bad" : d.descLen >= 120 && d.descLen <= 160 ? "ok" : "warn",
    d.description ? `<b>${d.descLen} chars</b> — ${esc(d.description.slice(0, 120))}` : "Missing", 2);

  add("H1 heading",
    d.headings.h1 === 1 ? "ok" : d.headings.h1 === 0 ? "bad" : "warn",
    d.headings.h1 === 1 ? `<b>1</b> — ${esc(d.h1[0] || "")}` :
      d.headings.h1 === 0 ? "No H1 on page" : `<b>${d.headings.h1}</b> H1s (use one)`, 2);

  add("Canonical", d.canonical ? "ok" : "warn",
    d.canonical ? esc(d.canonical) : "No canonical tag");

  add("Mobile viewport", d.viewport ? "ok" : "bad",
    d.viewport ? "Present" : "Missing viewport meta");

  add("HTTPS", d.https ? "ok" : "bad", d.https ? "Secure" : "Not served over HTTPS");

  add("Language", d.lang ? "ok" : "warn", d.lang ? `<b>${esc(d.lang)}</b>` : "No lang attribute");

  const altPct = d.images ? Math.round((d.imagesWithAlt / d.images) * 100) : 100;
  add("Image alt text",
    d.images === 0 ? "ok" : altPct === 100 ? "ok" : altPct >= 60 ? "warn" : "bad",
    d.images === 0 ? "No images" : `<b>${altPct}%</b> — ${d.imagesWithAlt}/${d.images} have alt`);

  add("Structured data", d.jsonLd ? "ok" : "warn",
    d.jsonLd ? `<b>${d.jsonLd}</b> JSON-LD block(s)` + (d.ldTypes.length
      ? `<div class="chips">${d.ldTypes.map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div>` : "")
      : "No JSON-LD schema");

  add("Open Graph", d.og.title ? "ok" : "warn",
    d.og.title ? "og:title present" : "No Open Graph tags");

  add("Indexability", /noindex/i.test(d.robots) ? "bad" : "ok",
    /noindex/i.test(d.robots) ? "⚠ noindex — blocked from search" : "Indexable" +
      (d.robots ? ` (robots: ${esc(d.robots)})` : ""));

  add("Content",
    d.words >= 300 ? "ok" : d.words >= 100 ? "warn" : "bad",
    `<b>${d.words.toLocaleString()}</b> words`);

  return checks;
}

function render(d) {
  const checks = buildChecks(d);
  const total = checks.reduce((s, c) => s + c.weight, 0);
  const got = checks.reduce((s, c) => s + scored(c.status) * c.weight, 0);
  const score = Math.round((got / total) * 100);

  scoreEl.textContent = score;
  scoreEl.className = "score " + (score >= 80 ? "ok" : score >= 50 ? "warn" : "bad");

  metaEl.innerHTML =
    `<b>${esc(d.host)}</b>` +
    `<div class="grid">` +
    ["h1", "h2", "h3", "h4", "h5", "h6"].map((h) =>
      `<div class="cell"><b>${d.headings[h]}</b><span>${h.toUpperCase()}</span></div>`).join("") +
    `</div>` +
    `<div class="grid" style="grid-template-columns:repeat(3,1fr);margin-top:4px">` +
    `<div class="cell"><b>${d.internalLinks}</b><span>internal</span></div>` +
    `<div class="cell"><b>${d.externalLinks}</b><span>external</span></div>` +
    `<div class="cell"><b>${d.images}</b><span>images</span></div>` +
    `</div>`;

  checksEl.innerHTML = checks.map((c) =>
    `<div class="check"><span class="dot ${c.status}"></span>` +
    `<div><div class="label">${esc(c.label)}</div><div class="val">${c.val}</div></div></div>`).join("");
}

async function main() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !/^https?:/.test(tab.url || "")) {
    checksEl.innerHTML = '<div class="loading">Open a normal web page (http/https) to inspect it.</div>';
    return;
  }
  try {
    const [res] = await chrome.scripting.executeScript({
      target: { tabId: tab.id }, func: omnirankInspect,
    });
    if (res && res.result) render(res.result);
    else throw new Error("no result");
  } catch (e) {
    checksEl.innerHTML =
      '<div class="loading">Can\'t inspect this page (browser/internal page or blocked by the site).</div>';
  }
}

main();
