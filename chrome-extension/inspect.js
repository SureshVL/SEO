// Injected into the active tab to extract on-page SEO signals from the DOM.
// Runs in the page context; returns a plain-serialisable object.
function omnirankInspect() {
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const meta = (name) =>
    ($(`meta[name="${name}"]`) || $(`meta[property="${name}"]`) || {}).content || "";

  const title = document.title || "";
  const description = meta("description");
  const canonical = ($('link[rel="canonical"]') || {}).href || "";
  const robots = meta("robots");
  const viewport = meta("viewport");
  const lang = document.documentElement.getAttribute("lang") || "";

  const h1 = $$("h1").map((h) => h.textContent.trim()).filter(Boolean);
  const headings = { h1: $$("h1").length, h2: $$("h2").length, h3: $$("h3").length,
                     h4: $$("h4").length, h5: $$("h5").length, h6: $$("h6").length };

  const imgs = $$("img");
  const imgsWithAlt = imgs.filter((i) => (i.getAttribute("alt") || "").trim().length > 0);

  const host = location.hostname;
  const links = $$("a[href]");
  let internal = 0, external = 0;
  for (const a of links) {
    try {
      const u = new URL(a.href, location.href);
      if (u.protocol.startsWith("http")) (u.hostname === host ? internal++ : external++);
    } catch (e) { /* ignore */ }
  }

  const ld = $$('script[type="application/ld+json"]');
  const ldTypes = [];
  for (const s of ld) {
    try {
      const data = JSON.parse(s.textContent);
      const arr = Array.isArray(data) ? data : [data];
      for (const d of arr) {
        const t = d && (d["@type"] || (d["@graph"] && d["@graph"].map((g) => g["@type"])));
        if (t) ldTypes.push(...[].concat(t));
      }
    } catch (e) { /* malformed JSON-LD */ }
  }

  const og = { title: meta("og:title"), description: meta("og:description"),
               image: meta("og:image"), type: meta("og:type") };
  const twitter = { card: meta("twitter:card"), title: meta("twitter:title") };

  const bodyText = (document.body ? document.body.innerText : "") || "";
  const words = (bodyText.match(/\S+/g) || []).length;

  return {
    url: location.href, host, https: location.protocol === "https:",
    title, titleLen: title.length,
    description, descLen: description.length,
    canonical, robots, viewport, lang,
    h1, headings,
    images: imgs.length, imagesWithAlt: imgsWithAlt.length,
    links: links.length, internalLinks: internal, externalLinks: external,
    jsonLd: ld.length, ldTypes: [...new Set(ldTypes.filter(Boolean))].slice(0, 12),
    og, twitter, words,
  };
}
