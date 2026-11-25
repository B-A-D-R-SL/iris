<!-- AI contribution: 50% or more AI-generated -->

# Iris domain model — Release 1 implementation

This domain model describes the confirmed business concepts and how they relate. The ERD documents their stored fields and database relationships.

Reviewed 15 November 2026 against `main` at `a022580` for SET-21 (#412).
The existing [database schema and ERD](database-schema.md#erd) now covers all
15 application models and 27 concrete foreign keys. The
[architecture review](../04-architecture/architecture.md#release-1-review)
records the code differences and their PR/issue evidence. Deferred workflows
are distinguished below from relationships already stored in the database.

## Changes over sprints

Iris follows an Agile methodology. Small design changes can be made in later sprints as requirements develop. The responsible module owners review changes and keep the domain model, ERD, schema documentation, and migration plan consistent.

## Business concepts

| Concept | Model | Owner module | Meaning |
| --- | --- | --- | --- |
| User account | User | accounts | A person who can sign in and act according to their role. |
| Account invitation | Invitation | accounts | A one-use invitation to create a new active account with an assigned role and optional store assignment. |
| Partner store | Store | stores | An approved business offering goods, including the B.A.D.R. store. |
| Partner application | PartnerApplication | stores | A business request to become a partner. |
| Household | Household | households | A household registration and approval file. |
| Household member | Member | households | A person belonging to a household. |
| Local registration history | HouseholdDraftEvent | households | Who created, edited or submitted a walk-in draft; retained alongside central audit. |
| Income evidence | IncomeNotice | documents | Income evidence for an adult member, or their required non-filing explanation. |
| Eligibility decision | EligibilityDecision | eligibility | A preserved assessment of household eligibility and the inputs and rules used. |
| Rule version | RuleSetVersion | rules | A preserved version of configurable business rules. |
| Goods category | Category | categories | A category used to organize goods and apply category-specific rules. |
| Goods listing | Listing | listings | Goods offered by a store, with quantities and a pickup window. |
| Reservation | Reservation | reservations | A household claim on goods from a listing. |
| Audit event | AuditEvent | audit | An accountable record of an action, its actor, target, and time. |
| Email delivery record | EmailLog | notifications | A record of notification delivery without retaining email content. |

The groups in the diagram organize related concepts for readability. The owner module is listed in the table.

## Business relationships

Connecting lines describe business associations. Their labels explain the relationship in words. They do not specify database cardinality, foreign-key rules, or deletion behavior.

Partner application approval and invitation acceptance are shown separately as business actions.

Audit events and email delivery records appear as supporting concepts without implying direct database links to every model.

```mermaid

flowchart LR
    subgraph Partners["Accounts and partners"]
        User["User account<br/>User"]
        Invitation["Account invitation<br/>Invitation"]
        Store["Partner store<br/>Store"]
        PartnerApplication["Partner application<br/>PartnerApplication"]
    end

    subgraph Households["Households and evidence"]
        Household["Household<br/>Household"]
        Member["Household member<br/>Member"]
        IncomeNotice["Income evidence<br/>IncomeNotice"]
        HouseholdDraftEvent["Local registration history<br/>HouseholdDraftEvent"]
    end

    subgraph Eligibility["Eligibility and rules"]
        EligibilityDecision["Eligibility decision<br/>EligibilityDecision"]
        RuleSetVersion["Rule version<br/>RuleSetVersion"]
    end

    subgraph Goods["Goods and reservations"]
        Category["Goods category<br/>Category"]
        Listing["Goods listing<br/>Listing"]
        Reservation["Reservation<br/>Reservation"]
    end

    subgraph Support["Supporting records"]
        AuditEvent["Audit event<br/>AuditEvent"]
        EmailLog["Email delivery record<br/>EmailLog"]
    end

    User ---|"Optional store assignment"| Store
    Invitation ---|"Optional store assignment"| Store
    PartnerApplication ---|"Optional stored link on resulting store"| Store
    Household ---|"Optional holder account; a walk-in file's is linked by invitation or at the counter"| User
    Invitation ---|"Walk-in invitation names its household"| Household
    Household ---|"Contains members"| Member
    Household ---|"Retains registration history"| HouseholdDraftEvent
    Member ---|"Has income evidence"| IncomeNotice
    Household ---|"Has eligibility assessments"| EligibilityDecision
    RuleSetVersion ---|"Supplies applied rules"| EligibilityDecision
    Store ---|"Offers goods through"| Listing
    Category ---|"Categorizes"| Listing
    Household ---|"Makes reservations"| Reservation
    Reservation ---|"Claims goods from"| Listing

    classDef concept fill:#14283e,stroke:#64748b,color:#ffffff;
    class User,Invitation,Store,PartnerApplication,Household,Member,HouseholdDraftEvent,IncomeNotice,EligibilityDecision,RuleSetVersion,Category,Listing,Reservation,AuditEvent,EmailLog concept;
```

## Partner onboarding actions

These arrows describe business actions. The stored links are Store.application,
Invitation.store and User.store; neither application-to-invitation nor
invitation-to-accepted-user has a dedicated foreign key.

```mermaid

flowchart LR
    PartnerApplication["Partner application"]
    Store["Partner store"]
    Invitation["Account invitation"]
    User["User account"]

    PartnerApplication -->|"Approval creates"| Store
    PartnerApplication -->|"Approval creates"| Invitation
    Invitation -->|"Acceptance creates a new active account"| User

    classDef concept fill:#14283e,stroke:#64748b,color:#ffffff;
    class PartnerApplication,Store,Invitation,User concept;
```

Approval creates the store and invitation, updates the application, and records the audit event in one transaction.

The invitation email is sent after the transaction commits.

Acceptance creates a new active user with the invited identity, role and optional store assignment. An existing active or inactive account with the same email is refused case-insensitively; acceptance never overwrites it or switches the browser session.

The invitation's expiry is saved when issued, using the active lifetime rule
(seven days by default). Later rule versions apply only to new invitations.
US-04's acceptance page (#431), partner approval (US-13), walk-in setup email
(US-18) and shared queued delivery (US-57) are implemented. Staff/team issuing
screens remain US-05/US-06. Walk-in household account linking is implemented by
US-93 (#704).

## Confirmed business rules

### Accounts and partners

- A store can have multiple managers and staff.
- A user has an optional store assignment.
- A partner application collects business and contact information, a business address, at least one goods category, expected donation frequency, opening hours, and contact consent.
- Approval creates the partner store and account invitation.

### Households and income evidence

- Household registration collects the main contact information, a structured address, and member details.
- Walk-in registration records an in-person identity-check confirmation without storing identity-document details.
- Each adult needs accepted income evidence or a required non-filing explanation.
- Income evidence is recorded for the individual member.
- The holder is a Member with relation `holder`; the optional holder User is a
  separate relationship. Accepting the walk-in invitation, which names its
  household, links the new account as holder; staff can link an existing
  beneficiary account after an ID check, or resend the invitation (US-93).
- Adult notices or non-filing reasons are recorded while draft, followed by
  submission/duplicate checking and then approval. Non-filing or other evidence
  review reasons leave the file in `review_required`; the review queue is deferred.

### Eligibility

- Eligibility uses accepted assessed income for members aged eighteen or older and the threshold for household size.
- Income at or below the threshold is eligible.
- Eligibility decisions preserve their calculation inputs, result, and applied rule version.
- Existing eligibility decisions are never updated.

### Goods and reservations

- Stores offer goods through listings.
- Listings belong to goods categories.
- Reservations claim stock from a listing.
- Stock allocation and reservation creation are atomic.
- Household eligibility and configured reservation limits are checked.
- Pickup confirmation records who confirmed collection and when.
- Household suspension cancels reserved claims and releases their stock. Store
  deactivation cancels open listings and their reserved claims without releasing
  counters; reactivation restores neither. No-show processing and late correction
  remain deferred, even though their statuses exist.

### Supporting records

- Audit events record actions without copying sensitive information into event metadata.
- Email delivery records track notification delivery without storing email content.
- Local HouseholdDraftEvent history remains separate from the database-protected
  central audit. EmailLog `sent` means provider acceptance, not inbox delivery.

## Sources

- Accounts and invitations: [#424](https://github.com/B-A-D-R-SL/iris/issues/424), [#428](https://github.com/B-A-D-R-SL/iris/issues/428), [#430](https://github.com/B-A-D-R-SL/iris/issues/430), [#433](https://github.com/B-A-D-R-SL/iris/issues/433).
- Partner onboarding: [#443](https://github.com/B-A-D-R-SL/iris/issues/443), [#445](https://github.com/B-A-D-R-SL/iris/issues/445), [#447](https://github.com/B-A-D-R-SL/iris/issues/447).
- Households and evidence: [#461](https://github.com/B-A-D-R-SL/iris/issues/461), [#463](https://github.com/B-A-D-R-SL/iris/issues/463), [#468](https://github.com/B-A-D-R-SL/iris/issues/468).
- Eligibility and rules: [#457](https://github.com/B-A-D-R-SL/iris/issues/457), [#460](https://github.com/B-A-D-R-SL/iris/issues/460), [Iteration 2 plan](https://github.com/B-A-D-R-SL/iris/blob/main/docs/06-planning/iteration-2.md).
- Goods and reservations: [#493](https://github.com/B-A-D-R-SL/iris/issues/493), [#501](https://github.com/B-A-D-R-SL/iris/issues/501), [#513](https://github.com/B-A-D-R-SL/iris/issues/513), [#515](https://github.com/B-A-D-R-SL/iris/issues/515), [#520](https://github.com/B-A-D-R-SL/iris/issues/520).
- Supporting records: [#541](https://github.com/B-A-D-R-SL/iris/issues/541), [#549](https://github.com/B-A-D-R-SL/iris/issues/549).
