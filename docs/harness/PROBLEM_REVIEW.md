# Problem review

## Online search recall

**Symptom:** The first Barcelona online run returned 48 accepted official-domain
PDFs but recalled none of the seven frozen source URLs.

**Evidence:** Transport and Firecrawl response validation passed. Repeating the
2020/21 query without Firecrawl's `includeDomains` request field immediately
returned the official club report. Exact-filename and exact-URL queries still
failed for some historical files.

**Root cause:** Provider-side domain filtering reduced recall, and the live
search index represents several reports under different official URLs while
omitting others. Domain/PDF filtering alone also admitted unrelated official
financial and foundation PDFs.

**Repair:** Keep domain enforcement local, add the study-required `memoria` URL
term, preserve raw responses, and support deterministic offline replay. Do not
inject frozen URLs into provider output or treat similar titles as equivalent.

**Verification:** The repaired run produced 117 auditable candidates, locally
rejected 93, and accepted 24. It recalled one frozen URL. Separate PDF checks
showed that the newly indexed 2020/21 and 2021/22 club-report URLs reproduce the
same 20 and 25 parsed roster names, but they remain candidates rather than
silent replacements. Search did not provide adequate 2018/19 or 2019/20 club
reports.

**Boundary:** Live search is a source-discovery aid, not an authoritative source
registry. Exact source coverage is enforced against frozen/reviewed evidence;
live source-set differences are reported. The deterministic Barcelona analysis
still matches all frozen 85-player business results.

## Direct Firecrawl recovery

The earlier routed credential eventually returned an account-level HTTP 403.
The integration was replaced, without a compatibility path, by direct
`https://api.firecrawl.dev/v2/search` bearer authentication using
`FIRECRAWL_API_KEY`.

The direct live run completed all seven committed queries and reproduced the
same normalized result as the prior successful run: 117 canonical candidates,
93 rejected, and 24 accepted. Comparison excludes only the retrieval timestamp;
all other normalized evidence fields match. Replaying the new raw responses
through the final code produced the same result again.

The live bundle still recalls one of seven frozen URLs. The academy source
validator therefore fails closed with six explicit missing URLs and does not
substitute similar official documents. This is a discovery-coverage result,
not a transport or implementation failure.
