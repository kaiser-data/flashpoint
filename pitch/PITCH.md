# Flashpoint · 90-second pitch

**One-liner:** Flashpoint turns quiet interest inside an organisation into a scored, explained sales moment, and acts on it the same day.

## Spoken pitch (~210 words, 1:30)

**[0:00 · Hook]**
Clay sells hiring and funding signals. Everybody has them, so everybody calls the same accounts. We asked: what signal does nobody use?

**[0:10 · The signal]**
Our answer is Flashpoint. When someone from a university signs up on our partner Kredible's landing page, Flashpoint starts researching that university. When a second and third colleague sign up (International Office, Admissions, Finance), that's critical mass: a buying committee forming on its own.

**[0:25 · More than a headcount]**
But critical mass is only one of eight signals. Apify reads the university's own website and the news: an extended application deadline means empty seats. A new programme launching. Free places. Students on Reddit who can't fund their blocked account. Budget freezes being lifted. And the semester clock: the winter term started two days ago.

**[0:45 · Action]**
Code turns those signals into a Flashpoint score. The agent e-mails the people who signed up by itself, because they opted in. Sales gets one briefing: the decision makers ranked with LinkedIn links, and an e-mail written for the current situation.

**[1:00 · Reliability]**
If LinkedIn isn't really that university, the agent abstains. A second model judges every analysis. We ran eighteen German universities live: seventeen took the right path, twelve of thirteen analyses passed the judge.

**[1:15 · Learning]**
Three times a day it watches the news, and it learns which searches find real signals.

**[1:25 · Close]**
About two and a half minutes per university. Flashpoint.

---

## Submission text (paste into the form)

**Project:** Flashpoint
**Tracks:** Capture (Apify) · Act (n8n) · Out of the box (Featherless)

Flashpoint finds the moment an organisation is ready to buy, using a signal nobody uses: several people from the same organisation signing up on their own. The first sign-up starts research; the third colleague is critical mass. But headcount is only one of eight weighted signals. Apify reads the organisation's own website and the news for extended application deadlines (unfilled seats), new programmes, free places, budget freezes being lifted and policy changes. It also reads students' public posts about funding, and checks the semester timing. Code turns these signals into a 0–100 Flashpoint score with evidence.

n8n then acts with no human in the middle. It e-mails the consented sign-ups, written for the current situation. Sales gets a briefing with the decision makers from LinkedIn, ranked A/B/C, plus a personal template per contact. A human only steps in for calls, high scores or anything uncertain.

Reliability: the agent abstains when the LinkedIn match isn't verified. Code, not the model, makes decisions. Every analysis is logged and graded by seven rule checks and an LLM judge from a different model family (Featherless: Qwen 72B as analyst, DeepSeek-V3 as judge). Live tests on 18 German universities (Berlin + TUM, LMU, RWTH, KIT, Mannheim, Dresden, Hamburg, Heidelberg): 17/18 took the expected path, 12/13 analyses passed the judge, compliance averaged 4.8–5.0/5, about 2.5 minutes per account.

Wild card: a Signal Watch runs three times a day. It rates every news hit, saves all of them as a knowledge base, tracks the precision of each search, retires dead searches and learns new ones from strong signals. Built for Kredible (financing for non-EU students at German universities); any B2B use case is a config file.

GDPR: sign-ups consent; automatic e-mail only to them, in BCC. LinkedIn contacts are never mailed automatically, and the briefing reminds sales of GDPR Art. 14.

**Stack:** Lovable landing page → Google Sheet + Apps Script → n8n (4 workflows) → Apify (LinkedIn company, posts, employees; RAG web browser) → Featherless (Qwen2.5-72B, DeepSeek-V3) → Gmail + Google Sheets.
**Repo:** github.com/kaiser-data/flashpoint

---

## Timing notes

- Read it once aloud with a timer. If you run over 1:35, drop the Reddit sentence in [0:25].
- Show the briefing e-mail on screen during [0:45]. It's the strongest visual.
- During [1:00] show `tests/germany_report.html`.
