#!/usr/bin/env node
/**
 * Fills the Kredible universities landing page form with test sign-ups from real universities.
 *
 *   node tests/fill-form.js --dry                         show what would be submitted, send nothing
 *   node tests/fill-form.js                               2 universities reach the threshold, 3 others get 1 sign-up
 *   node tests/fill-form.js --unis tu-berlin.de,lmu.de --per 3
 *   node tests/fill-form.js --headed --slow 120           visible browser that types slowly (for the demo video)
 *
 * Options
 *   --url <url>        form page (default: https://getkredible.lovable.app/universities)
 *   --unis <domains>   comma-separated domains from the list below (default: random pick)
 *   --hot <n>          how many universities get --per sign-ups (default 2)
 *   --cold <n>         how many universities get 1 sign-up only (default 3)
 *   --per <n>          sign-ups per "hot" university (default 3 = the workflow threshold)
 *   --seed <n>         same seed = same people, so a run can be repeated
 *   --headed --slow <ms> --dry
 *
 * Addresses look like test.<first>.<last>@<university domain>. They do not exist, so run the n8n
 * workflow in TEST_MODE (agent e-mail to sign-ups disabled) while using this script.
 */
const UNIVERSITIES = [
  { domain: 'tu-berlin.de', name: 'Technische Universität Berlin' },
  { domain: 'fu-berlin.de', name: 'Freie Universität Berlin' },
  { domain: 'hu-berlin.de', name: 'Humboldt-Universität zu Berlin' },
  { domain: 'htw-berlin.de', name: 'HTW Berlin' },
  { domain: 'bht-berlin.de', name: 'Berliner Hochschule für Technik' },
  { domain: 'udk-berlin.de', name: 'Universität der Künste Berlin' },
  { domain: 'hwr-berlin.de', name: 'Hochschule für Wirtschaft und Recht Berlin' },
  { domain: 'tum.de', name: 'Technische Universität München' },
  { domain: 'lmu.de', name: 'Ludwig-Maximilians-Universität München' },
  { domain: 'rwth-aachen.de', name: 'RWTH Aachen University' },
  { domain: 'kit.edu', name: 'Karlsruher Institut für Technologie' },
  { domain: 'uni-mannheim.de', name: 'Universität Mannheim' },
  { domain: 'uni-koeln.de', name: 'Universität zu Köln' },
  { domain: 'tu-dresden.de', name: 'Technische Universität Dresden' },
  { domain: 'uni-hamburg.de', name: 'Universität Hamburg' },
  { domain: 'uni-frankfurt.de', name: 'Goethe-Universität Frankfurt' },
  { domain: 'uni-heidelberg.de', name: 'Universität Heidelberg' },
  { domain: 'uni-leipzig.de', name: 'Universität Leipzig' },
];
const FIRST = ['Anna', 'Jonas', 'Lena', 'Paul', 'Sophie', 'Felix', 'Marie', 'Lukas', 'Clara', 'David', 'Hannah', 'Tim',
               'Aylin', 'Mehmet', 'Priya', 'Jan', 'Laura', 'Niklas', 'Sara', 'Elias'];
const LAST = ['Weber', 'Richter', 'Hoffmann', 'Schmidt', 'Becker', 'Wagner', 'Klein', 'Wolf', 'Neumann', 'Krüger',
              'Yilmaz', 'Schulz', 'Braun', 'Zimmermann', 'Hartmann', 'Lange', 'Werner', 'Koch'];
const ROLES = ['International office', 'Admissions', 'Finance', 'Leadership', 'Other'];

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i === -1 ? d : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true); };
const URL_ = opt('url', 'https://getkredible.lovable.app/universities');
const PER = Number(opt('per', 3)), HOT = Number(opt('hot', 2)), COLD = Number(opt('cold', 3));
const DRY = opt('dry', false) === true, HEADED = opt('headed', false) === true, SLOW = Number(opt('slow', HEADED ? 60 : 0));

// small seeded random, so --seed reproduces the same people
let seed = Number(opt('seed', Date.now() % 100000));
const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
const pick = (xs) => xs[Math.floor(rnd() * xs.length)];
const shuffle = (xs) => xs.map(x => [rnd(), x]).sort((a, b) => a[0] - b[0]).map(x => x[1]);
const ascii = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ß/g, 'ss').toLowerCase();

function plan() {
  const chosen = opt('unis', null)
    ? String(opt('unis')).split(',').map(d => UNIVERSITIES.find(u => u.domain === d.trim()) || { domain: d.trim(), name: d.trim() })
    : shuffle(UNIVERSITIES).slice(0, HOT + COLD);
  const used = new Set();
  const people = [];
  chosen.forEach((uni, i) => {
    const n = opt('unis', null) ? PER : (i < HOT ? PER : 1);
    const roles = shuffle(ROLES.slice(0, 4));
    for (let k = 0; k < n; k++) {
      let first, last, email;
      do { first = pick(FIRST); last = pick(LAST); email = `test.${ascii(first)}.${ascii(last)}@${uni.domain}`; } while (used.has(email));
      used.add(email);
      people.push({ name: `${first} ${last}`, email, inst: uni.name, role: roles[k % roles.length], partner: k === 1 });
    }
  });
  return people;
}

(async () => {
  const people = plan();
  console.log(`${DRY ? 'DRY RUN, nothing is sent. ' : ''}${people.length} sign-ups → ${URL_}`);
  people.forEach(p => console.log(`  ${p.inst.padEnd(42)} ${p.name.padEnd(18)} ${p.role.padEnd(21)} ${p.partner ? 'partner ' : '        '}${p.email}`));
  if (DRY) return;

  const { chromium } = require('playwright');
  const browser = await chromium.launch({ headless: !HEADED, slowMo: SLOW });
  let ok = 0;
  for (const p of people) {
    const page = await browser.newPage();
    const posts = [];
    page.on('response', r => { if (r.request().method() === 'POST') posts.push(r.status()); });
    try {
      await page.goto(URL_, { waitUntil: 'networkidle' });
      await page.locator('#uni-newsletter, form').first().scrollIntoViewIfNeeded();
      await page.fill('#u-name', p.name);
      await page.fill('#u-email', p.email);
      await page.fill('#u-institution, #u-inst', p.inst);
      await page.selectOption('#u-role', { label: p.role });
      if (p.partner) await page.locator('form input[type="checkbox"]').first().check();
      await page.locator('form button[type="submit"]').first().click();
      await page.waitForTimeout(4000);
      const sent = posts.some(s => s < 400);
      ok += sent ? 1 : 0;
      console.log(`${sent ? 'sent ' : 'NO POST'} ${p.email}${posts.length ? ' (HTTP ' + posts.join(',') + ')' : ''}`);
    } catch (e) {
      console.log(`FAILED ${p.email}: ${e.message.split('\n')[0]}`);
    } finally {
      await page.close();
    }
  }
  await browser.close();
  console.log(`\n${ok}/${people.length} submitted. Watch the "Flashpoint status" column in the sheet (updates within a minute).`);
})();
