// Turns a work e-mail into the company domain we cluster on.
// Freemail addresses return null: a gmail sign-up says nothing about an employer.

const FREEMAIL = new Set([
  "gmail.com", "googlemail.com", "gmx.de", "gmx.net", "gmx.at", "web.de",
  "yahoo.com", "yahoo.de", "outlook.com", "outlook.de", "hotmail.com", "hotmail.de",
  "live.com", "live.de", "icloud.com", "me.com", "mac.com", "t-online.de",
  "posteo.de", "mailbox.org", "proton.me", "protonmail.com", "aol.com", "freenet.de",
]);

// Second-level suffixes where the registrable domain has three labels.
const MULTI_PART_SUFFIXES = new Set(["co.uk", "com.au", "co.at", "or.at", "ac.uk"]);

export function companyDomainFromEmail(email: string): string | null {
  const at = email.trim().toLowerCase().lastIndexOf("@");
  if (at < 1) return null;
  const host = email.trim().toLowerCase().slice(at + 1);
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(host)) return null;

  const labels = host.split(".");
  const lastTwo = labels.slice(-2).join(".");
  const registrable = MULTI_PART_SUFFIXES.has(lastTwo) && labels.length >= 3
    ? labels.slice(-3).join(".")
    : lastTwo;

  return FREEMAIL.has(registrable) ? null : registrable;
}

// "doctolib.de" -> "Doctolib". Only a search hint for job boards, never shown as fact.
export function guessCompanyName(domain: string): string {
  const base = domain.split(".")[0].replace(/-/g, " ");
  return base.charAt(0).toUpperCase() + base.slice(1);
}
