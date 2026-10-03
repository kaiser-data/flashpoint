/**
 * Groundswell: landing page form -> Google Sheet -> n8n
 * Script Properties: N8N_WEBHOOK_URL, N8N_SECRET, THRESHOLD (e.g. 5), FORM_TOKEN (optional)
 */
const SHEET_NAME = 'Signups';
const HEADERS = ['Timestamp', 'Email', 'Company domain', 'Role', 'City', 'Note', 'Consent', 'Source'];
const FREEMAIL = new Set(['gmail.com', 'googlemail.com', 'gmx.de', 'gmx.net', 'web.de', 'yahoo.com', 'yahoo.de',
  'outlook.com', 'outlook.de', 'hotmail.com', 'hotmail.de', 'live.com', 'icloud.com', 'me.com', 't-online.de',
  'posteo.de', 'mailbox.org', 'proton.me', 'protonmail.com', 'aol.com', 'freenet.de']);
const MULTI = new Set(['co.uk', 'com.au', 'co.at', 'ac.uk']);

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000); // two sign-ups at the same second must not both trigger n8n
  try {
    const props = PropertiesService.getScriptProperties();
    const data = JSON.parse((e.postData && e.postData.contents) || '{}');

    const token = props.getProperty('FORM_TOKEN');
    if (token && data.token !== token) return reply({ status: 'error', message: 'Invalid request' });
    if (data.website) return reply({ status: 'ok' }); // honeypot field: bots fill it, people don't

    const email = String(data.email || '').trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/.test(email)) return reply({ status: 'error', message: 'Enter a valid work e-mail.' });
    if (data.consent !== true) return reply({ status: 'error', message: 'Please tick the consent box.' });

    const sheet = getSheet();
    const rows = sheet.getLastRow() > 1
      ? sheet.getRange(2, 1, sheet.getLastRow() - 1, HEADERS.length).getValues() : [];
    if (rows.some(r => String(r[1]).toLowerCase() === email)) return reply({ status: 'already_signed_up' });

    const domain = companyDomain(email);
    const row = [new Date(), email, domain || '', data.role || '', data.city || '',
      String(data.note || '').slice(0, 200), 'yes', data.source || 'landing-page'];
    sheet.appendRow(row);
    if (!domain) return reply({ status: 'private_email' });

    const company = rows.filter(r => r[2] === domain).concat([row]);
    const threshold = Number(props.getProperty('THRESHOLD') || 5);
    if (company.length === threshold) notifyN8n(props, row, company, threshold);

    return reply({ status: 'ok', colleagues: company.length, threshold });
  } catch (err) {
    console.error(err);
    return reply({ status: 'error', message: 'Something went wrong. Please try again.' });
  } finally {
    lock.releaseLock();
  }
}

function notifyN8n(props, row, company, threshold) {
  const res = UrlFetchApp.fetch(props.getProperty('N8N_WEBHOOK_URL'), {
    method: 'post',
    contentType: 'application/json',
    headers: { 'x-signal-secret': props.getProperty('N8N_SECRET') },
    payload: JSON.stringify({
      email: row[1],
      city: row[4] || null,
      company_domain: row[2],
      colleagues: company.length,
      threshold: threshold,
      colleague_emails: company.map(r => r[1]),
      roles: company.map(r => r[3]).filter(String),
      notes: company.map(r => r[5]).filter(String),
      source: row[7],
      submitted_at: new Date().toISOString(),
    }),
    muteHttpExceptions: true,
  });
  if (res.getResponseCode() >= 300) console.error('n8n returned ' + res.getResponseCode() + ': ' + res.getContentText());
}

function getSheet() {
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) sheet.appendRow(HEADERS);
  return sheet;
}

function companyDomain(email) {
  const host = email.split('@')[1] || '';
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(host)) return null;
  const labels = host.split('.');
  const lastTwo = labels.slice(-2).join('.');
  const reg = MULTI.has(lastTwo) && labels.length >= 3 ? labels.slice(-3).join('.') : lastTwo;
  return FREEMAIL.has(reg) ? null : reg;
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
