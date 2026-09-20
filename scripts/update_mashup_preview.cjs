// Refresh synthetic snapshots from built sibling plugin repositories.
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const assert = require('node:assert/strict');
const out = path.resolve(__dirname, '../docs/mashups');
const siblings = path.resolve(__dirname, '../..');

(async () => {
  const file = path.join(out, 'index.html');
  const html = fs.readFileSync(file, 'utf8');
  const marker = /(<script type="application\/json" id="data">)([\s\S]*?)(<\/script>)/;
  assert.ok(marker.test(html), 'Snapshot data block missing');
  const data = JSON.parse(html.match(marker)[2]);
  const provenance = {description: 'Synthetic demo HTML snapshots from the standalone plugin builds. No private data.', plugins: {}};
  const browser = await chromium.launch(process.env.CHROME_CHANNEL ? {channel: process.env.CHROME_CHANNEL} : {});
  try {
    const page = await browser.newPage();
    for (const [id, [repo]] of Object.entries(data.plugins)) {
      const source = path.join(siblings, repo);
      const views = ['half_vertical', 'half_horizontal', 'quadrant'];
      for (const view of views) {
        const raw = fs.readFileSync(path.join(source, '_build', `${view}.html`), 'utf8');
        const fragment = await page.evaluate(({raw, view}) => {
          const doc = new DOMParser().parseFromString(raw, 'text/html');
          const panel = doc.querySelector(`.view--${view}`);
          if (!panel || !panel.querySelector('.label--inverted')?.textContent.includes('DEMO')) {
            throw new Error('Only generated DEMO views may be published');
          }
          return {head: doc.head.innerHTML, body: panel.outerHTML};
        }, {raw, view});
        data.head = fragment.head;
        data.fragments[id][view] = fragment.body;
      }
      provenance.plugins[repo] = {repository: `https://github.com/JirakJ/${repo}`,
        commit: execFileSync('git', ['-C', source, 'rev-parse', 'HEAD'], {encoding: 'utf8'}).trim(), views};
    }
    const payload = JSON.stringify(data).replaceAll('<', '\\u003c');
    fs.writeFileSync(file, html.replace(marker, (_, open, old, close) => open + payload + close));
    fs.writeFileSync(path.join(out, 'sources.json'), JSON.stringify(provenance, null, 2) + '\n');
    console.log('Updated seven plugin snapshots. Run check:mashups and review before publishing.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
