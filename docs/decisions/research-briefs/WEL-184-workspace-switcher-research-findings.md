# WEL-184 Workspace Switcher Research Findings

Prepared for WellBe C17 workspace identity + switcher scoping research on 2026-06-18.

## Summary

The safest pattern for WellBe is a personal-first workspace selector that enumerates only contexts returned by the authorization-backed workspace/membership enumeration API, keeps the personal workspace always visible, and makes every non-personal workspace a visibly bounded “acting in/for” mode rather than a second login or an institutional home. This follows common SaaS switchers that show only signed-in or accessible workspaces, proxy-access healthcare flows that show “Acting for” banners, and delegated-access financial/government flows that require explicit authorization rather than credential sharing or default access. [B1] [S1] [S6] [S10] [S13]

A context switch should change visible data, available surfaces, and actions only through the active C17 access predicate; the UI should never fetch or render resources outside that predicate and should fail closed when the predicate is absent, stale, expired, revoked, or mismatched to the selected workspace. [B1] [S18] [S19] [S21] [S22]

Non-personal contexts should carry persistent indicators: subject/controller, role, purpose, capability summary, expiry, and audit status. This is consistent with AWS role-switch visual cues, NHS proxy “Acting for” banners, and usability research showing that poorly signaled modes cause user errors. [S4] [S13] [S25] [S26]

The common single-workspace case should not feel like an empty enterprise switcher: show “Your workspace” as the active identity and place the one-item workspace control near account/profile or the app shell, while exposing sharing/grant management separately. Notion’s guidance to start with one workspace and Open Banking’s guidance that consent dashboards must be findable but not confusing both support this split. [S5] [S27] [S28]

The authenticated session should remain one user session; active workspace is an in-session scope that is refreshed and enforced on every scoped request. Mainstream products commonly switch accounts/workspaces without full sign-out, while identity standards support reauthentication/step-up for sensitive or stale sessions and token introspection/revocation patterns for active-state checks. [S2] [S3] [S5] [S24] [S32] [S33]

The recommended trade-off is deliberate friction for non-personal, aggregate, export, invite, and research contexts. This adds one extra acknowledgement or step-up in higher-risk cases, but it reduces mode errors, stale-scope bugs, grant leakage, and accidental implication that an institution controls individual data. [B1] [S20] [S21] [S24] [S25]

This document assumes only the WellBe brief and the external sources below; no source code, running product, or team-specific information was used. Recommendations labeled “synthesis/inference” are design judgments derived from cited patterns rather than claims made directly by any one source. [B1]

## Sources reviewed

- **[B1] Research Brief — Workspace Switcher: Presentation & Scoping (C17)** — WellBe, 2026, URL: not public; provided in task prompt. **Credibility note:** Binding internal product/technical constraints for this research, but not independently verifiable.

- **[S1] “Switch between workspaces”** — Slack, 2026/accessed 2026, URL: https://slack.com/help/articles/1500002200741-Switch-between-workspaces. **Credibility note:** Official Slack help documentation for workspace switching behavior.

- **[S2] “Switching between accounts”** — GitHub Docs, 2026/accessed 2026, URL: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/switching-between-accounts. **Credibility note:** Official GitHub documentation for multi-account switching and session behavior.

- **[S3] “Sign in to multiple accounts at once”** — Google Account Help, 2026/accessed 2026, URL: https://support.google.com/accounts/answer/1721977. **Credibility note:** Official Google Account help for concurrent account sessions and switching cautions.

- **[S4] “Switch from a user to an IAM role (console)”** — Amazon Web Services IAM User Guide, 2026/accessed 2026, URL: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-console.html. **Credibility note:** Official AWS documentation for role switching, active-role display name/color, and changed permissions.

- **[S5] “Create, join & leave workspaces”** — Notion Help Center, 2026/accessed 2026, URL: https://www.notion.com/help/create-delete-and-switch-workspaces. **Credibility note:** Official Notion workspace guidance, including one-workspace simplicity, workspace separation, switcher placement, and token expiry.

- **[S6] “How to switch between apps and organizations”** — Atlassian Support, 2026/accessed 2026, URL: https://support.atlassian.com/platform-experiences/docs/how-to-switch-between-apps-and-organizations/. **Credibility note:** Official Atlassian guidance for listing apps/sites/organizations a user has access to and hiding unrelated organization content.

- **[S7] “Manage accounts and organizations in Microsoft Teams”** — Microsoft Support, 2026/accessed 2026, URL: https://support.microsoft.com/en-US/teams/notifications-settings/manage-accounts-and-organizations-in-microsoft-teams. **Credibility note:** Official Microsoft guidance for switching accounts/organizations and one active account/activity context.

- **[S8] “How to switch between companies”** — Intuit QuickBooks Help, 2026/accessed 2026, URL: https://quickbooks.intuit.com/learn-support/en-us/help-article/company-file/switch-companies/L0YcDeQPP_US_en_US. **Credibility note:** Official QuickBooks guidance for switching between companies/client files and permission-based visibility.

- **[S9] “Delegated authority guidance”** — GOV.UK / Government Digital Service, 2024/accessed 2026, URL: https://www.gov.uk/guidance/delegated-authority-guidance. **Credibility note:** UK government service-design guidance for acting on behalf of another person and verifying evidence of authority.

- **[S10] “How to get authorised to act as a tax agent on behalf of your clients”** — HM Revenue & Customs, 2022; updated 2026, URL: https://www.gov.uk/guidance/how-to-get-authorised-to-act-as-a-tax-agent-on-behalf-of-your-clients. **Credibility note:** Official HMRC delegated-agent authorization guidance, including prohibition on using client credentials.

- **[S11] “Authorise an agent for taxes that use the digital handshake”** — HM Revenue & Customs, 2026/accessed 2026, URL: https://www.gov.uk/guidance/authorise-an-agent-to-deal-with-certain-tax-services-for-you. **Credibility note:** Official HMRC user-facing authorization flow with time-limited links and user-managed removal.

- **[S12] “Assisting someone with their money”** — HSBC UK, 2026/accessed 2026, URL: https://www.hsbc.co.uk/help/life-events/assisting-someone-with-their-money/. **Credibility note:** Official bank guidance for third-party access and third-party mandates.

- **[S13] “Manage health services for others”** — NHS App Help, 2026/accessed 2026, URL: https://www.nhs.uk/nhs-app/help/profile/manage-health-services-for-others/. **Credibility note:** Official NHS App proxy-access user guidance showing “Acting for” banner behavior and permissions examples.

- **[S14] “Manage health services for others in the NHS App (proxy access)”** — NHS England Digital, updated 2026-06-08, URL: https://digital.nhs.uk/services/nhs-app/nhs-app-features/manage-health-services-for-others-in-the-nhs-app-proxy-access. **Credibility note:** Official NHS England Digital implementation/service guidance for proxy access, feature-level permissions, time limits, safeguarding, and escalation.

- **[S15] “How to get proxy access”** — NHS, reviewed 2024/accessed 2026, URL: https://www.nhs.uk/nhs-services/gps/gp-services-for-someone-else-proxy-access/how-to-get-proxy-access/. **Credibility note:** Official NHS public guidance on proxy access approval, refusal, and available services.

- **[S16] “Consent — Detailed Descriptions”** — HL7 FHIR R5, 2023/accessed 2026, URL: https://fhir.hl7.org/fhir/consent-definitions.html. **Credibility note:** Primary healthcare interoperability standard describing consent as choices about actors, actions, purposes, and periods.

- **[S17] “AuditEvent”** — HL7 FHIR R5, 2023/accessed 2026, URL: https://fhir.hl7.org/fhir/auditevent.html. **Credibility note:** Primary healthcare interoperability standard for security/privacy event recording, including who/what/where/when/why.

- **[S18] “Security and Privacy Module”** — HL7 FHIR R5, 2023/accessed 2026, URL: https://fhir.hl7.org/fhir/secpriv-module.html. **Credibility note:** Primary healthcare interoperability standard covering access control, consent, audit, provenance, and preventing information leakage.

- **[S19] “Security Labels”** — HL7 FHIR R6 CI Build/Ballot, 2026/accessed 2026, URL: https://build.fhir.org/security-labels.html. **Credibility note:** HL7 current build guidance on labels used by access-control engines to determine which resources are returned and handling caveats; ballot/current-build status means less stable than R5.

- **[S20] “45 CFR § 164.312 — Technical safeguards”** — U.S. Electronic Code of Federal Regulations, current/accessed 2026, URL: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312. **Credibility note:** Authoritative U.S. HIPAA Security Rule text for access control, unique user identification, emergency access, automatic logoff, and audit controls.

- **[S21] “Authorization Cheat Sheet”** — OWASP Cheat Sheet Series, current/accessed 2026, URL: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html. **Credibility note:** Widely used application-security guidance; especially relevant to not relying on client-side checks.

- **[S22] “ASVS V4 Access Control”** — OWASP Application Security Verification Standard, current/accessed 2026, URL: https://github.com/OWASP/ASVS/blob/master/4.0/en/0x12-V4-Access-Control.md. **Credibility note:** Widely used application-security verification standard for least privilege, fail-secure access control, and IDOR prevention.

- **[S23] “Guide to Attribute Based Access Control (ABAC) Definition and Considerations,” NIST SP 800-162** — NIST, 2014; updated page 2019/accessed 2026, URL: https://csrc.nist.gov/pubs/sp/800/162/upd2/final. **Credibility note:** U.S. government security guidance for attribute-based authorization decisions over subjects, objects, operations, and environment.

- **[S24] “Digital Identity Guidelines: Authentication and Lifecycle Management,” NIST SP 800-63B** — NIST, current/accessed 2026, URL: https://pages.nist.gov/800-63-4/sp800-63b.html. **Credibility note:** U.S. government digital-identity guidance for sessions, reauthentication, token/session considerations, and assurance levels.

- **[S25] “Modes in User Interfaces: When They Help and When They Hurt Users”** — Page Laubheimer, Nielsen Norman Group, 2019, URL: https://www.nngroup.com/articles/modes/. **Credibility note:** Established usability research explaining why poorly signaled modes cause user errors.

- **[S26] “Indicators, Validations, and Notifications: Pick the Correct Communication Option”** — Kim Flaherty, Nielsen Norman Group, 2024, URL: https://www.nngroup.com/articles/indicators-validations-notifications/. **Credibility note:** Established usability guidance on when passive indicators are sufficient and when action-required notifications should be intrusive.

- **[S27] “AIS Consent Dashboard”** — Open Banking UK Customer Experience Guidelines, published/latest 2026-03-18, URL: https://standards.openbanking.org.uk/customer-experience-guidelines/dashboards/ais-consent-dashboard-revocation-refresh/v3-1-2/. **Credibility note:** Regulated financial-data-sharing UX standard for consent dashboards, revocation, data categories, duration, and clear labels.

- **[S28] “Revocation”** — Open Banking UK Customer Experience Guidelines, 2024/accessed 2026, URL: https://standards.openbanking.org.uk/customer-experience-guidelines/introduction/revocation/v4-0/. **Credibility note:** Regulated financial-data-sharing UX standard emphasizing findable dashboards and low-friction revocation.

- **[S29] “Consumer consent, authorisation and dashboards”** — Office of the Australian Information Commissioner, 2026/accessed 2026, URL: https://www.oaic.gov.au/consumer-data-right/consumer-data-right-guidance-for-business/privacy-obligations/consumer-consent%2C-authorisation-and-dashboards. **Credibility note:** Official Consumer Data Right privacy guidance on voluntary, express, informed, specific-purpose, time-limited, withdrawable consent.

- **[S30] “How the Consumer Data Right opt-in process works”** — Office of the Australian Information Commissioner, 2026/accessed 2026, URL: https://www.oaic.gov.au/consumer-data-right/information-for-consumers/how-the-consumer-data-right-opt-in-process-works. **Credibility note:** Official consumer-facing CDR guidance on opt-in data sharing, dashboards, expiry, and withdrawal.

- **[S31] “OAuth 2.0 Rich Authorization Requests,” RFC 9396** — IETF / RFC Editor, 2023, URL: https://www.rfc-editor.org/rfc/rfc9396.html. **Credibility note:** Internet Standards Track RFC for fine-grained authorization request details beyond coarse OAuth scopes.

- **[S32] “OAuth 2.0 Token Introspection,” RFC 7662** — IETF / RFC Editor, 2015, URL: https://www.rfc-editor.org/info/rfc7662/. **Credibility note:** Internet Standards Track RFC for checking whether a token is active and retrieving authorization context metadata.

- **[S33] “OAuth 2.0 Token Revocation,” RFC 7009** — IETF / RFC Editor, 2013, URL: https://datatracker.ietf.org/doc/html/rfc7009. **Credibility note:** Internet Standards Track RFC for invalidating access/refresh tokens and related grant-derived tokens.

- **[S34] “Break-the-Glass”** — UI Health Care Epic Education / University of Iowa, 2026/accessed 2026, URL: https://epicsupport.sites.uiowa.edu/epic-resources/break-glass. **Credibility note:** Healthcare-organization training source describing Epic restricted-record access, reason entry, audit trail, and compliance notification.

- **[S35] “My Health Record: Locked Records — Emergency Access to MHR ‘Breakglass’”** — Government of Western Australia Department of Health, 2018/accessed 2026, URL: https://www.health.wa.gov.au/-/media/Files/Corporate/general-documents/My-health-record/Emergency-Break-Glass-Procedure.pdf. **Credibility note:** Official health-system procedure for emergency access, documentation, patient-visible access history, and oversight review; older but still useful as a health-sector pattern.

## Findings by question

### Q1 — Enumeration & presentation without leakage

Comparable products generally enumerate only contexts that the authenticated user is already entitled to use, rather than exposing a global directory of possible contexts. Slack’s switcher lists workspaces the user is signed into, Atlassian’s app switcher lists apps/sites the user has access to and filters by selected organization, and QuickBooks notes that a client company appears only when the user has the needed permission or has been added to the firm/client file. [S1] [S6] [S8]

Healthcare and delegated-access examples use an even stricter pattern: a proxy or agent context appears only after an external authority or the controller has set up authorization. NHS App proxy access appears after GP setup and consent/safeguarding checks, while HMRC requires client authorization and explicitly tells agents not to use the client’s credentials. [S10] [S13] [S14] [S15]

The no-leakage implication for WellBe is that the switcher should be a view over active, displayable memberships/grants for the signed-in actor, not a searchable directory of patients, clinicians, organizations, dependents, research protocols, or possible grants. This is a synthesis from SaaS switchers that list only accessible contexts and WellBe’s own rule that no audience gets default access or should learn about grants/workspaces they should not see. [B1] [S1] [S6] [S8]

A useful presentation hierarchy is: **Personal**, then **Acting for someone / delegated individual**, then **Clinical or care-team work**, then **Institution aggregate**, then **Research sandbox**, with development/test workspaces clearly grouped as testing contexts rather than default homes. This grouping is a synthesis from WellBe’s workspace types, NHS proxy “acting for” language, Atlassian organization filtering, and AWS role-switch labeling. [B1] [S4] [S6] [S13]

Labels should emphasize the controller and role rather than the distributor or institution. For example, “Your workspace,” “Acting for Jordan — caregiver — specific thread — until 2026-07-15,” or “Institution continuity — aggregate only — no individual records” is safer than “Hospital workspace” because WellBe’s invariant is that the individual remains data controller and institutions are not default data controllers. [B1] [S13] [S16] [S27] [S29]

The switcher should not show hidden or ineligible contexts as locked rows. In financial-data-sharing guidance, users manage consents they gave through dashboards that show the data, duration, and receiving party; the guidance does not suggest exposing unavailable accounts or potential third parties as locked options. [S27] [S28] [S30]

The switcher can safely show “missing context” troubleshooting only after the user independently names an expected context, using generic wording that avoids confirming the existence of another person’s data. QuickBooks frames missing company visibility as a permission/addition issue, and NHS proxy guidance directs users to the GP practice or permission settings when expected services are missing. [S8] [S14]

Presentation should distinguish **role** from **account identity**. GitHub, Google, Notion, and Teams all allow multiple accounts or workspaces inside a session-like experience, but WellBe’s model is not “log in as the patient” or “log in as the institution”; the authenticated actor remains one user, and the workspace is the currently selected authorization scope. [B1] [S2] [S3] [S5] [S7]

Delegated-access services are explicit that acting on behalf of someone requires evidence or authorization, not credential sharing or assumed access. GOV.UK delegated-authority guidance says services need evidence of authority; HMRC warns agents not to use client credentials; HSBC describes third-party account operation as a specific mandate or third-party-access arrangement. [S9] [S10] [S12]

Open Banking and Consumer Data Right guidance supports making consent/grant management findable and understandable without turning every possible grant into a switcher item. Consent dashboards should show what data is shared, with whom, for how long, and how to revoke; OAIC/CDR guidance emphasizes voluntary, active, informed, purpose-specific, time-limited, withdrawable consent with no default/preselected consent. [S27] [S28] [S29] [S30]

Break-the-glass patterns are not a good default enumeration model for WellBe because they intentionally allow exceptional emergency access outside normal consent paths. When used in health systems, break-the-glass flows require reason entry, audit trails, oversight notification, and often emergency justification/authorization; they should remain exceptional, not a normal workspace-switcher choice. [B1] [S20] [S34] [S35]

**Answer to Q1:** enumerate only the contexts the signed-in actor may currently act in; group them by role/purpose with the personal workspace first; label delegated and aggregate contexts by controller, role, purpose, expiry, and capability class; never show locked or suggested contexts that would reveal a patient, grant, organization relationship, or research cohort the actor is not already entitled to see. This is a synthesis from the cited SaaS, healthcare proxy, delegated-authority, and consent-dashboard sources. [B1] [S1] [S6] [S13] [S27]

### Q2 — What a context switch should change, and how to signal it

A workspace switch is a mode change: the same visible controls may have different consequences depending on the active workspace. Nielsen Norman Group warns that modes are error-prone when users do not notice which mode they are in, and recommends visible state indicators to keep the mode apparent. [S25]

Comparable products make the active context persistently visible. AWS replaces the username area with the selected role display name and color and explicitly says that the active role changes permissions; NHS App proxy access shows a yellow “Acting for” banner with the other person’s name and a switch-back affordance; Slack can keep a workspace switcher visible in the sidebar. [S1] [S4] [S13]

For WellBe, switching should change three things and signal all three: the **data scope** that may be visible, the **actions/capabilities** allowed, and the **surfaces/features** available. This maps directly to the C17 access predicate’s resource filters, data categories, security labels, capabilities, obligations, and expiry. [B1]

The persistent indicator should include, at minimum, the active workspace name, role, data subject/controller or “aggregate only” status, purpose, expiry/review date when applicable, and a short capability summary such as “read + comment; no export.” This is a synthesis from NHS proxy subject labeling, Open Banking dashboard requirements to show data/duration, FHIR Consent’s purpose/period/action model, and AWS active-role display cues. [S4] [S13] [S16] [S27]

Non-personal workspaces should use a more prominent entry confirmation than personal-workspace navigation. NN/g guidance distinguishes passive indicators from action-required notifications, and NIST identity guidance supports reauthentication when session assurance or freshness is insufficient; entering a different subject’s health context, export-capable context, invite-capable context, aggregate/research context, or break-glass-like emergency context is higher risk than ordinary navigation. [S24] [S26] [S34] [S35]

A safe switch confirmation should say what will change before entry: “You are acting for [person/controller] as [role] for [purpose]. You can [capabilities]. Access expires [date/time]. Views are audited.” This is a synthesis from NHS proxy banners, Open Banking/CDR consent dashboards, FHIR Consent/AuditEvent, and WellBe’s audit/predicate obligations. [B1] [S13] [S16] [S17] [S27] [S30]

Color can help but should not be the only cue. AWS uses color for role-switch awareness, but accessibility and safety argue for text labels and layout changes because color-only cues can be missed by users with visual impairments or in low-attention states; NN/g’s indicator guidance supports placing state information near the affected element and making it conditional and contextual. [S4] [S26]

The switch should clear or scope transient UI state that could otherwise cross contexts: selected resources, search results, export queues, invite drafts, comments, uploads, clinical notes, and copied link targets should be tied to the originating workspace and either hidden or require explicit confirmation before reuse in another workspace. This is a security/UX synthesis from OWASP’s warning not to rely on client-side state for authorization, NN/g’s mode-error warning, and WellBe’s resource-filtered predicate requirement. [B1] [S21] [S25]

External or deep links should not silently drop the user into a non-personal or different-subject context. GitHub prompts users to choose an account for external links when multiple accounts could apply; the analogous WellBe pattern is to resolve the link to a workspace only if the user has an active matching membership/grant, otherwise show a neutral “not available in your current workspace” or “choose a workspace” flow that does not reveal unauthorized context details. [B1] [S2]

Aggregate and cross-patient views need additional signaling because WellBe forbids them as defaults. A context labeled “aggregate only,” with no individual-level record affordances, and an explicit “enter aggregate view” choice better matches Open Banking/CDR opt-in consent principles and WellBe’s cross-patient comparison constraints. [B1] [S27] [S29] [S30]

Break-the-glass patterns show that exceptional access must be noisy, justified, audited, and reviewed. University of Iowa’s Epic training says users outside the immediate care team must enter a reason and that audit/compliance notification occurs; the Western Australia procedure requires emergency conditions, authorization/documentation, patient-visible access history, and oversight review. [S34] [S35]

**Answer to Q2:** switching should visibly and functionally change only the currently authorized data, actions, and surfaces; the active context should remain obvious through a persistent header/banner/chip; higher-risk entries should require acknowledgement or step-up; and cross-context drafts, selections, links, and caches should be reset or scoped so accidental cross-context actions are hard to perform. [B1] [S4] [S13] [S21] [S24] [S25]

### Q3 — Enforcing the controller/grant invariant in the UI

The UI should treat the server-side C17 access predicate as the only authority for what may be displayed or acted on. OWASP says client-side access checks are only for user experience and must not be relied on for security, and OWASP ASVS requires access to only permitted resources, least privilege, fail-secure behavior, and protection from IDOR-style resource access. [B1] [S21] [S22]

The UI should receive a display-safe predicate summary or “presentation entitlement” for the active workspace and use it to configure navigation, feature availability, resource filters, and action affordances. This is a synthesis from NIST ABAC’s subject/object/action/environment model, FHIR security labels that guide which resources are returned, and WellBe’s C17 predicate design. [B1] [S19] [S23]

Out-of-scope data should never be fetched “then hidden.” FHIR Security and Privacy guidance emphasizes that data should be discovered/accessed/altered only according to policy and that errors should not leak information; WellBe’s brief already requires downstream reads to be constrained before retrieval/search/export. [B1] [S18]

The UI should hide actions that are not part of the active workspace’s permitted capability set, especially high-risk actions such as export, invite, run analysis, and view aggregate. This avoids implying that the actor has latent entitlement and reduces accidental triggering of denied flows; server-side enforcement remains mandatory. [B1] [S21] [S22]

Disabling with explanation is appropriate when the user can legitimately know the feature exists but lacks the current grant capability, such as a caregiver who can comment but not export within a visible shared thread. The explanation should name the missing capability generically, for example “Export is not included in this grant,” rather than exposing hidden people, grants, or institutional relationships. This is a synthesis from NN/g’s contextual-indicator guidance and Open Banking’s emphasis on clear data-sharing explanations. [B1] [S26] [S27]

For aggregate-only or institution-continuity workspaces, the UI should remove individual-record affordances entirely, not disable a table of patients. WellBe’s constraints forbid default individual-level institutional access, and the C17 evaluator denies resources outside grant scope; showing individual rows would imply availability even when server-side policy denies them. [B1]

The UI should always include workspace_id, role_binding_id or equivalent active binding, purpose, requested action, resource hints, and data category/security-label context in scoped requests, but should not trust those client-supplied fields as authorization facts. This is a synthesis from WellBe’s C17 request shape, NIST ABAC, and OWASP server-side authorization guidance. [B1] [S21] [S23]

The safest failure mode is to remove the non-personal workspace from the switcher when enumeration no longer returns it, revoke or discard the active predicate, stop rendering scoped data, cancel pending actions, and return the user to the personal workspace with a neutral explanation. OAuth token introspection and revocation standards support checking active state and invalidating grant-derived tokens, and GitHub/Notion examples show that expired sessions/tokens require reauthentication or re-adding connections rather than silently continuing. [B1] [S2] [S5] [S32] [S33]

UI and server consistency requires a single entitlement source for both navigation and data fetches. If navigation is based on one endpoint and data on another with different rules, the app can create confusing “visible but denied” or “hidden but accessible by URL” states; OWASP ASVS specifically calls for centralized trusted service-layer enforcement when client-side code can be bypassed. [S21] [S22]

The UI should not use organization membership alone to show individual-level data. WellBe’s model says institutions are distribution channels and receive only aggregate, consented intelligence; OAIC/CDR and Open Banking consent patterns also frame data sharing as specific, time-limited, revocable choices rather than broad institution ownership. [B1] [S27] [S29] [S30]

Audit obligations should be reflected in the interface when they matter to user trust, not buried only in logs. HL7 AuditEvent frames security/privacy events around who, what, where, when, and why, and HIPAA technical safeguards require audit controls; a non-personal workspace indicator that says “Views are audited” is consistent with these obligations. [S17] [S20]

**Answer to Q3:** the UI should be a projection of the active C17 predicate, not an independent permissions system. It should fetch only in-scope resources, configure navigation/actions from the predicate summary, hide unavailable capabilities, disable with minimal explanatory copy when appropriate, treat absent/stale predicates as deny, and rely on server-side authorization for every read/search/export/invite/contribute action. [B1] [S18] [S21] [S22]

### Q4 — Personal-first coherence & the “always present” personal workspace

The personal workspace should be the default mental model, not a special case. WellBe’s product identity says the individual is always the controller and controller self-access is the simple personal-first case, so the app should feel complete for a user who has exactly one personal workspace. [B1]

Comparable workspace products support a simple single-workspace starting point. Notion says it is best to start simple with one workspace and that multiple workspaces are separate silos; Slack and Notion place workspace switching in the app shell/top-left area once multiple workspaces are relevant. [S1] [S5]

For a user with only the personal workspace, the app should show a stable active identity such as “Your workspace” or “[Name]’s health workspace,” but it should not show an empty enterprise-style selector, “no other workspaces” messaging, or institutional language. This is a synthesis from Notion’s one-workspace guidance and WellBe’s no-default-institution constraint. [B1] [S5]

The workspace control can still exist as a small identity/status affordance in the app shell or profile menu so the concept remains coherent when grants are later added. However, the primary call to action for solo users should be ordinary product navigation and grant/sharing management, not “switch workspace.” Open Banking’s consent-dashboard guidance supports making data-sharing controls easy to find without making them the default navigation destination. [S27] [S28]

When a second workspace appears, the same location should expand into a true switcher, with the personal workspace pinned first and a visible switch-back path from non-personal contexts. NHS App proxy access uses a banner with a switch-back link when acting for another person, which is a strong analogue for returning to WellBe’s personal workspace. [B1] [S13]

The switcher should live in the global app shell, near the current workspace label and account identity, because the active workspace affects every downstream surface and action. Slack, Notion, Atlassian, Teams, and AWS all place switch controls or active-context indicators in global navigation/account-shell areas rather than inside a specific page. [S1] [S4] [S5] [S6] [S7]

Personal-first does not mean “personal-only.” The switcher should scale by adding groups only when the user actually has displayable contexts in that group, such as “People you help,” “Clinical cases,” “Aggregate insights,” or “Research sandboxes.” This avoids empty categories that imply hidden access opportunities while preserving a clear growth path as memberships/grants appear. [B1] [S6] [S13]

Dev/test workspaces should appear only when the actor has an active membership/role and should be clearly labeled as testing. AWS’s role-switch display color/name pattern supports differentiating dangerous or unusual contexts, but WellBe should also use explicit text such as “Test data” or “Dev workspace” so it is not ever the automatic default. [B1] [S4]

Grant management and workspace switching should be related but not collapsed into one control. Consent dashboards in Open Banking and CDR let users see/revoke/amend sharing arrangements; the active workspace selector answers “where am I acting now?” while grant management answers “who can access what under which grants?” [B1] [S27] [S28] [S30]

The solo-user switcher should avoid language like “organization,” “tenant,” “managed by,” or “admin” unless the user is actually in such a role and the view is aggregate-only or administrative over consented metadata. This is a WellBe-specific synthesis from the controller invariant and institutional non-control constraint. [B1]

**Answer to Q4:** show the personal workspace as the active identity for everyone, but make the full switcher prominent only when there is more than one displayable workspace. Put it in the global shell/profile area, pin personal first, add role-based groups only when populated, and keep grant management findable as a separate sharing/permissions surface. [B1] [S1] [S5] [S13] [S27]

### Q5 — Session composition & safety

The active workspace should be an in-session authorization scope, not a separate login. GitHub, Google, Notion, and Teams all support switching between accounts, workspaces, or organizations without requiring full sign-out for every switch, and WellBe’s brief explicitly says workspace should compose with one authenticated identity. [B1] [S2] [S3] [S5] [S7]

Single sign-in does not mean single authorization state. The active workspace, role binding, membership, grant, purpose, capabilities, resource filters, obligations, and expiry should be checked or refreshed independently from the base session. This follows WellBe’s C17 design and aligns with NIST ABAC’s view that authorization evaluates subject, object, action, and environment attributes rather than only login identity. [B1] [S23]

The browser/client may remember the last selected workspace for convenience, but it should not be authoritative. If the server no longer enumerates that workspace or the predicate cannot be refreshed, the client should fall back to the personal workspace or a neutral no-access state; OWASP guidance supports fail-secure behavior and server-side authorization over client state. [B1] [S21] [S22]

Step-up authentication should be risk-based. Ordinary switching among low-risk displayable workspaces may not need reauthentication, but export, invite, research sandbox, aggregate analysis, emergency/break-glass-like access, or access after a long idle period should require step-up or reauthentication when assurance/freshness is insufficient. NIST 800-63B provides reauthentication/session-timeout guidance, and HIPAA technical safeguards include automatic logoff and unique user identification. [S20] [S24]

Revocation and expiry must take effect mid-session. Open Banking and CDR guidance treats consent as revocable and time-limited; NHS proxy guidance recommends time limits and review reminders; OAuth introspection and revocation standards provide general patterns for checking active state and invalidating tokens/authorization-derived credentials. [S14] [S27] [S29] [S30] [S32] [S33]

In WellBe, a grant revocation or expiry should remove the corresponding workspace from enumeration, invalidate active predicates tied to it, cancel pending actions, and prevent stale search/export/invite/contribute requests. This is a synthesis from the cited revocation/expiry guidance and WellBe’s C17 rule that an active, unexpired, unrevoked matching grant is required. [B1] [S14] [S27] [S32] [S33]

Audit should occur at context entry and at sensitive view/action points, especially for non-personal workspaces. HL7 AuditEvent identifies security/privacy events such as access-control decisions, logins/logouts, data manipulation, and accounting of disclosures; HIPAA requires audit controls for systems containing ePHI. [S17] [S20]

Audit logging should include the authenticated actor, active workspace, role binding, grant/purpose, data subject/controller or aggregate label, requested action, resource category/security labels, decision, obligations, and timestamp. This is a synthesis from HL7 AuditEvent’s who/what/where/when/why model and WellBe’s C17 decision-request/predicate fields. [B1] [S17]

A non-personal workspace can show a short “views are audited” indicator, while detailed access-history views should live in privacy/sharing controls where the individual can review non-personal access. My Health Record emergency access records appear in patient access history and can trigger patient notifications, and Open Banking/CDR dashboards expose data-sharing status to consumers. [S27] [S30] [S35]

To avoid stale-scope bugs, every API request should include the intended active workspace and purpose, and the server should reject requests if the active binding/predicate no longer matches. Token introspection guidance notes that active-state metadata can be queried and that caching security information has trade-offs; this supports short-lived predicate caching and refresh on switch, page load, sensitive action, expiry boundary, and revocation event. [B1] [S21] [S32]

Deep links should be resolved against current authorization at open time, not at link-creation time. GitHub’s external-link account choice pattern shows that the correct context may need user selection; WellBe should additionally avoid confirming unauthorized resources when no active grant matches the link. [B1] [S2] [S18]

**Answer to Q5:** keep one authenticated session, but make workspace a fresh, server-validated in-session scope. Refresh predicates on switch and sensitive actions, require risk-based step-up, honor expiry/revocation immediately, audit context entry and use, and bind all transient UI state and API requests to the active workspace to avoid stale-scope errors. [B1] [S17] [S20] [S21] [S24] [S32]

## Approaches considered

### Approach 1 — Minimal SaaS-style dropdown | Simple list of accessible workspaces

**What it does |** A single header dropdown shows “Your workspace” plus every active workspace returned by enumeration. Selecting a workspace immediately switches context. The label changes in the header, but there is no dedicated confirmation screen or persistent non-personal banner beyond the header label. This mirrors the simplest Slack/Notion-style workspace selector. [S1] [S5]

**Pros |** It is simple, familiar, low-friction, and scales naturally from one workspace to several. Mainstream SaaS users already understand selecting a workspace from a global app-shell control. [S1] [S5] [S6]

**Cons |** It under-communicates healthcare-specific scoping: users may not notice that they are acting for a different subject, under a grant, with different allowed actions. Mode-error research and NHS/AWS examples suggest that a mere dropdown label is not enough for high-stakes context switches. [S4] [S13] [S25]

**Fit with our constraints (§5) |** It can satisfy enumeration/no-leakage if backed by C17 enumeration, but it is weak on constraints 2, 4, 5, and 7 because active scope, capability changes, aggregate opt-in, and audit obligations may not be salient enough. [B1] [S21]

### Approach 2 — Personal-first explicit switcher with grant cards and persistent active-scope banner

**What it does |** The global app shell always shows the active personal workspace. When more workspaces exist, a switcher lists only displayable workspaces grouped by role/purpose. Each non-personal item is a compact grant card showing controller/subject or aggregate-only status, role, purpose, key capabilities, expiry, and audit note. Entering higher-risk non-personal/aggregate/research/export-capable contexts shows an acknowledgement or step-up when needed. After entry, a persistent banner/chip/header states “Acting for…,” “Aggregate only,” or “Research sandbox,” with capability and switch-back cues. [B1] [S4] [S13] [S16] [S17] [S24] [S27]

**Pros |** It makes the active context unambiguous, protects personal-first coherence, supports no-leak enumeration, communicates what changes on switch, aligns with healthcare proxy and consent-dashboard patterns, and creates a natural place to show audit/expiry obligations. [B1] [S13] [S14] [S17] [S25] [S27]

**Cons |** It is more verbose and adds friction for non-personal work. It requires careful copy and visual design to avoid overwhelming users with grant details or making routine caregiver work feel punitive. This is a design trade-off inferred from NN/g guidance that intrusive notifications should be reserved for action-required or higher-risk situations. [S26]

**Fit with our constraints (§5) |** Strong fit. It supports the always-present personal workspace, explicit switching, unambiguous active scope, no workspace leakage, clear data/action/surface boundaries, single-session composition, aggregate opt-in, and auditability. [B1] [S4] [S13] [S21] [S24] [S27]

### Approach 3 — Separate login or impersonation session per workspace

**What it does |** Each role/workspace requires separate authentication or a formal “impersonate” mode. A caregiver, clinician, researcher, or institution user signs into a distinct account/session for that workspace, or the app uses a strong impersonation screen before context entry.

**Pros |** It can create very strong psychological and technical separation between contexts. It may reduce some accidental cross-context actions because the user must intentionally start a different session. Emergency/break-glass systems sometimes use separate reason-entry or password prompts for exceptional access, which shows the value of explicit boundaries for unusual cases. [S34] [S35]

**Cons |** It conflicts with WellBe’s constraint that workspace is a scope within one authenticated identity, not a separate login. It also risks encouraging credential sharing or “log in as the patient,” which HMRC explicitly warns against in delegated-agent contexts. [B1] [S10]

**Fit with our constraints (§5) |** Poor fit for constraint 6 and likely poor user experience for ordinary delegated/caregiver work. Useful only as a narrow step-up pattern for very sensitive actions, not as the general workspace-switching model. [B1] [S10] [S24]

### Approach 4 — Global all-workspaces inbox/dashboard with lightweight context switching

**What it does |** The user lands in an “all workspaces” dashboard that aggregates notifications, tasks, cases, delegated threads, and possibly aggregate/research items. Selecting an item switches into the relevant workspace or opens the item in place. This resembles Slack Enterprise “All workspaces” filtering or Teams cross-account/activity surfaces. [S1] [S7]

**Pros |** It is efficient for users with many contexts, such as clinicians or caregivers managing several cases. It can reduce navigation overhead and make outstanding work visible. [S1] [S7]

**Cons |** It is risky for WellBe because a global dashboard can leak relationships, patient names, grant existence, or cross-patient metadata; it can also normalize cross-patient views, which WellBe explicitly forbids as a default. [B1]

**Fit with our constraints (§5) |** Limited fit. A highly redacted notification count like “2 updates need review” may be acceptable if server-filtered and no PHI/relationship details leak, but an all-workspaces content dashboard should not be the default. Aggregate or cross-patient content should remain explicit opt-in inside a clearly labeled aggregate/research workspace. [B1] [S18] [S27]

## Recommendation

Recommend **Approach 2 — Personal-first explicit switcher with grant cards and persistent active-scope banner**.

The switcher should be a global app-shell control whose default state is the personal workspace. For a single-workspace user, it should read as a normal identity/status affordance, not an empty enterprise switcher; for multi-workspace users, it should expand into a role-grouped list of only active displayable workspaces. [B1] [S1] [S5]

The personal workspace should always be pinned first and labeled in personal-controller language. Delegated workspaces should use “Acting for [person/controller]” language, clinical/care-team workspaces should show the specific role/purpose, institution contexts should say “aggregate only” when that is the grant, and research contexts should clearly say “research sandbox” and protocol/purpose. [B1] [S13] [S16] [S27]

Each workspace row/card should show only display-safe fields: workspace display name, type, role, purpose, capability summary, expiry/review date, and audit indicator. It should not show inaccessible grants, hidden patients, unrelated institution relationships, unavailable cohorts, or locked rows for resources outside the actor’s current entitlement. [B1] [S6] [S14] [S18] [S21]

Entering a non-personal workspace should show an acknowledgement when the subject/controller changes, when the context is aggregate/research, when export/invite/run-analysis is available, when the grant is near expiry, or when the session requires freshness. The acknowledgement should explain data scope, allowed actions, purpose, expiry, and audit. [B1] [S13] [S17] [S24] [S26] [S27]

After entry, the active context should be persistent in the shell: for example, a banner or chip reading “Acting for [name] — caregiver — specific thread — read/comment — expires [date] — views audited,” or “Aggregate only — no individual records.” Text should do the safety work; color or iconography may reinforce but should not be required to understand the state. [B1] [S4] [S13] [S26]

The UI should be generated from a server-returned predicate summary and should fail closed. If the predicate is missing, expired, revoked, superseded, or mismatched, the UI should stop rendering non-personal data, cancel pending actions, remove the workspace if enumeration no longer includes it, and return to the personal workspace or a neutral no-access screen. [B1] [S21] [S22] [S32] [S33]

The product should treat grant management as a related but separate privacy/control surface. The switcher answers “where am I acting now?” while a sharing/permissions dashboard answers “who can access what, for what purpose, until when, and how do I revoke it?” This split follows Open Banking/CDR dashboard patterns and keeps the solo personal workspace from feeling like an unfinished organization switcher. [B1] [S27] [S28] [S30]

Accepted trade-offs: non-personal entry has more friction; some actions will be hidden or blocked even when users expect them; aggregate and cross-patient workflows require deliberate opt-in; the header/banner consumes visual space; and the design requires precise copy for roles, purposes, capabilities, expiry, and audit. These costs are justified by WellBe’s controller/grant invariants and by external evidence that hidden mode changes, client-side authorization assumptions, and unclear delegated access are unsafe in sensitive systems. [B1] [S21] [S24] [S25]

## Open risks / unknowns

- **Exact personal-workspace label.** “Your workspace,” “[Name]’s health workspace,” and “Personal health memory” carry different trust and comprehension trade-offs; this needs product/content testing against WellBe’s brand language. [B1]

- **Capability-summary vocabulary.** Users may not understand internal terms like “specific-thread,” “labs+symptoms,” “aggregate-metrics,” or “research-protocol”; the product needs plain-language mappings that remain legally/security accurate. [B1] [S16] [S27]

- **Step-up thresholds.** The research supports risk-based step-up, but product/security must decide exactly which contexts/actions require reauthentication, MFA, reason entry, or acknowledgement. [S20] [S24] [S34] [S35]

- **Audit visibility.** The team must decide which audit events are visible to individuals, caregivers, clinicians, compliance admins, or institutions, and how to avoid audit logs themselves leaking sensitive relationships or investigations. [B1] [S17] [S20] [S35]

- **Notification metadata.** A global notification count may be useful, but even subject names, thread titles, or grant names can leak relationships; rules are needed for what can appear outside the active workspace. [B1] [S18] [S21]

- **Minor/dependent and safeguarding rules.** NHS proxy access has age milestones, safeguarding checks, and review requirements; WellBe needs its own jurisdiction-specific policy for dependents, capacity, guardianship, and revocation conflicts. [S14] [S15]

- **Emergency/break-glass stance.** The brief says access is explicit, scoped, time-boxed, and grant-based; product/legal/security should decide whether WellBe supports any emergency override at all, and if so whether it is outside the workspace switcher with reason entry, step-up, narrow scope, automatic expiry, patient-visible history, and retrospective review. [B1] [S20] [S34] [S35]

- **Aggregate/research de-identification thresholds.** The switcher can label “aggregate only,” but separate policy is needed for minimum cohort size, re-identification risk, suppression, export limits, and whether aggregate/research views can ever contain small-cell or rare-disease signals. [B1]

- **Legal/regulatory mapping.** HIPAA, UK delegated-authority patterns, NHS proxy access, Open Banking/CDR, and FHIR are useful analogues but are not a complete legal determination for WellBe’s jurisdictions, user classes, or health-data role model. [S9] [S14] [S16] [S20] [S27] [S29]

- **Offline or degraded mode.** The safest behavior is fail-closed when predicate refresh fails, but product must decide whether any cached personal-only access is allowed and how to communicate outages without implying grant loss. [B1] [S21] [S32]

- **Dev/test workspace governance.** The brief says dev/test is just one selectable workspace and never default; product/security still need rules for who can see it, how it is visually distinguished, whether it can contain real data, and how to prevent accidental production actions. [B1] [S4]
