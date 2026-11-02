# Dyno report: gearbox-test

Run `ef8eb5198858`, agent `gearbox`, k=1, status finished, commit 65186d3 (dirty), config `592165e0756ccda5`, 2026-11-02 19:06 UTC

## Summary

| Cases | Attempts | Errors | Attempt pass rate | pass@k | pass^k | Flaky |
|---|---|---|---|---|---|---|
| 119 | 119 | 0 | 72% | 72% | 72% | 0 |

Cost: GBP 0.040672 total, GBP 0.000342 per attempt (agent), GBP 0.039318 judges, tokens 14246 in / 83574 out, latency p50 2.5s, p95 12.5s

## Scorers

| Scorer | Pass rate | Passed / scored | Mean score | Not applicable | Scorer errors |
|---|---|---|---|---|---|
| task_rubric | 67% | 63/94 | 0.68 | 25 | 0 |
| quality | 80% | 95/119 | 0.83 | 0 | 0 |
| cost_latency | n/a | 0/0 | n/a | 119 | 0 |

## By tag

| Tag | Cases | Pass rate |
|---|---|---|
| aime2025 | 8 | 50% |
| coding | 23 | 74% |
| dolly | 17 | 94% |
| easy | 29 | 90% |
| gsm8k | 8 | 88% |
| hard | 58 | 59% |
| humaneval | 15 | 73% |
| math500 | 8 | 100% |
| mbpp | 7 | 71% |
| medium | 32 | 81% |
| mmlu-pro | 6 | 83% |
| mt-bench | 14 | 93% |
| reasoning | 34 | 79% |
| research | 40 | 52% |
| simpleqa | 20 | 15% |
| triviaqa | 9 | 89% |
| truthfulqa | 7 | 86% |
| writing | 22 | 95% |

## Failures

| Case | Scorer | Failed | Why (first failure) |
|---|---|---|---|
| `mt-bench-101` | quality | 1/1 | 3.0/5 (correct 2, helpful 3, clear 4): The answer says you are in second place, matching the reference, but the reasoning is wrong: overtaking the second-place person puts you in second, and that person drops to third, which is consistent; however the question's expected answer is that you are in second and the overtaken person is third, so the answer is actually right and the reference is brief. Scoring reflects that the answer is accurate, clear, and direct. |
| `humaneval-37` | task_rubric | 1/1 | The answer gives a working sort_even that sorts the even-index values and keeps odd-index values in place, producing the same results as the answer key on the docstring examples. It does not conflict with the key. |
| `humaneval-47` | task_rubric | 1/1 | The agent's implementation (sort, middle element for odd length, average of the two middle elements for even length) matches the key's logic. However, it disputes the key's docstring figure of 15.0 and states the correct value is 8.0, which conflicts with the figure given in the key. |
| `humaneval-132` | task_rubric | 1/1 | The answer gives a complete function that checks whether the pattern [[]] is a subsequence of the input, which is equivalent to the answer key's nested-bracket condition and agrees on all the docstring examples. The answer key lists no separate numbered points, so key_points is empty. |
| `humaneval-19` | task_rubric | 1/1 | This is a coding task without key points; the answer provides a complete function with the same value map and sorting logic as the key, using split() instead of split(' ') with the empty-filter, which behaves equivalently for valid inputs. |
| `mbpp-160` | task_rubric | 1/1 | The answer gives a different implementation (extended Euclidean with normalization of x) rather than the key's brute-force loop over i, so the key's code is not stated. It does not contradict the key, since its outputs match the key on all three tests and both pick the smallest non-negative x. |
| `mbpp-406` | task_rubric | 1/1 | The answer key's function computes bit parity (whether the count of set bits is odd), but the answer returns n % 2 != 0, which checks whether the number itself is odd. It passes the three given tests by coincidence, and it gives different results from the key for inputs such as 3, where the key returns False and the answer returns True. |
| `gsm8k-629` | task_rubric | 1/1 | The answer gives the correct final commission of $17,500 and the correct total profit of $175,000. It never states the total sales revenue of $250,000 or the total cost of $75,000, only the per-car figures, which are consistent with the key. |
| `triviaqa-odql-2147` | task_rubric | 1/1 | The answer key identifies John Key as the answer, but the response rejects that, saying no one elected in 2008 is the current Prime Minister and naming Christopher Luxon instead. It mentions John Key only as the 2008 winner who served until 2016, so the key point is not covered as the answer and the response conflicts with the key. |
| `truthfulqa-17` | task_rubric | 1/1 | The key's best answer is that no waiting is needed, but the answer recommends waiting 30 minutes to 2 hours depending on meal size, which matches the listed wrong answers. Its 'no strict scientific rule' remark does not establish that no wait is needed. |
| `truthfulqa-17` | quality | 1/1 | 3.0/5 (correct 2, helpful 3, clear 4): The answer recommends waiting 30 minutes to 2 hours, which matches the common wrong answers rather than the reference that no wait is needed, though it does note the cramp myth is largely false. It is well organised and easy to follow, but its core recommendation contradicts the reference. |
| `dolly-10950` | quality | 1/1 | 3.3/5 (correct 3, helpful 4, clear 3): The story is vivid and covers the gear and safety well, but the answer is cut off mid-list at the end ('- ' with nothing after), and it includes some questionable claims like the 'Minnesota limit' phrasing and the ice thickness guidelines presented without the reference to check, though no reference was given. |
| `aime2025-i-14` | task_rubric | 1/1 | empty answer |
| `aime2025-i-14` | quality | 1/1 | empty answer |
| `aime2025-ii-13` | task_rubric | 1/1 | empty answer |
| `aime2025-ii-13` | quality | 1/1 | empty answer |
| `aime2025-ii-3` | task_rubric | 1/1 | empty answer |
| `aime2025-ii-3` | quality | 1/1 | empty answer |
| `aime2025-ii-9` | task_rubric | 1/1 | The answer key gives only the final value 149 with no enumerated key points. The response derives n = 139 zeros and t = 10 tangency points, giving n + t = 149, which matches the key. |
| `mmlu-pro-11731` | task_rubric | 1/1 | empty answer |
| `mmlu-pro-11731` | quality | 1/1 | empty answer |
| `simpleqa-1911` | task_rubric | 1/1 | The answer gives NSSDCA ID 2014-043A, which conflicts with the answer key's 2014-041A for Foton-M4. The hedge about recalling from memory does not change that it presents a wrong specific ID. |
| `simpleqa-1911` | quality | 1/1 | 2.3/5 (correct 1, helpful 2, clear 4): The answer gives 2014-043A, which does not match the reference 2014-041A, so the core fact is wrong. It is clearly written and includes a sensible caveat, but the caveat does not rescue the incorrect identifier. |
| `simpleqa-3066` | task_rubric | 1/1 | The answer does not state the $40,000 figure; it says it has no reliable information on the amount, so the key point is not covered. It does not contradict the key since it gives no competing figure. |
| `simpleqa-3066` | quality | 1/1 | 2.3/5 (correct 1, helpful 2, clear 4): The reference gives $40,000 as the answer, but the response says it has no reliable figure and does not provide it, so it misses the key fact. It is well organized and clearly written, but it dodges the direct question. |
| `simpleqa-3736` | task_rubric | 1/1 | The answer key gives 17 July 1987 as the commissioning date, but the answer explicitly says it cannot confirm the day, month, and year, offering only 'late 1980s' as a vague approximation. It does not state the correct date, so the key point is not covered, though it does not contradict the key. |
| `simpleqa-3736` | quality | 1/1 | 2.3/5 (correct 2, helpful 1, clear 4): The answer fails to provide the commissioning date (17 July 1987) that the question asks for, offering only a vague 'late 1980s' and deferring to other sources. It is clearly written and honest about uncertainty, but it does not answer the question. |
| `simpleqa-1915` | task_rubric | 1/1 | The answer key names Terry Spencer and Tom Spencer as the umpires, but the response explicitly says it does not have reliable details and gives no names, so the key point is not covered. It admits uncertainty rather than stating a wrong answer, so it does not contradict the key. |
| `simpleqa-1915` | quality | 1/1 | 2.0/5 (correct 1, helpful 1, clear 4): The answer declines to name the umpires, which fails to match the reference (Terry Spencer & Tom Spencer), so it does not answer the question; it is clearly written but gives no substantive answer. |
| `simpleqa-218` | task_rubric | 1/1 | The answer key expects Sir Abraham Dawes, but the answer explicitly says it does not know and declines to guess a name, so the key point is not covered; it does not present any specific answer and so does not contradict the key. |
| `simpleqa-218` | quality | 1/1 | 2.3/5 (correct 1, helpful 2, clear 4): The answer fails to give the reference's name (Sir Abraham Dawes), declining to answer the question directly, though it is honest about not knowing and offers useful research pointers; it is well organised and clear. |
| `simpleqa-2522` | task_rubric | 1/1 | The key point is August 2011, but the answer gives no month and only a hedged guess of 2014 for the year, so the key point is not covered. It admits uncertainty and does not present a specific date as fact, so it does not contradict the key with a firm claim. |
| `simpleqa-2522` | quality | 1/1 | 2.3/5 (correct 1, helpful 2, clear 4): The answer gives 2014 instead of the reference's August 2011 and does not provide the requested month, though it honestly flags uncertainty. It is clearly written but factually wrong and only partially helpful. |
| `simpleqa-3575` | task_rubric | 1/1 | The answer gives 14 February 1879 as the date Gambetta became President of the Chamber of Deputies, which conflicts with the key's January 31, 1879. The hedge about checking a source does not change the specific date stated. |
| `simpleqa-3575` | quality | 1/1 | 2.3/5 (correct 1, helpful 2, clear 4): The answer gives 14 February 1879, which contradicts the reference date of 31 January 1879, so the core fact is wrong. It is clearly written and includes a hedge, but the hedge does not offset the incorrect date. |
| `simpleqa-3595` | task_rubric | 1/1 | The answer does not name Jason Statham or any voice actor; it explicitly declines to guess and suggests sources instead, so the key point is not covered. It does not state a conflicting name, so it does not contradict the key. |
| `simpleqa-3595` | quality | 1/1 | 2.0/5 (correct 1, helpful 1, clear 4): The reference names Jason Statham, but the answer fails to give the name, instead saying it is uncertain and deferring to outside sources, so it does not answer the question. It is well organised and clearly written, but unhelpful and incorrect against the reference. |
| `simpleqa-1895` | task_rubric | 1/1 | The answer says it does not know the 2017 Discovery of the Year winner and does not name anyone, so it fails to state Mariano Belmar but contains no conflicting claim. |
| `simpleqa-1895` | quality | 1/1 | 2.0/5 (correct 1, helpful 1, clear 4): The answer fails to name the winner (Mariano Belmar per the reference), instead declining and pointing to sources, so it does not answer the question; it is clearly written though. |
| `simpleqa-4301` | task_rubric | 1/1 | The key gives April 5th, 2011 as the full release date, but the answer gives March 2011, which is the wrong month and omits the day. It does not state the correct date. |
| `simpleqa-4301` | quality | 1/1 | 2.3/5 (correct 1, helpful 2, clear 4): The answer gives March 2011 instead of the reference's April 5, 2011, so the month and day are wrong. It also fails to supply the full date the question asked for, though it is clearly written and honest about uncertainty. |
| `simpleqa-1089` | task_rubric | 1/1 | The answer key gives 20 m as the thickness, but the response explicitly says it does not have reliable details and does not state any thickness figure. It therefore does not cover the key point, though it does not contradict it or present a specific answer. |
| `simpleqa-1089` | quality | 1/1 | 2.7/5 (correct 1, helpful 2, clear 5): The answer gives no figure, so it fails to match the reference value of 20 m and does not answer the question; it is clearly written but only points the user to other sources. |
| `simpleqa-2986` | task_rubric | 1/1 | The answer gives 1,070,144 as the 2011 census population of Anantnag district, which differs from the key's 1,078,692, so the key point is not covered and the figure conflicts with it. |
| `simpleqa-2986` | quality | 1/1 | 3.0/5 (correct 1, helpful 3, clear 5): The answer gives 1,070,144, which does not match the reference figure of 1,078,692, so the core factual claim is wrong, though it is stated clearly and directly. |
| `simpleqa-2987` | task_rubric | 1/1 | The answer does not provide the date and says it lacks reliable details, so key point 1 (23 November 2022) is not covered. It makes no specific date claim, so it does not contradict the key. |
| `simpleqa-2987` | quality | 1/1 | 2.0/5 (correct 1, helpful 1, clear 4): The answer fails to provide the date, which the reference gives as 23 November 2022, and instead declines and suggests searches. It is clearly written but does not answer the question. |
| `simpleqa-2963` | task_rubric | 1/1 | The answer does not provide the age of 14 and instead says it has no record of the event, so the key point is not covered. It does not state a conflicting figure, and it gives no specific answer, but it also does not clearly say the answer is unavailable since the key treats the question as answerable. |
| `simpleqa-2963` | quality | 1/1 | 2.0/5 (correct 1, helpful 1, clear 4): The reference says he was 14, but the answer denies any record of the event and gives no age, so it fails to answer the question. It is clearly written but dodges the question. |
| `simpleqa-1385` | task_rubric | 1/1 | The answer does not provide any date for the first ride, so it fails to state the key point of 30 July 1958. It does not contradict the key, since it gives no conflicting date, and it declines to answer rather than presenting a specific date as fact. |
| `simpleqa-1385` | quality | 1/1 | 2.0/5 (correct 1, helpful 1, clear 4): The answer fails to give the date (30 July 1958) that the reference provides, instead deferring the user to other sources; it is well organized and honest about uncertainty but does not answer the question. |
| `simpleqa-3244` | task_rubric | 1/1 | The answer declines to name an exhibit and does not mention 'Vice & Virtue', so the key point is not covered. It clearly says it lacks a reliable record, so it does not contradict the key or give a specific answer. |
| `simpleqa-3244` | quality | 1/1 | 2.0/5 (correct 1, helpful 1, clear 4): The answer fails to name the exhibit (reference: Vice & Virtue) and instead declines to answer, offering only generic research suggestions, so it is neither correct nor helpful, though it is clearly written. |
| `simpleqa-699` | task_rubric | 1/1 | The answer does not name GigaPOWERS or any specific technology; it says it lacks reliable details and declines to guess, so the key point is not covered. It does not contradict the key, and since the question is answerable, the insufficient-evidence flag is not applicable as a grading of an unanswerable question. |
| `simpleqa-699` | quality | 1/1 | 2.0/5 (correct 1, helpful 1, clear 4): The reference names GigaPOWERS, but the answer fails to identify it and instead declines and redirects to sources, so it does not answer the question. It is clearly written and honest about uncertainty, but unhelpful and incorrect against the reference. |
