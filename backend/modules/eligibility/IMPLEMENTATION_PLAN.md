# US-16 Eligibility Engine - Implementation Skeleton

Issues: #457 (story), #458 (tests), #459 (rule), #460 (service).

## 1. Pure eligibility rule - #459

File: domain/eligibility.py

    immutable Decision:
        eligible: bool
        household_income_cents: int
        threshold_cents: int
        family_size_used: int

    decide(household_size, incomes_cents, thresholds):
        validate household size >= 1
        validate integer, nonnegative incomes and thresholds
        family_size_used = min(household_size, 7)
        threshold = thresholds[family_size_used]
        household_income = sum(incomes_cents)
        eligible = household_income <= threshold
        return Decision(...)

No Django imports, database access, floats or hardcoded LICO values.

## 2. Decision model - #460

File: models.py

    EligibilityDecision:
        id, household, household_size, adult_incomes_cents
        household_income_cents, threshold_cents, threshold_year
        ruleset_version, eligible, decided_by_type
        decided_by, created_at

    Each decision is a new immutable row.
    Reject updates, bulk updates and deletion.
    Preserve the exact rule version used.

## 3. Public decision service - #460

File: services.py

    decide_for_household(household_id, decided_by):
        start database transaction
        obtain household/member data through households.queries
        determine adults aged >= 18 on application date
        obtain each adult's latest accepted confirmed notice
        reject missing, invalid or unconfirmed income evidence
        obtain active lico_thresholds through rules.queries
        validate threshold configuration and year
        call domain.decide(...)
        insert a new EligibilityDecision
        return the persisted decision

    Never silently treat missing income evidence as zero.
    Do not expose income details through logs or exceptions.
    Other modules call this service, not the domain directly.

## 4. Verification - #458

    Preserve existing 21 threshold boundary cases.
    Test households of size 8+ use threshold 7.
    Test multi-adult summation, minors and missing notices.
    Test invalid inputs and missing or malformed rules.
    Test immutable records and historical rule versions.
    Test staff and automatic decisions, transactional failures.
    Test database integration with synthetic data.
    Target >= 90% domain coverage and >= 70% changed code.

## 5. Integration dependencies

    US-17: Member model and households.queries.
    US-18/Documents: confirmed notice persistence and read contract.
    SET-07/08: published lico_thresholds rule versions.

Do not copy incomplete dependency models into Eligibility.
Reconcile the current database schema with implemented Django models.
Do not claim full service integration until its upstream data exists.
