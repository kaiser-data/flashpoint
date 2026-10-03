/**
 * LunchSignal: Google Form -> n8n, instantly.
 *
 * Setup (in the Form's linked response Sheet: Extensions -> Apps Script):
 *  1. Paste this file.
 *  2. Project Settings -> Script Properties:
 *       N8N_WEBHOOK_URL = production URL of the n8n Webhook node "Form sign-up"
 *       N8N_SECRET      = any long random string (same value in the n8n Header Auth credential "x-lunchsignal-secret")
 *  3. Run installTrigger() once and grant access.
 *
 * Every response is sent. n8n decides (IF colleagues == 5). The sheet stays the record of all responses.
 */

const THRESHOLD = 5;
const FREEMAIL = new Set(['gmail.com', 'googlemail.com', 'gmx.de', 'gmx.net', 'web.de', 'yahoo.com', 'yahoo.de',
  'outlook.com', 'outlook.de', 'hotmail.com', 'hotmail.de', 'live.com', 'icloud.com', 'me.com', 't-online.de',
  'posteo.de', 'mailbox.org', 'proton.me', 'protonmail.com', 'aol.com', 'freenet.de']);
const MULTI = new Set(['co.uk', 'com.au', 'co.at', 'ac.uk']);

function installTrigger() {
  const ss = SpreadsheetApp.getActive();
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'onFormSubmit')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('onFormSubmit').forSpreadsheet(ss).onFormSubmit().create();
}

function companyDomain(email) {
  const host = String(email || '').trim().toLowerCase().split('@')[1] || '';
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(host)) return null;
  const labels = host.split('.');
  const lastTwo = labels.slice(-2).join('.');
  const reg = MULTI.has(lastTwo) && labels.length >= 3 ? labels.slice(-3).join('.') : lastTwo;
  return FREEMAIL.has(reg) ? null : reg;
}

function onFormSubmit(e) {
  const values = e.namedValues; // { "Work email": ["a@b.de"], ... }
  const emailKey = Object.keys(values).find(k => /mail/i.test(k));
  const cityKey = Object.keys(values).find(k => /city|stadt|office/i.test(k));
  const email = String(values[emailKey][0]).trim().toLowerCase();
  const domain = companyDomain(email);

  // Distinct e-mails from the same company, counted over the whole response sheet.
  const sheet = e.range.getSheet();
  const header = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const col = header.findIndex(h => /mail/i.test(h));
  const all = sheet.getRange(2, col + 1, Math.max(sheet.getLastRow() - 1, 1), 1).getValues()
    .map(r => String(r[0]).trim().toLowerCase()).filter(Boolean);
  const colleagues = domain ? [...new Set(all.filter(a => companyDomain(a) === domain))] : [];

  const payload = {
    email,
    city: cityKey ? values[cityKey][0] : null,
    company_domain: domain,
    colleagues: colleagues.length,
    threshold: THRESHOLD,
    // Consented sign-ups only, and only once the company qualifies.
    colleague_emails: colleagues.length >= THRESHOLD ? colleagues : [],
    submitted_at: new Date().toISOString(),
  };

  const props = PropertiesService.getScriptProperties();
  UrlFetchApp.fetch(props.getProperty('N8N_WEBHOOK_URL'), {
    method: 'post',
    contentType: 'application/json',
    headers: { 'x-lunchsignal-secret': props.getProperty('N8N_SECRET') },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });
}
