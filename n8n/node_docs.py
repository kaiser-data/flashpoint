"""One place that explains every node: phase, what it does, which API it calls and what it costs.
Used for the node notes, the legend boxes in n8n and the HTML documentation page."""

# name: (phase, what it does, API / tool, cost per account)
MAIN = {
    "Form sign-up": ("1 Trigger", "Receives the sign-up from the sheet script. Rejects calls without the x-signal-secret header.", "n8n Webhook", "free"),
    "Exactly 3 colleagues?": ("1 Trigger", "Continues only on the exact threshold sign-up, so each organisation runs once.", "n8n IF", "free"),
    "LinkedIn company": ("2 Research", "Finds the organisation's LinkedIn page by the name typed in the form, or by the domain.", "Apify harvestapi/linkedin-company", "~$0.004"),
    "Verify company match": ("2 Research", "Accepts the match only if the website contains the domain or the name matches the form. Otherwise abstains.", "Code", "free"),
    "LinkedIn posts": ("2 Research", "Last 20 posts with likes, comments and shares. Commenters are not stored.", "Apify harvestapi/linkedin-company-posts", "~$0.03"),
    "Decision-maker roles": ("2 Research", "Real people in buying roles: name, title, LinkedIn URL, location. Titles go to the LLM; names go to sales.", "Apify harvestapi/linkedin-company-employees", "~$0.06"),
    "Latest news": ("2 Research", "Google search for the organisation's news from the last 120 days, with page text.", "Apify apify/rag-web-browser", "~$0.01"),
    "Website": ("2 Research", "The organisation's homepage as Markdown.", "Apify apify/rag-web-browser", "~$0.002"),
    "Pain signal": ("2 Research", "Signal nobody uses: public evidence of the pain on the org's own site (e.g. extended deadlines = empty seats).", "Apify apify/rag-web-browser", "~$0.01"),
    "Customer voice": ("2 Research", "What the org's own customers say publicly (e.g. students on Reddit). Usernames and e-mails removed.", "Apify apify/rag-web-browser", "~$0.01"),
    "Build context": ("3 Analysis", "Merges all sources, drops off-target search hits, and ranks the contacts A/B/C by role and seniority in code.", "Code", "free"),
    "Featherless analysis": ("3 Analysis", "The analyst: culture, structure, news, pain evidence, buying committee, angle, score 0-100 and the e-mail.", "Featherless Qwen2.5-72B", "flat plan"),
    "Parse analysis": ("3 Analysis", "Validates the model's JSON. Code decides: auto e-mail, hand to a human, or both.", "Code", "free"),
    "Send automatically?": ("4 Act", "True only if the analysis is valid, LinkedIn is verified and there are consented sign-ups.", "n8n IF", "free"),
    "Agent e-mails the sign-ups": ("4 Act", "Sends the agent's e-mail to the people who signed up, in BCC. Sales gets the visible copy.", "Gmail", "free"),
    "Hand to a human?": ("4 Act", "True if contacts were found, a call was requested, the score is high, LinkedIn is unverified or the LLM output was unusable.", "n8n IF", "free"),
    "Write briefing": ("4 Act", "Builds the sales briefing: priority, contact list with names and LinkedIn links, evidence, analysis.", "Code", "free"),
    "Briefing to sales": ("4 Act", "E-mails the briefing to the sales team.", "Gmail", "free"),
    "Prepare log row": ("4 Act", "Flattens the analysis, the contact list and the context into one row for documentation and evaluation.", "Code", "free"),
    "Log analysis to sheet": ("4 Act", "Appends the row to the Analyses tab. The eval workflow reads it from there.", "Google Sheets", "free"),
    "Reply received": ("5 Replies", "Polls the inbox every minute for unread replies to the agent's e-mail.", "Gmail Trigger", "free"),
    "Classify reply": ("5 Replies", "Labels the reply: interested, question, not interested or stop.", "Featherless Qwen2.5-72B", "flat plan"),
    "Parse reply": ("5 Replies", "Reads the label. Anything unclear is treated as a question, so a human sees it.", "Code", "free"),
    "Interested or question?": ("5 Replies", "Routes interested replies and questions to a human. Stop and no-interest end here.", "n8n IF", "free"),
    "Hand reply to a human": ("5 Replies", "E-mails the reply and its summary to the sales team.", "Gmail", "free"),
}

EVAL = {
    "Run evaluation now": ("1 Load", "Start the evaluation by hand.", "Manual Trigger", "free"),
    "Every day at 18:00": ("1 Load", "Runs the evaluation every evening.", "Schedule Trigger", "free"),
    "Read analyses": ("1 Load", "All analyses the main workflow logged.", "Google Sheets", "free"),
    "Read evals": ("1 Load", "All analyses that were already judged.", "Google Sheets", "free"),
    "Select unjudged": ("1 Load", "Keeps only analyses without a verdict, at most 20 per run.", "Code", "free"),
    "Rule checks": ("2 Grade", "7 deterministic checks: STOP line, no e-mail addresses, e-mail length, score range, reasons for high scores, evidence behind pain claims, auto e-mail only when verified.", "Code", "free"),
    "LLM judge": ("2 Grade", "A different model family grades 6 criteria from 1 to 5: groundedness, relevance, actionability, e-mail quality, compliance, calibration.", "Featherless DeepSeek-V3", "flat plan"),
    "Parse verdict": ("2 Grade", "Combines rules and grades into pass / fail / judge-error.", "Code", "free"),
    "Write to Evals tab": ("3 Report", "Appends one row per judged analysis to the Evals tab.", "Google Sheets", "free"),
    "Build report": ("3 Report", "Averages per criterion, rule failures and the three weakest analyses.", "Code", "free"),
    "Anything judged?": ("3 Report", "Skips the e-mail when nothing new was judged.", "n8n IF", "free"),
    "E-mail eval team": ("3 Report", "Sends the report to the eval team.", "Gmail", "free"),
}


def legend(docs, title):
    lines = [f"# Legend · {title}", "Every node, in order. **Phase** · what it does · *API* · cost per account.", ""]
    phase = None
    for name, (ph, what, api, cost) in docs.items():
        if ph != phase:
            lines += ["", f"### {ph}"]
            phase = ph
        lines.append(f"- **{name}**: {what} *({api}, {cost})*")
    return "\n".join(lines)
