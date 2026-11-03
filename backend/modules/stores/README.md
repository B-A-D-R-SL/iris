<!-- AI contribution: 50% or more AI-generated -->
# Stores module

**Owner pair:** Fairness & partners
**Status:** Store (US-11) and partner applications (US-12) implemented; decisions (US-13) planned

## Responsibility

Own stores (B.A.D.R. and approved partners) and the partner applications that
lead to them, within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Models

- `Store`: a place offering goods. `application` links a store to the
  `PartnerApplication` that created it; the US-13 approval sets it, and it stays
  empty for B.A.D.R. and manually created stores.
- `PartnerApplication`: a business request to become a partner. No account or
  store is created at submission. See
  [database-schema.md](../../../docs/03-design/database-schema.md#partnerapplication).

## Public functions

- `services.save_store(store)`
- `services.ensure_badr_store()`
- `services.submit_application(values, *, language, mailer=None)`: saves a
  `submitted` application from validated form values and sends the
  `partner_application_received` email after the commit. Raises
  `ApplicationAlreadyOpen` while the contact email has a submitted application,
  and a `ValidationError` for inactive or unknown category codes.

## Endpoints

- `POST /api/partner-applications/`: public, 5 requests per hour per IP. Contract
  in [api.md](../../../docs/03-design/api.md#post-apipartner-applications-us-12).

## Dependencies

- `categories.queries`: active category codes for `goods_categories`.
- `adapters.mailer`: confirmation email (`SmtpMailer`; Mailpit locally). Moves to
  the templated email system and background jobs with US-57.

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Audit events

None yet. US-13 records approval and rejection decisions in the audit log.
