"""Published Research C sample cases used by the dev demo seed.

Wording comes only from the Research C file ``cases_or_examples.csv``
(cases C001-C018). Researcher lessons and product implications are not
copied into the patient-facing text. Each case stays its own note.
"""

from __future__ import annotations

PUBLISHED_CASES: list[dict[str, str]] = [
    {
        "case_id": "C001",
        "title": "Dismissed and silenced hospital assessment",
        "source_url": "https://www.careopinion.org.uk/1429947",
        "text": (
            "Published sample case C001: Dismissed and silenced hospital assessment\nS"
            "ource: https://www.careopinion.org.uk/1429947\n\nPatient attended hospital"
            " after long wait and tried to describe symptoms.\n\nDoctor reportedly rest"
            "ricted history to yes/no answers.\n\nPatient narrative and context not cap"
            "tured.\n\nTimeline: same encounter\n\nOutcome recorded: Emotional harm; clin"
            "ical outcome unknown."
        ),
    },
    {
        "case_id": "C002",
        "title": "Autistic patient multi-issue primary care visit",
        "source_url": "https://www.careopinion.org.uk/1258944",
        "text": (
            "Published sample case C002: Autistic patient multi-issue primary care vi"
            "sit\nSource: https://www.careopinion.org.uk/1258944\n\nPatient brought advo"
            "cate and prioritized list.\n\nOnly reflux was addressed according to patie"
            "nt.\n\nPain medication and asthma concerns not addressed.\n\nTimeline: chron"
            "ic pain over 10 years noted\n\nOutcome recorded: Patient felt unheard."
        ),
    },
    {
        "case_id": "C003",
        "title": "ED discharge after normal bloods and X-ray",
        "source_url": "https://www.careopinion.org.uk/1117906",
        "text": (
            "Published sample case C003: ED discharge after normal bloods and X-ray\nS"
            "ource: https://www.careopinion.org.uk/1117906\n\nPatient sent by out-of-ho"
            "urs GP with severe symptoms.\n\nBloods/chest X-ray considered reassuring; "
            "discharged.\n\nCause of severe symptoms not identified/explained.\n\nTimelin"
            "e: same-day ED visit\n\nOutcome recorded: Ongoing severe pain and no expla"
            "nation."
        ),
    },
    {
        "case_id": "C004",
        "title": "Back pain after bowel cancer dismissed as old age",
        "source_url": "https://www.careopinion.org.uk/1349233",
        "text": (
            "Published sample case C004: Back pain after bowel cancer dismissed as ol"
            "d age\nSource: https://www.careopinion.org.uk/1349233\n\nOlder patient had "
            "severe back pain and recent bowel cancer history.\n\nMultiple services rep"
            "ortedly dismissed pain as age-related.\n\nSpinal cancer reportedly identif"
            "ied late.\n\nTimeline: diagnosed after admission; death just over two week"
            "s later\n\nOutcome recorded: Patient died."
        ),
    },
    {
        "case_id": "C005",
        "title": "CAMHS low mood vs later bipolar diagnosis",
        "source_url": "https://www.careopinion.org.uk/176152",
        "text": (
            "Published sample case C005: CAMHS low mood vs later bipolar diagnosis\nSo"
            "urce: https://www.careopinion.org.uk/176152\n\nFamily sought specialist me"
            "ntal health help for daughter.\n\nInitial psychiatrist reportedly dismisse"
            "d family input/genetic history.\n\nBipolar disorder not identified until a"
            "fter deterioration.\n\nTimeline: six months before psychiatrist change\n\nOu"
            "tcome recorded: Inpatient admission and later treatment."
        ),
    },
    {
        "case_id": "C006",
        "title": "Adult ADHD referral rejected without meeting patient",
        "source_url": "https://www.careopinion.org.uk/1167674",
        "text": (
            "Published sample case C006: Adult ADHD referral rejected without meeting"
            " patient\nSource: https://www.careopinion.org.uk/1167674\n\nGP sent repeate"
            "d referrals with high questionnaire scores.\n\nPsychiatry declined assessm"
            "ent; later no adult pathway stated.\n\nPatient felt ADHD effectively ruled"
            " out without assessment.\n\nTimeline: eight months complaint/ombudsman pur"
            "suit noted\n\nOutcome recorded: Unclear pathway; patient distress."
        ),
    },
    {
        "case_id": "C007",
        "title": "Pulmonary embolism missed after clear chest X-ray",
        "source_url": (
            "https://www.ombudsman.org.uk/publications/broken-trust-making-patient-sa"
            "fety-more-just-promise-report/broken-trust-our-casework-evidence-clinica"
            "l-failings"
        ),
        "text": (
            "Published sample case C007: Pulmonary embolism missed after clear chest "
            "X-ray\nSource: https://www.ombudsman.org.uk/publications/broken-trust-mak"
            "ing-patient-safety-more-just-promise-report/broken-trust-our-casework-ev"
            "idence-clinical-failings\n\nMan had breathlessness, fast heart/respiratory"
            " rate, low oxygen.\n\nED diagnosed pneumonia and discharged after clear ch"
            "est X-ray.\n\nPulmonary embolism likely missed; PE blood test not done.\n\nT"
            "imeline: death next day\n\nOutcome recorded: Patient died; PHSO found like"
            "ly survival with right treatment."
        ),
    },
    {
        "case_id": "C008",
        "title": "Brian continuity-of-care delayed metastatic cancer diagnosis",
        "source_url": (
            "https://www.hssib.org.uk/patient-safety-investigations/continuity-of-car"
            "e-delayed-diagnosis-in-gp-practices/investigation-report/"
        ),
        "text": (
            "Published sample case C008: Brian continuity-of-care delayed metastatic "
            "cancer diagnosis\nSource: https://www.hssib.org.uk/patient-safety-investi"
            "gations/continuity-of-care-delayed-diagnosis-in-gp-practices/investigati"
            "on-report/\n\nPatient had severe back pain after previous breast cancer.\n\n"
            "Multiple clinicians saw him over eight months.\n\nMetastatic cancer not id"
            "entified until spinal lump found.\n\nTimeline: eight months\n\nOutcome recor"
            "ded: Metastatic cancer diagnosis delayed."
        ),
    },
    {
        "case_id": "C009",
        "title": "Child diabetes delayed despite urinalysis",
        "source_url": "https://www.hdc.org.nz/decisions/search-decisions/2023/20hdc02300/",
        "text": (
            "Published sample case C009: Child diabetes delayed despite urinalysis\nSo"
            "urce: https://www.hdc.org.nz/decisions/search-decisions/2023/20hdc02300/"
            "\n\nChild had two appointments and urinalysis.\n\nUrinalysis did not lead to"
            " timely diagnosis.\n\nDiabetes not promptly identified.\n\nOutcome recorded:"
            " Delayed diagnosis and risk."
        ),
    },
    {
        "case_id": "C010",
        "title": "Positive prostate cancer histology not actioned",
        "source_url": "https://www.hdc.org.nz/decisions/search-decisions/2025/22hdc02105/",
        "text": (
            "Published sample case C010: Positive prostate cancer histology not actio"
            "ned\nSource: https://www.hdc.org.nz/decisions/search-decisions/2025/22hdc"
            "02105/\n\nPositive histology was reported.\n\nStaff did not understand share"
            "d clinical information system; result not actioned.\n\nCancer diagnosis de"
            "layed.\n\nTimeline: about six months\n\nOutcome recorded: Delayed diagnosis."
        ),
    },
    {
        "case_id": "C011",
        "title": "Abnormal Bence Jones protein result not followed up",
        "source_url": "https://www.hdc.org.nz/decisions/search-decisions/2012/10hdc01419/",
        "text": (
            "Published sample case C011: Abnormal Bence Jones protein result not foll"
            "owed up\nSource: https://www.hdc.org.nz/decisions/search-decisions/2012/1"
            "0hdc01419/\n\nAbnormal lab result received.\n\nGP marked result but did not "
            "inform patient or arrange follow-up.\n\nAbnormal result not acted on.\n\nOut"
            "come recorded: Potential delayed investigation."
        ),
    },
    {
        "case_id": "C012",
        "title": "Endometriosis referral dismissed, later diagnosed",
        "source_url": "https://www.endometriosis-uk.org/tayas-story",
        "text": (
            "Published sample case C012: Endometriosis referral dismissed, later diag"
            "nosed\nSource: https://www.endometriosis-uk.org/tayas-story\n\nPatient trac"
            "ked symptoms and obtained referral.\n\nFirst specialist belittled concern "
            "and pushed hormones; later consultant agreed to diagnosis-first.\n\nEndome"
            "triosis found by laparoscopy.\n\nTimeline: nearly 11 years symptom trackin"
            "g\n\nOutcome recorded: Diagnosis at age 25 in story context."
        ),
    },
    {
        "case_id": "C013",
        "title": "Severe adolescent symptoms normalized before endometriosis diagnosis",
        "source_url": "https://www.endometriosis-uk.org/orlas-story",
        "text": (
            "Published sample case C013: Severe adolescent symptoms normalized before"
            " endometriosis diagnosis\nSource: https://www.endometriosis-uk.org/orlas-"
            "story\n\nPatient had severe adolescent pelvic symptoms and later infertili"
            "ty.\n\nGP reportedly normalized symptoms and delayed referral.\n\nSevere end"
            "ometriosis/adenomyosis diagnosed later.\n\nTimeline: roughly 9 years\n\nOutc"
            "ome recorded: Diagnosis at age 24 in story."
        ),
    },
    {
        "case_id": "C014",
        "title": "Blood in stool attributed to IBS/piles before bowel cancer",
        "source_url": (
            "https://www.bowelcanceruk.org.uk/how-we-can-help/real-life-stories/perso"
            "nal-experiences/debbie-cameron%2C-merseyside/"
        ),
        "text": (
            "Published sample case C014: Blood in stool attributed to IBS/piles befor"
            "e bowel cancer\nSource: https://www.bowelcanceruk.org.uk/how-we-can-help/"
            "real-life-stories/personal-experiences/debbie-cameron%2C-merseyside/\n\nPa"
            "tient had blood in stool.\n\nMultiple GP contacts attributed symptoms to I"
            "BS/piles; patient said not examined.\n\nStage 3 bowel cancer diagnosed lat"
            "er.\n\nTimeline: about 11 months\n\nOutcome recorded: Stage 3 diagnosis."
        ),
    },
    {
        "case_id": "C015",
        "title": "Young bowel cancer patient sent through wrong specialty loop",
        "source_url": (
            "https://www.bowelcanceruk.org.uk/how-we-can-help/real-life-stories/young"
            "er-people-with-bowel-cancer/sarah-mccollum-surrey/"
        ),
        "text": (
            "Published sample case C015: Young bowel cancer patient sent through wron"
            "g specialty loop\nSource: https://www.bowelcanceruk.org.uk/how-we-can-hel"
            "p/real-life-stories/younger-people-with-bowel-cancer/sarah-mccollum-surr"
            "ey/\n\nYoung patient had urgency, blood in stool, pain.\n\nA&E reportedly di"
            "smissed cancer due to age and referred to gynecology.\n\nRectal cancer ide"
            "ntified after screening/colonoscopy.\n\nTimeline: symptoms worsened over t"
            "hree months\n\nOutcome recorded: Stage 2 then stage 3 after lymph node tes"
            "ting."
        ),
    },
    {
        "case_id": "C016",
        "title": "Severe back pain dismissed before rare cancer diagnosis",
        "source_url": (
            "https://people.com/22-year-old-diagnosed-with-terminal-cancer-after-docs"
            "-dismiss-symptoms-11855746"
        ),
        "text": (
            "Published sample case C016: Severe back pain dismissed before rare cance"
            "r diagnosis\nSource: https://people.com/22-year-old-diagnosed-with-termin"
            "al-cancer-after-docs-dismiss-symptoms-11855746\n\n22-year-old had severe b"
            "ack pain affecting sleep/mobility.\n\nGiven analgesics/stretches; question"
            "ed for A&E attendance.\n\nRare metastatic cancer found after scans.\n\nTimel"
            "ine: Nov 2024 to Apr 2025\n\nOutcome recorded: Stage 4 diagnosis."
        ),
    },
    {
        "case_id": "C017",
        "title": "Nigerian patient repeated tests before cervical cancer diagnosis",
        "source_url": (
            "https://businessday.ng/health/article/wrong-diagnosis-killing-many-patie"
            "nts-in-nigerian-hospitals/"
        ),
        "text": (
            "Published sample case C017: Nigerian patient repeated tests before cervi"
            "cal cancer diagnosis\nSource: https://businessday.ng/health/article/wrong"
            "-diagnosis-killing-many-patients-in-nigerian-hospitals/\n\nPatient had fat"
            "igue, pelvic pain, bleeding, weight loss.\n\nRepeated infection explanatio"
            "ns, antibiotics and inconclusive tests.\n\nCervical cancer identified by b"
            "iopsy.\n\nTimeline: three tough months after worsening noted\n\nOutcome reco"
            "rded: Stage 4 diagnosis."
        ),
    },
    {
        "case_id": "C018",
        "title": "Thorough doctor listened and explained results",
        "source_url": "https://www.careopinion.org.uk/1333013",
        "text": (
            "Published sample case C018: Thorough doctor listened and explained resul"
            "ts\nSource: https://www.careopinion.org.uk/1333013\n\nPatient had consultat"
            "ion and test results/pathway.\n\nDoctor listened, explained, examined, and"
            " considered mental health differential.\n\nPatient felt properly assessed."
            "\n\nTimeline: same consultation\n\nOutcome recorded: Positive experience."
        ),
    },
]
