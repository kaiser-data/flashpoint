# Flashpoint · 90-second pitch

**One-liner:** Flashpoint turns quiet interest inside an organisation into a scored, explained sales moment, and acts on it the same day.

## Spoken pitch (~220 words, 1:30)

**[0:00 · Kredible's problem]**
Kredible finances the blocked account for non-EU students: €11,904 they must deposit before they get a visa. Every year German universities admit talented students who never arrive, because they can't raise that money. Kredible fixes that at no cost to the university. Its challenge: which university to talk to, and when.

**[0:15 · The signal]**
Clay sells hiring and funding signals; everybody has them. We built Flashpoint on a signal nobody uses. When staff from one university sign up on Kredible's page, research starts. When International Office, Admissions and Finance all sign up, that's critical mass: a buying committee forming on its own.

**[0:30 · Why now]**
Headcount is one of eight signals. Apify reads the university's own site and the news: extended application deadlines mean empty seats, new programmes, free places, students on Reddit who can't fund their blocked account, budget freezes lifted. And the semester clock: winter term started two days ago.

**[0:50 · Action]**
Code turns that into a Flashpoint score. The agent e-mails the people who signed up by itself. Kredible's sales team gets the decision makers ranked, with an e-mail written for this moment.

**[1:05 · Trust]**
It abstains when unsure, and a second model judges every analysis: 17 of 18 universities took the right path.

**[1:15 · Learning]**
Every reply is logged. The next analysis learns which signals and angles got answers. The news is watched three times a day.

**[1:25 · Close]**
Flashpoint: Kredible talks to the right university at the right moment.

---

## Submission text (paste into the form)

**Project:** Flashpoint
**Tracks:** Capture (Apify) · Act (n8n) · Out of the box (Featherless)

Built for Kredible, which finances the €11,904 blocked account, tuition and living costs of admitted non-EU students so they can actually enrol at German universities. Flashpoint finds the moment a university is ready to partner, using a signal nobody uses: several people from the same organisation signing up on their own. The first sign-up starts research; the third colleague is critical mass. But headcount is only one of eight weighted signals. Apify reads the organisation's own website and the news for extended application deadlines (unfilled seats), new programmes, free places, budget freezes being lifted and policy changes. It also reads students' public posts about funding, and checks the semester timing. Code turns these signals into a 0–100 Flashpoint score with evidence.

n8n then acts with no human in the middle. It e-mails the consented sign-ups, written for the current situation. Sales gets a briefing with the decision makers from LinkedIn, ranked A/B/C, plus a personal template per contact. A human only steps in for calls, high scores or anything uncertain.

Reliability: the agent abstains when the LinkedIn match isn't verified. Code, not the model, makes decisions. Every analysis is logged and graded by seven rule checks and an LLM judge from a different model family (Featherless: Qwen 72B as analyst, DeepSeek-V3 as judge). Live tests on 18 German universities (Berlin + TUM, LMU, RWTH, KIT, Mannheim, Dresden, Hamburg, Heidelberg): 17/18 took the expected path, 12/13 analyses passed the judge, compliance averaged 4.8–5.0/5, about 2.5 minutes per account.

Learning: every reply is logged and linked to the signals and angle of its analysis; the next analysis receives a playbook of what got positive replies. Wild card: a Signal Watch runs three times a day. It rates every news hit, saves all of them as a knowledge base, tracks the precision of each search, retires dead searches and learns new ones from strong signals. Built for Kredible (financing for non-EU students at German universities); any B2B use case is a config file.

GDPR: sign-ups consent; automatic e-mail only to them, in BCC. LinkedIn contacts are never mailed automatically, and the briefing reminds sales of GDPR Art. 14.

**Stack:** Lovable landing page → Google Sheet + Apps Script → n8n (4 workflows) → Apify (LinkedIn company, posts, employees; RAG web browser) → Featherless (Qwen2.5-72B, DeepSeek-V3) → Gmail + Google Sheets.
**Repo:** github.com/kaiser-data/flashpoint

---

## Timing notes

- Read it once aloud with a timer. If you run over 1:35, drop the Reddit sentence in [0:25].
- Show the briefing e-mail on screen during [0:45]. It's the strongest visual.
- During [1:00] show `tests/germany_report.html`.
