<!-- AI contribution: 50% or more AI-generated -->
# Eligibility module

**Owner pair:** Fairness & partners
**Status:** US-16 decisions and US-18 household evidence integration implemented

## Responsibility

Own the eligibility feature boundary within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Public functions

- `domain.eligibility.decide(household_size, incomes_cents, thresholds)`:
  pure, deterministic eligibility calculation.
- `services.decide_for_household(household_id, decided_by)`:
  validates evidence and active rules, then inserts a new historical decision.
  Other modules must call this service rather than writing decision rows.
- `services.EligibilityEvidenceUnavailableError`: raised when the public
  household evidence reader is unavailable or returns incomplete evidence.

## Application logging

After the surrounding transaction commits, each new decision emits one
`eligibility_decided` event through `iris.eligibility`, with only `decision_id`,
`household_id`, `outcome` (`eligible` or `ineligible`), and `rule_version` (the
LICO rule's version number). Income amounts, thresholds, names and evidence
never enter the event. Rolled-back decisions emit no event. The JSON formatter
allows these four fields only for this logger/event pair; see the
[observability guide](../../../docs/guides/observability.md).

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Household evidence integration (required before US-16 closure)

The service consumes `households.queries.eligibility_inputs(household_id)`.
That public query must return an object with:

- `household`: persisted Household instance matching the requested UUID
- `household_size`: holder and all members, counting each person once
- `adult_count`: number of members aged 18 or older on the decision date
- `adult_incomes_cents`: one confirmed line-199 income per adult, in integer cents

The reader must verify all of the following:

1. Every adult is included; children do not contribute income.
2. Each adult has an accepted, confirmed Revenu Québec notice.
3. The notice tax year meets the application's accepted-year rules.
4. Missing, unconfirmed, outdated, or ambiguous evidence is rejected.
5. A `did_not_file` declaration is sent for staff review, not counted as zero.
6. The list of incomes contains exactly `adult_count` verified values.

The reader now checks current US-18 notices, names, postal codes, in-person
verification and accepted tax years. It uses Montreal's current date for ages.
It locks the household for the caller's transaction, matching staff edits and
notice entry. Invalid evidence is refused, never replaced with zero income.

**Dependencies:** US-17 household members and US-18 IncomeNotice records.
The US-18 approval tests exercise this reader and the real decision service
together; the eligibility unit tests still isolate the reader contract.

## Decision persistence

Each successful calculation inserts a new `EligibilityDecision`, including
adult incomes, total, threshold, reference year, rule version, result and actor.
Existing decisions must not be edited or deleted. Migration 0002 adds a
PostgreSQL trigger enforcing this rule.

## Audit events

Eligibility decision audit events must be recorded through audit.services.record() once US-62 is integrated. This is pending; decision records alone do not satisfy SEC-08.

## Sensitive income snapshots and erasure

**Privacy review required before merge.**

US-16 (#457/#460) and the project database schema explicitly require
`EligibilityDecision` to retain each adult income and the calculated
household total. These values make historical decisions explainable.

This requirement conflicts with the general sensitive-data restriction
in `docs/05-process/review-rules.md` and `.coderabbit.yaml`.

A narrowly scoped exception for the EligibilityDecision table is
requested, not assumed approved. Income amounts must never be included
in application logs, emails, or audit-event metadata.

**Proposed erasure approach:** The privacy/retention owner must approve
a retention period and implement a privileged, audited maintenance
operation to erase or anonymize sensitive decision snapshots when
required. It must operate outside ordinary application permissions,
respect the PostgreSQL append-only trigger's protection against
normal UPDATE/DELETE operations, and have database-level tests.

No such privileged erasure path or privacy exception is approved or
implemented in this PR. The related CodeRabbit privacy finding remains
open until the team confirms the design.
