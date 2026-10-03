/**
 * Flashpoint: watches a Google Sheet and sends a company to n8n
 * when THRESHOLD different people from the same e-mail domain have signed up.
 *
 * Works for rows from any source: Google Form, Lovable/Zapier via API, manual entry.
 * Script Properties:
 *   SHEET_ID         id of the spreadsheet (between /d/ and /edit in its URL)
 *   SHEET_NAME       optional tab name; default = first tab
 *   N8N_WEBHOOK_URL  production URL of the n8n webhook
 *   N8N_SECRET       same value as the n8n Header Auth credential "x-signal-secret"
 *   THRESHOLD        e.g. 3 (2 for testing)
 * Run checkSetup() first, then installTriggers() once (it also creates the Analyses and Evals tabs).
 */

const STATUS_HEADER = 'Flashpoint status';
const FREEMAIL = new Set(['gmail.com', 'googlemail.com', 'gmx.de', 'gmx.net', 'web.de', 'yahoo.com', 'yahoo.de',
  'outlook.com', 'outlook.de', 'hotmail.com', 'hotmail.de', 'live.com', 'icloud.com', 'me.com', 't-online.de',
  'posteo.de', 'mailbox.org', 'proton.me', 'protonmail.com', 'aol.com', 'freenet.de']);
const MULTI = new Set(['co.uk', 'com.au', 'co.at', 'ac.uk']);

// Tabs the n8n workflows write to. Headers must match n8n/flashpoint.py.
const LOG_TABS = {
  Analyses: ['analysis_id', 'logged_at', 'domain', 'organisation', 'locations', 'linkedin_verified', 'colleagues', 'roles', 'score', 'decision', 'handoff_reason', 'angle', 'news_summary', 'pain_evidence', 'culture', 'structure', 'buying_committee', 'score_reasons', 'email_subject', 'email_html', 'contacts', 'evidence_urls', 'dropped_hits', 'context_json', 'model'],
  Evals: ['analysis_id', 'judged_at', 'domain', 'judge_model', 'groundedness', 'relevance', 'actionability', 'email_quality', 'compliance', 'calibration', 'llm_overall', 'rule_checks_passed', 'rule_failures', 'verdict', 'issues', 'judge_comment'],
  Signals: ['signal_id', 'found_at', 'query', 'query_origin', 'title', 'url', 'excerpt', 'event_type', 'region', 'sector', 'relevance', 'urgency', 'action', 'summary', 'affected_accounts', 'useful'],
  Outcomes: ['replied_at', 'domain', 'from', 'label', 'summary', 'subject'],
  'Watch queries': ['query', 'status', 'origin', 'added_at', 'runs', 'hits', 'relevant_hits', 'precision', 'last_run', 'note'],
};

function setupTabs() {
  const ss = openSheet_().getParent();
  Object.entries(LOG_TABS).forEach(([name, headers]) => {
    const tab = ss.getSheetByName(name) || ss.insertSheet(name);
    if (tab.getLastRow() === 0) {
      tab.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
      tab.setFrozenRows(1);
    }
    console.log('Tab ' + name + ': ready');
  });
}

// Run this first: shows which properties are set (never their values) and which columns were recognised.
function checkSetup() {
  const props = PropertiesService.getScriptProperties();
  ['SHEET_ID', 'N8N_WEBHOOK_URL', 'N8N_SECRET', 'THRESHOLD', 'SHEET_NAME'].forEach(k =>
    console.log(k + ': ' + (props.getProperty(k) ? 'set' : (k === 'SHEET_NAME' ? 'not set (uses first tab)' : 'MISSING'))));
  const sheet = openSheet_();
  console.log('Spreadsheet: ' + sheet.getParent().getName() + ' / tab: ' + sheet.getName() + ' / rows: ' + Math.max(sheet.getLastRow() - 1, 0));
  const header = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), 1)).getValues()[0].map(String);
  const find = (re) => { const i = header.findIndex(h => h !== STATUS_HEADER && re.test(h)); return i === -1 ? '(not found)' : '"' + header[i] + '"'; };
  console.log('E-mail column: ' + find(/mail/i) + '  <- required');
  console.log('Role: ' + find(/role|rolle|position|function/i) + ' | Organisation: ' + find(/institution|university|universität|hochschule|company|firma|organi[sz]ation/i));
  console.log('Call request: ' + find(/partner|call|meeting|termin|demo/i) + ' | Consent: ' + find(/consent|einwilligung|agree|zustimm|datenschutz/i) + ' | City: ' + find(/city|stadt|location|standort|\bort\b/i));
}

// Web-app endpoint for the landing page form (Deploy → Web app, execute as me, access: anyone).
// Appends the sign-up as a row, then processes the sheet right away. Body: JSON sent as text/plain.
const FORM_HEADERS = ['Timestamp', 'Name', 'Work email', 'University or institution', 'Role', 'Partnership call', 'Source'];

function doPost(e) {
  const out = (o) => ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
  let data = {};
  try { data = JSON.parse((e && e.postData && e.postData.contents) || '{}'); } catch (err) { return out({ status: 'error', message: 'Invalid request' }); }
  if (data.website) return out({ status: 'ok' }); // honeypot: bots fill it, people don't
  const token = PropertiesService.getScriptProperties().getProperty('FORM_TOKEN');
  if (token && data.token !== token) return out({ status: 'error', message: 'Invalid request' });
  const email = String(data.email || '').trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/.test(email)) return out({ status: 'error', message: 'Please enter a valid work e-mail.' });

  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sheet = openSheet_();
    if (sheet.getLastRow() === 0) sheet.appendRow(FORM_HEADERS);
    const header = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(String);
    const value = {
      timestamp: new Date(),
      name: String(data.name || '').slice(0, 120),
      email: email,
      org: String(data.institution || data.organisation || data.company || '').slice(0, 160),
      role: String(data.role || '').slice(0, 80),
      call: data.partner === true || data.partner === 'on' || data.partner === 'yes' ? 'yes' : 'no',
      source: String(data.source || 'landing-page').slice(0, 60),
    };
    const pick = (h) => /time|zeit|date/i.test(h) ? value.timestamp
      : /mail/i.test(h) ? value.email
      : /institution|university|universität|hochschule|company|firma|organi[sz]ation/i.test(h) ? value.org
      : /role|rolle|position|function/i.test(h) ? value.role
      : /partner|call|meeting|termin|demo/i.test(h) ? value.call
      : /source|quelle/i.test(h) ? value.source
      : /name/i.test(h) ? value.name
      : h === STATUS_HEADER ? '' : '';
    sheet.appendRow(header.map(pick));
  } finally {
    lock.releaseLock();
  }
  try { processNewRows(); } catch (err) { console.error(err); } // the 1-minute trigger retries if this fails
  return out({ status: 'ok' });
}

function installTriggers() {
  setupTabs();
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
      name: header.findIndex((h, i) => i !== statusCol && /name/i.test(h) && !/mail|institution|company|firma|organi|universit/i.test(h)),
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

      if (set.size === 1 || set.size === threshold) { // first sign-up starts research; critical mass escalates
        const people = valid.get(domain);
        const pick = (k) => c[k] === -1 ? [] : people.map(x => String(x[c[k]] || '').trim()).filter(Boolean);
        const code = notifyN8n_(props, {
          email,
          city: c.city === -1 ? null : String(r[c.city] || '') || null,
          company_domain: domain,
          colleagues: set.size,
          threshold,
          colleague_emails: [...set],
          signups: people.map(x => ({
            name: c.name === -1 ? '' : String(x[c.name] || '').trim(),
            email: String(x[c.email] || '').trim().toLowerCase(),
            role: c.role === -1 ? '' : String(x[c.role] || '').trim(),
          })),
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
