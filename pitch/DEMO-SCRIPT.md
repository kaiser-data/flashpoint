# Flashpoint · demo video (2:00) and live pitch

**Rule from the organisers:** a small thing that runs beats a big thing that does not. Show real runs, real universities, real e-mails.

## Before you record (10 min)

- [ ] Sheet open on the **sign-up tab** with 2 TU Berlin test rows already in (your own domain addresses, `+1`, `+2`).
- [ ] n8n main workflow open, zoomed so all 5 coloured phases fit; one finished execution open in a second tab.
- [ ] Gmail open on the **[HOT …] briefing** from a finished run (TU Berlin or FU Berlin).
- [ ] Signal Watch digest e-mail open, plus the **Signals** and **Watch queries** tabs.
- [ ] Eval workflow with a finished run, plus `tests/berlin_report.html` in the browser.
- [ ] Screen: 1920×1080, browser zoom 110 %, bookmarks bar hidden, notifications off (Do Not Disturb).
- [ ] Record with QuickTime: **Cmd + Shift + 5 → Record Selected Portion**. Voice-over in one take, or record the screen first and talk over it.

## Shot list

| Time | Screen | Say |
|---|---|---|
| 0:00 | Title slide | "Clay sells hiring and funding signals. Everyone has them. We built a signal nobody uses." |
| 0:08 | Sheet: 2 TU Berlin sign-ups → type the **3rd** | "One sign-up is curiosity. Three people from the same university is a flashpoint." |
| 0:18 | Status column flips to `sent to n8n` | "The sheet counts sign-ups per e-mail domain and fires once, exactly at the threshold." |
| 0:25 | n8n canvas, pan across the coloured phases | "Apify researches the account from seven sources: LinkedIn, decision makers, news, the website, and two signals nobody uses: deadline extensions on the university's own site, which mean empty seats, and students on Reddit who can't fund their blocked account." |
| 0:45 | Finished execution: Verify company match → green | "If LinkedIn isn't really this university, the agent abstains instead of guessing." |
| 0:52 | Gmail: [HOT 85] briefing, scroll slowly | "Sales gets one briefing: who signed up, the decision makers ranked A to C with LinkedIn links, the evidence, and a template per person. Ready to send on Monday." |
| 1:12 | Agent e-mail copy (BCC) | "The people who signed up get a personal e-mail automatically. They opted in, so no human in the middle and no cold-mail risk." |
| 1:22 | Signal Watch digest + Signals tab | "Three times a day the watch reads the news: budget freezes lifted, visa rules changed. It rates each hit, saves everything and tells sales which accounts to call now." |
| 1:38 | Watch queries tab: precision column, a `learned` row | "It learns: every search has a precision score, dead searches retire, strong signals propose new ones." |
| 1:48 | Berlin report / eval workflow | "A second model judges every analysis, plus seven hard rule checks. We ran all of Berlin's universities through it." |
| 1:55 | Closing slide | "About 15 cents and 3 minutes per account. Flashpoint." |

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
