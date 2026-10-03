/**
 * Groundswell: watches a Google Sheet and sends a company to n8n
 * when THRESHOLD different people from the same e-mail domain have signed up.
 *
 * Works for rows from any source: Google Form, Lovable/Zapier via API, manual entry.
 * Script Properties:
 *   SHEET_ID         id of the spreadsheet (between /d/ and /edit in its URL)
 *   SHEET_NAME       optional tab name; default = first tab
 *   N8N_WEBHOOK_URL  production URL of the n8n webhook
 *   N8N_SECRET       same value as the n8n Header Auth credential "x-signal-secret"
 *   THRESHOLD        e.g. 3 (2 for testing)
 * Run installTriggers() once.
 */

const STATUS_HEADER = 'Groundswell status';
const FREEMAIL = new Set(['gmail.com', 'googlemail.com', 'gmx.de', 'gmx.net', 'web.de', 'yahoo.com', 'yahoo.de',
  'outlook.com', 'outlook.de', 'hotmail.com', 'hotmail.de', 'live.com', 'icloud.com', 'me.com', 't-online.de',
  'posteo.de', 'mailbox.org', 'proton.me', 'protonmail.com', 'aol.com', 'freenet.de']);
const MULTI = new Set(['co.uk', 'com.au', 'co.at', 'ac.uk']);

function installTriggers() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  const ss = openSheet_().getParent();
  ScriptApp.newTrigger('processNewRows').forSpreadsheet(ss).onFormSubmit().create(); // instant for Google Forms
  ScriptApp.newTrigger('processNewRows').forSpreadsheet(ss).onChange().create();     // instant for manual edits
  ScriptApp.newTrigger('processNewRows').timeBased().everyMinutes(1).create();       // catches rows written by apps/API
}

function processNewRows() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(25000)) return; // another run is busy; the next one picks up the rows
  try {
    const props = PropertiesService.getScriptProperties();
    const threshold = Number(props.getProperty('THRESHOLD') || 3);
    const sheet = openSheet_();
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) return;

    let header = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(String);
    let statusCol = header.indexOf(STATUS_HEADER);
    if (statusCol === -1) {
      statusCol = header.length;
      sheet.getRange(1, statusCol + 1).setValue(STATUS_HEADER);
      header.push(STATUS_HEADER);
    }
    const col = (re) => header.findIndex((h, i) => i !== statusCol && re.test(h));
    const c = {
      email: col(/mail/i),
      role: col(/role|rolle|position|function/i),
      city: col(/city|stadt|location|standort|\bort\b/i),
      org: col(/institution|university|universität|hochschule|company|firma|organi[sz]ation/i),
      note: col(/note|message|nachricht|comment|kommentar|help/i),
      call: col(/partner|call|meeting|termin|demo/i),
      consent: col(/consent|einwilligung|agree|zustimm|datenschutz/i),
    };
    if (c.email === -1) throw new Error('No e-mail column found in the header row.');

    const values = sheet.getRange(2, 1, lastRow - 1, header.length).getValues();
    const seen = new Map(); // domain -> Set(emails), counted in sheet order
    const valid = new Map(); // domain -> first row of each consented, distinct e-mail
    const updates = [];

    values.forEach((r, i) => {
      const email = String(r[c.email] || '').trim().toLowerCase();
      const status = String(r[statusCol] || '');
      const domain = companyDomain_(email);
      const consented = c.consent === -1 || /^(yes|ja|true|x|1|.*agree.*|.*zustimm.*)$/i.test(String(r[c.consent]).trim()) || r[c.consent] === true;

      if (!email) return;
      if (!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/.test(email)) { if (!status) updates.push([i, 'invalid e-mail']); return; }
      if (!consented) { if (!status) updates.push([i, 'no consent']); return; }
      if (!domain) { if (!status) updates.push([i, 'private e-mail']); return; }

      const set = seen.get(domain) || new Set();
      const duplicate = set.has(email);
      set.add(email);
      seen.set(domain, set);
      if (!duplicate) (valid.get(domain) || valid.set(domain, []).get(domain)).push(r);
      if (status) return; // already processed in an earlier run
      if (duplicate) { updates.push([i, 'duplicate']); return; }

      if (set.size === threshold) {
        const people = valid.get(domain);
        const pick = (k) => c[k] === -1 ? [] : people.map(x => String(x[c[k]] || '').trim()).filter(Boolean);
        const code = notifyN8n_(props, {
          email,
          city: c.city === -1 ? null : String(r[c.city] || '') || null,
          company_domain: domain,
          colleagues: set.size,
          threshold,
          colleague_emails: [...set],
          roles: pick('role'),
          notes: pick('org').map((org, k) => org + (pick('call')[k] && /yes|ja|true|x/i.test(pick('call')[k]) ? ' | wants partnership call' : ''))
            .concat(pick('note')),
          source: 'google-sheet',
          submitted_at: new Date().toISOString(),
        });
        updates.push([i, code < 300 ? 'sent to n8n ' + new Date().toISOString() : 'n8n error ' + code + ' (will retry)']);
        if (code >= 300) updates.pop(); // leave empty so the next run retries
      } else {
        updates.push([i, 'counted ' + set.size + '/' + threshold]);
      }
    });

    updates.forEach(([i, text]) => sheet.getRange(i + 2, statusCol + 1).setValue(text));
  } finally {
    lock.releaseLock();
  }
}

function notifyN8n_(props, payload) {
  const res = UrlFetchApp.fetch(props.getProperty('N8N_WEBHOOK_URL'), {
    method: 'post',
    contentType: 'application/json',
    headers: { 'x-signal-secret': props.getProperty('N8N_SECRET') },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });
  const code = res.getResponseCode();
  if (code >= 300) console.error('n8n returned ' + code + ': ' + res.getContentText());
  return code;
}

function openSheet_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('SHEET_ID');
  const ss = id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActive();
  const name = props.getProperty('SHEET_NAME');
  return name ? ss.getSheetByName(name) : ss.getSheets()[0];
}

function companyDomain_(email) {
  const host = email.split('@')[1] || '';
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(host)) return null;
  const labels = host.split('.');
  const lastTwo = labels.slice(-2).join('.');
  const reg = MULTI.has(lastTwo) && labels.length >= 3 ? labels.slice(-3).join('.') : lastTwo;
  return FREEMAIL.has(reg) ? null : reg;
}
