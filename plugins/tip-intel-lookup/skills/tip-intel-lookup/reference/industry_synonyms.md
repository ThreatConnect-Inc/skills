# Industry / Sector Synonym Table

Used for industry-impact scans (`SKILL.md`'s "Industry / country / regional impact scan" workflow). A user-named industry should expand to this OR'd list, not just the literal word they typed — "finance" alone misses "bank," "insurance," etc. Loosely aligned to NAICS sector groupings, worded for how these actually appear in report/tag text rather than as codes.

| User-facing industry | Expand `summary CONTAINS` / `hasTag(name CONTAINS ...)` to (OR'd) |
|---|---|
| Finance / Financial Services | financial, finance, bank, banking, insurance, fintech, credit union, payment processor, investment, brokerage |
| Healthcare | healthcare, hospital, clinic, medical, pharma, pharmaceutical, health system, biotech, medical device |
| Hospitality | hospitality, hotel, resort, casino, restaurant, travel, airline, cruise |
| Manufacturing | manufacturing, factory, industrial, automotive, aerospace manufacturing, semiconductor fab |
| Energy / Utilities / Oil & Gas / Critical Infrastructure | energy, utility, utilities, power grid, electric grid, oil and gas, pipeline, refinery, water treatment, critical infrastructure, ICS, SCADA, OT |
| Government | government, federal, municipal, state agency, public sector, ministry, defense department, DoD, national security |
| Telecommunications | telecom, telecommunications, ISP, carrier, mobile network operator, broadband provider |

**Extend, don't replace.** If the customer names an industry not on this list during `customer_context.md` setup, ask them for 2-3 adjacent terms they'd also want caught, and save the expansion alongside their stated industry — don't silently fall back to searching only their literal word.

**Still combine with the tag/attribute pattern from `SKILL.md`'s industry-scan section** — this table expands *which words* to search for, it doesn't replace searching tags/`Description` attributes in addition to `summary`.
