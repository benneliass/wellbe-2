# Decision: Home signals summary / health-adaptive UI semantics (computation + never-alarm framing)

**Status:** Approved  
**Date opened:** 2026-06-17  
**Date approved:** 2026-06-18  
**Approved by:** User  
**Jira Spike:** WEL-167  
**Blocks:** WEL-91 [Implement health-adaptive UI with state-driven design tokens, never-alarm rule, and a11y]

---

## Question

For the Home "signals" summary / health-adaptive UI (the "Your signals look steady · N of N systems in range" line, currently hard-coded mock), how should a live health-status summary be computed and framed?
1. **Signal computation** — which signals/systems are summarized and how status ("in range / steady") is derived (C4 Processing).
2. **Never-alarm framing** — how an aggregate health-status line is phrased to avoid both false reassurance and alarm (C10).
3. **Confidence/uncertainty** — how confidence is surfaced.
4. **Missing/stale data** — what is shown when inputs are missing or out of date.

## Context

Touches C4 (Processing — signal computation) and C10 (never-alarm framing of a user-facing derived health judgment). The status line is currently mock data in `apps/web/lib/meta.ts`; going live turns it into a derived health-status claim. See `docs/architecture/component-map.md`, `docs/safety/safety_model.md`. Relates to WEL-43 (WB2-F040 Health-adaptive UI).

## Research provided

> User-provided research, recorded verbatim per research-protocol.mdc Section D (received 2026-06-18). Source file: `track-h-signals-research-result.md`. Not synthesised by the agent.

# Track H: Home signals summary / health-adaptive UI - research brief

Date researched: 2026-06-17

Scope note: This brief is decision-neutral. It summarizes external patterns and evidence relevant to a live home-screen health-status summary, without choosing a final computation policy, copy policy, safety-gate rule, or product decision.

## External patterns to examine

### 1. Decision-support and wellness boundary patterns

A live line such as "signals look steady" is not just a visual component; it is a derived, user-facing health interpretation. External patterns to examine include clinical decision support (CDS), patient-centered CDS, software as a medical device (SaMD) clinical evaluation, and low-risk wellness-device framing.

- The [AHRQ CDS overview](https://www.ahrq.gov/topics/clinical-decision-support-cds.html) defines CDS broadly as person-specific knowledge presented to clinicians, patients, or others at appropriate times. This is relevant because a home health-status line is person-specific and timing-sensitive.
- The AHRQ patient-centered CDS framework, summarized in the [NCBI Bookshelf chapter on Patient-Centered Clinical Decision Support](https://www.ncbi.nlm.nih.gov/books/NBK618176/), frames CDS as knowledge, data, delivery, and use that supports patients, caregivers, and care teams in decision-making aligned with circumstances and preferences.
- The [FDA Clinical Decision Support Software guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software) distinguishes some non-device CDS from software functions that remain under medical-device policy, including patient- or caregiver-facing functions when they meet the device definition.
- The [FDA General Wellness: Policy for Low Risk Devices](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices) gives a separate low-risk wellness pattern for products that promote or maintain a healthy lifestyle and are not tied to diagnosis, cure, mitigation, prevention, or treatment.
- The [IMDRF SaMD clinical evaluation guidance](https://www.imdrf.org/sites/default/files/docs/imdrf/final/technical/imdrf-tech-170921-samd-n41-clinical-evaluation_1.pdf) and FDA's SaMD materials describe clinical evaluation in terms of valid clinical association, analytical validation, and clinical validation. For Track H, this is relevant as a governance pattern for derived signals even if the final product route is not treated as SaMD.

Pattern space to examine: wellness-only informational framing; patient-facing CDS framing; SaMD-like validation discipline for internal safety even where regulatory classification is not being decided in this brief.

### 2. Reference ranges, clinical decision limits, personal baselines, and trends

External evidence distinguishes population reference ranges from personal baselines and from clinically meaningful change over time.

- Patient-facing lab education sources such as [MedlinePlus on understanding lab results](https://medlineplus.gov/lab-tests/how-to-understand-your-lab-results/) explain reference ranges as the comparator used on many lab reports, while also noting that interpretation depends on context.
- The [MSD Manual normal laboratory values resource](https://www.msdmanuals.com/professional/resources/normal-laboratory-values/normal-laboratory-values) describes reference ranges as typically based on the central range of values in healthy populations, not as perfect separators between health and disease.
- A 2025 family-medicine review on [interpreting normal lab values and reference ranges](https://www.jabfm.org/content/38/1/174) describes how the common central-95-percent convention can label some healthy people as abnormal and how clinical significance language may differ from simple in-range/out-of-range flags.
- The [EFLM Biological Variation Database background](https://biologicalvariation.eu/background) describes within-subject and between-subject biological variation, supporting the pattern of comparing an individual with their own homeostatic variation when enough valid data exist.
- A 2025 Clinical Chemistry paper on [reference change values](https://academic.oup.com/clinchem/article/71/2/307/7874401) describes RCV as a way to identify serial changes unlikely to be explained by random within-person, preanalytical, and analytical variation.
- Research on [personalized reference intervals](https://academic.oup.com/clinchem/article-abstract/67/2/374/5981754) and [personalized reference intervals using biological variation and historical results](https://www.degruyterbrill.com/document/doi/10.1515/cclm-2021-1066/html?lang=en) supports the existence of a personal-baseline pattern, while also implying data-sufficiency and steady-state assumptions.

Pattern space to examine: population reference range; clinical decision threshold; personal baseline; reference change value; trend direction and velocity; hybrid status combining multiple comparators.

### 3. Domain-specific signal frameworks

No single external standard was found that maps exactly to WellBe's six proposed systems and yields an aggregate "N of N systems in range" status. External frameworks are domain-specific and use different evidence bases.

- The [American Heart Association Life's Essential 8](https://www.heart.org/en/healthy-living/healthy-lifestyle/lifes-essential-8) summarizes cardiovascular health across health behaviors and health factors: diet, physical activity, nicotine exposure, sleep, weight, blood lipids, blood glucose, and blood pressure.
- The [AHA/ACC 2025 high blood pressure guideline summary](https://professional.heart.org/en/science-news/2025-high-blood-pressure-guideline/top-things-to-know) uses blood pressure categories and treatment goals, and it notes home blood-pressure monitoring while cautioning against relying on cuffless devices and smartwatches until precision and reliability are demonstrated.
- The ADA [Standards of Care in Diabetes - 2026 diagnosis and classification chapter](https://diabetesjournals.org/care/article/49/Supplement_1/S27/163926/2-Diagnosis-and-Classification-of-Diabetes) and [glycemic goals chapter](https://diabetesjournals.org/care/article/49/Supplement_1/S132/163927/6-Glycemic-Goals-Hypoglycemia-and-Hyperglycemic) provide metabolic reference points for diabetes-related measures, but they are clinical standards rather than consumer-dashboard status rules.
- The AASM/Sleep Research Society consensus statement on [recommended sleep duration for healthy adults](https://link.springer.com/article/10.5664/jcsm.4758) provides a sleep-duration pattern, while the [National Sleep Foundation recommendations](https://www.sleephealthjournal.org/article/S2352-7218%2815%2900015-7/fulltext) provide age-banded sleep-duration ranges.
- The [WHO physical activity and sedentary behavior guidelines](https://www.who.int/publications/i/item/9789240015128) and [CDC adult physical activity guidance](https://www.cdc.gov/physical-activity-basics/guidelines/adults.html) provide activity thresholds and muscle-strengthening patterns.
- [MedlinePlus on C-reactive protein testing](https://medlineplus.gov/lab-tests/c-reactive-protein-crp-test/) describes CRP as a nonspecific marker of inflammation and states that a high CRP result may show inflammation but does not identify the cause by itself.

Pattern space to examine: system-specific thresholds from clinical or public-health guidance; wearable-derived behavioral signals; lab-derived signals; per-system status that explicitly records which standards or baselines were used.

### 4. Consumer health-dashboard and wearable framing patterns

Consumer wearables often display readiness, recovery, energy, or notification states using contributor explanations and personal baselines, with non-diagnostic disclaimers. These examples are product patterns, not proof that the patterns are clinically safe for WellBe.

- [Oura Readiness Score](https://support.ouraring.com/hc/en-us/articles/360025589793-Readiness-Score) and [Oura Readiness Contributors](https://ouraringhelp.zendesk.com/hc/en-us/articles/360057791533-Readiness-Contributors) use contributors and personal averages; Oura states that contributors can take time to learn average values. Oura's [medical-conditions article](https://support.ouraring.com/hc/en-us/articles/43392238303763-Oura-Medical-Conditions) states that the ring is not intended to diagnose, treat, cure, monitor, or prevent medical conditions.
- [WHOOP Recovery](https://support.whoop.com/s/article/WHOOP-Recovery?language=en_US) frames recovery with color bands and guidance about adjusting strain or prioritizing recovery.
- [Garmin Body Battery](https://www.garmin.com/en-US/garmin-technology/health-science/body-battery/) frames a composite energy metric as context for decisions about exercise and habits.
- Google's [Fitbit readiness support page](https://support.google.com/googlehealth/answer/14236710?hl=en) and [Fitbit Daily Readiness explanation](https://store.google.com/us/magazine/fitbit_daily_readiness_score?hl=en-US) frame readiness as a daily recovery snapshot based on factors such as activity, sleep, and heart-rate variability. Google's 2026 Fitbit health-coach update includes a health disclaimer that the coach is not intended to diagnose, treat, cure, prevent, or monitor disease and points users to health professionals before changes ([Google blog](https://blog.google/products-and-platforms/devices/fitbit/fitbit-personal-health-coach-updates-2026/)).
- Apple's [heart-health notification support page](https://support.apple.com/en-us/120276) uses wording such as rhythms "suggestive of" atrial fibrillation rather than diagnostic language, and Apple's [Apple Watch heart-health guide](https://support.apple.com/guide/watch/heart-health-apde39f5426c/watchos) separates specific notifications and cardio-fitness estimates.

Pattern space to examine: contributor-level explanation; personal baseline learning period; color or category bands; specific-signal notification instead of global health judgment; non-diagnostic disclaimers; next-step copy that does not assert diagnosis.

### 5. Risk communication, reassurance, and patient-facing result interpretation

The never-alarm question has two sides: avoiding panic and avoiding false reassurance. External evidence shows that normal or negative results can be misunderstood, and that format and explanation change patient interpretation.

- A BMJ Open trial on [communicating residual risk after a negative test](https://bmjopen.bmj.com/content/12/3/e056533) found that people can misunderstand negative tests as meaning no risk, and that adding a short residual-risk statement improved understanding.
- A JAMA Internal Medicine systematic review on [reassurance after diagnostic testing with low pretest probability](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/1656539) and a [BMJ Evidence-Based Medicine commentary](https://ebm.bmj.com/content/19/1/14) discuss evidence that normal diagnostic tests do not necessarily reassure patients or reduce anxiety.
- The [FDA risk communication page](https://www.fda.gov/science-research/science-and-research-special-topics/risk-communication) and [FDA risk communication guide](https://www.fda.gov/media/81597/download) provide general principles for communicating benefits, risks, and uncertainties to intended audiences.
- The [NICE shared decision-making guidance](https://www.nice.org.uk/guidance/ng197) frames risk communication as part of helping people understand options, benefits, harms, and consequences.
- A 2024 JMIR systematic review on [presentation formats for lab test results](https://www.jmir.org/2024/1/e53993) found that presentation format affects patient information processing and that numbers plus reference ranges alone are often insufficient.
- The paper [Numbers, graphs, and words: helping patients to understand laboratory test results](https://pmc.ncbi.nlm.nih.gov/articles/PMC7592036/) supports combining visuals, brief verbal explanation, and action/urgency context rather than relying on raw abnormal flags.

Pattern space to examine: scoped reassurance; residual-risk language; clear takeaway with uncertainty; actionability without panic; urgency calibrated to the signal and source.

### 6. Confidence, uncertainty, missing data, and data quality patterns

External patterns treat confidence as a data-quality and communication problem, not only as a model-score problem.

- The JAMIA article on [electronic health record data quality assessment](https://academic.oup.com/jamia/article/30/10/1730/7216383) identifies commonly assessed dimensions such as completeness, correctness, concordance, plausibility, and currency.
- The CDC surveillance manual chapter on [data quality](https://archive.cdc.gov/www_cdc_gov/ncbddd/birthdefects/surveillancemanual/chapters/chapter-7/chapter7.5.html) uses completeness, accuracy, and timeliness as core quality concepts.
- A BMC Medical Informatics and Decision Making review on [healthcare data quality assessment](https://link.springer.com/article/10.1186/s12911-025-03136-y) emphasizes that data quality is multidimensional and context-dependent.
- Research on [wearable data quality challenges](https://www.nature.com/articles/s41598-024-67767-3) discusses missing data, artifacts, non-wear periods, and countermeasures such as compliance visualization and non-wear detection.
- A Nature Medicine article on [visual health communication](https://www.nature.com/articles/s41591-023-02328-1) and a 2025 Journal of General Internal Medicine article on [communicating numeric risk information to patients](https://link.springer.com/article/10.1007/s11606-025-09520-8) are relevant to how confidence and uncertainty can be shown in patient-facing interfaces.
- WHO Europe guidance on [communicating uncertainty in health emergencies](https://www.who.int/europe/publications/m/item/communicating-uncertainty-in-health-emergencies-guidance-and-tips) is emergency-focused, but it provides the general risk-communication pattern that uncertainty disclosure can support trust when communicated clearly.

Pattern space to examine: per-signal recency; source quality; measurement quality; baseline sufficiency; missingness; confidence labels; visual uncertainty; explicit "not enough current data" states.

## Evidence inventory

| Source | URL | What it covers | Context for Track H | Limitations |
|---|---|---|---|---|
| AHRQ Clinical Decision Support | [URL](https://www.ahrq.gov/topics/clinical-decision-support-cds.html) | Person-specific knowledge and information presented to clinicians, patients, or others at appropriate times. | Places a live health-status line in the broader CDS pattern because it is person-specific and user-facing. | High-level topic page; not a UI specification. |
| AHRQ Patient-Centered CDS chapter | [URL](https://www.ncbi.nlm.nih.gov/books/NBK618176/) | Patient-centered CDS framework: knowledge, data, delivery, use, and patient preferences/circumstances. | Relevant to personal-first, user-controlled interpretation and preference-aware display. | Book chapter; not specific to home dashboards or wearables. |
| FDA Clinical Decision Support Software guidance | [URL](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software) | FDA interpretation of CDS software functions and non-device CDS under the 21st Century Cures Act. | Helps identify why an aggregate health-status judgment needs governance and scope control. | Regulatory classification depends on actual intended use and implementation; this brief does not classify WellBe. |
| FDA General Wellness policy | [URL](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices) | Low-risk wellness-device framing and distinction from diagnosis/treatment/mitigation/prevention claims. | Useful for non-diagnostic, calm framing boundaries. | Wellness-policy applicability depends on claims and risk. |
| FDA Digital Health Technologies guidance | [URL](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/digital-health-technologies-remote-data-acquisition-clinical-investigations) | Use of digital health technologies for remote data acquisition, including fit-for-purpose considerations. | Relevant to connected-device data quality, validation, and source reliability. | Clinical-investigation context; not a consumer home-screen design guide. |
| IMDRF SaMD clinical evaluation guidance | [URL](https://www.imdrf.org/sites/default/files/docs/imdrf/final/technical/imdrf-tech-170921-samd-n41-clinical-evaluation_1.pdf) | Clinical evaluation concepts for software outputs: clinical association, analytical validation, clinical validation. | Provides a validation-pattern lens for derived signal computation. | SaMD framework may exceed WellBe's intended regulatory posture; decision-neutral use only. |
| AHA Life's Essential 8 | [URL](https://www.heart.org/en/healthy-living/healthy-lifestyle/lifes-essential-8) | Cardiovascular-health factors and behaviors including sleep, activity, glucose, lipids, blood pressure, and weight. | Offers a cross-domain external framework overlapping several WellBe systems. | Cardiovascular-health framework; not a six-system dashboard scoring rule. |
| AHA/ACC 2025 high blood pressure guideline summary | [URL](https://professional.heart.org/en/science-news/2025-high-blood-pressure-guideline/top-things-to-know) | Blood-pressure categories, goals, home monitoring, and caution about cuffless smartwatch BP. | Relevant to cardiovascular/vitals status and device-source confidence. | Summary page; detailed clinical decisions require full guideline and clinical context. |
| ADA Standards of Care in Diabetes - 2026 | [Diagnosis URL](https://diabetesjournals.org/care/article/49/Supplement_1/S27/163926/2-Diagnosis-and-Classification-of-Diabetes) / [Glycemic goals URL](https://diabetesjournals.org/care/article/49/Supplement_1/S132/163927/6-Glycemic-Goals-Hypoglycemia-and-Hyperglycemic) | Diabetes diagnosis criteria and glycemic goals. | Relevant to metabolic signals such as A1C or glucose. | Clinical standard; WellBe is non-diagnostic and should not turn criteria into diagnosis claims. |
| AASM/Sleep Research Society sleep-duration consensus | [URL](https://link.springer.com/article/10.5664/jcsm.4758) | Recommended sleep duration for healthy adults and caveats about individual variability. | Relevant to sleep-system status and trend interpretation. | Sleep duration alone is incomplete; not a total sleep-health score. |
| WHO physical activity guidelines | [URL](https://www.who.int/publications/i/item/9789240015128) | Evidence-based recommendations for amount and intensity of physical activity and sedentary behavior. | Relevant to activity-system thresholds. | Public-health guidance; individual constraints and medical context may differ. |
| CDC adult physical activity guidance | [URL](https://www.cdc.gov/physical-activity-basics/guidelines/adults.html) | Adult physical-activity target of 150 minutes moderate activity weekly plus muscle strengthening. | Patient-friendly threshold pattern for activity. | General adult guidance; not personalized to conditions, age constraints, or recovery. |
| MedlinePlus: understanding lab results | [URL](https://medlineplus.gov/lab-tests/how-to-understand-your-lab-results/) | Patient-facing explanation of reference ranges and interpretation context. | Relevant to in-range/out-of-range language and source-linked explanations. | General education; not per-analyte status logic. |
| MSD Manual: normal laboratory values | [URL](https://www.msdmanuals.com/professional/resources/normal-laboratory-values/normal-laboratory-values) | Professional reference-ranges resource and population-range framing. | Relevant to limitations of reference ranges. | Professional source; ranges vary by lab, method, age, sex, and context. |
| JABFM: interpreting normal lab values and reference ranges | [URL](https://www.jabfm.org/content/38/1/174) | Reference-range conventions, false abnormality risk, and patient-facing significance language. | Supports treating "in range" as contextual rather than equivalent to "healthy". | Primary-care perspective; not a consumer UI trial. |
| EFLM Biological Variation Database background | [URL](https://biologicalvariation.eu/background) | Within-subject and between-subject biological variation concepts. | Supports personal-baseline and meaningful-change logic. | Database/application requires analyte-specific methods and careful interpretation. |
| Clinical Chemistry 2025 RCV paper | [URL](https://academic.oup.com/clinchem/article/71/2/307/7874401) | Reference change values from serial results and variation sources. | Relevant to trend-vs-point computation and "steady" definitions. | Laboratory-data context; wearable and symptom data may need other methods. |
| Personalized reference interval research | [Clinical Chemistry URL](https://academic.oup.com/clinchem/article-abstract/67/2/374/5981754) / [CCLM URL](https://www.degruyterbrill.com/document/doi/10.1515/cclm-2021-1066/html?lang=en) | Approaches for individualized lab reference intervals using historical results, biological variation, and analytical variation. | Relevant to personal-first baselines and data-sufficiency rules. | Often laboratory-specific; steady-state assumptions and number of observations matter. |
| MedlinePlus: C-reactive protein test | [URL](https://medlineplus.gov/lab-tests/c-reactive-protein-crp-test/) | CRP as a nonspecific inflammation marker; high CRP does not identify cause by itself. | Important for inflammation-system framing and non-diagnostic copy. | General patient education; not a dashboard status algorithm. |
| BMJ Open residual-risk message study | [URL](https://bmjopen.bmj.com/content/12/3/e056533) | How people interpret negative test results and residual risk statements. | Relevant to avoiding false reassurance in "steady" or "in range" copy. | Specific test-communication context; not a broad wearable dashboard study. |
| JAMA Internal Medicine systematic review on reassurance after diagnostic testing | [URL](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/1656539) | Evidence on whether diagnostic tests reassure patients with low pretest probability. | Relevant to the assumption that "normal" displays calm users. | Diagnostic-testing context; dashboard interaction may differ. |
| FDA risk communication guide | [URL](https://www.fda.gov/media/81597/download) | Evidence-based communication of risks, benefits, uncertainties, and audience needs. | Relevant to C10 never-alarm copy review. | Broad FDA communication guide; not specific to personalized apps. |
| NICE shared decision-making guideline | [URL](https://www.nice.org.uk/guidance/ng197) | Communicating options, risks, benefits, harms, and consequences with patients. | Supports patient-understandable, non-authoritarian framing. | Clinical-care context; not a consumer home screen. |
| JMIR systematic review of lab-result presentation formats | [URL](https://www.jmir.org/2024/1/e53993) | Evidence on numbers, reference ranges, horizontal bars, color, labels, personalized ranges, and patient perception. | Relevant to per-system detail display, explanatory labels, and risk of misinterpretation. | Most included studies used mock results; action and memory outcomes were limited. |
| Numbers, graphs, and words for lab results | [URL](https://pmc.ncbi.nlm.nih.gov/articles/PMC7592036/) | User-centered presentation of lab results with verbal explanations, visuals, and action context. | Relevant to explaining "in range," "attention," and next steps. | Lab-results focus; not aggregate home status. |
| JAMIA EHR data quality assessment | [URL](https://academic.oup.com/jamia/article/30/10/1730/7216383) | Data-quality dimensions including completeness, correctness, concordance, plausibility, and currency. | Relevant to confidence and missing/stale data in C4. | EHR data-quality scope; device/lab consumer aggregation adds extra issues. |
| CDC surveillance data quality chapter | [URL](https://archive.cdc.gov/www_cdc_gov/ncbddd/birthdefects/surveillancemanual/chapters/chapter-7/chapter7.5.html) | Completeness, accuracy, and timeliness as data-quality concepts. | Supports treating stale or absent inputs as quality states, not green states. | Public-health surveillance context. |
| Nature Scientific Reports wearable data quality paper | [URL](https://www.nature.com/articles/s41598-024-67767-3) | Wearable missing data, non-wear, artifacts, and compliance visualization. | Relevant to connected wearable data and confidence. | Study-specific methods; not a general product standard. |
| Nature Medicine visual health communication | [URL](https://www.nature.com/articles/s41591-023-02328-1) | Visual communication framework for health test results and risk scenarios. | Relevant to uncertainty, confidence, and visual display choices. | Framework-level article; concrete UI performance depends on testing. |
| JGIM 2025 numeric risk communication | [URL](https://link.springer.com/article/10.1007/s11606-025-09520-8) | Patient-centered numeric risk communication, meaning, cognitive effort, and uncertainty. | Relevant to confidence wording and numeric labels. | Focuses on risk communication, not signal aggregation. |
| Oura readiness documentation | [Readiness URL](https://support.ouraring.com/hc/en-us/articles/360025589793-Readiness-Score) / [Contributors URL](https://ouraringhelp.zendesk.com/hc/en-us/articles/360057791533-Readiness-Contributors) / [Medical conditions URL](https://support.ouraring.com/hc/en-us/articles/43392238303763-Oura-Medical-Conditions) | Readiness score, contributors, personal averages, and non-diagnostic disclaimer. | Consumer pattern for contributor explanations and personal baseline learning. | Vendor documentation; not independent safety evidence. |
| WHOOP Recovery documentation | [URL](https://support.whoop.com/s/article/WHOOP-Recovery?language=en_US) | Recovery categories and guidance to adjust strain or prioritize recovery. | Consumer pattern for calm, behavior-oriented framing. | Vendor documentation; color bands can still affect anxiety. |
| Garmin Body Battery documentation | [URL](https://www.garmin.com/en-US/garmin-technology/health-science/body-battery/) | Composite energy metric from activity, stress, rest, and sleep. | Consumer pattern for aggregate energy/status summaries. | Vendor documentation; not diagnostic or cross-system clinical status. |
| Google/Fitbit readiness documentation | [Google Health URL](https://support.google.com/googlehealth/answer/14236710?hl=en) / [Fitbit Daily Readiness URL](https://store.google.com/us/magazine/fitbit_daily_readiness_score?hl=en-US) / [Google Fitbit health-coach blog](https://blog.google/products-and-platforms/devices/fitbit/fitbit-personal-health-coach-updates-2026/) | Daily readiness, recovery snapshot, inputs, and health disclaimer. | Consumer pattern for recovery-oriented status and disclaimers. | Vendor documentation and marketing/support materials. |
| Apple Watch heart-health support | [Notifications URL](https://support.apple.com/en-us/120276) / [Heart-health guide URL](https://support.apple.com/guide/watch/heart-health-apde39f5426c/watchos) | Irregular rhythm notifications, cardio-fitness ranges, and signal-specific wording. | Pattern for specific health notifications and non-diagnostic phrasing such as "suggestive of." | Device-specific; not a general aggregate-status model. |
| JAHA wearable anxiety and healthcare use in AF | [URL](https://www.ahajournals.org/doi/pdf/10.1161/JAHA.123.033750) | Association of wearable use with health anxiety, symptom monitoring, and healthcare use among people with atrial fibrillation. | Evidence that health-status signals can increase monitoring, concern, and utilization in some populations. | AF population; observational/cross-sectional elements; does not prove all wearables cause anxiety. |

## Decision-neutral findings

### Decision question 1: Signal computation - which systems/signals and how to derive status

External sources support several computation patterns, but they do not provide a single standard for a home aggregate such as "6 of 6 systems in range." The closest broad external framework is [AHA Life's Essential 8](https://www.heart.org/en/healthy-living/healthy-lifestyle/lifes-essential-8), which overlaps with cardiovascular, metabolic, sleep, activity, and vitals-like domains but is specifically a cardiovascular-health framework rather than a general home status summary.

For C4, the key factual distinction is that "in range" can mean different things depending on the comparator. Reference ranges, as explained by [MedlinePlus](https://medlineplus.gov/lab-tests/how-to-understand-your-lab-results/) and the [MSD Manual](https://www.msdmanuals.com/professional/resources/normal-laboratory-values/normal-laboratory-values), are population or lab-report comparators and do not automatically mean "healthy" or "unhealthy." The [JABFM reference-range review](https://www.jabfm.org/content/38/1/174) further describes how central-reference-interval conventions can produce false abnormal flags for some healthy people and can miss clinical meaning for others.

Personal-baseline approaches are also externally supported. The [EFLM biological-variation background](https://biologicalvariation.eu/background) distinguishes within-person from between-person variation. The [Clinical Chemistry RCV paper](https://academic.oup.com/clinchem/article/71/2/307/7874401) describes reference change value as a method for identifying changes unlikely to be random variation from within-person, preanalytical, and analytical sources. Personalized-reference-interval literature, including [Clinical Chemistry](https://academic.oup.com/clinchem/article-abstract/67/2/374/5981754) and [CCLM](https://www.degruyterbrill.com/document/doi/10.1515/cclm-2021-1066/html?lang=en), supports individualized ranges from prior results, with implied requirements for enough historical values and stable-state assumptions.

The evidence points to an option space rather than a single computation rule:

- Population comparator: status based on a reference range, clinical decision limit, or public-health threshold.
- Personal comparator: status based on personal baseline, personal range, or expected within-person variation.
- Trend comparator: status based on direction, magnitude, persistence, or reference change value rather than a single point.
- Hybrid comparator: status based on both external limits and personal deviation.
- Data-quality-gated comparator: status withheld or qualified when source, recency, completeness, or validity are insufficient.

For individual systems, the source landscape differs:

- Cardiovascular/vitals: the [AHA/ACC 2025 high blood pressure guideline summary](https://professional.heart.org/en/science-news/2025-high-blood-pressure-guideline/top-things-to-know) gives blood-pressure categories and goals, while also cautioning about cuffless devices and smartwatches for blood pressure until precision and reliability are established. This affects both status computation and confidence.
- Metabolic: ADA [diagnosis/classification](https://diabetesjournals.org/care/article/49/Supplement_1/S27/163926/2-Diagnosis-and-Classification-of-Diabetes) and [glycemic-goals](https://diabetesjournals.org/care/article/49/Supplement_1/S132/163927/6-Glycemic-Goals-Hypoglycemia-and-Hyperglycemic) standards provide clinical context for A1C and glucose. Because WellBe is non-diagnostic, these sources support threshold awareness rather than diagnosis claims.
- Sleep: the [AASM/SRS sleep-duration consensus](https://link.springer.com/article/10.5664/jcsm.4758) and [National Sleep Foundation ranges](https://www.sleephealthjournal.org/article/S2352-7218%2815%2900015-7/fulltext) provide duration references, but sleep status may also depend on quality, timing, regularity, symptoms, and device validity.
- Activity: the [WHO guidelines](https://www.who.int/publications/i/item/9789240015128) and [CDC adult activity guidance](https://www.cdc.gov/physical-activity-basics/guidelines/adults.html) provide general activity thresholds. They do not define a daily personal-readiness score.
- Inflammation: [MedlinePlus CRP guidance](https://medlineplus.gov/lab-tests/c-reactive-protein-crp-test/) states that CRP is nonspecific and high values do not identify a cause by themselves, making non-diagnostic framing especially important.
- Aggregate status: no consulted source validated a simple count of body systems as a global health state. Consumer systems such as [Oura](https://support.ouraring.com/hc/en-us/articles/360025589793-Readiness-Score), [WHOOP](https://support.whoop.com/s/article/WHOOP-Recovery?language=en_US), [Garmin](https://www.garmin.com/en-US/garmin-technology/health-science/body-battery/), and [Fitbit](https://support.google.com/googlehealth/answer/14236710?hl=en) use aggregate readiness, recovery, or energy summaries, but those are vendor patterns and are not equivalent to clinical coverage across cardiovascular, metabolic, sleep, activity, inflammation, and vitals systems.

C4 affected components therefore include source ingestion, signal normalization, threshold provenance, personal-baseline windows, trend calculations, data-quality scoring, and per-system evidence bundles. The evidence supports treating every computed status as traceable to a source, comparator, timestamp, and confidence basis.

### Decision question 2: Never-alarm framing - how to phrase aggregate status without false reassurance or alarm

Risk-communication evidence shows that a "normal" or negative result can be interpreted incorrectly. The BMJ Open study on [residual risk after a negative test](https://bmjopen.bmj.com/content/12/3/e056533) is directly relevant to false reassurance: it examines misunderstanding of negative results as zero risk and tests residual-risk language. The [JAMA Internal Medicine systematic review](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/1656539) and [BMJ Evidence-Based Medicine commentary](https://ebm.bmj.com/content/19/1/14) are relevant to the opposite assumption: normal diagnostic tests do not necessarily reassure or reduce anxiety.

Patient-facing lab-result evidence also shows that presentation format matters. The [JMIR systematic review](https://www.jmir.org/2024/1/e53993) found that numbers plus reference ranges alone are often insufficient, and that adding labels, reference or personalized goal ranges, and explanatory text changes cognitive perception and communication perception. [Numbers, graphs, and words](https://pmc.ncbi.nlm.nih.gov/articles/PMC7592036/) supports pairing visual displays with brief verbal explanation and action or urgency context.

External consumer patterns show several non-diagnostic framing choices without proving that any one is right for WellBe:

- Signal-specific notifications: [Apple](https://support.apple.com/en-us/120276) uses specific notifications such as rhythms "suggestive of" atrial fibrillation rather than declaring a diagnosis.
- Recovery/readiness framing: [Oura](https://support.ouraring.com/hc/en-us/articles/360025589793-Readiness-Score), [WHOOP](https://support.whoop.com/s/article/WHOOP-Recovery?language=en_US), [Garmin](https://www.garmin.com/en-US/garmin-technology/health-science/body-battery/), and [Fitbit](https://support.google.com/googlehealth/answer/14236710?hl=en) frame aggregate states around readiness, recovery, energy, or contributors rather than global "healthy/unhealthy" judgments.
- Medical-scope disclaimers: [Oura's medical-conditions page](https://support.ouraring.com/hc/en-us/articles/43392238303763-Oura-Medical-Conditions) and the [Google Fitbit health-coach update](https://blog.google/products-and-platforms/devices/fitbit/fitbit-personal-health-coach-updates-2026/) explicitly state non-diagnostic/non-treatment intent.
- Calm next steps: [WHOOP Recovery](https://support.whoop.com/s/article/WHOOP-Recovery?language=en_US) uses behavior-oriented next-step language such as adjusting strain or prioritizing recovery; this is a consumer pattern, not a clinical recommendation standard.

Evidence on wearable-related anxiety shows that health displays can affect monitoring behavior and concern. The JAHA paper on [wearable devices, health anxiety, and healthcare use in people with atrial fibrillation](https://www.ahajournals.org/doi/pdf/10.1161/JAHA.123.033750) found associations between wearable use, symptom monitoring/preoccupation, AF concern, and healthcare use in that population. This does not prove all health dashboards cause anxiety, but it is relevant to never-alarm safety review.

For C10, the framing issue is the scope of the claim. The evidence distinguishes at least four copy patterns to evaluate without selecting among them here:

- Observation pattern: "recent connected data look stable" style language that scopes the claim to observed data.
- Coverage pattern: "current data available for X of Y systems" style language that foregrounds what is and is not assessed.
- Actionability pattern: "no immediate follow-up suggested by these signals" versus "one signal may be worth reviewing" style language, with calibrated next steps.
- Uncertainty pattern: "based on limited/recent/high-confidence data" style language that makes confidence part of the status.

The false-reassurance risk increases when an aggregate line sounds global, final, diagnostic, or complete despite limited inputs. The alarm risk increases when normal variation, low-confidence measurements, or stale single points are framed as urgent. The sources above support examining copy that is scoped, source-linked, residual-risk-aware, and paired with calibrated next steps, while leaving final wording to maintainers.

### Decision question 3: Confidence and uncertainty - how to surface confidence honestly to a layperson

The evidence suggests that confidence has multiple layers. It is not only a model score. Relevant confidence inputs include source reliability, measurement method, recency, completeness, concordance between sources, plausibility, personal-baseline sufficiency, and the amount of biological, preanalytical, or analytical variation.

Data-quality sources provide terms for the C4 side. The JAMIA [EHR data-quality assessment](https://academic.oup.com/jamia/article/30/10/1730/7216383) identifies completeness, correctness, concordance, plausibility, and currency. The CDC [data-quality chapter](https://archive.cdc.gov/www_cdc_gov/ncbddd/birthdefects/surveillancemanual/chapters/chapter-7/chapter7.5.html) emphasizes completeness, accuracy, and timeliness. The BMC review on [healthcare data quality assessment](https://link.springer.com/article/10.1186/s12911-025-03136-y) describes data quality as context-dependent and multidimensional. Wearable data add non-wear, artifact, and compliance issues, as discussed in [Scientific Reports](https://www.nature.com/articles/s41598-024-67767-3).

Communication sources provide terms for the C10 side. The [FDA risk communication guide](https://www.fda.gov/media/81597/download), [Nature Medicine visual health communication framework](https://www.nature.com/articles/s41591-023-02328-1), and [JGIM numeric risk communication article](https://link.springer.com/article/10.1007/s11606-025-09520-8) are relevant to presenting numbers with meaning, reducing cognitive burden, and acknowledging uncertainty. The [JMIR lab-result presentation review](https://www.jmir.org/2024/1/e53993) also notes that limited numeracy and graph literacy affect interpretation.

Decision-neutral confidence display dimensions to examine include:

- Per-signal source confidence: lab, device, manual entry, derived metric, or document-extracted fact.
- Per-signal recency: last measured, measurement frequency, and whether the data are current for that signal type.
- Per-signal sufficiency: enough observations for personal baseline, trend, or only point-in-time comparison.
- Per-system confidence: whether all required sub-signals are available or only a partial view exists.
- Aggregate confidence: whether the aggregate is driven by the weakest system, by weighted evidence, by coverage count, or by a separate data-quality summary.
- Explanation format: plain-language labels, source chips, timestamps, confidence bars, uncertainty intervals, or expandable provenance.

The sources do not settle whether confidence should be numeric, categorical, visual, or textual. Numeric scores can look precise; categorical labels can hide complexity; visual bands can be easy to scan but can also be over-interpreted. For a layperson-facing home screen, the evidence base points to testing whether confidence language improves understanding without increasing worry or implying certainty.

### Decision question 4: Missing or stale data - what to show when inputs are absent or out of date

Missing and stale data are data-quality states, not neutral positives. The JAMIA [data-quality assessment](https://academic.oup.com/jamia/article/30/10/1730/7216383) includes completeness and currency; the CDC [data-quality chapter](https://archive.cdc.gov/www_cdc_gov/ncbddd/birthdefects/surveillancemanual/chapters/chapter-7/chapter7.5.html) includes completeness and timeliness; wearable-data research in [Scientific Reports](https://www.nature.com/articles/s41598-024-67767-3) discusses non-wear and missingness as real issues for wearable signals.

For the home aggregate, the evidence raises a specific semantic risk: "6 of 6 systems in range" can imply both favorable status and complete coverage. If a system is missing or stale, that denominator can become misleading unless the product defines whether missing systems are excluded, counted as unknown, or block aggregate display. The consulted sources do not provide a universal denominator policy.

Decision-neutral missing/stale display options to examine include:

- Explicit unknown state: a system is shown as "not enough current data" rather than green, yellow, or red.
- Separate coverage count: the UI distinguishes "systems with current data" from "systems in range."
- Age-of-data labeling: each system and aggregate line exposes last-updated timestamps or freshness labels.
- Denominator adjustment: the aggregate counts only systems with sufficient current data, while separately showing excluded systems.
- Aggregate suppression: the aggregate line is not shown when required systems are missing or confidence is below threshold.
- Progressive onboarding: the system uses a learning state before personal baselines are available, similar to consumer wearable patterns such as [Oura contributors needing time to learn average values](https://ouraringhelp.zendesk.com/hc/en-us/articles/360057791533-Readiness-Contributors).

C4 affected components include stale-data thresholds per signal, baseline-establishment rules, non-wear and artifact detection, source conflict handling, and provenance. C10 affected components include copy review for denominator ambiguity, suppression or qualification of unsupported aggregate claims, and prevention of "all clear" language when the evidence base is partial.

## Tradeoffs and open questions

### 1. Aggregate line versus per-system-only display

- Aggregate line tradeoff: high scanability and emotional simplicity, but higher risk of global false reassurance or global alarm.
- Per-system-only tradeoff: more transparent and source-specific, but less useful as an at-a-glance home summary.
- Open question: What level of aggregate claim is acceptable under WellBe's never-alarm and non-diagnostic guardrails?

### 2. "N of N systems in range" versus coverage-first semantics

- Count tradeoff: "N of N" is simple, but it can imply complete assessment and equal weighting across systems.
- Coverage-first tradeoff: clearer about what data exists, but less emotionally satisfying and potentially less useful as a status line.
- Open question: Should the denominator represent all possible systems, only systems with current data, or only systems with enough confidence to classify?

### 3. Population reference ranges versus personal baselines

- Reference-range tradeoff: easier to explain and source-link, but can be nonspecific, lab-dependent, and poorly personalized.
- Personal-baseline tradeoff: aligns with personal-first design and trend meaning, but requires enough clean historical data and may normalize chronically abnormal states.
- Hybrid tradeoff: may capture both clinical thresholds and personal change, but increases complexity and explanation burden.
- Open question: Which signals require external clinical limits even when personal baseline appears steady?

### 4. Point value versus trend or persistence

- Point-value tradeoff: simple and responsive, but vulnerable to noise, transient fluctuations, and measurement artifacts.
- Trend/persistence tradeoff: calmer and less noisy, but may delay attention to sudden changes.
- Open question: For each system, what time window and persistence rule distinguishes "steady" from "needs attention"?

### 5. System inclusion and weighting

- Equal-system tradeoff: simple and easy to communicate, but may imply that inflammation, activity, sleep, and blood pressure carry equal meaning.
- Weighted-system tradeoff: may better reflect evidence or urgency, but can appear opaque and authority-like.
- Open question: Are cardiovascular, metabolic, sleep, activity, inflammation, and vitals the right system set for the first live version, and are any sub-signals required before a system can be classified?

### 6. Consumer wearable patterns versus clinical-signal standards

- Wearable-pattern tradeoff: readiness/recovery framing is familiar and calm, but vendor scores are not equivalent to clinical health status.
- Clinical-standard tradeoff: stronger threshold provenance, but can feel medicalized and may increase alarm if copied directly into a consumer home screen.
- Open question: Should WellBe use a wellness/readiness-like vocabulary, a source/coverage vocabulary, or a clinical-threshold vocabulary for the home line?

### 7. Confidence display as score, label, or explanation

- Numeric confidence tradeoff: precise-looking and sortable, but may imply more certainty than exists.
- Categorical confidence tradeoff: easier to read, but may hide why confidence is low.
- Explanation tradeoff: more transparent, but can overload a home screen.
- Open question: What minimum confidence explanation is required on the home surface versus the expanded system detail?

### 8. Missing and stale data policy

- Excluding missing systems tradeoff: avoids penalizing the user for absent data, but can make an aggregate look better than coverage supports.
- Marking missing as unknown tradeoff: honest, but can make the home screen feel incomplete.
- Blocking aggregate tradeoff: safer against false reassurance, but reduces the feature's utility during onboarding or sparse-data periods.
- Open question: What freshness thresholds are appropriate for labs, wearables, manual vitals, sleep, activity, and document-derived facts?

### 9. Alarm calibration and next steps

- Low-alarm copy tradeoff: reduces panic risk, but may understate meaningful deviations if too soft.
- Urgency-tier copy tradeoff: supports action, but may increase anxiety and healthcare use if thresholds are noisy.
- Open question: Which statuses require no action, self-review, routine clinician review, prompt clinician contact, or emergency-disclaimer routing, and how does C10 enforce those distinctions?

### 10. Source-linked provenance depth

- Inline provenance tradeoff: builds trust and supports user control, but can clutter the home screen.
- Expandable provenance tradeoff: keeps the home calm, but may obscure why the line says "steady" unless users open details.
- Open question: Which provenance items must be visible at home level: source type, last updated date, threshold source, personal-baseline window, confidence, or all of these?

### 11. Validation and evaluation

- Internal validation tradeoff: C4 can test analytical correctness and data-quality behavior, but user comprehension and emotional response require user research.
- User-research tradeoff: tests false reassurance and alarm risk, but requires carefully designed scenarios including normal, borderline, missing, stale, and conflicting data.
- Open question: What evaluation metrics define acceptable safety for a never-alarm aggregate line: comprehension, residual-risk awareness, trust calibration, action appropriateness, anxiety, or clinician-contact intent?

### 12. Handling symptoms, diagnoses, medications, and clinician-set goals

- Signal-only tradeoff: simpler and less diagnostic, but may miss context that changes interpretation.
- Context-aware tradeoff: more personally relevant, but closer to clinical judgment and requires stronger governance.
- Open question: Should symptoms, known conditions, medications, pregnancy, clinician-set ranges, or user goals override generic per-system statuses, and how should that override be displayed without diagnosing?

## Approaches considered

Grounded only in the recorded research:

- **Computation.** No external standard maps to a "N of N systems in range" home aggregate. Reference ranges (MedlinePlus, MSD, JABFM) are population/lab comparators that don't equal "healthy". Personal baselines and RCV (EFLM biological variation; Clinical Chemistry RCV; personalized reference intervals) need enough clean history and steady-state assumptions. AHA Life's Essential 8, ADA, AASM/NSF, WHO/CDC activity, MedlinePlus CRP give per-system reference points; consumer wearables (Oura/WHOOP/Garmin/Fitbit) use readiness/recovery framing with non-diagnostic disclaimers.
- **Never-alarm framing.** Negative/normal results are misread both ways: residual-risk language helps (BMJ Open), and normal results don't reliably reassure (JAMA IM review). Presentation format matters (JMIR; "Numbers, graphs, and words"). Apple uses signal-specific "suggestive of" wording; wearable use is associated with health anxiety in some populations (JAHA AF).
- **Confidence + missing/stale.** Data-quality dimensions (JAMIA, CDC, BMC) include completeness/currency/accuracy; wearables add non-wear/artifacts. Missing and stale are data-quality states, not positives; an "N of N in range" denominator conflates favorable status with complete coverage.

## Decision

1. **Computation = per-signal, comparator-explicit, fully traceable.** Each per-system status records its comparator and is traceable to source + comparator + timestamp + confidence. **No system is classified without sufficient current data.** Comparators are hybrid and explicit: population reference / clinical decision limit where applicable **plus** personal baseline / trend (RCV-style) where enough clean history exists; trend/persistence is preferred over single noisy points. Initial system set: cardiovascular/vitals, metabolic, sleep, activity, inflammation (as scoped).
2. **Never-alarm framing = scoped, observation-based, coverage-aware.** The Home line scopes its claim to observed data and foregrounds coverage — e.g. *"recent connected data look steady"* with *"current data for X of Y systems"* — and is **never** a global/final/diagnostic "all clear". It avoids false reassurance (residual-risk-aware copy) and avoids alarm (normal variation, low-confidence, or stale single points are never framed as urgent). Any "worth reviewing" signal is paired with a calibrated next step. **C10 reviews the copy and blocks "all clear" language when the evidence base is partial.**
3. **Confidence = multi-layer, plain-language, honest.** Confidence reflects source reliability, measurement method, recency, completeness, concordance, and baseline sufficiency — shown as plain-language labels + source chips + last-updated, with detail on expand; **not** a single precise-looking number. Aggregate confidence is driven by the weakest contributing system / coverage and is surfaced honestly.
4. **Missing/stale = explicit unknown, never green.** A system with no current/fresh data shows *"not enough current data"* (unknown), not in-range. The Home **denominator counts only systems with sufficient current data** and separately shows coverage; the aggregate line is **suppressed or qualified** when required systems are missing or confidence is below threshold. A learning/onboarding state applies before personal baselines exist.

## Trade-offs accepted

- **Coverage-first semantics** over a satisfying "N of N in range" count: less emotionally simple, but honest and non-diagnostic, and avoids the denominator conflating status with completeness.
- **Suppress/qualify aggregate when sparse:** reduces utility during onboarding/sparse data, but prevents false reassurance.
- **Qualitative confidence over numeric:** less sortable, avoids false precision.
- **Trend/persistence over point values:** calmer and less noisy, may slightly delay attention to a sudden change — accepted because time-sensitive change routes through the Track C check-in / continuity flow, not this calm line.

## Implementation notes

- **C4:** compute per-system status with comparator provenance, baseline windows, trend calculation, data-quality + freshness scoring, and per-system evidence bundles; mark missing/stale explicitly.
- **C10:** review the aggregate copy for denominator ambiguity and never-alarm compliance; block unsupported "all clear" when coverage/confidence is partial. This is **C10-adjacent (safety copy)** — keep WEL-91 implementation gated on this approval.
- Home shows the scoped/coverage line with expandable per-system provenance (source type, last updated, comparator, baseline window, confidence).
- **Deferred (tracked):** per-signal freshness thresholds, system weighting, final copy, evaluation metrics (comprehension / residual-risk awareness / anxiety), and context overrides (conditions, meds, pregnancy, clinician-set goals) — to implementation with user research.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
