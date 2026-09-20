// Exercise the real HTTP service and decode a live, locally generated QR.
const { chromium } = require('playwright');
const jsQR = require('jsqr');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { spawn, execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const python = process.env.PYTHON || 'python3';

(async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'trmnl-maintenance-'));
  let server, browser;
  try {
    const probe = net.createServer();
    await new Promise(resolve => probe.listen(0, '127.0.0.1', resolve));
    const port = probe.address().port;
    await new Promise(resolve => probe.close(resolve));
    const config = path.join(directory, 'config.json');
    fs.writeFileSync(config, JSON.stringify({timezone: 'UTC', state_file: 'state.sqlite3',
      confirmation_base_url: `http://127.0.0.1:${port}`, allow_http: true,
      tasks: [{id: 'demo-filter', name: 'Example ventilation filter', last_done: '2026-01-01', interval_days: 30}]
    }), {mode: 0o600});
    const collect = () => JSON.parse(execFileSync(python, ['-m', 'everyday', 'maintenance', '--config', config], {cwd: root, encoding: 'utf8'}));
    const data = collect(), size = data.qr_size, stride = Math.ceil(size / 4), scale = 4;
    const pixels = new Uint8ClampedArray(size * scale * size * scale * 4).fill(255);
    for (let y = 0; y < size; y++) {
      const row = BigInt('0x' + data.qr_bits.slice(y * stride, (y + 1) * stride));
      for (let x = 0; x < size; x++) if ((row >> BigInt(size - 1 - x)) & 1n) {
        for (let dy = 0; dy < scale; dy++) for (let dx = 0; dx < scale; dx++) {
          const offset = ((y * scale + dy) * size * scale + x * scale + dx) * 4;
          pixels[offset] = pixels[offset + 1] = pixels[offset + 2] = 0;
        }
      }
    }
    const decoded = jsQR(pixels, size * scale, size * scale);
    assert.ok(decoded?.data.startsWith(`http://127.0.0.1:${port}/complete/`));
    server = spawn(python, ['-m', 'everyday.maintenance_server', '--config', config, '--port', String(port)], {cwd: root, stdio: 'ignore'});
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      try { if ((await fetch(decoded.data)).ok) { ready = true; break; } } catch {}
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert.ok(ready, 'confirmation service did not start');
    browser = await chromium.launch(process.env.CHROME_CHANNEL ? {channel: process.env.CHROME_CHANNEL} : {});
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    await page.goto(decoded.data);
    assert.equal(await page.getByRole('heading', {name: 'Example ventilation filter'}).count(), 1);
    const count = execFileSync(python, ['-c', 'import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute("SELECT COUNT(*) FROM completed").fetchone()[0])', path.join(directory, 'state.sqlite3')], {encoding: 'utf8'});
    assert.equal(count.trim(), '0', 'GET must not complete a task');
    await page.screenshot({path: path.join(root, 'docs/previews/maintenance-confirmation.png')});
    const postResponse = page.waitForResponse(response => response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Mark completed today'}).click();
    const submitted = await postResponse;
    assert.equal(submitted.status(), 303, `confirmation POST must succeed (origin: ${submitted.request().headers().origin || 'absent'})`);
    await page.waitForURL(`http://127.0.0.1:${port}/saved`);
    assert.match(await page.locator('main').innerText(), /Saved/);
    assert.equal((await page.goto(decoded.data)).status(), 410, 'old QR must be invalid after completion');
    assert.equal(collect().rows[0].time, 'In 30d');
    console.log('OK maintenance: live QR, read-only GET, browser confirmation, persisted date, invalidated link');
  } finally {
    if (browser) await browser.close();
    if (server && server.exitCode === null) {
      server.kill('SIGTERM');
      await new Promise(resolve => server.once('exit', resolve));
    }
    fs.rmSync(directory, {recursive: true, force: true});
  }
})().catch(error => { console.error(error.message); process.exit(1); });
