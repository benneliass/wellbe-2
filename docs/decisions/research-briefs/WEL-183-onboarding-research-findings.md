# WEL-183 Onboarding Research Findings

## Summary

WellBe should use an **authenticate-first, onboard-second** MVP flow: let ZITADEL/OIDC prove identity, key the WellBe controller record on the OIDC `(issuer, subject)`, then create or resume a pending onboarding record.

The first-run consent surface should capture only the **core personal-workspace processing** needed for the product to function: create the personal workspace, store/retrieve user-provided health memory, organize/link that content into Health Threads for the user's own use, and maintain essential privacy/security/audit records.

All optional capabilities should be deferred to **point-of-use consent**: imports from Apple Health/Health Connect/EHRs/wearables, sharing with caregivers or clinicians, notifications, research/cross-patient analysis, model-training use, organizational access, and any device permissions.

The minimum baseline profile should be limited to OIDC identity linkage, a contact channel if supplied by the IdP, locale/time zone or unit preferences where needed, consent/audit metadata, and any legally required eligibility attestation. Health profile details such as date of birth, sex, height, weight, medications, allergies, diagnoses, and emergency contacts should be optional and progressively requested.

Abandonment should leave only a **pending account/onboarding draft** and **draft consent choices**; no consent scope becomes effective until the user gives an explicit final confirmation. Finalization should be atomic and idempotent so refreshes and retries do not create duplicate identities, workspaces, or consent rows.

The recommended UX is calm and layered: plain-language summaries, separate consent decisions by purpose, no pre-checked boxes, easy decline for optional features, visible revocation controls, and accessible form behavior.

This is research input, not legal advice. Product/legal still need to decide the exact lawful basis, age/guardian rules, regional consumer-health-law obligations, and retention for abandoned drafts.

## Sources reviewed

[S1] **Data minimisation: How much data can be collected?** — European Commission, current guidance, accessed 2026-06-18. URL: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr/how-much-data-can-be-collected_en. Credibility note: official European Commission guidance on the GDPR data-minimisation principle.

[S2] **Consent** — UK Information Commissioner's Office (ICO), current UK GDPR guidance, accessed 2026-06-18. URL: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/a-guide-to-lawful-basis/consent/. Credibility note: official UK data-protection regulator guidance; credible for consent quality, granularity, withdrawal, and recordkeeping.

[S3] **Special category data** — UK Information Commissioner's Office (ICO), updated 2024, accessed 2026-06-18. URL: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/a-guide-to-lawful-basis/special-category-data/. Credibility note: official regulator guidance on the heightened rules for health and other special-category data.

[S4] **ISO/IEC 29184:2020 — Information technology — Online privacy notices and consent** — ISO/IEC, 2020; confirmed 2026. URL: https://www.iso.org/standard/70331.html. Credibility note: international standard specifying controls for online privacy notices and the process of asking consent for personal-information processing.

[S5] **45 CFR §164.508 — Uses and disclosures for which an authorization is required** — U.S. eCFR / Department of Health and Human Services, current regulation, accessed 2026-06-18. URL: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.508. Credibility note: authoritative U.S. HIPAA authorization rule; useful as a health-data authorization analogue even if WellBe is not a HIPAA covered entity.

[S6] **FHIR Consent Resource — Definitions** — HL7 International, FHIR R5, accessed 2026-06-18. URL: https://fhir.hl7.org/fhir/consent-definitions.html. Credibility note: healthcare interoperability specification for representing consent status, actors, actions, purposes, data categories, and periods.

[S7] **FHIR Consent Resource — Narrative and boundaries** — HL7 International, FHIR R5, accessed 2026-06-18. URL: https://fhir.hl7.org/fhir/consent.html. Credibility note: healthcare-standard description of computable consent directives and their use in privacy/access decisions.

[S8] **Health App & Privacy** — Apple, updated 2026. URL: https://www.apple.com/legal/privacy/data/en/health-app/. Credibility note: primary-source privacy description for a leading consumer-health product; relevant to user control, sharing, revocation, and optional sync.

[S9] **Protecting access to user's health data** — Apple Platform Security, Apple, published 2026. URL: https://support.apple.com/guide/security/protecting-access-to-users-health-data-sec88be9900f/web. Credibility note: primary-source security documentation for HealthKit/Apple Health access controls, including granular read/write/data-type permissions and revocation.

[S10] **Fill out your Health Details in Health on iPhone** — Apple Support, current support guidance, accessed 2026-06-18. URL: https://support.apple.com/guide/iphone/fill-out-your-health-details-iph08022b194/ios. Credibility note: primary-source description of what Apple asks for at Health first use and what can be added later.

[S11] **Health Connect privacy** — Google Health, current product privacy page, accessed 2026-06-18. URL: https://health.google/privacy/. Credibility note: primary-source description of Health Connect's centralized, granular permission controls.

[S12] **Manage connected apps in Health Connect** — Google Android Help, current support guidance, accessed 2026-06-18. URL: https://support.google.com/android/answer/12201230?hl=en. Credibility note: primary-source user documentation on granting and revoking app access to health data.

[S13] **Permissions and data access: Health Connect** — Android Developers, updated 2026. URL: https://developer.android.com/health-and-fitness/health-connect/ui/permissions. Credibility note: primary-source developer guidance on health-data permission UX, app settings, sync toggles, and insufficient-access states.

[S14] **Update your profile and goals** — Google Fit Help, current support guidance, accessed 2026-06-18. URL: https://support.google.com/fit/answer/6075110?co=GENIE.Platform%3DAndroid&hl=en-NA. Credibility note: primary-source product guidance showing which basic health/fitness attributes and goals are used for personalization.

[S15] **OpenID Connect Core 1.0 incorporating errata set 2** — OpenID Foundation, 2023. URL: https://openid.net/specs/openid-connect-core-1_0.html. Credibility note: authoritative OIDC specification defining authentication, ID tokens, the `sub` claim, issuer, state/nonce, and subject-identifier properties.

[S16] **Authenticate users using OpenID Connect** — ZITADEL Docs, current integration guidance, accessed 2026-06-18. URL: https://zitadel.com/docs/guides/integrate/login/oidc/login-users. Credibility note: primary-source documentation for the selected identity provider and its OIDC authorization-code integration.

[S17] **OAuth 2.0 recommended flows** — ZITADEL Docs, current guidance, accessed 2026-06-18. URL: https://zitadel.com/docs/guides/integrate/login/oidc/oauth-recommended-flows. Credibility note: primary-source ZITADEL guidance recommending Authorization Code with PKCE for modern clients.

[S18] **NIST SP 800-63C Revision 4 — Federation and Assertions** — National Institute of Standards and Technology, 2025. URL: https://pages.nist.gov/800-63-4/sp800-63c.html. Credibility note: U.S. government digital-identity standard; credible for federated identifiers, issuer+subject uniqueness, pairwise identifiers, and account linking/resolution.

[S19] **Idempotent requests** — Stripe API Documentation, current developer documentation, accessed 2026-06-18. URL: https://docs.stripe.com/api/idempotent_requests. Credibility note: mature production pattern from a high-integrity payments API for preventing duplicate effects during retries; used here as a general engineering pattern, not as health-specific authority.

[S20] **FTC Report Shows Rise in Sophisticated Dark Patterns Designed to Trick and Trap Consumers** — U.S. Federal Trade Commission, 2022. URL: https://www.ftc.gov/news-events/news/press-releases/2022/09/ftc-report-shows-rise-sophisticated-dark-patterns-designed-trick-trap-consumers. Credibility note: official consumer-protection regulator source identifying privacy-choice dark patterns such as buried terms, false urgency, and steering users toward more data sharing.

[S21] **Permission Requests** — Nielsen Norman Group, 2019. URL: https://www.nngroup.com/articles/permission-requests/. Credibility note: established UX research organization; relevant for timing permission requests, reversible decisions, and avoiding coercive permission UX.

[S22] **Progressive Disclosure** — Nielsen Norman Group, 2006, current UX reference. URL: https://www.nngroup.com/articles/progressive-disclosure/. Credibility note: established UX research reference for reducing cognitive load by deferring advanced or less common controls.

[S23] **WCAG 2.2 Understanding Docs: Labels or Instructions; Error Identification; Focus Appearance** — W3C Web Accessibility Initiative, WCAG 2.2, 2023 with current understanding documents. URLs: https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions, https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html, https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html. Credibility note: authoritative accessibility standard and implementation guidance for understandable form inputs, visible errors, and keyboard focus.

## Findings by question

### Q1 — Consent granularity & timing

The strongest through-line across the standards is that consent and privacy notices should be **purpose-specific, actively chosen, recorded, and easy to withdraw**. ICO guidance says valid consent requires a clear positive opt-in, separate treatment from general terms, specific and granular purposes, no pre-ticked boxes, named parties where relevant, withdrawal information, and retained evidence of what the user was told and when they consented [S2]. ISO/IEC 29184 similarly focuses on the content and structure of online privacy notices and the process of asking for consent before personal-information processing [S4]. GDPR data minimisation requires limiting collection to what is adequate, relevant, and necessary for the stated purpose, and ICO special-category guidance treats health data as needing additional protection and advance determination of the applicable Article 6 basis and Article 9 condition [S1, S3].

Comparable consumer-health products draw a practical line between **core local/personal health functionality** and **external access, sharing, or sync**. Apple Health lets users choose which apps may read or write health data, requires app explanations, separates read/write/data-type permissions, and lets users view or revoke access later [S8, S9]. Apple also treats iCloud sync and sharing with people or healthcare organizations as user-controlled choices that can be changed or stopped [S8]. Google Health Connect centralizes app permissions, gives granular controls over which apps can access which health data, and provides ways to grant or revoke app connections [S11, S12]. Android developer guidance also recommends app settings for managing connections, sync toggles, and clear handling when access is insufficient [S13].

Healthcare authorization models point to the same scope dimensions: **who**, **what data/resource**, **what action**, **what purpose**, **which recipient/actor**, **which time period**, and **how revocation works**. HIPAA authorization rules require a description of the information, authorized discloser, recipient, purpose, expiration, signature/date, right to revoke, and plain-language copy; they also restrict conditioning treatment or services on authorization in most cases [S5]. HL7 FHIR Consent models consent status, actors, actions, purposes, resource types, data periods, and controlled data; it explicitly includes statuses such as draft and active, which is relevant to preventing partially effective consent [S6, S7].

For WellBe, the recommended MVP line is therefore: ask up front only for **the core personal-workspace processing without which the product cannot function**, and ask later for every optional purpose, external connection, third-party grant, research/analytics use, or device permission. This is an inference from the cited standards and product patterns applied to the brief's constraints: up-front consent should be enough to make the personal core work, but not so broad that it becomes bundled consent or consent fatigue [S1, S2, S4, S8, S11, S21, S22].

At first run, WellBe should capture explicit records for these core purposes:

1. **Controller and personal workspace establishment** — create a WellBe controller record, bind it to the authenticated OIDC identity, and create a personal workspace controlled by that individual. This is identity/account setup rather than a third-party health-data grant, but it should still be disclosed and audited because it establishes the trust relationship [S2, S4, S15, S18].
2. **Store and retrieve user-provided health memory** — allow the user to enter, upload, view, edit, and delete their own health notes, symptoms in their own words, PDFs, messages, and similar personal health context. This should be framed as storage and organization for the user's own use, not diagnosis [S1, S2, S3, S4].
3. **Organize and link the user's content into Health Threads** — allow the service to classify, connect, summarize, and maintain the user's own records inside their personal workspace for the purpose of investigation support and continuity. This is part of the core product purpose and should be clearly named rather than hidden inside generic “improve experience” language [S2, S4, S6].
4. **Maintain essential privacy, security, audit, and consent records** — keep logs and consent records needed for security, access control, revocation, accountability, and evidence of consent. Consent-law treatment may vary by jurisdiction, so this should be disclosed up front and captured as a durable processing-basis/audit record even if legal later decides the exact lawful basis is not consent [S2, S3, S5, S6].

The following should be deferred to point-of-use because they are optional, more sensitive, or involve a new purpose, actor, data source, or data recipient:

- **External imports** from Apple Health, Google Health Connect, EHR/clinical-record connections, labs, wearables, pharmacies, email, cloud drives, or messaging accounts. Leading platforms ask at the moment an app requests specific categories or connections, and they provide revocation controls [S8, S9, S11, S12, S13].
- **Sharing grants** to caregivers, clinicians, care teams, institutions, or researchers. These require recipient, purpose, resource/data category, time limit, and revocation details; HIPAA-style authorization and FHIR Consent both support this structured model [S5, S6, S7].
- **Research, cross-patient analysis, population analytics, model training, or product-improvement use beyond the user's own service**. These are distinct purposes from a personal health-memory workspace and should not be bundled into core onboarding [S2, S3, S4, S20].
- **Notifications, reminders, device permissions, contacts, location, camera, microphone, and background sync**. UX research and platform patterns support asking close to the moment of need and letting users reverse decisions later [S13, S21].
- **Organizational or role-specific workspaces**. The brief states that organizational/caregiver/clinician access exists only under explicit, scoped, time-boxed, purpose-bound grants; first-run personal onboarding should not silently create or default to those grants [S5, S6, S7].

The right granularity for the MVP is **purpose/resource/action granularity**, not a checkbox for every data field. For the personal core, one clearly named core-purpose consent can cover user-entered health memory and Health Thread organization, provided the notice explains the actions and limits. For optional capabilities, granularity should align to the new purpose and actor: for example, import “heart rate and sleep from Health Connect for trend context,” share “Thread X with Dr. Y until date Z for consultation,” or allow “notifications for reminders.” External health-platform integrations may require data-type granularity because Apple and Google expose permissions that way [S8, S9, S11, S12, S13].

A useful implementation mapping to the existing WellBe consent model is: consent rows should identify the authenticated controller as subject/actor, the relevant resource type such as `workspace`, `health_memory`, `thread`, `document`, `integration`, or `share_grant`, the permitted action such as `create`, `store`, `read`, `process`, `import`, `share`, `notify`, or `analyze`, the purpose, the effective period, and revocation status. For safety, avoid semantics where a missing `resource_id` or missing data category accidentally means “all data for all purposes”; FHIR Consent allows broad provisions, but broad “all data” defaults are exactly where product policy should be explicit and conservative [S2, S5, S6, S7].

### Q2 — Minimal baseline identity & profile

The smallest first-run dataset should be the data needed to authenticate the person, create the controller/workspace relationship, present the product correctly, and let the person begin with their own words. GDPR data minimisation supports collecting only what is adequate, relevant, and necessary, and health data receives heightened protection as special-category data under GDPR-style regimes [S1, S3]. Apple and Google patterns also show that health profile fields can be useful for personalization or estimates, but can be added later rather than being mandatory at first use [S10, S14].

Recommended minimum at first run:

1. **OIDC identity linkage** — the WellBe account should store the OIDC issuer and subject identifier as the canonical external identity key after authentication. OIDC defines `sub` as the end-user subject identifier, and NIST treats the federated identifier as the issuer+subject combination to avoid collisions [S15, S18].
2. **Contact channel from the identity provider, if available** — email or another verified contact claim may support account recovery, security notices, and user communication, but it should not be the canonical identity key because email can change and can collide across identity providers [S15, S18].
3. **Consent and notice metadata** — the product should record notice version, consent version, timestamp, authenticated subject, and the user's explicit choices because consent guidance emphasizes retaining evidence of what the user consented to and when [S2, S5].
4. **Locale/time zone/unit preferences when needed for safe presentation** — time zone and units affect how health timelines, reminders, and measurements are displayed. If these can be inferred from browser/device settings and edited later, they do not need to become a heavy profile step; they should be reviewed rather than silently over-collected [S1, S23].
5. **Eligibility attestation only if legal/product requires it** — age, region, guardian status, or terms eligibility may be necessary, but the exact requirement is a legal decision and should be minimized to what is required [S1, S3].
6. **Optional first concern or goal in the user's own words** — a free-text prompt such as “What would you like WellBe to help you keep track of?” can make the health-memory product immediately useful without asking for a diagnosis. This should be optional/skippable to preserve calm onboarding and avoid self-diagnosis framing [S21, S22, S23].

Recommended optional or deferred fields:

- Date of birth, sex assigned at birth, gender, height, weight, blood type, conditions, allergies, medications, pregnancy status, family history, emergency contacts, and clinician/institution details should be optional and requested only when a feature needs them. Apple asks users for basic health details and allows missing information to be added later; Apple Medical ID fields such as medical conditions, medications, allergies, and emergency contacts are separate and optional [S10]. Google Fit uses height, weight, age, and gender to improve distance and calorie estimates, which illustrates the right pattern: collect profile attributes when they are relevant to a feature's calculation, not as universal onboarding requirements [S14].
- A list of diagnosed conditions should not be required at first run. The brief says WellBe investigates and organizes but does not diagnose, and asking for diagnosis labels at onboarding can push users toward self-diagnosis or over-disclosure before the system needs it. This recommendation is an inference from the brief's “investigate, never diagnose” principle combined with data minimisation and calm-permission UX [S1, S21, S22].
- Third-party identity attributes such as employer, insurer, clinic, or organization should not be required because the brief requires a lone individual with no organization to complete onboarding. If these become relevant later, they should be added through a separate workspace or grant flow [S5, S6, S7].

The leading-product comparison is consistent: Apple Health makes basic health details useful for personalization but not permanently blocking, and Medical ID is a separate optional profile; Google Fit uses profile and goals to improve estimates and defaults/progress but supports adjustment over time [S10, S14]. For WellBe, the MVP should therefore start with “who controls this workspace?” and “what would you like to keep track of?” rather than a medical intake form.

### Q3 — Identity bootstrap vs. OIDC

The recommended ordering is **authenticate first, then onboard and capture consent**. ZITADEL's OIDC guidance describes the application redirecting the user to ZITADEL, the user authenticating there, and the app receiving an authorization code that is exchanged for tokens including an ID token; ZITADEL also recommends Authorization Code with PKCE for modern clients [S16, S17]. OIDC defines the ID token as the way a relying party verifies the end user's identity, and it defines the subject identifier used for the user at the issuer [S15]. NIST guidance emphasizes that a federated identifier is the combination of subject identifier and issuer, that relying parties must account for the issuer to avoid collisions, and that account resolution must avoid associating account information with the wrong federated identifier [S18].

Responsibility split:

| Responsibility | ZITADEL / OIDC provider | WellBe application |
| --- | --- | --- |
| Authenticate the user | Performs login, MFA or recovery if configured, and issues ID/access tokens through OIDC [S16, S17]. | Redirects to provider, validates tokens, state, nonce, issuer, audience, and expiry according to OIDC integration requirements [S15, S16]. |
| Canonical external identity | Provides issuer and subject identifier; may provide profile/email claims if requested [S15]. | Keys the WellBe user/controller account on `(issuer, subject)`, not email alone [S15, S18]. |
| Product identity | Not responsible for WellBe controller/workspace semantics. | Creates or resumes WellBe controller record, personal workspace, onboarding state, consent records, and audit trail. |
| Consent | OIDC consent, if any, concerns identity claims/scopes released to the client. | Captures product-specific health-data processing consent and later point-of-use grants. |
| Duplicate prevention | Provides stable subject identifiers within the issuer; pairwise identifiers may be used to reduce cross-client correlation [S15, S18]. | Enforces unique account mapping for `(issuer, subject)`, idempotent create/resume, and explicit user-driven account-linking if ever needed. |

Authenticate-first is a better fit for this brief than collect-then-bind because it avoids orphaned health data, duplicate accounts, and ambiguous consent subject identity. A collect-then-bind pattern may be acceptable for a no-data marketing preview or a purely local, non-health draft, but it is a poor default for a personal health-memory system because the product would collect sensitive context before knowing which durable controller identity owns it. This is an inference from data minimisation, special-category health-data handling, and federated-identity guidance [S1, S3, S15, S18].

Email should not be the canonical key for WellBe identity. OIDC's stable subject identifier is the intended identifier for the authenticated user at the issuer, while NIST warns relying parties to use the issuer plus subject and to avoid account-linking mistakes [S15, S18]. Email can still be stored as a contact claim if provided and verified by the IdP, but it should not decide controller self-access, workspace ownership, or duplicate detection by itself.

The practical bootstrap should be: after the ZITADEL callback succeeds, WellBe performs `get_or_create_account_by_issuer_subject`, creates or resumes a `pending_onboarding` record, and only then shows the product onboarding/consent screens. On successful final confirmation, WellBe atomically creates the controller self-access identity, personal workspace, core consent records, and audit event. This keeps OIDC authentication separate from WellBe's product-specific controller and consent semantics [S2, S5, S6, S15, S16, S18].

### Q4 — Abandonment / resume / idempotency

The safe pattern is **pending state until explicit final confirmation**. FHIR Consent includes status concepts such as draft and active, which maps well to storing consent choices without making them effective during onboarding [S6, S7]. HIPAA authorization rules treat authorizations as defective if incomplete, expired, revoked, or otherwise invalid, which reinforces the product rule that an incomplete onboarding flow should not silently grant access or activate processing [S5]. ICO consent guidance also emphasizes evidence, management, review, and easy withdrawal rather than hidden or inferred consent [S2].

Recommended abandonment/resume states:

| State | What exists | What must not exist yet | Resume behavior |
| --- | --- | --- | --- |
| No authenticated identity | No durable server health record; at most local UI state or anonymous non-health preview. | No controller workspace, no health-memory storage, no active consent scopes. | Send the user through ZITADEL authentication before any durable health-data onboarding. |
| Authenticated but onboarding incomplete | Account shell keyed by `(issuer, subject)`, pending onboarding record, draft choices, notice version, timestamp/progress metadata. | No active core consent rows; no active personal workspace grants; no third-party grants. | Load the same pending record after OIDC login and let the user continue, edit, decline, or delete the pending draft. |
| Final confirmation in progress | Server receives explicit final consent/account activation request with an idempotency key. | Duplicate workspace, duplicate controller identity, duplicate consent rows. | Repeated submissions return the same result; server finalization is atomic. |
| Active onboarding complete | Controller record, personal workspace, active core processing records, audit event, and consent dashboard. | No optional grants unless the user separately made them. | Returning user signs in and lands in the active personal workspace. |
| User declined core consent | Account shell may remain only if needed for account deletion/retry, subject to retention policy. | No active personal workspace and no health-memory processing. | Explain that the personal workspace cannot be activated without core processing; provide retry, delete account, or exit. |

The final submit should be both **atomic** and **idempotent**. Stripe's API idempotency model is not a health standard, but it is a mature production pattern: clients send an idempotency key for create/update operations, and retries with the same key return the original result rather than creating duplicates [S19]. WellBe can apply the same idea to onboarding finalization: the server should treat repeated final-confirmation requests for the same `(issuer, subject, onboarding_session_id, consent_version)` as the same operation, and it should reject conflicting replays with different parameters.

Identity idempotency should be anchored on `(issuer, subject)`. OIDC and NIST both support this because the subject is stable within an issuer and the issuer must be included to avoid collisions [S15, S18]. Product records should have uniqueness constraints so the same OIDC identity cannot create multiple MVP personal-controller accounts by refreshing, using the browser back button, or abandoning and returning later.

Consent idempotency should be versioned. A final activation record should capture the exact notice/consent version, choices, timestamp, user identity, and workspace being activated. If the product changes the core consent text before the user resumes, the user should see the current version and explicitly confirm it; the old draft should not silently activate under changed terms. ICO and HIPAA-style authorization rules both emphasize the content of what was consented to and evidence of that authorization [S2, S5].

Abandoned pending records should have a retention policy. The sources do not prescribe a WellBe-specific duration, but data minimisation and special-category caution suggest retaining only what is necessary to let the user resume and deleting stale pending drafts after a defined period [S1, S3]. The retention period and any reminder email are product/legal decisions.

### Q5 — Calm, non-coercive, accessible consent UX

A legally robust health-data consent flow can still be calm if it uses **layered notices**: a short plain-language summary first, a clear statement of what the product needs and why, and links or expandable sections for detailed privacy terms. ISO/IEC 29184 is specifically about online privacy notices and consent processes, and ICO guidance requires consent requests to be prominent, concise, easy to understand, separate from other terms, and granular by purpose [S2, S4].

Concrete UX patterns for WellBe:

1. **Plain-language consent cards** — one card for the core personal workspace, with a brief “What this allows,” “What this does not allow,” and “You can change/delete later” structure. This reduces ambiguity without turning onboarding into a legal wall [S2, S4, S22].
2. **Separate optional decisions** — do not ask for imports, sharing, notifications, research, or model-training use on the same checkbox as the core workspace. ICO guidance explicitly disfavors bundled consent and supports granular options for different purposes and processing types [S2].
3. **Just-in-time prompts** — ask for Apple Health, Health Connect, EHR, caregiver sharing, reminders, or other optional capabilities only when the user chooses that feature. Apple and Google health ecosystems use data-type/app-specific permission prompts and revocation controls, and UX research supports timing permission requests near the moment of value [S8, S9, S11, S12, S13, S21].
4. **Equal, consequence-clear decline paths** — optional declines should be easy and consequence-free except that the specific optional feature stays off. If core consent is declined, the product can explain that a personal health-memory workspace cannot be activated without storing and processing user-provided health data, but it should not shame, alarm, or pressure the user [S2, S20, S21].
5. **Visible revocation and privacy dashboard** — after onboarding, a privacy/consent page should list active core processing, connected imports, shares, notification preferences, and optional analysis/research choices, with clear revoke/disable actions. ICO guidance recommends making withdrawal easy and keeping consent under review; Apple and Google products expose permission-management controls [S2, S8, S9, S11, S12].
6. **Accessible form behavior** — every consent control needs a clear label or instruction, error states must identify what is wrong in text, and keyboard focus must be visible. WCAG guidance on labels/instructions, error identification, and focus appearance is directly applicable to consent and onboarding forms [S23].
7. **Calm medical framing** — use language such as “organize your health context,” “keep track of concerns,” and “prepare questions,” and avoid words that imply diagnosis, emergency triage, or clinical certainty. This is an inference from the brief's non-diagnosis principle combined with dark-pattern and progressive-disclosure UX guidance [S20, S21, S22].

Anti-patterns to avoid:

- Pre-checked boxes, implied consent, or consent hidden inside general Terms of Service [S2, S20].
- A single “I agree to everything” checkbox that bundles core storage, imports, sharing, research, analytics, marketing, and model training [S2, S4, S20].
- Making optional consent a condition for using the personal core, unless the optional processing is genuinely necessary for that specific feature [S2, S5].
- False urgency, alarming health language, repeated prompts after a decline, burying key terms, confusing toggles, or steering design that nudges users toward maximum data sharing [S20, S21].
- Revocation flows that are harder than consent flows, or settings pages that hide which actors and integrations currently have access [S2, S8, S9, S11, S12, S20].
- Consent screens that are inaccessible to keyboard or screen-reader users, rely only on color, or fail to show form errors clearly [S23].

## Approaches considered

### Approach 1 — Authenticate first, then minimal core consent and progressive point-of-use grants

**What it does |** The user chooses “new user,” authenticates through ZITADEL/OIDC, WellBe creates or resumes a pending account keyed on `(issuer, subject)`, then shows layered MVP onboarding for core personal-workspace consent and minimal baseline profile. Optional features ask later at point of use.

**Pros |** Best duplicate-prevention because the account is keyed on a stable federated identifier; best fit with ZITADEL Authorization Code with PKCE; avoids orphaned health data; supports audited, explicit consent; naturally supports resume; aligns with Apple/Google-style just-in-time optional permissions and ICO/ISO granular-consent guidance [S2, S4, S8, S11, S15, S16, S17, S18].

**Cons |** Requires the user to authenticate before seeing much product value. Requires a pending-onboarding state and a clean explanation that core health-memory processing is necessary to activate the personal workspace. Later point-of-use prompts require careful UX so the product does not feel interruptive [S21, S22].

**Fit with our constraints (§5) |** Strongest fit. A lone individual can complete it; consent is explicit and granular; the up-front/point-of-use line is clear; the baseline can be minimal; OIDC composition is clean; abandonment is safe; regulatory norms are well supported [S1, S2, S3, S4, S5, S15, S18].

### Approach 2 — Collect a light draft first, then authenticate and bind

**What it does |** The user first answers a few onboarding questions, perhaps including a first concern or goal, then authenticates and binds that draft to an OIDC identity.

**Pros |** May feel lower-friction because the user experiences product context before signing in. It can help users understand why an account is needed if the pre-auth stage contains no sensitive data [S21, S22].

**Cons |** Risky if the draft contains health data: it can create orphaned sensitive records, ambiguous consent subject identity, duplicate accounts, and harder deletion/resume semantics. It is also less aligned with NIST account-resolution caution and OIDC's role as the identity proofing/authentication layer [S1, S3, S15, S18].

**Fit with our constraints (§5) |** Weak unless restricted to a non-health preview with no durable server persistence. It does not naturally satisfy safe abandonment, no duplicates, and source-linked auditable consent for a health-memory product.

### Approach 3 — Authenticate first, create account shell, defer even core consent until first capture

**What it does |** The user authenticates and lands in an empty shell workspace. The app asks for core health-memory consent only when the user first enters or uploads health information.

**Pros |** Minimizes up-front consent requests and may let the user browse a tour, settings, or empty workspace before committing. It avoids collecting health content before consent if implemented strictly [S1, S21, S22].

**Cons |** The product's main value depends on health-memory storage and organization, so the user may immediately encounter blocked features or repeated prompts. It can under-communicate the trust relationship because onboarding is the first consent surface and defines the product's role [S2, S4].

**Fit with our constraints (§5) |** Mixed. It satisfies authentication and can be safe, but it is less useful as an MVP first-run flow and may produce confusing “feature unavailable until consent” moments. It is better as an optional tour mode than as the default activation path.

### Approach 4 — Full consent bundle up front

**What it does |** First run asks the user to consent to the personal workspace plus imports, sharing, notifications, research/cross-patient analysis, model training, and other future capabilities in one broad onboarding package.

**Pros |** Simpler implementation and fewer prompts later. It may make feature enablement seem smooth in the short term.

**Cons |** Conflicts with granular consent, data minimisation, and non-coercive UX. It increases consent fatigue, risks bundled or invalid consent, makes optional sharing/research feel like a condition of core use, and resembles dark-pattern steering toward maximum data use [S1, S2, S3, S4, S20, S21].

**Fit with our constraints (§5) |** Poor. It violates the brief's explicit constraints that consent be scoped, revocable, non-bundled, calm, and minimal up front.

## Recommendation

Recommend **Approach 1 — authenticate first, then minimal core consent and progressive point-of-use grants**.

Concrete MVP flow:

1. **Front door** — show calm choices: “New to WellBe,” “Sign in,” and explicit workspace switching if applicable. This brief covers the new-user path and identity bootstrap.
2. **ZITADEL authentication** — redirect the new user through OIDC Authorization Code with PKCE. WellBe validates the OIDC response and obtains the issuer and subject identifier [S15, S16, S17].
3. **Account/onboarding resume** — server performs `get_or_create_by_issuer_subject`. If onboarding is pending, resume it; if active, sign in normally; if no record exists, create a pending account shell and pending onboarding state. The canonical key is `(issuer, subject)`, not email [S15, S18].
4. **Layered welcome and core consent** — present the core personal-workspace consent separately from general terms and optional features. The consent should explicitly cover creating the personal workspace, storing/retrieving user-provided health memory, organizing/linking that content into Health Threads for the user's own use, and maintaining privacy/security/audit records [S2, S4, S5, S6].
5. **Minimal baseline profile** — collect or confirm only minimal identity/presentation fields: contact claim from IdP if available, display name or preferred name if useful, locale/time zone/unit preferences if needed, required eligibility attestation if legal requires it, and an optional first concern or goal in the user's own words. Allow skipping the health-goal prompt [S1, S10, S14, S22].
6. **Explicit final confirmation** — do not activate any consent scope until the user makes a clear final action. On final submit, atomically create the active controller record, personal workspace, controller self-access, core consent records, and audit event with notice/consent versions [S2, S5, S6, S19].
7. **Point-of-use permissions after activation** — ask later for imports, sharing, organization workspaces, caregivers/clinicians, notifications, research/cross-patient analysis, model training, device permissions, and external integrations. Each prompt should name the resource/data, action, recipient or actor where relevant, purpose, duration or expiry, and revocation path [S5, S6, S7, S8, S9, S11, S12, S13].
8. **Privacy/consent dashboard** — provide an always-available page that shows active core processing, imports, shares, optional analysis/research preferences, and revocation/disable controls [S2, S8, S9, S11, S12].

Accepted trade-offs:

- **Higher trust and safer identity over lower first-click friction.** Authentication before health onboarding adds a step, but it prevents orphaned health drafts and duplicate controller identities [S15, S16, S18].
- **One up-front core consent over pure just-in-time consent.** Because WellBe's personal core cannot function without storing and organizing user-provided health memory, a narrow up-front core consent is justified. Optional features still move to point-of-use [S1, S2, S4, S21].
- **More later prompts over broad bundled consent.** Deferring imports, sharing, research, notifications, and device permissions reduces over-collection and improves consent quality, but it requires consistent UX patterns so prompts are understandable rather than annoying [S2, S8, S11, S21, S22].
- **Product simplicity over medical completeness.** The MVP should avoid a medical-intake style profile. This may reduce personalization early, but it better supports data minimisation, calm onboarding, and “investigate, never diagnose” [S1, S10, S14].

## Open risks / unknowns

1. **Exact lawful basis and jurisdictional model.** Product/legal must decide the GDPR Article 6 basis and Article 9 condition for core personal health processing, whether consent is the legal basis or only the UX/control mechanism, and how this varies by region [S1, S2, S3].
2. **HIPAA and consumer-health-law applicability.** HIPAA authorization concepts are useful design analogues, but legal must determine whether WellBe is a covered entity, business associate, or neither, and assess state or country-specific consumer health privacy laws [S5].
3. **Minors and guardian consent.** The minimum age, parental/guardian authorization, and age-verification burden are unresolved legal/product decisions [S1, S3].
4. **Core-consent withdrawal behavior.** The team needs a policy for what happens if a user revokes the core processing needed to operate the personal workspace: disable workspace, export/delete data, retain legal/audit records, and define retention windows [S2, S3, S5].
5. **Retention for abandoned pending onboarding.** The recommendation requires a limited pending state, but the retention period and deletion/reminder policy are still open [S1, S3].
6. **OIDC account linking beyond MVP.** The MVP should key on `(issuer, subject)`. If the product later supports multiple IdPs, email changes, or account linking, it needs a high-assurance user-driven linking flow to avoid attaching health data to the wrong identity [S15, S18].
7. **MFA and account recovery requirements.** ZITADEL can support strong authentication patterns, but the brief does not specify MFA, passkeys, recovery policies, or risk-based controls for health data access [S16, S17, S18].
8. **AI/subprocessor/model-use disclosures.** If WellBe uses external AI services, subprocessors, or any training/improvement use beyond processing for the user's own workspace, product/legal must decide whether separate consent, notice, opt-out, or prohibition is required [S2, S3, S4].
9. **Exact consent-scope taxonomy.** The existing service has consent scopes and share grants, but product policy still needs to define the canonical resource types, actions, purpose labels, expiry defaults, and whether broad workspace-level scopes are ever acceptable [S5, S6, S7].
10. **Plain-language and accessibility validation.** The recommended patterns should be tested with users, including assistive-technology users, and reviewed for reading level, localization, error handling, and low-anxiety language [S20, S21, S22, S23].
