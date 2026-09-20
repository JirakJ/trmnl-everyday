// Optional visual regression check: npm ci && npx playwright install chromium.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');

(async () => {
  const browser = await chromium.launch(process.env.CHROME_CHANNEL ? {channel: process.env.CHROME_CHANNEL} : {});
  try {
    const page = await browser.newPage({viewport: {width: 800, height: 480}});
    const slugs = process.argv[2] ? [process.argv[2]] : fs.readdirSync(path.join(root, 'plugins'));
    for (const slug of slugs) {
      for (const view of ['full', 'half_horizontal', 'half_vertical', 'quadrant']) {
        const errors = [];
        const onError = e => errors.push(e.message);
        page.on('pageerror', onError);
        await page.goto(pathToFileURL(path.join(root, 'plugins', slug, '_build', `${view}.html`)).href, {waitUntil: 'domcontentloaded'});
        await page.waitForFunction(() => document.querySelector('.screen').offsetWidth === 800);
        await page.evaluate(() => document.fonts.ready);
        const bounds = await page.locator(`.view--${view}`).first().evaluate(el => {
          const layout = el.querySelector('.layout');
          const rect = el.getBoundingClientRect();
          const footer = el.querySelector('.title_bar').getBoundingClientRect();
          return {text: el.innerText, overflowX: layout.scrollWidth - layout.clientWidth,
            overflowY: layout.scrollHeight - layout.clientHeight,
            footerOutside: footer.bottom - rect.bottom};
        });
        assert.match(bounds.text, /DEMO/, `${slug}/${view}: demo label absent`);
        assert.doesNotMatch(bounds.text, /Liquid (error|syntax)|undefined/i);
        assert.ok(bounds.overflowX <= 2, `${slug}/${view}: horizontal overflow ${bounds.overflowX}`);
        assert.ok(bounds.overflowY <= 2, `${slug}/${view}: vertical overflow ${bounds.overflowY}`);
        assert.ok(bounds.footerOutside <= 2, `${slug}/${view}: footer outside screen`);
        assert.deepEqual(errors, [], `${slug}/${view}: browser errors`);
        const out = path.join(root, 'docs', 'previews');
        fs.mkdirSync(out, {recursive: true});
        if (view === 'full') await page.screenshot({path: path.join(out, `${slug}.png`)});
        page.off('pageerror', onError);
        console.log(`OK ${slug}/${view}`);
      }
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exit(1); });
