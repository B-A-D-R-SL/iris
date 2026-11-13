<!-- AI contribution: 50% or more AI-generated -->

**US-57: email system and core emails — implementation draft**

This records the original implementation proposal. The shared mail adapters,
template catalog, queued send service and delivery metadata are now implemented;
the [notification module runbook](../../backend/modules/notifications/README.md)
describes the current contracts and operational limits. Business producers owned
by later stories and live Azure verification remain separate. The planning
wording below is preserved for traceability.

The later merge of US-13 adds partner approval, rejection and operator invitation
reissue to the shared queue. Its existing bounded rejection-reason email contract
is preserved only in the dedicated partner rejection template; that exception
supersedes the proposal's generic reason-exclusion wording below.

Build one shared, bilingual email delivery service using the existing PostgreSQL-backed Procrastinate queue. Use Azure Communication Services (ACS) in staging, SMTP through Mailpit locally, and a reusable fake in tests. Migrate the email paths that already exist, and provide templates and calling contracts for workflows delivered by other stories.

The proposal was based on checkout commit `2b389ed`, the documentation under `docs/`, [US-57 #538](https://github.com/B-A-D-R-SL/iris/issues/538), and all three child tasks. Azure details below come from the supplied inventory; resource connectivity, permissions, sender identity and delivery have not been inspected in Azure. Writing the original draft involved no application changes or Azure operations.

| Task | Deliverable |
| --- | --- |
| [#539 — Unit tests](https://github.com/B-A-D-R-SL/iris/issues/539) | Tests accompany both build tasks in their respective pull requests, including API/database integration, error paths and the required coverage. |
| [#540 — Azure and fake mailers](https://github.com/B-A-D-R-SL/iris/issues/540) | Add `adapters/mailer/azure.py` and `fake.py` alongside SMTP; configure adapter selection and test transport behavior. |
| [#541 — Templates and send job](https://github.com/B-A-D-R-SL/iris/issues/541) | Add EmailLog, the public send service, bilingual template files, queued delivery, retries, and migrations of existing callers. Depends on #540. |

The foundations already exist: the [Mailer protocol](../../backend/adapters/mailer/base.py), [SMTP adapter](../../backend/adapters/mailer/smtp.py), and [Compose Mailpit and worker services](../../docker-compose.yml). The [architecture](../04-architecture/architecture.md) assigns EmailLog and delivery to notifications. Additional queue infrastructure is unnecessary.

At the proposal snapshot, two paths needed attention. [Partner application submission](../../backend/modules/stores/services.py) sent SMTP directly in an after-commit callback, keeping network delivery in the request process. [Household notification services](../../backend/modules/notifications/services.py) enqueued rendered subjects and bodies; their [worker task](../../backend/modules/notifications/tasks.py) hardcoded SMTP and caught failures without re-raising them. Consequently, unsuccessful sends finished as successful queue jobs and could not retry. The [notification model file](../../backend/modules/notifications/models.py) was still a placeholder. These paths have since been migrated to the shared service.

1. Establish the Azure configuration using the resources already supplied.

   | Existing resource | Proposed use and remaining check |
   | --- | --- |
   | `iris-stg-email-ar1` | Email Communication Service that owns the sending domain. |
   | `iris-stg-email-ar1/AzureManagedDomain` | Use its provisioned MailFrom address for staging. Verify the domain is ready and connected. |
   | `iris-stg-acs-ar1` | The Communication Service used by the email SDK. Obtain its actual endpoint/credentials and verify its domain connection. |
   | `iris-stg-kv-ar1` | Store the ACS connection string if using key-based authentication; grant the deployed workload read access. The currently listed West US 2 vault is planned to move/be replaced in Canada East. |
   | `STUDENT-AVD-0` | This VM is in a different subscription/resource group. The inventory does not establish it as Iris web or worker hosting. |

   Verify the managed domain is linked to `iris-stg-acs-ar1`; having both resources does not establish that connection. ACS and Email Communication Service must have compatible data geographies. The portal location `Global` does not establish their configured `dataLocation`. [Microsoft domain connection instructions](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/email/connect-email-communication-resource)

   Recommended staging setup: inject a Key Vault-backed ACS connection string and the exact verified sender address into the deployed worker configuration. If SET-17 uses App Service, Key Vault references can resolve secrets using the application's managed identity. This does not require adding a runtime Key Vault client to every email job. Direct Entra authentication to ACS is another supported option if the deployment already provisions it. [Key Vault references](https://learn.microsoft.com/en-us/azure/app-service/app-service-key-vault-references), [Python email SDK authentication](https://learn.microsoft.com/en-us/python/api/overview/azure/communication-email-readme?view=azure-python)

   Reconcile geography with the intended architecture: the docs target Canada East, while the supplied vault is in West US 2; a Canada East move/replacement is planned. `Global` is a normal resource location for these communication resources, with their configured data geography verified independently. Canadian data location does not establish that every transit hop remains in Canada. The inventory also does not identify application hosting or PostgreSQL; coordinate the existing queue's staging execution with SET-17. Use synthetic staging content as required by the architecture.

   Record a provider lifecycle follow-up: Microsoft has announced ACS Email retirement on September 30, 2028. Its guide currently permits onboarding email workloads during the transition but recommends migration. Keep the requested ACS adapter isolated so replacing the provider does not change business callers or templates. [Microsoft retirement guide](https://learn.microsoft.com/en-us/azure/communication-services/acs-retirement-and-breaking-changes-guide)

2. Complete the adapters in #540, with #539 tests alongside the work.

   Preserve `Mailer.send(to, subject, html=None, text=None) -> int` initially. Add an `AzureMailer` using `azure-communication-email`, and update `pyproject.toml` and `uv.lock`. Poll the send operation and inspect its final status; only `Succeeded` counts as acceptance. Calling `begin_send` or merely finishing polling is insufficient. Bound network/polling waits and translate failures into safe internal exceptions. Provider acceptance does not establish inbox delivery. [SDK send behavior](https://learn.microsoft.com/en-us/python/api/overview/azure/communication-email-readme?view=azure-python), [send status meanings](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/email/send-email)

   Add one reusable `FakeMailer` that records recipient, subject, text and HTML in memory and can simulate success, refusal and failures. Business/service tests use this fake. Adapter contract tests replace the Azure client or SMTP transport, so CI never contacts a real provider. Replace the duplicated test mailers currently scattered through store and notification tests.

   Add an explicit adapter factory, for example `MAILER_ADAPTER=smtp|azure|fake`. Keep `EMAIL_BACKEND`/Django `MAILERS` as the SMTP transport configuration. Local web and worker processes select SMTP/Mailpit; tests select the fake; staging selects Azure. Do not infer the provider from hostname or debug mode.

   At the proposal snapshot, [production validation](../../backend/iris/settings/production.py) checked only the Django delivery backend, and only local settings read `DEFAULT_FROM_EMAIL` from the environment. The planned change was to validate the selected adapter and load sender configuration in shared/production settings, with placeholder configuration in `backend/.env.example`. These changes are now implemented; actual credentials remain outside source control.

3. Implement the public notification service and metadata model in #541.

   Preserve the issue's public API:

   ```python
   notifications.services.send(user_or_email, template_key, context)
   ```

   The service validates the template key, permitted context fields and required values; resolves the recipient and language; creates EmailLog within the caller's transaction; and registers a delivery job with `transaction.on_commit`. It should also work when called outside an existing transaction. Network delivery happens only in the worker.

   For a User, use `preferred_language`. For a raw email address, reserve `context["language"]` for the caller's persisted application/household preference; default to French consistently with current behavior. Capture that language when queueing. Browser language and the worker's active translation state are insufficient.

   Implement the [documented EmailLog fields](../03-design/database-schema.md#emaillog): `to_email`, nullable `user`, `template_key`, `language`, `status`, `attempts`, `error`, and `sent_at`, with the normal primary key and a reversible migration. Use a lazy model reference for the account relation and public services/queries for cross-module work.

   Suggested statuses are `pending`, `sending`, `retrying`, `sent`, and `failed`. Count actual delivery attempts; an enqueue failure has zero attempts. Set `sent_at` after successful provider acceptance, and document that meaning of `sent`. Store bounded internal error codes such as `transport_unavailable` or `provider_rejected`, never raw exception text. Do not add subject, body, rendered HTML, context or token fields to EmailLog. Recipient addresses belong in this protected table; they remain prohibited in application stdout logs.

4. Make delivery failures retry visibly and predictably.

   Queue the EmailLog identifier and a small, validated rendering context; render inside the worker. Avoid putting rendered subjects and bodies in job arguments. On success, update the existing log. On a retryable failure, update its attempt/error state and re-raise a sanitized exception, suppressing the original exception chain. Returning normally after an error would defeat queue retries.

   Use the story's three delays after successive failed attempts: 60, 300 and 900 seconds. This means one initial attempt plus three retries, at most four delivery attempts. A simple exponential strategy does not produce that sequence; use Procrastinate's custom retry strategy. Validate malformed recipients/templates before queueing, and treat confirmed permanent failures as terminal; document and test that distinction. [Procrastinate retry strategy documentation](https://procrastinate.readthedocs.io/en/stable/howto/advanced/retry.html)

   Follow the repository [review rules](../05-process/review-rules.md): add a small notifications RuleSet schema/default with the requested delay list, rather than hardcoding the delays in task code. At the proposal snapshot, no notifications rule type existed. Its schema, seed/default support, BR-NOTIF rules and validation tests are now implemented. Capture the effective policy for each queued send so publishing a new version does not alter an in-flight delivery.

   Cover enqueue failures separately. An `on_commit` callback failure cannot roll back the saved business action. Record `queue_unavailable` where the database remains available and emit a safe failure event; a PostgreSQL outage may prevent both queue insertion and the log update. After-commit callbacks leave a commit-to-enqueue crash window, and provider acceptance followed by a worker crash can cause duplicate delivery. Use stable log identifiers, job serialization and sent-status checks to reduce duplicates. Stronger outbox/recovery guarantees require a separate design; this story must not claim atomic enqueue or exactly-once delivery.

   Preserve a compatibility task under the existing household email task name, or explicitly drain old jobs during rollout. Already queued jobs contain the old arguments.

5. Deliver the entire bilingual catalog, while preserving ownership of business triggers.

   Suggested keys below are proposed conventions, except `partner_application_received`, which is already documented. Each needs French and English subjects and plain-text bodies; HTML can share a small wrapper if included. A registry should specify required context per key and reject unexpected/sensitive fields.

   | Family | Template keys |
   | --- | --- |
   | Accounts | `account_confirmation`, `password_reset`, `invitation`, `walk_in_set_password` |
   | Partner applications | `partner_application_received`, `partner_application_approved`, `partner_application_rejected` |
   | Household files | `file_approved`, `file_in_review`, `file_invited_in_person`, `file_rejected`, `expiry_reminder` |
   | Reservations | `reservation_confirmed`, `pickup_window_open`, `reservation_cancelled_by_store` |
   | Other requested notifications | `strike`, `digest`, `need_match` |
   | Existing behavior to preserve | `household_suspended`, `household_reactivated` |

   This is 18 requested keys plus two existing status notices: 40 language/template combinations. Include render tests for every combination. Keep messages to a reviewed status, next action and trusted link; do not copy case notes, income, scores, tiers, birth dates or document values. Preserve current household reason validation and audit behavior. The later [US-59 #543](https://github.com/B-A-D-R-SL/iris/issues/543) adds dedicated sensitive-content checks; baseline safe content applies immediately.

   Build links from a configured public application origin. `/invitation/:token` and `/sign-in` are implemented. Signup/reset and several household pages are still placeholders in [the router](../../frontend/src/app/App.tsx); define future URL contracts with their owning stories and avoid sending live links to unfinished workflows.

6. Migrate working callers and publish explicit handoffs for the remaining workflows.

   Replace the inline partner receipt with `send(contact_email, "partner_application_received", ...)`, using saved application language. Route existing household suspension/reactivation through the shared service, keeping the current wrapper if useful. Preserve successful actions when a household has no email or delivery later fails.

   Prepare an allauth mail bridge in the [account adapter](../../backend/modules/accounts/adapter.py) for confirmation/reset templates so those emails use the same queue and logs when US-02/US-03 activate them. Keep signup closed and leave token generation, expiry, authentication behavior and working reset/confirmation routes to accounts.

   Invitation issuing workflows should build the invitation link from the raw token returned by `accounts.services.create_invitation` and the configured public origin, then call notifications. Do not add an automatic send to invitation acceptance or blindly send from the low-level creation service. Partner approval should deliberately choose its approval/invitation message, avoiding two emails for the same setup step. US-13 and US-18 remain responsible for approval and walk-in setup transactions.

   Do not send `file_approved` merely because an eligibility calculation succeeds: eligibility currently records a decision without completing household approval. Likewise, suspension-driven reservation cancellation is not a store-cancellation trigger. Reservation creation, expiry/pickup schedules, strikes, digest selection/consent and need matching remain with their owning stories. Their bilingual templates and context contracts belong here; working producers must be tracked separately. A template render test is not evidence of an implemented event trigger.

7. Handle one-use links and operational logging explicitly.

   Invitations currently store only token hashes in the accounts table. A durable asynchronous email needs the raw link temporarily in its restricted queue payload unless a secure alternative is implemented. Document that boundary; never put it in EmailLog, application events, exception text or API responses beyond the intended issuing handoff. Queue a copied, allowlisted JSON context rather than ORM objects or request/allauth context wholesale.

   Add concrete cleanup for terminal email jobs while preserving EmailLog metadata. The implemented default makes payloads eligible after 24 hours of terminal success/failure, with an hourly cleanup operation; normal removal is approximately 24–25 hours with a healthy worker. Retention comes from the same small notifications RuleSet. Pending/retrying jobs must remain available. Check provider and Procrastinate diagnostics for argument leakage, and test that failure logging cannot expose addresses, content or token-bearing links. Do not describe queue tokens as temporary without implementing cleanup.

   Follow the existing [observability guide](../guides/observability.md). Its formatter drops arbitrary `extra` values, so any new operational metadata needs a deliberate, tested allowlist. Static send/retry/failure event names are sufficient initially; EmailLog supplies durable outcome details. The staff failure/bounce screen belongs to [US-61 #545](https://github.com/B-A-D-R-SL/iris/issues/545). Provider delivery/bounce events need separate integration before the system can claim inbox delivery or bounce detection.

8. Verify the behavior through #539 and document the result.

   | Verification | Required evidence |
   | --- | --- |
   | Adapter behavior | Azure request mapping, bounded polling, provider success/refusal/failure, fake recording, SMTP multipart behavior; no real network in CI. |
   | Catalog and locale | Every key renders in FR/EN; required/missing context, fallback language and HTML escaping are checked. |
   | Transaction boundary | A real commit creates one queued delivery; rollback leaves no surviving log/job/send. Delivery never runs in the request. |
   | Retries and outcomes | Fake failures yield the exact delay sequence and stop after four attempts; success updates the original log; zero acceptance is failure. |
   | Existing workflows | Partner API/database/job/fake main path; household suspension/reactivation; valid households without email; saved actions survive later delivery failure. |
   | Privacy and links | Inspect EmailLog, raw log records and formatted output under success/failure; verify trusted URL origin, token handling and terminal-job cleanup. |
   | Deployment | Local end-to-end Mailpit receipt through the worker; one separate, deliberate ACS staging smoke test using synthetic content and a controlled recipient. |

   Follow #539's role matrix for any endpoint changed, including the existing partner application API; no new public send endpoint is needed. Meet at least 70% coverage of changed code and 90% for any changed domain code. Keep tests in the same PR as each build task. Run the applicable existing CI checks: formatting/lint, typing, import boundaries, migration checks, backend coverage and dependency audit; check generated API artifacts if the API schema changes.

   A practical split is one PR for #540 plus its #539 tests, followed by #541 plus its #539 tests and caller migrations. Update notification/store module READMEs, environment examples, business rules, schema and production/observability guidance to describe the final implementation. Link PRs and verification to the story, answer CodeRabbit feedback, obtain a substantive teammate review, and record customer sign-off before closing it.

The issue's roughly 12.5-hour estimate is plausible only with a narrow shared-infrastructure scope and ready staging configuration. The complete bilingual catalog, queue failure handling, legacy caller migration and token cleanup make it worth re-estimating after adapter/configuration work. Integrating every future business workflow would extend beyond the current three tasks and Release 1's implemented flows.
