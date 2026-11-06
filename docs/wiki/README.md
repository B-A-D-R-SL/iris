
# Professional and context wiki pages

These five Markdown pages are the review drafts for
[SET-31, issue #590](https://github.com/B-A-D-R-SL/iris/issues/590).
They are ready to copy into the separate GitHub wiki repository after review.
They have not been published to the live wiki.

| Requirement | Review draft | Wiki destination | Teammate review |
| --- | --- | --- | --- |
| Top risks and mitigations | [Risk register](Risks.md) | Replace `Risks.md` | Pending |
| Societal impact and design mitigations | [Societal impact](Societal-Impact.md) | Add `Societal-Impact.md` | Pending |
| Equity and diversity statement | [Equity and diversity](Diversity-Statement.md) | Add `Diversity-Statement.md` | Pending |
| Consultant cost, infrastructure and funding | [Economics](Economic-Impact.md) | Replace `Economic-Impact.md` | Pending |
| MIT, Law 25 and data in Canada | [Licence and legal aspects](Legal-&-Ethical-Issues.md) | Replace `Legal-&-Ethical-Issues.md` | Pending |

## Source and status

Prepared on October 30, 2026 from application repository `main` at
`cb1da4ca0f8835472ef8483444e8e03e66622605` and the wiki at
`12e46ccc8d601562620507b02bcc580d8507332e`. Source links are
included where claims are made. Requirements and proposed mitigations are not
claims that a feature has been delivered or a control verified.

The drafts retain the existing Risks, Economic Impact and Legal & Ethical Issues
page titles. The existing sidebar already links to Diversity Statement; this
draft supplies that missing page. Existing Budget, Cloud Cost Estimation, MIT
License, Accessibility and Privacy & Data Protection pages remain references.
Links between the five pages use their final wiki URLs so their contents can be
copied without rewriting links. Use the review-draft links in the table above
until the two new wiki destinations are published.

## Review and publish

1. Have at least one teammate review **each** of the five pages. Record their
   name, review date and review/PR link in the corresponding page's review
   record. Do not mark the records reviewed until that review actually occurs.
2. Resolve the explicitly listed team confirmations. Confirm budget assumptions
   with the project owner and privacy/operational choices with B.A.D.R. Keep
   unresolved items labelled as proposals or unknowns.
3. Merge the reviewed source drafts through the normal repository PR process.
   Copy the five files, using the destination filenames above, into a current
   checkout of `https://github.com/B-A-D-R-SL/iris.wiki.git`.
4. In the wiki's existing `_Sidebar.md`, add `[[Societal Impact]]` beside
   `[[Legal & Ethical Issues]]`. Keep `[[Diversity Statement]]` and the existing
   Risks and Economic Impact links. Inspect the five rendered pages, tables,
   source links and sidebar destinations before pushing the wiki changes.
5. Link the published pages and the five teammate reviews from #590. Close the
   issue only after its page and review acceptance criteria are met.

The wiki uses a separate Git repository: merging the application PR does not
publish these pages automatically. Keep later wiki edits and these reviewed
sources aligned in the same change when possible.
