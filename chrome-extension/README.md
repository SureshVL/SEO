# OMNI-RANK SEO Inspector — Chrome Extension

A one-click on-page SEO inspector (Manifest V3). Click the toolbar icon on any
page to get a live SEO score plus pass/warn/fail checks — no login, no backend,
everything runs locally in your browser.

## What it checks
- Title tag (presence + length)
- Meta description (presence + length)
- H1 (exactly one) and the full H1–H6 outline
- Canonical tag · mobile viewport · HTTPS · `lang` attribute
- Image `alt`-text coverage
- Structured data (JSON-LD blocks + detected types)
- Open Graph tags
- Indexability (`robots` `noindex`)
- Word count · internal vs external link counts

Each check is scored (pass = 1, warning = ½, fail = 0, weighted) into a 0–100
page score.

## Load it (unpacked, for development)
1. Open **`chrome://extensions`**
2. Turn on **Developer mode** (top-right)
3. Click **Load unpacked** and select this `chrome-extension/` folder
4. Pin the extension, open any website, and click the icon

## Files
| File | Role |
|------|------|
| `manifest.json` | MV3 manifest (`activeTab` + `scripting` permissions only) |
| `inspect.js` | DOM extractor injected into the active tab |
| `popup.html` / `popup.css` / `popup.js` | the popup UI, scoring and rendering |
| `icons/` | 16 / 48 / 128 px icons |

## Privacy
No data leaves the browser. The extension reads the current tab's DOM only when
you open the popup, and does not make any network requests.

## Publishing
To ship on the Chrome Web Store: zip the contents of this folder, create a
developer account, and upload via the Web Store dashboard. Replace the generated
gradient icons with branded artwork first.
