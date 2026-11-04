# Failure clusters: `8c2395a69c09`, `12fbcb8b0759`

26 failed attempts in 6 clusters (silhouette 0.32; naming cost GBP 0.0005).

- **Says sources lack key dates and rates, so omits required facts** - 23% of failures (6) - `web-brexit-dates`, `web-minimum-wage-start`
- **States the facts but refuses to draw the final conclusion** - 23% of failures (6) - `both-company-size`, `both-singapore-cabin-class`, `docs-london-hotel-cap`
- **Identifies Daventry site but refuses to infer its county, Northamptonshire** - 15% of failures (4) - `both-daventry-county`
- **Correct chemistry but omits the requested cell voltage, claiming sources lack it** - 15% of failures (4) - `both-ax7-battery-voltage`
- **Answers partially, omitting key facts the grader's rubric required** - 15% of failures (4) - `both-coventry-river`, `web-ben-nevis-height`, `web-london-underground-opening`, `web-penicillin-discovery`
- **States the correct fact but omits the explanation or context the key requires** - 8% of failures (2) - `both-ax7-ip-rating`, `both-iso-3691-4`

## Says sources lack key dates and rates, so omits required facts

- task_rubric: The answer gives only the year 1999 and says the sources lack the exact start date (1 April 1999) and the adult rate (GBP 3.60). It does not state either key point, though it does not contradict the key and it correctly declines to give a specific figure for the starting rate.
- task_rubric: The answer correctly gives the start date of 1 April 1999 but states that the starting adult hourly rate is not in the notes, so it omits the GBP 3.60 rate. It does not present a wrong figure, only admits the gap, and the later rates it cites are labelled as context.
- task_rubric: The answer states the start date as 1 April 1999, matching key point 1, but says the initial adult rate is not in the notes, so it does not give the GBP 3.60 rate from key point 2. It does not present any incorrect figure as fact.

## States the facts but refuses to draw the final conclusion

- task_rubric: The answer correctly states the policy rule that premium economy applies to flights over 6 hours and economy to 6 hours or less, which covers key point 1. It does not state that a direct London to Singapore flight takes about 13 hours or conclude that premium economy is allowed, instead saying the duration cannot be confirmed, so key point 2 is not covered.
- task_rubric: The answer key gives GBP 190 per night excluding breakfast, but the answer says the documents do not state a specific London hotel maximum and never mentions the GBP 190 figure. It fails to provide the key point, and while it does not state a conflicting figure, it does claim the policy has no hotel limits, which is inconsistent with the key.
- task_rubric: The answer says the documents give no London hotel cap, so it does not state the GBP 190 per night figure excluding breakfast. Its limitations section mentions a GBP 190 cap, which conflicts with its own claim that no London cap is stated.

## Identifies Daventry site but refuses to infer its county, Northamptonshire

- task_rubric: The answer correctly identifies the Daventry fulfilment site as the outage location (key point 1), but it explicitly states that the county is not answered by the sources, so it fails to give Northamptonshire (key point 2). It does not contradict the key.
- task_rubric: The answer correctly identifies the Daventry fulfilment site as the outage location (point 1) but fails to state that Daventry is in Northamptonshire, instead claiming the notes do not give the county and refusing to answer. It does not contradict the key, and it gives no specific county answer.
- task_rubric: The answer correctly identifies the Daventry fulfilment site as the outage location, but it never names Northamptonshire and says the sources do not state the county. It therefore misses the county point while not contradicting the key.

## Correct chemistry but omits the requested cell voltage, claiming sources lack it

- task_rubric: The answer correctly identifies LiFePO4 as the AX-7 chemistry (point 1) but says the single-cell nominal voltage is not available from the sources, so it does not state the ~3.2 V figure (point 2 not covered). It does not contradict the key, and it does not present a wrong cell voltage.
- task_rubric: The answer correctly identifies LiFePO4 chemistry (key point 1) but explicitly says the single-cell nominal voltage is not available, so the 3.2 V figure in key point 2 is not stated. It does not contradict the key and gives no specific cell voltage.
- task_rubric: The answer correctly identifies LiFePO4 as the AX-7 chemistry (point 1) but does not provide the ~3.2 V nominal cell voltage, instead saying the notes don't give it (point 2 not covered). It does not contradict the key.

## Answers partially, omitting key facts the grader's rubric required

- task_rubric: The answer gives the 10 January 1863 opening date, though it does not explicitly tie that railway to the London Underground name. It says the first section ran between Paddington and King's Cross, which conflicts with the key's Paddington to Farringdon route and does not state Farringdon.
- task_rubric: The answer states Ben Nevis is 1,345m, matching key point 1, but does not give the feet equivalent (4,413 ft) and does not mention it is the highest mountain in the UK, so key point 2 is missing. Nothing contradicts the key.
- task_rubric: The answer credits Alexander Fleming with the discovery in 1928 and says it took place in London, which covers points 1 and 2. It explicitly says the notes do not identify the building, so it does not state St Mary's Hospital and point 3 is not covered. Nothing it says conflicts with the key.

## States the correct fact but omits the explanation or context the key requires

- task_rubric: The answer key says the AX-7 is certified to ISO 3691-4, but the answer says the sources do not state the AX-7's certification and explicitly refuses to link ISO 3691-4 to the AX-7. It does correctly describe what ISO 3691-4 covers, matching key point 2, but it does not state key point 1 and does not contradict it.
- task_rubric: The answer states the AX-7 is rated IP54, matching key point 1. It explicitly says the notes do not explain what the digits 5 and 4 mean, so it omits the dust protection meaning of 5 and the splashing-water meaning of 4. It does not state anything that conflicts with the key.
