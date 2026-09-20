const {chromium} = require('playwright');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const jsQR = require('jsqr');
const out = path.resolve(__dirname, '../docs/mashups');

(async () => {
  const browser = await chromium.launch(process.env.CHROME_CHANNEL ? {channel: process.env.CHROME_CHANNEL} : {});
  try {
    const page = await browser.newPage({viewport: {width: 1100, height: 940}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.join(out, 'index.html')).href);
    const frame = page.frameLocator('iframe');
    async function ready() {
      const revision = await page.locator('iframe').getAttribute('data-revision');
      await frame.locator(`body[data-preview-version="${revision}"]`).waitFor();
      await frame.locator('.screen').evaluate(async el => {
        await document.fonts.ready;
        if (el.offsetWidth !== 800) throw new Error('TRMNL framework did not load');
      });
    }
    for (const [name, count] of [['work', 3], ['home', 3], ['overview', 4], ['pair', 2]]) {
      await page.locator(`[data-preset=${name}]`).click();
      await ready();
      const boxes = await frame.locator('.view').evaluateAll(elements => elements.map(el => {
        const rect = el.getBoundingClientRect(), layout = el.querySelector('.layout');
        return {x: rect.x, y: rect.y, w: rect.width, h: rect.height,
          overflowX: layout.scrollWidth - layout.clientWidth,
          overflowY: layout.scrollHeight - layout.clientHeight, text: el.innerText};
      }));
      assert.equal(boxes.length, count);
      for (const b of boxes) {
        assert.ok(b.w > 300 && b.h > 200, 'Panel is too small');
        assert.ok(b.x >= 0 && b.y >= 0 && b.x + b.w <= 801 && b.y + b.h <= 481, 'Panel outside screen');
        assert.ok(b.overflowX <= 2 && b.overflowY <= 2, `Content overflow: ${JSON.stringify(b)}`);
        assert.match(b.text, /DEMO/);
        assert.doesNotMatch(b.text, /Liquid (error|syntax)|undefined/i);
      }
      for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
        const a = boxes[i], b = boxes[j];
        assert.ok(a.x + a.w <= b.x + 1 || b.x + b.w <= a.x + 1 ||
          a.y + a.h <= b.y + 1 || b.y + b.h <= a.y + 1, 'Panels overlap');
      }
      for (const canvas of await frame.locator('canvas.everyday-qr').all()) {
        const pixels = await canvas.evaluate(c => ({w: c.width, h: c.height,
          data: Array.from(c.getContext('2d').getImageData(0, 0, c.width, c.height).data)}));
        assert.equal(jsQR(new Uint8ClampedArray(pixels.data), pixels.w, pixels.h)?.data,
          'https://example.invalid/maintenance-demo');
      }
      if (process.env.UPDATE_MASHUP_SCREENSHOTS === '1') {
        await frame.locator('.screen').screenshot({path: path.join(out, `${name}.png`)});
      }
      console.log(`OK mashup ${name}: ${count} panels`);
    }
    for (const mode of ['three', 'topthree', 'four', 'pair', 'stack']) {
      await page.locator('#layout').selectOption(mode);
      await ready();
      assert.equal(await frame.locator('.view').count(), {three: 3, topthree: 3, four: 4, pair: 2, stack: 2}[mode]);
      assert.equal(await page.locator('nav button[aria-pressed=true]').count(), 0);
    }
    const ids = await page.locator('#slot-1 option').evaluateAll(options => options.map(o => o.value));
    assert.equal(ids.length, 7);
    for (const id of ids) {
      await page.locator('#slot-1').selectOption(id);
      await ready();
      const title = await frame.locator('.view').nth(1).locator('.title_bar .title').innerText();
      const expected = {workday: 'Workday Windows', outside: 'Outside Window', sales: 'Digital Product Sales',
        family: 'Family Day', shifts: 'Shift Together', homelab: 'Homelab Watch', maintenance: 'Home Maintenance'};
      assert.equal(title, expected[id]);
    }
    assert.deepEqual(errors, []);
    console.log('OK all layout and plugin selectors; no browser errors');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
