<!-- AI contribution: 50% or more AI-generated -->
# Notice reading: Law 25 evidence for the privacy impact assessment

This page holds the evidence that spike SET-19 ([#410](https://github.com/B-A-D-R-SL/iris/issues/410)) gathered for B.A.D.R.'s privacy impact assessment, about two services that could read notices of assessment: Azure AI Document Intelligence and Gemini on Vertex AI in Montréal. It is not a legal opinion and not the assessment itself: B.A.D.R.'s privacy officer, [Nadia Mirsraoui](../01-project/overview.md#people), makes the legal call. All sources were read on 2026-10-23. The spike sends the mock notices and the public redacted sample (no personal data) to the services, and never a real notice.

## How to read this page

- There is one row per question. The `Law 25` column names the sections of the Act (P-39.1) that the question relates to; "¶2" means the second paragraph of a section. Their wording is under [What the Act says](#what-the-act-says).
- Each provider cell starts with a status in bold. Then comes a short quote from the provider's own documents or contract, and a link with the date we read it. Longer explanations are in [Notes](#notes), numbered by row.
- Status meanings:
  - **Meets**: the provider's own documents state the fact the row asks about. It never means "Law 25 is satisfied".
  - **Partly**: the documents state part of it.
  - **No**: the option does not have it.
  - **Unknown**: the sources we could read do not answer it. We did not guess.
  - **Legal review**: the facts are in the notes, but whether they are enough under Law 25 is for the privacy officer to decide.
- Terms used on this page:
  - **DPA**: the Microsoft Products and Services Data Protection Addendum, Microsoft's contract terms for the data it processes for a customer.
  - **CDPA**: Google's Cloud Data Processing Addendum, Google Cloud's equivalent contract terms.
  - **Geo**: Microsoft's word for a large geographic area in which it keeps customer data at rest. For Iris it is Canada, which holds the Canada East and Canada Central regions.
  - **Multi-Region**: Google's word for a location made of several regions. Montréal (`northamerica-northeast1`) is a single region, not a Multi-Region.
  - **Entra ID**: Microsoft Entra ID, Microsoft's sign-in and identity service (formerly Azure Active Directory). It lets an application sign in to a service without an API key.
  - **Private endpoints**: a private network address for a service inside the customer's own Azure network, so requests do not travel over the public internet.
  - **FIPS 140-2**: a US government standard for checking that encryption modules work as specified.

## What the team already requires

- Personal data is stored and processed in Canada, and AI reading runs in a Canadian region.
- Automated decisions are announced, explained, and can be reviewed by a person.
- B.A.D.R. signs the privacy impact assessment before any real personal data enters Iris. Until then, Iris uses generated data only.
- Production runs on an account held by B.A.D.R., so the written agreements under s. 17 and s. 18.3 are between B.A.D.R. and the provider.

## Comparison

| # | Question | Law 25 | Azure AI Document Intelligence | Gemini on Vertex AI (Montréal) |
| --- | --- | --- | --- | --- |
| 1 | Where is the document processed? | s. 17(3), (4) | **Partly.** "The incoming data is processed in the same region where the Document Intelligence resource was created." Canada availability and contract coverage not confirmed (notes 1, 2). [Document Intelligence privacy page, 2026-10-23](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security) | **Unknown.** The terms promise where "machine learning processing" happens only for "a specific Multi-Region". Iris uses the single Montréal region. [Service Specific Terms §16, 2026-10-23](https://cloud.google.com/terms/service-terms) |
| 2 | Where is it stored at rest, and can it be copied to other regions? | s. 17(3), (4) | **Partly.** Data is "stored temporarily in Azure Storage in the same region." [Document Intelligence privacy page, 2026-10-23](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security) "Microsoft may copy customer data between regions within a given Geo". [Azure data residency, 2026-10-23](https://azure.microsoft.com/en-us/explore/global-infrastructure/data-residency) Canada availability and contract coverage not confirmed (notes 1, 2). | **Unknown.** Google "will store Customer Data for that Service at rest only within the selected Region or Multi-Region", but only for services on a list we could not read. [Service Specific Terms §1(b), 2026-10-23](https://cloud.google.com/terms/service-terms) |
| 3 | How long are inputs and outputs kept, and can we trigger deletion? | s. 18.3(2), s. 23 | **Meets.** Kept "for 24 hours after an analysis operation completes". To delete earlier, "call the Delete Analyze Result API". [Document Intelligence privacy page, 2026-10-23](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security) | **Partly.** Prompts are not kept outside our account "for longer than is reasonably necessary to create the Generated Output". No fixed time is given. [Service Specific Terms §20(h), 2026-10-23](https://cloud.google.com/terms/service-terms) |
| 4 | Does the provider cache, log or let staff review our requests (abuse monitoring)? | s. 17(3), s. 10 | **Partly.** For the Geo (here, Canada): "Microsoft personnel (including subprocessors) located outside the Geo may remotely operate data processing systems in the Geo but will not access Customer Data without your authorization." Abuse monitoring is not mentioned. [Azure data residency, 2026-10-23](https://azure.microsoft.com/en-us/explore/global-infrastructure/data-residency) | **Unknown.** Google's page on caching and abuse monitoring could not be read. The logging clauses we found cover partners and optional features. [Service Specific Terms, 2026-10-23](https://cloud.google.com/terms/service-terms) |
| 5 | Is our data used to train or improve models? | s. 18.3(2) | **Unknown.** No Document Intelligence page says. The DPA limits use to providing the service but does not mention training. [Microsoft DPA, 2026-10-23](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx) | **Meets.** "Google will not use Customer Data to train or fine-tune any AI/ML models without Customer's prior permission or instruction." [Service Specific Terms §18, 2026-10-23](https://cloud.google.com/terms/service-terms) |
| 6 | Which written terms apply, and who is the customer of record? | s. 17 ¶2, s. 18.3(1) | **Partly.** "The DPA is incorporated by reference into the Product Terms and other Microsoft agreements." The Microsoft contracting entity for a Canadian nonprofit was not confirmed. [Microsoft DPA, 2026-10-23](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx) | **Partly.** The CDPA is "incorporated into the Agreement(s) ... between Google and Customer". The Google entity for Canada was not confirmed. [Google CDPA, 2026-10-23](https://cloud.google.com/terms/data-processing-addendum) |
| 7 | Do the terms cover confidentiality, use only for the service, deletion at the end, breach notice to B.A.D.R., verification right? | s. 18.3(2); s. 18.3, paragraph after (2) | **Legal review.** All five topics are covered. Breach: Microsoft will "promptly and without undue delay (1) notify Customer". Audits have limits and costs. [Microsoft DPA, 2026-10-23](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx) | **Legal review.** All five topics are covered. Customer audits only "if required under Applicable Privacy Law". [Google CDPA §7.5.2, 2026-10-23](https://cloud.google.com/terms/data-processing-addendum) |
| 8 | Which laws govern the data: storage jurisdiction, provider's home jurisdiction including foreign lawful access (e.g. US CLOUD Act); provider commitments on government requests | s. 17(4) | **Legal review.** The customer lets Microsoft transfer data "to the United States or any other country in which Microsoft or its Subprocessors operate". Microsoft commits to redirect and notify. [Microsoft DPA, 2026-10-23](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx) | **Legal review.** "Customer Data may be processed in any country where Google or its Subprocessors maintain facilities." No government-request commitment found. [Google CDPA §10.1, 2026-10-23](https://cloud.google.com/terms/data-processing-addendum) |
| 9 | Encryption in transit and at rest, customer-managed keys, keyless identity authentication, private networking | s. 10 | **Meets.** Data at rest uses "256-bit AES encryption". Customer-managed keys, Microsoft Entra ID sign-in and private endpoints are supported (note 9). [Document Intelligence encryption page, 2026-10-23](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/encrypt-data-at-rest) | **Partly.** "Google makes HTTPS encryption (also referred to as SSL or TLS connection) available." The pages on keys, sign-in and private networking could not be read. [Google CDPA Appendix 2, 2026-10-23](https://cloud.google.com/terms/data-processing-addendum) |
| 10 | Certifications (ISO 27001, ISO 27701, SOC 2) as evidence of "generally recognized principles" | s. 17 ¶2 | **Partly.** "The Azure ISO/IEC 27001 certificate covers Azure, Dynamics 365, Power Platform, and select Microsoft 365 cloud services." Document Intelligence is not named. [Azure ISO 27001, 2026-10-23](https://learn.microsoft.com/en-us/azure/compliance/offerings/offering-iso-27001) | **Partly.** Google keeps "certificates for ISO 27001" and "SOC 2 and SOC 3 reports". ISO 27701 was not found. [Google CDPA §7.4, 2026-10-23](https://cloud.google.com/terms/data-processing-addendum) |
| 11 | Billing and governance fit: is it covered by B.A.D.R.'s Microsoft nonprofit grant, and does it mean one vendor or two? | — | **Meets.** "$2,000 (USD) Azure services credits per year". Iris already plans to run on Azure, so one vendor. [Microsoft for Nonprofits, 2026-10-23](https://www.microsoft.com/en-us/nonprofits/azure) | **No.** The grant is "Azure services credits". Gemini is a Google Cloud service: a second vendor, account and agreement. [Microsoft for Nonprofits, 2026-10-23](https://www.microsoft.com/en-us/nonprofits/azure) |

## Notes

1. **Where processing happens.**
   - Azure: Iris plans to use the Canada East region ([ADR 0001](../adr/0001-tech-stack.md)). No page we could read confirms that Document Intelligence is offered in Canada East or Canada Central: the Azure products-by-region table did not load as text. The team checks this when it creates the resource.
   - Azure: features in preview are different. The [Microsoft DPA](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx) says previews "may employ lesser or different privacy and security measures" and that "Location of Customer Data does not apply to Previews". Iris should use only generally available versions of the service.
   - Gemini: the team uses only the Montréal regional endpoint `northamerica-northeast1`, never the global endpoint. Google's pages on data residency and on which models run in which region now live on `docs.cloud.google.com`, which our tools could not open on 2026-10-23. So we could not confirm that Gemini models are offered in Montréal, or that processing stays there.
   - Gemini: Google's terms now use the new name "Gemini Enterprise Agent Platform API (formerly Vertex AI API)" ([Service Specific Terms §31(a)](https://cloud.google.com/terms/service-terms)). Documents may use either name.
2. **Storage and copies.**
   - Azure: the quote "stored temporarily in Azure Storage in the same region." comes from the [Document Intelligence privacy page](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security). The [Azure data residency page](https://azure.microsoft.com/en-us/explore/global-infrastructure/data-residency) also says "Microsoft will not store or process customer data outside the customer-specified Geo without your authorization." The Canada Geo pairs Canada East with Canada Central ([Azure regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list)). So a copy made "between regions within a given Geo" can sit in Canada Central, in Toronto, outside Québec ([Azure regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list)); this matters for s. 17, which applies to communicating information "outside Québec". **Legal review.**
   - Azure: the contract ties its location promise to "Core Online Services": "For the Core Online Services, Microsoft will store Customer Data at rest within certain major geographic areas (each, a Geo) as set forth in the Product Terms" ([Microsoft DPA](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx)). We did not check whether Document Intelligence is listed as a Core Online Service in the [Product Terms](https://www.microsoft.com/licensing/terms/product/PrivacyandSecurityTerms/all).
   - Gemini: the same clause lets Google "replicate that Customer Data within any other Region located within the country of the selected Region" ([Service Specific Terms §1(b)](https://cloud.google.com/terms/service-terms)). The list of services it covers (Google Cloud Platform Services Data Residency) did not load.
3. **Retention and deletion.**
   - Azure: the Delete Analyze Result API "permanently deletes the submitted input data and analyze result associated with the request" ([Document Intelligence privacy page](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security)). Iris can call it right after reading a notice.
   - Gemini: deleting data through the services is an instruction to delete it "within a maximum period of 180 days" ([Google CDPA §6.1](https://cloud.google.com/terms/data-processing-addendum)). Two optional features keep data longer: Grounding with Google Search keeps logs "for up to three (3) days", and Grounding with Google Maps stores prompts "for thirty (30) days" ([Service Specific Terms §20(k), §20(m)](https://cloud.google.com/terms/service-terms)). Iris does not need either feature. Google's page on caching could not be read.
4. **Caching, logging and staff access.**
   - Azure: the DPA says "there is no standing access by Microsoft personnel to Customer Data, and any required access is for a limited time" ([Microsoft DPA](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx)). That sentence is about Core Online Services (see note 2). The Document Intelligence pages we read say nothing about abuse monitoring or human review.
   - Gemini: the only general prompt-logging clause we found applies to partners and Non-TOS customers: it lets Google log their prompts only to review whether a violation has occurred ([Service Specific Terms](https://cloud.google.com/terms/service-terms), section not identified). That part of the long page was seen only as a summary by our tools, so this is a paraphrase, not a quote. Google's page "Generative AI and data governance" covers caching and abuse monitoring; B.A.D.R. should read it.
5. **Training.**
   - Azure: the DPA says Microsoft processes Customer Data "only as described ... (a) to provide Customer the Products and Services in accordance with Customer's documented instructions and (b) for business operations incident to providing the Products and Services". "To provide" includes "enhancing user productivity, reliability, efficacy, quality, and security". The DPA rules out "user profiling", "advertising or similar commercial purposes" and "market research aimed at creating new functionalities" ([Microsoft DPA](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx)). It does not say "training" either way. B.A.D.R. should ask Microsoft in writing whether Document Intelligence uses submitted documents to train or improve models.
6. **Terms and customer of record.**
   - Azure: "Microsoft makes the commitments in this DPA to all Customers with an existing Customer's agreement", and on any conflict "the DPA Terms shall prevail" ([Microsoft DPA](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx)). The DPA's contact section gives a mailing address for "Microsoft Corporation" in Redmond, Washington, USA. That is a contact address, not proof of which Microsoft company contracts with a Canadian nonprofit; we did not confirm that.
   - Gemini: the CDPA does not define which Google company signs. The Google Contracting Entity page did not load.
   - Both: B.A.D.R. must be the customer on the production account (team requirement above).
7. **The five topics s. 18.3 lists.**
   - Azure ([Microsoft DPA](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx)):
     - Confidentiality: personnel "will be obligated to maintain the confidentiality and security of such data even after their engagement ends."
     - Use only for the service: see note 5.
     - Deletion at the end: Microsoft keeps data "for 90 days after expiration or termination", then deletes it "within an additional 90 days".
     - Breach notice: sent "by any means Microsoft selects, including via email". B.A.D.R. must keep its contact details current.
     - Verification: Microsoft gives its audit reports on request. A customer audit is possible only "To the extent Customer's audit requirements ... cannot reasonably be satisfied through audit reports", and "Customer is responsible for all costs and fees related to such audit".
   - Gemini ([Google CDPA](https://cloud.google.com/terms/data-processing-addendum)):
     - Confidentiality (§7.1.2(c)): Google will "ensure that all persons authorized to process Customer Data are under an obligation of confidentiality."
     - Use only for the service (§5.2): Google processes data "only as follows: a. to provide, secure, and monitor the Services".
     - Deletion at the end (§6.2): "After a recovery period of up to 30 days from that date, Google will comply with this Instruction as soon as reasonably practicable and within a maximum period of 180 days".
     - Breach notice (§7.2.1): "Google will notify Customer promptly and without undue delay after becoming aware of a Data Incident", sent to the customer's "Notification Email Address" (§13).
     - Verification (§7.5): audits only "if required under Applicable Privacy Law"; otherwise the customer verifies "by reviewing the Security Documentation". "Google may charge a fee".
   - s. 18.3 asks the provider to notify "the person in charge of the protection of personal information" and to let that person "conduct any verification relating to confidentiality requirements". Whether either contract does that is a **Legal review** question.
8. **Laws and government requests.**
   - Azure: if law enforcement asks, "Microsoft will attempt to redirect the law enforcement agency to request that data directly from Customer". If forced to disclose, "Microsoft will promptly notify Customer and provide a copy of the demand unless legally prohibited from doing so" ([Microsoft DPA](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx)).
   - Azure: Microsoft's report for July to December 2025 says "In 45 cases, we were required to disclose customer content" for enterprise customers, and "None of these disclosures involved Azure content data belonging to a commercial, public sector, or educational customer" ([law enforcement requests report](https://www.microsoft.com/en-us/corporate-responsibility/law-enforcement-requests-report)).
   - Gemini: we read the whole CDPA and found no clause on government requests. Google's own report on government requests was not read.
   - Both: we found no statement by either provider about the US CLOUD Act. Whether the risk of foreign lawful access is acceptable is a **Legal review** question under s. 17(4).
9. **Security measures.**
   - Azure: the encryption page names the FIPS 140-2 standard for its 256-bit AES encryption. "The scope for data encrypted with customer-managed keys includes the analysis response stored for 24 hours" ([Document Intelligence encryption page](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/encrypt-data-at-rest)). "Authorization is supported with Microsoft Entra ID credentials or with a valid API key", and "You can use private endpoints for your Foundry Tools resources to allow clients on a virtual network to securely access data over Azure Private Link" ([virtual networks page](https://learn.microsoft.com/en-us/azure/ai-services/cognitive-services-virtual-networks)). The [FAQ](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/faq) refers to resources where "local (key-based) authentication is disabled". In transit, the DPA says data "over public networks between Customer and Microsoft, or between Microsoft data centers, is encrypted by default". Microsoft now calls these services "Foundry Tools".
   - Gemini: the CDPA says "The Security Measures include measures to encrypt Customer Data" (§7.1.1). Google's pages on default encryption and on security controls for generative AI could not be read.
10. **Certifications.**
   - Azure: the [ISO 27701](https://learn.microsoft.com/en-us/azure/compliance/offerings/offering-iso-27701) certificate "covers Azure, Dynamics 365, Power Platform, and select Microsoft 365 cloud services." Azure has "SOC 2 Type 2 audits" covering "system security, availability, processing integrity, and confidentiality" ([SOC 2 page](https://learn.microsoft.com/en-us/azure/compliance/offerings/offering-soc-2)); privacy is not in that list. The DPA commits that Microsoft's security measures "shall comply with the requirements set forth in ISO 27001, ISO 27002, and ISO 27018". The list of individual services in scope is in the Microsoft Azure Compliance Offerings appendices on the Service Trust Portal, which we did not read.
   - Gemini: Google's [services-in-scope page](https://cloud.google.com/security/compliance/services-in-scope) covers ISO 27001, 27017 and 27018, and SOC 1, 2 and 3. It does not name ISO 27701. A row for generative AI on Gemini Enterprise Agent Platform (formerly generative AI on Vertex AI) appeared in scope, but our tools only saw a summary of that part of the page, not its exact wording, so B.A.D.R. should check it.
   - Both: whether these certifications show "generally recognized principles" under s. 17 is a **Legal review** question.
11. **Billing and vendors.**
   - Azure: the grant gives access to "the complete portfolio of Azure products and cloud services" ([Microsoft for Nonprofits](https://www.microsoft.com/en-us/nonprofits/azure)). We did not read the eligibility page for exclusions. Iris's hosting on Azure is already planned to be covered by this grant ([ADR 0001](../adr/0001-tech-stack.md)).
   - Gemini: a second vendor means a second account held by B.A.D.R., a second contract and data protection addendum, a second bill, and a second s. 17 assessment.

## Same for both options

These duties apply whichever service is chosen.

- **s. 3.3, privacy impact assessment.** B.A.D.R. assesses Iris as a whole, and must consult its privacy officer "from the outset of the project".
- **s. 8, what households are told.** When Iris collects a notice, it tells the household the purposes, the means, and their rights. It also names the categories of third persons who receive the data (here, the AI reading provider) and "the possibility that the information could be communicated outside Québec". The current consent text, `consent_ai_reading` in the [glossary](../01-project/glossary.md), says only "I agree that software reads my notices of assessment to fill in the fields". It will be updated in US-22.
- **ss. 12 to 14, consent.** Iris treats notices as sensitive personal information, because they show the income of low-income households. Consent to sensitive information must be given "expressly". It must be "clear, free and informed", given for specific purposes, and, in writing, "presented separately from any other information". Iris asks in its own consent step. Whether s. 18.3 lets B.A.D.R. send notices to a provider without consent is a **Legal review** question; Iris asks for consent either way.
- **s. 12.1, automated decisions.** The team treats automatic approval as a decision "based exclusively on an automated processing". Iris says so when it gives the decision. On request, it must explain the personal information used and "the reasons and the principal factors and parameters", and let a staff member review the decision. The team's business rules already plan an approval email that says the decision was automated and offers a review by a person.
- **s. 11, keep decision inputs.** The information used to make a decision is kept "for at least one year following the decision". The team's plan is that Iris keeps these decision inputs in its own records, so it does not rely on the provider's copy.
- **s. 23, destroy when done.** When the purpose is achieved, Iris must "destroy the information, or anonymize it". The provider's copy should be deleted as soon as the notice is read (row 3).

### Why a data centre in Québec may not avoid s. 17

s. 17 starts with communicating information "outside Québec". Its third paragraph adds: "The same applies where the person carrying on an enterprise entrusts a person or body outside Québec with the task of collecting, using, communicating or keeping such information on his behalf." So the location of the data centre is not the only test: who is entrusted also counts. For both options, which company would be entrusted, and where it is, was not confirmed (row 6, note 6). Both contracts also allow processing in other countries (row 8). B.A.D.R. should plan a s. 17 assessment and written agreement for either option. **Legal review.**

## Still unknown, and what B.A.D.R. should read

The spike's Law 25 pass criterion cannot be checked on the rows below until these documents are read.

| Row | Option | What is missing | Document to read |
| --- | --- | --- | --- |
| 1 | Azure | Is Document Intelligence offered in Canada East or Canada Central? | [Azure products by region](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/table), or the Azure portal when creating the resource |
| 1, 2, 4 | Azure | Is Document Intelligence a "Core Online Service" for the contract's location and access promises? | [Microsoft Product Terms, Privacy and Security Terms](https://www.microsoft.com/licensing/terms/product/PrivacyandSecurityTerms/all) |
| 5 | Azure | Are submitted documents used to train or improve models? | A written answer from Microsoft |
| 6 | Azure | Which Microsoft company contracts with a Canadian nonprofit? | The agreement B.A.D.R. accepts for its Azure subscription |
| 10 | Azure | Is Document Intelligence in scope of the certificates? | Microsoft Azure Compliance Offerings, appendices A and B, on the [Service Trust Portal](https://servicetrust.microsoft.com/) |
| — | Azure (ADR 0005 alternative) | Is a vision language model offered on Azure with processing in Canada? Foundry Models deployed as "Global" "may process prompts and completions ... in any Microsoft Foundry region globally" ([Azure data residency](https://azure.microsoft.com/en-us/explore/global-infrastructure/data-residency)). | The Azure AI Foundry model catalog, filtered on Canada East and Canada Central with deployment type Standard |
| 1, 2 | Gemini | Are Gemini models offered in Montréal, and do storage and processing stay there? | [Generative AI data residency](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/data-residency), [Generative AI locations](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations), [Data Residency services list](https://cloud.google.com/terms/data-residency) |
| 3, 4 | Gemini | How long are requests cached, are they logged for abuse monitoring, and can that be turned off? | [Generative AI and data governance](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance), [Zero data retention](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/vertex-ai-zero-data-retention) |
| 6 | Gemini | Which Google company contracts with a Canadian customer? | [Google Contracting Entity](https://cloud.google.com/terms/google-entity) |
| 8 | Gemini | What does Google commit to when a government asks for customer data? | Google's government-requests policy for Google Cloud and the [Google Transparency Report](https://transparencyreport.google.com/) |
| 9 | Gemini | Customer-managed keys, keyless sign-in, private networking | [Security controls for generative AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/security-controls), [Default encryption at rest](https://docs.cloud.google.com/docs/security/encryption/default-encryption) |
| 10 | Gemini | Is generative AI on Vertex AI in scope, and does Google hold ISO 27701? | [Services in scope](https://cloud.google.com/security/compliance/services-in-scope), [ISO/IEC 27701](https://cloud.google.com/security/compliance/iso-27701) |

## Questions for B.A.D.R.'s privacy officer

1. Will B.A.D.R. hold the production account with the chosen provider, so that the written agreements under s. 17 and s. 18.3 are between B.A.D.R. and that provider?
2. Are the provider's standard terms (the Microsoft DPA or the Google CDPA) acceptable under s. 18.3? In particular, the paragraph of s. 18.3 after (2) places two duties on the provider itself, not only in the contract: to notify the person in charge of the protection of personal information without delay of any violation, and to let that person verify confidentiality. Do the providers' breach-notice and audit terms fit those duties (row 7, note 7)?
3. Is the risk of foreign lawful access acceptable under s. 17(4) (row 8, note 8)? For example, US law such as the CLOUD Act. Microsoft's DPA allows transfers "to the United States or any other country in which Microsoft or its Subprocessors operate", and Google's CDPA allows processing "in any country where Google or its Subprocessors maintain facilities". Which company would be entrusted is not confirmed for either option (row 6).
4. How long should Iris keep the values it reads from a notice? s. 11 asks for at least one year after a decision; s. 23 asks to destroy the data once it is no longer needed.

## What the Act says

Short quotes from the [Act respecting the protection of personal information in the private sector (P-39.1)](https://www.legisquebec.gouv.qc.ca/fr/document/lc/p-39.1?langCont=en), English text current to October 15, 2026.

| Section | Words of the Act |
| --- | --- |
| s. 3.3 | "the person must consult the person in charge of the protection of personal information within the enterprise from the outset of the project." |
| s. 8 | "the name of the third persons or categories of third persons to whom it is necessary to communicate the information [...], and the possibility that the information could be communicated outside Québec." |
| s. 10 | "security measures necessary to ensure the protection of the personal information [...] that are reasonable given the sensitivity of the information" |
| s. 11 | "The information used to make such a decision is kept for at least one year following the decision." |
| s. 12 | "Such consent must be given expressly when it concerns sensitive personal information." |
| s. 12.1 | "The person concerned must be given the opportunity to submit observations to a member of the personnel of the enterprise who is in a position to review the decision." |
| s. 14 | "If the request for consent is made in writing, it must be presented separately from any other information provided to the person concerned." |
| s. 17(3), (4) | "(3) the protection measures, including those that are contractual, that would apply to it; and (4) the legal framework applicable in the State in which the information would be communicated" |
| s. 17 ¶2 | "The information may be communicated if the assessment establishes that it would receive adequate protection, in particular in light of generally recognized principles regarding the protection of personal information. The communication of the information must be the subject of a written agreement" |
| s. 18.3(1) | "entrust the mandate or contract in writing" |
| s. 18.3(2) | "specify in the mandate or contract the measures [...] to protect the confidentiality of the personal information communicated, to ensure that the information is used only for carrying out the mandate [...] and to ensure that the mandatary or person does not keep the information after the expiry of the mandate or contract." |
| s. 18.3, paragraph after (2) | "A person or body carrying out a mandate or performing a contract of enterprise or for services referred to in the first paragraph must notify the person in charge of the protection of personal information without delay of any violation or attempted violation [...], and must also allow the person in charge of the protection of personal information to conduct any verification relating to confidentiality requirements." |
| s. 23 | "the person carrying on an enterprise must destroy the information, or anonymize it to use it for serious and legitimate purposes, subject to any preservation period provided for by an Act." |

## Sources

All read on 2026-10-23. Page dates are given where the page shows one.

Microsoft:

- [Data, privacy, and security for Document Intelligence](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security) (page dated 2026-07-22)
- [Azure data residency](https://azure.microsoft.com/en-us/explore/global-infrastructure/data-residency)
- [Azure regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list)
- [Microsoft Products and Services Data Protection Addendum, index page](https://www.microsoft.com/licensing/docs/view/Microsoft-Products-and-Services-Data-Protection-Addendum-DPA), and the [DPA itself, English, May 22, 2026 (Word file)](https://www.microsoft.com/licensing/docs/documents/download/MicrosoftProductandServicesDPA%28WW%29%28English%29%28May2026%29%28CR%29.docx)
- [Microsoft Product Terms, Privacy and Security Terms](https://www.microsoft.com/licensing/terms/product/PrivacyandSecurityTerms/all) (opened; not checked for Document Intelligence)
- [Document Intelligence encryption of data at rest](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/encrypt-data-at-rest) (updated 2026-10-19)
- [Configure Foundry Tools virtual networks](https://learn.microsoft.com/en-us/azure/ai-services/cognitive-services-virtual-networks) (updated 2026-06-05)
- [Document Intelligence FAQ](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/faq) (updated 2026-10-19)
- [Azure ISO/IEC 27001](https://learn.microsoft.com/en-us/azure/compliance/offerings/offering-iso-27001), [ISO/IEC 27701](https://learn.microsoft.com/en-us/azure/compliance/offerings/offering-iso-27701) and [SOC 2](https://learn.microsoft.com/en-us/azure/compliance/offerings/offering-soc-2) pages (updated 2024-10-10)
- [Microsoft for Nonprofits, Azure](https://www.microsoft.com/en-us/nonprofits/azure)
- [Microsoft Law Enforcement Requests Report](https://www.microsoft.com/en-us/corporate-responsibility/law-enforcement-requests-report) (July to December 2025)

Google:

- [Cloud Data Processing Addendum](https://cloud.google.com/terms/data-processing-addendum) (last modified 2026-06-08)
- [Google Cloud Service Specific Terms](https://cloud.google.com/terms/service-terms) (last modified 2026-10-12)
- [Google Cloud services in scope of its certifications](https://cloud.google.com/security/compliance/services-in-scope) (last modified 2026-09-28)

Law:

- [P-39.1 on LégisQuébec](https://www.legisquebec.gouv.qc.ca/fr/document/lc/p-39.1?langCont=en), current to 2026-10-15. The text was supplied by the project owner; the site refuses automated reading.

Could not be read on 2026-10-23: Google's Vertex AI documentation pages, which moved to `docs.cloud.google.com`; Google's data-residency list, contracting-entity and ISO 27701 pages, and the Azure products-by-region table, which did not load. They are listed in [Still unknown](#still-unknown-and-what-badr-should-read), and the rows that depend on them say `Unknown` or `Partly`.
