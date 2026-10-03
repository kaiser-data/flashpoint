# Flashpoint · demo video (2:00) and live pitch

**Rule from the organisers:** a small thing that runs beats a big thing that does not. Show real runs, real universities, real e-mails.

## Before you record (10 min)

- [ ] Sheet open on the **sign-up tab** with 2 TU Berlin test rows already in (your own domain addresses, `+1`, `+2`).
- [ ] n8n main workflow open, zoomed so all 5 coloured phases fit; one finished execution open in a second tab.
- [ ] Gmail (the sales inbox from SALES_EMAIL) open on a **[HOT/WARM …] briefing** with the scorecard table (runs after 16:22 have it, e.g. Mannheim, Dresden, Hamburg).
- [ ] Signal Watch digest e-mail open, plus the **Signals** and **Watch queries** tabs.
- [ ] Eval workflow with a finished run, plus `tests/berlin_report.html` in the browser.
- [ ] Screen: 1920×1080, browser zoom 110 %, bookmarks bar hidden, notifications off (Do Not Disturb).
- [ ] Record with QuickTime: **Cmd + Shift + 5 → Record Selected Portion**. Voice-over in one take, or record the screen first and talk over it.

## Shot list (1:30, matches PITCH.md)

| Time | Screen | Say |
|---|---|---|
| 0:00 | Kredible landing page `/universities` | "Kredible finances the €11,904 blocked account for non-EU students. Universities admit them, many never arrive. Kredible's question: which university, and when?" |
| 0:15 | Form: type the 3rd TU Berlin sign-up (or `npm run fill:demo` in the test folder) | "Clay sells hiring and funding signals. We use one nobody does: staff from the same university signing up on their own." |
| 0:25 | Sheet: Flashpoint status flips to `sent to n8n` | "The first sign-up starts research. International Office, Admissions and Finance together is critical mass." |
| 0:32 | n8n main workflow, pan across the coloured phases | "Apify reads LinkedIn, the news and the university's own site: extended deadlines, new programmes, free places, students who can't fund the blocked account." |
| 0:50 | Briefing e-mail: scorecard table at the top | "Eight signals, each with evidence, become a Flashpoint score. Here: winter term started two days ago, three roles signed up." |
| 1:00 | Briefing: decision makers A/B/C + template | "Sales gets the right people ranked, and an e-mail written for this moment. The sign-ups get theirs automatically." |
| 1:08 | Germany report (`tests/germany_report.html`) | "It abstains when unsure, and a second model judges every analysis: 17 of 18 universities on the right path." |
| 1:16 | n8n Replies phase → Outcomes → Learned playbook node | "Every reply is logged; the next analysis learns which signals got answers. The news is watched three times a day." |
| 1:25 | README hero screenshot or title slide | "Flashpoint: Kredible talks to the right university at the right moment." |

## Live pitch (3 min) if there is no video slot

1. Slides 1–3 (40 s): problem, the signal, how it works.
2. **Live:** add the 3rd sign-up row, show the status flip and the execution starting (20 s). Do not wait for it.
3. Switch to the finished briefing e-mail and the watch digest (60 s).
4. Slides 5–7 (50 s): results, reliability, learning loop, cost.
5. Close with the one-liner (10 s).

## Questions to expect

- **"Isn't this a hiring signal?"** No. The trigger is first-party consented demand: several colleagues asking on their own. Research only enriches it.
- **"GDPR?"** Sign-ups consent. Automatic e-mail only to them, in BCC. LinkedIn contacts go to sales, are never mailed automatically, and the briefing reminds sales of GDPR Art. 14. The LLM sees job titles, not names.
- **"What if it's wrong?"** Code decides, not the model: unverified LinkedIn → human. Every analysis is logged and judged by a different model family.
- **"Does it work beyond universities?"** Yes, it's a config file: product text, ICP, decision roles, signal queries. `n8n/configs/b2b-saas-example.json`.
- **"Cost?"** Apify about $0.13 per account (7 actors), Featherless is a flat plan, n8n and Google are free tiers.
