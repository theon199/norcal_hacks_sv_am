# LabMirror demo script (plain language)

About three minutes, using the **Factory machine breakdowns (synthetic)** example. Words in quotes are what to say; the rest is what to click.

Before judging, open the live site once so the backend is awake (it can take up to a minute after a quiet period).

---

**1. The problem (on the home page)**

"When someone says 'our AI model is better', they usually tested it once. One test can be lucky. LabMirror re-runs the same comparison under different conditions and tells you whether the claim still holds."

**2. Pick the example**

Click **Try this example** on *Factory machine breakdowns*.

"This is a made-up factory: 400 machines, each with eight everyday readings like temperature, vibration, oil pressure and hours since last service. The question is simple: will this machine break down?

The claim we're checking: a Random Forest model predicts breakdowns at least 5 points more accurately than a simpler model called Logistic Regression."

Point at the provenance note: "We made this data up and picked it on purpose to show the effect. The app says so right here."

**3. Run it**

Click **Run stress test**. While the stages tick:

"It's training both models on the same machines and testing them on the same held-back machines. Then it reshuffles which machines are held back and does it again, five more times."

**4. The first result looks great**

Point at the default-split card: **91.3% vs 83.8%, a 7.5-point gap**.

"On the usual single test, the claim checks out: 7.5 points better, more than the 5 promised. Most people would stop here."

**5. Then it wobbles**

Point at **3 / 5** and the lift chart.

"But when we reshuffle, Random Forest only hits the 5-point bar on 3 of 5 tries, and each of those lands exactly on the line. On one try the two models tie. So the big win came partly from which machines happened to be in the test."

**6. The other checks**

Noise chart: "We also added small errors to the readings, like a slightly miscalibrated gauge. That barely changed anything, so the issue isn't fragile readings."

Warnings: "And it found no signs of data leakage, like the same machine showing up in both training and testing."

**7. The verdict**

Point at **Mixed: sensitive to conditions** and the fixed rule.

"The verdict comes from a fixed rule written before we built the example, not from an AI. Random Forest is usually a bit better here, but 'at least 5 points better' isn't reliable."

**8. The AI auditor panel (preview)**

Scroll to the dashed **AI auditor** box.

"This is the AI layer we've designed. Be clear that it was written ahead of time for this example, and the badge says so. One part picks which tests to run and why, in plain English. The other writes the summary. The AI never touches the numbers: every finding here is read from the real run, and the summary is only shown if every number in it matches the report. That green check is that test passing."

**9. Proof you can rerun it**

Click **Download report (Markdown)** and scroll to the hash, seeds and versions.

"Everything needed to rerun this exactly is in the report: the file's fingerprint, the random seeds and the library versions."

**10. Close**

"LabMirror doesn't say a claim is true or false in general. It says how well the evidence holds up when you poke at it."

---

**If asked:**
- *Is the AI live?* No. The panel is a pre-written preview for this one example, and the badge and text say so. Every score and the verdict are computed live by Python.
- *Is "Mixed" a statistical test?* No. It's a product label from a published rule. LabMirror reports no p-values.
- *Contrast case:* the Breast Cancer example fails the same claim on all five reshuffles, so its verdict is *Not reproduced in tested settings*.
