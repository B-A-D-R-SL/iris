# Iris review rules

Every reviewer, human or AI, checks these ten rules.

1. `domain/` folders never import Django, the ORM, network code or adapters.
2. Thresholds, weights, fees and delays come from the RuleSet, never hard-coded; each changed rule has a test naming its BR- ID.
3. No read-modify-write on counters; use `filter().update(F(...))`, and enforce new uniqueness with a database constraint.
4. Every endpoint checks role and ownership, with a test for each role; deny by default.
5. Never log, email or store a SIN, income amounts, immigration status or document text outside their tables.
6. Money is integer cents; datetimes are timezone-aware (America/Montreal).
7. All visible text goes through translations, with both French and English entries.
8. The front end decides nothing that matters; eligibility or visibility logic in TypeScript is a bug.
9. Outside services are called only through adapters, and tests use the fakes.
10. Migrations are reversible; any data deletion is called out in the PR description.
