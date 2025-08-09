"""
Seed script for all lookup tables.
Run with: python manage.py shell < seed_lookups.py
Works locally and on Heroku (as long as Django is set up and models are migrated).
Add more lookup values as needed in the appropriate sections.
"""
from users.models_profile import Faith, Gender, InsuranceProvider, LGBTQIA, LicenseType, PaymentMethod, RaceEthnicity, TherapyType, Title, AgeGroup, ParticipantType
# --- Participant Types (core set, singular forms) ---
PARTICIPANT_TYPE_VALUES = [
    "Individual",
    "Couple",
    "Family",
    "Group",
]
for name in PARTICIPANT_TYPE_VALUES:
    ParticipantType.objects.get_or_create(name=name)
print(f"Seeded {len(PARTICIPANT_TYPE_VALUES)} participant type values.")
# --- Age Groups ---
AGE_GROUP_VALUES = [
    "Children (0-5)",
    "Children (6-10)",
    "Preteens (11-12)",
    "Teens (13-17)",
    "Young Adults (18-25)",
    "Adults (26-64)",
    "Older Adults (65+)",
]
for name in AGE_GROUP_VALUES:
    AgeGroup.objects.get_or_create(name=name)
print(f"Seeded {len(AGE_GROUP_VALUES)} age group values.")

# --- Faith / Religious / Philosophical Affiliation ---
# Expanded set balances inclusivity with manageable filter size.
# If you prefer leaner data, you can remove sub-categories (e.g., keep only "Christian (General)" instead of Catholic / Protestant / Orthodox).
# Notes:
#  - "Spiritual but Not Religious" distinct from formal traditions.
#  - "Secular / Non-Religious", "Agnostic", and "Atheist" separated for user self-identification nuance.
#  - "Interfaith" covers multi-faith practice context.
#  - Keep "Other" as a catch-all; avoid long-tail micro-denominations here.
FAITH_VALUES = [
    "Buddhist",
    "Christian (General)",
    "Catholic",
    "Protestant / Evangelical",
    "Orthodox Christian",
    "Hindu",
    "Jewish",
    "Muslim",
    "Sikh",
    "The Church of Jesus Christ of Latter-day Saints",
    "Spiritual but Not Religious",
    "Secular / Non-Religious",
    "Agnostic",
    "Atheist",
    "Interfaith",
    "Indigenous / Traditional",
    "Other",
]
for name in FAITH_VALUES:
    Faith.objects.get_or_create(name=name)
print(f"Seeded {len(FAITH_VALUES)} faith values.")


# --- Gender ---
GENDER_VALUES = [
    "Male",
    "Female",
]
for name in GENDER_VALUES:
    Gender.objects.get_or_create(name=name)
print(f"Seeded {len(GENDER_VALUES)} gender values.")


# --- Insurance Providers (consolidated canonical list) ---
# Includes national, major behavioral, regionals, government programs, and a self-pay option.
# Duplicates / legacy names consolidated (e.g., BlueCross variants, Cigna/Evernorth, New Directions/Lucet, MultiPlan PHCS).
INSURANCE_PROVIDER_VALUES = [
    # National Commercial
    "Aetna",
    "Anthem Blue Cross Blue Shield",
    "Blue Cross Blue Shield (BCBS)",
    "Cigna (Evernorth)",
    "UnitedHealthcare / Optum",
    "Humana",
    "Kaiser Permanente",
    "Molina Healthcare",
    "Oscar Health",
    "Oxford (UHC)",
    # Regionals / Blues
    "Highmark BCBS",
    "Horizon BCBS",
    "Regence BCBS",
    "Premera Blue Cross",
    # Behavioral / Networks / EAP
    "Carelon Behavioral Health",
    "Magellan",
    "Lucet (New Directions)",
    "Behavioral Health Systems (BHS)",
    "MultiPlan (PHCS)",
    "ComPsych",
    "Concern",
    "Dayforce",
    "TELUS Health",
    # Government / Public
    "Medicare",
    "Medicaid",
    "Children's Health Insurance Program (CHIP)",
    "TRICARE",
    "TriWest",
    "Military OneSource",
    # Other TPAs / Regionals / Specialty
    "GEHA",
    "Health Net",
    "HealthLink",
    "Medical Mutual",
    "Meritain Health",
    "Paramount",
    "Sagamore",
    "WellCare",
    "Wellfleet",
    "Amerigroup (Wellpoint)",
    # Payment alternative
    "Self-Pay / Private Pay",
]
for idx, name in enumerate(INSURANCE_PROVIDER_VALUES, start=1):
    prov, _ = InsuranceProvider.objects.get_or_create(name=name)
    ins_cats = {
        "Aetna": "Commercial",
        "Anthem Blue Cross Blue Shield": "Commercial",
        "Blue Cross Blue Shield (BCBS)": "Commercial",
        "Cigna (Evernorth)": "Commercial",
        "UnitedHealthcare / Optum": "Commercial",
        "Humana": "Commercial",
        "Kaiser Permanente": "Commercial",
        "Molina Healthcare": "Commercial",
        "Oscar Health": "Commercial",
        "Oxford (UHC)": "Commercial",
        "Highmark BCBS": "Regional",
        "Horizon BCBS": "Regional",
        "Regence BCBS": "Regional",
        "Premera Blue Cross": "Regional",
        "Carelon Behavioral Health": "Behavioral",
        "Magellan": "Behavioral",
        "Lucet (New Directions)": "Behavioral",
        "Behavioral Health Systems (BHS)": "Behavioral",
        "MultiPlan (PHCS)": "Network",
        "ComPsych": "EAP",
        "Concern": "EAP",
        "Dayforce": "EAP",
        "TELUS Health": "EAP",
        "Medicare": "Government",
        "Medicaid": "Government",
        "Children's Health Insurance Program (CHIP)": "Government",
        "TRICARE": "Government",
        "TriWest": "Government",
        "Military OneSource": "Government",
        "GEHA": "Commercial",
        "Health Net": "Commercial",
        "HealthLink": "Commercial",
        "Medical Mutual": "Regional",
        "Meritain Health": "Commercial",
        "Paramount": "Regional",
        "Sagamore": "Regional",
        "WellCare": "Government",
        "Wellfleet": "Commercial",
        "Amerigroup (Wellpoint)": "Government",
        "Self-Pay / Private Pay": "Self-Pay",
    }
    desired_cat = ins_cats.get(prov.name, "Other")
    changed = False
    if getattr(prov, 'category', '') != desired_cat:
        try:
            prov.category = desired_cat
            changed = True
        except Exception:
            pass
    if hasattr(prov, 'sort_order') and prov.sort_order != idx:
        prov.sort_order = idx
        changed = True
    if changed:
        prov.save()
print(f"Seeded {len(INSURANCE_PROVIDER_VALUES)} insurance provider values.")



# --- LGBTQIA+ (inclusive identities) ---
# Keep list concise yet representative; combine closely related terms to avoid over-fragmentation.
# Notes:
#  - Non-binary / Genderqueer combined to reduce duplication.
#  - Two-Spirit included (Indigenous-specific; users should self-select only if culturally appropriate).
#  - "Queer" included as reclaimed umbrella term for those who prefer it.
#  - Retain "Other" as catch-all; optionally add a free-text field in UI when "Other" selected.
LGBTQIA_VALUES = [
    "Lesbian",
    "Gay",
    "Bisexual",
    "Transgender",
    "Queer",
    "Questioning",
    "Intersex",
    "Asexual",
    "Pansexual",
    "Non-binary / Genderqueer",
    "Two-Spirit",
    "Other",
]
for name in LGBTQIA_VALUES:
    LGBTQIA.objects.get_or_create(name=name)
print(f"Seeded {len(LGBTQIA_VALUES)} LGBTQIA values.")


# --- License Types ---
# Actual independently licensed clinician credentials only (no technicians, no pre-license associates).
# Each tuple: (code/name stored, long description, human short_description WITHOUT leading acronym redundancy).
LICENSE_TYPE_VALUES = [
    # Psychiatry (medical)
    ("MD", "Medical Doctor specializing in psychiatry. Evaluates, diagnoses, and treats mental health conditions; may provide psychotherapy and can prescribe medications. Often collaborates with therapists for integrated care.", "Psychiatrist"),
    ("DO", "Doctor of Osteopathic Medicine specializing in psychiatry. Similar scope to MD psychiatrists with additional training in whole‑person / osteopathic principles; evaluates, diagnoses, and prescribes.", "Psychiatrist"),
    # Psychology (doctoral)
    ("PhD", "Doctoral-level Licensed Psychologist (PhD). Extensive training in psychological assessment, evidence-based psychotherapy, research methodology, and complex diagnostic formulation.", "Clinical Psychologist"),
    ("PsyD", "Doctoral-level Licensed Psychologist (PsyD). Emphasis on clinical practice and therapeutic interventions; trained in assessment, diagnosis, and evidence-based treatment planning.", "Clinical Psychologist"),
    # Clinical Social Work
    ("LCSW", "Licensed Clinical Social Worker. Provides psychotherapy with a biopsychosocial lens; integrates systemic, environmental, and resource coordination perspectives; may deliver individual, family, or group therapy.", "Clinical Social Worker"),
    ("LICSW", "Licensed Independent Clinical Social Worker (regional title). Scope parallels LCSW with possible supervisory credentials depending on state regulations.", "Clinical Social Worker"),
    # Marriage & Family Therapy
    ("LMFT", "Licensed Marriage & Family Therapist. Specializes in systemic / relational therapy addressing couples, families, and interpersonal dynamics; trained in evidence-based modalities for relational functioning.", "Marriage & Family Therapist"),
    ("MFT", "Marriage & Family Therapist (title variant). Provides systemic therapy for couples/families; equivalent clinical scope to LMFT subject to state licensure.", "Marriage & Family Therapist"),
    # Professional / Mental Health Counseling (state variants share unified client-facing role)
    ("LPC", "Licensed Professional Counselor. Delivers psychotherapy, diagnostic assessment, treatment planning, and skills-based interventions across a range of mental health concerns.", "Professional Counselor"),
    ("LPCC", "Licensed Professional Clinical Counselor (expanded clinical designation). Includes advanced training in assessment, differential diagnosis, and treatment of complex presentations.", "Professional Counselor"),
    ("LCPC", "Licensed Clinical Professional Counselor (state variant). Provides psychotherapy, diagnosis, and coordinated mental health treatment.", "Professional Counselor"),
    ("LMHC", "Licensed Mental Health Counselor (state variant). Offers psychotherapy, psychoeducation, and evidence-based interventions for diverse mental health conditions.", "Professional Counselor"),
    ("LCMHC", "Licensed Clinical Mental Health Counselor (state variant). Emphasis on clinical assessment, individualized treatment planning, and outcome-focused therapy.", "Professional Counselor"),
    # Advanced Practice Nursing in Psychiatry
    ("PMHNP-BC", "Psychiatric Mental Health Nurse Practitioner – Board Certified. Conducts psychiatric evaluations, diagnoses, prescribes and manages psychotropic medications, and may provide psychotherapy depending on practice model.", "Psychiatric Nurse Practitioner"),
    # Behavior Analysis
    ("BCBA", "Board Certified Behavior Analyst. Designs and implements behavior analytic interventions (often in autism spectrum or developmental contexts); conducts functional behavior assessments and data-driven treatment.", "Behavior Analyst"),
    # Substance Use Counseling (regional/credential variants unified for users)
    ("LADC", "Licensed Alcohol and Drug Counselor. Provides substance use assessment, individual/group counseling, relapse prevention planning, and coordination of recovery supports.", "Substance Use Counselor"),
    ("CADC", "Certified Alcohol and Drug Counselor (state-recognized). Delivers counseling, psychoeducation, and recovery planning for substance use and co-occurring disorders.", "Substance Use Counselor"),
    ("CASAC", "Credentialed Alcoholism and Substance Abuse Counselor (New York). Specializes in assessment, treatment planning, counseling, and recovery management for substance-related disorders.", "Substance Use Counselor"),
]
for name, description, short_desc in LICENSE_TYPE_VALUES:
    obj, created = LicenseType.objects.get_or_create(name=name, defaults={"description": description, "short_description": short_desc})
    update_needed = False
    if obj.description != description and description:
        obj.description = description
        update_needed = True
    if obj.short_description != short_desc:
        obj.short_description = short_desc
        update_needed = True
    family_map = {
        "Psychiatrist": "Psychiatry",
        "Clinical Psychologist": "Psychology",
        "Licensed Psychologist": "Psychology",
        "Clinical Social Worker": "Social Work",
        "Marriage & Family Therapist": "Marriage & Family",
        "Professional Counselor": "Counseling",
        "Psychiatric Nurse Practitioner": "Nursing",
        "Behavior Analyst": "Behavior Analysis",
        "Substance Use Counselor": "Substance Use",
    }
    desired_cat = family_map.get(obj.short_description, "Other")
    if getattr(obj, 'category', '') != desired_cat:
        try:
            obj.category = desired_cat
            update_needed = True
        except Exception:
            pass
    if hasattr(obj, 'sort_order') and obj.sort_order == 0:
        obj.sort_order = 0
    if update_needed:
        obj.save()
print(f"Seeded {len(LICENSE_TYPE_VALUES)} license type values (actual licenses, unified short descriptions).")


# --- Payment Methods ---
# Canonical, client-facing list (actual methods clients recognize). Includes card brands for logo display.
# Rename map handles legacy entries created under older naming conventions.
PAYMENT_METHOD_RENAMES = {
    "ACH Bank transfer": "ACH Transfer",
    "Wire": "Wire Transfer",
    "Apple Cash": "Apple Pay",  # treat Apple Cash under Apple Pay wallet acceptance
    "Paypal": "PayPal",
    "Health Savings Account": "HSA Card",
}
for old, new in PAYMENT_METHOD_RENAMES.items():
    try:
        if PaymentMethod.objects.filter(name=old).exists() and not PaymentMethod.objects.filter(name=new).exists():
            pm = PaymentMethod.objects.get(name=old)
            pm.name = new
            pm.save()
    except Exception:
        pass  # non-fatal; continue

PAYMENT_METHOD_VALUES = [
    "Cash",
    "Check",
    # Card brands
    "Visa",
    "Mastercard",
    "American Express",
    "Discover",
    "Debit Card",
    # Health account funding
    "HSA Card",
    "FSA Card",
    # Bank transfers
    "ACH Transfer",
    "Wire Transfer",
    # Digital wallets / P2P
    "Apple Pay",
    "Google Pay",
    "PayPal",
    "Venmo",
    "Zelle",
]
for idx, name in enumerate(PAYMENT_METHOD_VALUES, start=1):
    pm, _ = PaymentMethod.objects.get_or_create(name=name)
    cat_map = {
        "Cash": "Cash",
        "Check": "Cash",
        "Visa": "Card",
        "Mastercard": "Card",
        "American Express": "Card",
        "Discover": "Card",
        "Debit Card": "Card",
        "HSA Card": "Health Account",
        "FSA Card": "Health Account",
        "ACH Transfer": "Bank",
        "Wire Transfer": "Bank",
        "Apple Pay": "Digital Wallet",
        "Google Pay": "Digital Wallet",
        "PayPal": "Digital Wallet",
        "Venmo": "Peer-to-Peer",
        "Zelle": "Peer-to-Peer",
    }
    desired_cat = cat_map.get(pm.name, "Other")
    changed = False
    if getattr(pm, 'category', '') != desired_cat:
        try:
            pm.category = desired_cat
            changed = True
        except Exception:
            pass
    if hasattr(pm, 'sort_order') and pm.sort_order != idx:
        pm.sort_order = idx
        changed = True
    if changed:
        pm.save()
print(f"Seeded {len(PAYMENT_METHOD_VALUES)} payment method values (canonical list).")


# --- Race/Ethnicity ---
# Canonical, user-facing categories (concise, inclusive, not overly granular).
# Rename legacy entries to new standardized labels.
RACE_ETHNICITY_RENAMES = {
    "Black": "Black / African American",
    "Hispanic and Latino": "Hispanic / Latino/a/e",
    "Asian": "Asian (East Asian)",
    "Native American": "Native American / Alaska Native",
    "Mixed Race Family": "Multiracial",
    "Pacific Islander": "Pacific Islander / Native Hawaiian",
    "Middle Eastern": "Middle Eastern / North African (MENA)",
}
for old, new in RACE_ETHNICITY_RENAMES.items():
    try:
        if RaceEthnicity.objects.filter(name=old).exists():
            if not RaceEthnicity.objects.filter(name=new).exists():
                RaceEthnicity.objects.filter(name=old).update(name=new)
            else:
                # If target exists, move any relations then delete duplicate
                from users.models_profile import RaceEthnicitySelection
                try:
                    old_obj = RaceEthnicity.objects.get(name=old)
                    new_obj = RaceEthnicity.objects.get(name=new)
                    RaceEthnicitySelection.objects.filter(race_ethnicity=old_obj).update(race_ethnicity=new_obj)
                    old_obj.delete()
                except Exception:
                    pass
    except Exception:
        pass

RACE_ETHNICITY_VALUES = [
    "Black / African American",
    "Hispanic / Latino/a/e",
    "White",
    "Asian (East Asian)",
    "South Asian",
    "Middle Eastern / North African (MENA)",
    "Native American / Alaska Native",
    "Pacific Islander / Native Hawaiian",
    "Caribbean",
    "Multiracial",
    "Other",
]
for name in RACE_ETHNICITY_VALUES:
    RaceEthnicity.objects.get_or_create(name=name)
print(f"Seeded {len(RACE_ETHNICITY_VALUES)} race/ethnicity values (canonical list).")


# --- Therapy Types ---
# Curated canonical list. Removed supervision/coaching (not modalities), generic duplicates, and normalized naming.
THERAPY_TYPE_RENAMES = {
    "Acceptance and Commitment (ACT)": "Acceptance & Commitment Therapy (ACT)",
    "Cognitive Behavioral (CBT)": "Cognitive Behavioral Therapy (CBT)",
    "Dialectical Behavior (DBT)": "Dialectical Behavior Therapy (DBT)",
    "Exposure Response Prevention (ERP)": "Exposure & Response Prevention (ERP)",
    "Mindfulness-Based (MBCT)": "Mindfulness-Based Cognitive Therapy (MBCT)",
    "Psychobiological Approach Couple Therapy": "PACT (Psychobiological Approach to Couple Therapy)",
    "Internal Family Systems (IFS)": "Internal Family Systems (IFS)",  # keep as-is for clarity
    "Solution Focused Brief (SFBT)": "Solution Focused Brief Therapy (SFBT)",
    "Parent-Child Interaction (PCIT)": "Parent-Child Interaction Therapy (PCIT)",
}
for old, new in THERAPY_TYPE_RENAMES.items():
    try:
        if TherapyType.objects.filter(name=old).exists():
            if not TherapyType.objects.filter(name=new).exists():
                TherapyType.objects.filter(name=old).update(name=new)
            else:
                from users.models_profile import TherapyTypeSelection
                try:
                    old_obj = TherapyType.objects.get(name=old)
                    new_obj = TherapyType.objects.get(name=new)
                    TherapyTypeSelection.objects.filter(therapy_type=old_obj).update(therapy_type=new_obj)
                    old_obj.delete()
                except Exception:
                    pass
    except Exception:
        pass

THERAPY_TYPE_VALUES = [
    # Evidence-based / structured
    "Acceptance & Commitment Therapy (ACT)",
    "Cognitive Behavioral Therapy (CBT)",
    "Dialectical Behavior Therapy (DBT)",
    "Exposure & Response Prevention (ERP)",
    "Mindfulness-Based Cognitive Therapy (MBCT)",
    "Prolonged Exposure Therapy",
    "Solution Focused Brief Therapy (SFBT)",
    "Internal Family Systems (IFS)",
    "Eye Movement Desensitization & Reprocessing (EMDR)",
    "Schema Therapy",
    "Acceptance-Based Relational (ABR)",
    # Trauma / somatic / attachment
    "Somatic Therapy",
    "Attachment-Based",
    "Brainspotting",
    "Trauma Focused",
    # Psychodynamic / analytic
    "Psychodynamic",
    "Psychoanalytic",
    "Jungian",
    # Relational / systemic / family / couples
    "Marriage & Family Therapy",
    "Family Systems",
    "Structural Family Therapy",
    "PACT (Psychobiological Approach to Couple Therapy)",
    "Gottman Method",
    "Emotionally Focused Therapy (EFT)",
    "Imago Relationship Therapy",
    # Humanistic / experiential
    "Humanistic",
    "Person-Centered",
    "Gestalt",
    "Experiential Therapy",
    "Existential",
    "Transpersonal",
    # Cultural / strengths / integrative
    "Multicultural",
    "Culturally Sensitive",
    "Strength-Based",
    "Integrative",
    "Eclectic",
    # Behavioral / analytic / coaching-adjacent (kept only if therapy-focused)
    "Applied Behavior Analysis (ABA)",
    "Behavioral Activation",
    # Specialty / modality specific
    "Mindfulness-Based Stress Reduction (MBSR)",
    "Compassion Focused",
    "Positive Psychology",
    "Narrative Therapy",
    "Motivational Interviewing",
    "Rational Emotive Behavior Therapy (REBT)",
    "Reality Therapy",
    "Relational",
    # Creative / expressive
    "Art Therapy",
    "Expressive Arts",
    "Music Therapy",
    "Dance / Movement Therapy",
    "Sandplay",
    "Play Therapy",
    # Specialized / emerging / adjunct
    "Neurofeedback",
    "Biofeedback",
    "Energy Psychology",
    "Hypnotherapy",
    "Ketamine-Assisted Psychotherapy",
    "Neuro-Linguistic Programming (NLP)",
    # Assessment
    "Psychological Testing & Evaluation",
]

# Ensure creation
for idx, name in enumerate(THERAPY_TYPE_VALUES, start=1):
    t, _ = TherapyType.objects.get_or_create(name=name)
    cat_rules = [
        ("Trauma", "Trauma / Somatic"),
        ("Somatic", "Trauma / Somatic"),
        ("Brainspot", "Trauma / Somatic"),
        ("EMDR", "Trauma / Somatic"),
        ("IFS", "Parts / Internal"),
        ("Internal Family Systems", "Parts / Internal"),
        ("Mindfulness", "Mindfulness / Third Wave"),
        ("Acceptance & Commitment", "Mindfulness / Third Wave"),
        ("Dialectical", "Mindfulness / Third Wave"),
        ("CBT", "CBT / Structured"),
        ("Exposure", "CBT / Structured"),
        ("Solution Focused", "Brief / Solution-Focused"),
        ("Family", "Family / Couples"),
        ("Marriage & Family", "Family / Couples"),
        ("Gottman", "Family / Couples"),
        ("PACT", "Family / Couples"),
        ("Emotionally Focused", "Family / Couples"),
        ("Imago", "Family / Couples"),
        ("Play", "Child / Adolescent"),
        ("Parent-Child", "Child / Adolescent"),
        ("Jungian", "Psychodynamic / Analytic"),
        ("Psychoanalytic", "Psychodynamic / Analytic"),
        ("Psychodynamic", "Psychodynamic / Analytic"),
        ("Narrative", "Constructivist / Narrative"),
        ("Schema", "CBT / Structured"),
        ("Art", "Creative / Expressive"),
        ("Expressive", "Creative / Expressive"),
        ("Music", "Creative / Expressive"),
        ("Dance", "Creative / Expressive"),
        ("Sandplay", "Creative / Expressive"),
        ("Hypno", "Adjunct / Specialized"),
        ("Ketamine", "Adjunct / Specialized"),
        ("Neurofeedback", "Adjunct / Specialized"),
        ("Biofeedback", "Adjunct / Specialized"),
        ("Energy", "Adjunct / Specialized"),
        ("Integrative", "Integrative / Eclectic"),
        ("Eclectic", "Integrative / Eclectic"),
        ("Humanistic", "Humanistic / Experiential"),
        ("Gestalt", "Humanistic / Experiential"),
        ("Experiential", "Humanistic / Experiential"),
        ("Existential", "Humanistic / Experiential"),
        ("Transpersonal", "Humanistic / Experiential"),
        ("Relational", "Relational / Attachment"),
        ("Attachment", "Relational / Attachment"),
        ("Compassion", "Mindfulness / Third Wave"),
        ("Motivational Interviewing", "Motivational / Change"),
        ("Positive Psychology", "Motivational / Change"),
        ("Reality", "CBT / Structured"),
        ("Rational Emotive", "CBT / Structured"),
        ("Strength-Based", "Strength / Identity"),
        ("Multicultural", "Cultural / Identity"),
        ("Culturally Sensitive", "Cultural / Identity"),
    ]
    assigned = None
    for substr, cat in cat_rules:
        if substr.lower() in t.name.lower():
            assigned = cat
            break
    if not assigned:
        assigned = "Other"
    changed = False
    if getattr(t, 'category', '') != assigned:
        try:
            t.category = assigned
            changed = True
        except Exception:
            pass
    if hasattr(t, 'sort_order') and t.sort_order != idx:
        t.sort_order = idx
        changed = True
    if changed:
        t.save()
print(f"Seeded {len(THERAPY_TYPE_VALUES)} therapy type values (canonical list).")


# --- Titles ---
# Streamlined, inclusive honorifics commonly relevant in mental health / allied professional contexts.
# We unify gendered variants (Mrs., Miss.) under Ms. to reduce filter clutter; keep Mx. for gender-neutral.
TITLE_RENAMES = {
    "Mrs.": "Ms.",
    "Miss.": "Ms.",
}
for old, new in TITLE_RENAMES.items():
    try:
        if Title.objects.filter(name=old).exists():
            if not Title.objects.filter(name=new).exists():
                Title.objects.filter(name=old).update(name=new)
            else:
                # If target exists just remove duplicate
                Title.objects.filter(name=old).delete()
    except Exception:
        pass

TITLE_VALUES = [
    "Dr.",          # Doctor (doctoral degree)
    "Mr.",
    "Ms.",          # Unified feminine honorific
    "Mx.",          # Gender-neutral
    "Prof.",        # Academic title
    "Rev.",         # Ordained (generic)
    "Rev. Dr.",     # Dual religious + doctoral
    "Rabbi",        # Jewish clergy
    "Pastor",       # Christian clergy (generic)
    "Father",       # Catholic / Orthodox clergy
    "Sister",       # Catholic religious
]
for name in TITLE_VALUES:
    Title.objects.get_or_create(name=name)
print(f"Seeded {len(TITLE_VALUES)} title values (canonical list).")


from users.models_profile import SpecialtyLookup, OtherIdentity

# --- Specialty Lookup ---
SPECIALTY_LOOKUP_RENAMES = {
    "Alcohol Use": "Alcohol Use Disorder",
    "Drug Abuse": "Substance Use Disorder",
    "Substance Use": "Substance Use Disorder",
    "Addiction": "Addiction / Compulsive Behaviors",
    "Internet Addiction": "Internet / Screen Overuse",
    "Video Game Addiction": "Gaming Addiction",
    "Sexual Addiction": "Compulsive Sexual Behavior",
    "Domestic Abuse ": "Domestic Violence / Abuse",
    "Domestic Violence": "Domestic Violence / Abuse",
    "Borderline Personality (BPD)": "Borderline Personality Disorder (BPD)",
    "Narcissistic Personality (NPD)": "Narcissistic Personality Disorder (NPD)",
    "Developmental Disorders": "Neurodevelopmental Disorders",
    "Education and Learning Disabilities": "Learning Disabilities",
    "Testing and Evaluation": "Psychological Testing & Evaluation",
    "Psychosis": "Psychotic Disorders",
    "Thinking Disorders": "Psychotic Disorders",
    "Geriatric and Seniors": "Older Adults / Geriatric",
    "Transgender": "Gender Identity / Transition Support",
    "Impulse Control Disorders": "Impulse-Control Disorders",
    "Open Relationships Non-Monogamy": "Open / Consensual Non-Monogamy",
}

from users.models_profile import Specialty as _SpecModel
try:
    from django.db import transaction
    for old, new in SPECIALTY_LOOKUP_RENAMES.items():
        try:
            if SpecialtyLookup.objects.filter(name=old).exists():
                if not SpecialtyLookup.objects.filter(name=new).exists():
                    SpecialtyLookup.objects.filter(name=old).update(name=new)
                else:
                    old_obj = SpecialtyLookup.objects.get(name=old)
                    new_obj = SpecialtyLookup.objects.get(name=new)
                    _SpecModel.objects.filter(specialty=old_obj).update(specialty=new_obj)
                    old_obj.delete()
        except Exception:
            pass
except Exception:
    pass

# Curated canonical specialty list
SPECIALTY_LOOKUP_VALUES = [
    # Substance / Behavioral Compulsions
    "Substance Use Disorder",
    "Alcohol Use Disorder",
    "Addiction / Compulsive Behaviors",
    "Gaming Addiction",
    "Internet / Screen Overuse",
    "Compulsive Sexual Behavior",
    "Gambling",
    # Mood / Anxiety / Trauma
    "Depression",
    "Anxiety",
    "Obsessive-Compulsive (OCD)",
    "Trauma and PTSD",
    "Stress",
    "Suicidal Ideation",
    "Panic / Agoraphobia",
    "Mood Disorders",
    # Personality / Psychotic / Dissociative
    "Borderline Personality Disorder (BPD)",
    "Narcissistic Personality Disorder (NPD)",
    "Personality Disorders",
    "Psychotic Disorders",
    "Dissociative Disorders (DID)",
    # Neurodevelopmental / Cognitive
    "ADHD",
    "Autism",
    "Neurodevelopmental Disorders",
    "Learning Disabilities",
    "Intellectual Disability",
    "Hoarding",
    # Physical / Chronic / Health
    "Chronic Illness",
    "Chronic Pain",
    "Cancer",
    "Sleep or Insomnia",
    "Obesity",
    "Weight Loss",
    "Medical Detox",
    # Life Stage / Identity / Population
    "Child",
    "Parenting",
    "Teen Violence",
    "Older Adults / Geriatric",
    "Caregivers",
    "First Responders",
    "Veterans",
    "Women's Issues",
    "Men's Issues",
    "Gender Identity / Transition Support",
    "Open / Consensual Non-Monogamy",
    "Sex-Positive, Kink Allied",
    "Racial Identity",
    "LGBTQ+",
    # Relationships / Family
    "Relationship Issues",
    "Marital and Premarital",
    "Infidelity",
    "Divorce",
    "Family Conflict",
    "Domestic Violence / Abuse",
    "Infertility",
    "Pregnancy, Prenatal, Postpartum",
    # Skills / Functioning / Performance
    "Coping Skills",
    "Social / Peer Relationships",
    "Life Transitions",
    "Career Counseling",
    "Sports Performance",
    "Self Esteem",
    "Anger Management",
    "Impulse-Control Disorders",
    "Chronic Impulsivity",
    # Sexual Health
    "Sex Therapy",
    "Sexual Abuse / Assault",
    # Trauma & Brain Injury
    "Traumatic Brain Injury (TBI)",
    # Specialty Clinical Areas
    "Eating Disorders",
    "Dual Diagnosis",
    "Codependency",
    "Oppositional Defiance (ODD)",
    "Emotional Disturbance",
    "Behavioral Issues",
    "Self-Harming",
    "Grief",
    "Body Positivity",
    # Spiritual / Meaning
    "Spirituality",
    # Testing / Assessment
    "Psychological Testing & Evaluation",
    # Other / Catch-all
    "Other",
]
for idx, name in enumerate(SPECIALTY_LOOKUP_VALUES, start=1):
    s, _ = SpecialtyLookup.objects.get_or_create(name=name)
    spec_cat_rules = [
        ("Substance Use", "Substance / Addictive"),
        ("Alcohol", "Substance / Addictive"),
        ("Addiction", "Substance / Addictive"),
        ("Gaming", "Substance / Addictive"),
        ("Internet", "Substance / Addictive"),
        ("Compulsive Sexual", "Substance / Addictive"),
        ("Gambling", "Substance / Addictive"),
        ("Depression", "Mood / Anxiety"),
        ("Anxiety", "Mood / Anxiety"),
        ("OCD", "Mood / Anxiety"),
        ("Panic", "Mood / Anxiety"),
        ("Mood Disorder", "Mood / Anxiety"),
        ("Trauma", "Trauma / Stressor"),
        ("PTSD", "Trauma / Stressor"),
        ("Stress", "Trauma / Stressor"),
        ("Suicidal", "Crisis / Safety"),
        ("Self-Harming", "Crisis / Safety"),
        ("Psychotic", "Serious Mental Illness"),
        ("Psychosis", "Serious Mental Illness"),
        ("Dissociative", "Serious Mental Illness"),
        ("Personality", "Personality"),
        ("BPD", "Personality"),
        ("Narcissistic", "Personality"),
        ("ADHD", "Neurodevelopmental"),
        ("Autism", "Neurodevelopmental"),
        ("Neurodevelopmental", "Neurodevelopmental"),
        ("Learning", "Neurodevelopmental"),
        ("Intellectual", "Neurodevelopmental"),
        ("Hoarding", "Neurodevelopmental"),
        ("Chronic Illness", "Health / Medical"),
        ("Chronic Pain", "Health / Medical"),
        ("Cancer", "Health / Medical"),
        ("Sleep", "Health / Medical"),
        ("Obesity", "Health / Medical"),
        ("Weight", "Health / Medical"),
        ("Medical Detox", "Health / Medical"),
        ("Child", "Life Stage / Role"),
        ("Parent", "Life Stage / Role"),
        ("Teen", "Life Stage / Role"),
        ("Older Adults", "Life Stage / Role"),
        ("Geriatric", "Life Stage / Role"),
        ("Caregiver", "Life Stage / Role"),
        ("First Responder", "Population / Identity"),
        ("Veterans", "Population / Identity"),
        ("Women's Issues", "Population / Identity"),
        ("Men's Issues", "Population / Identity"),
        ("Gender Identity", "Population / Identity"),
        ("Racial Identity", "Population / Identity"),
        ("LGBTQ", "Population / Identity"),
        ("Relationship", "Relationships / Family"),
        ("Marital", "Relationships / Family"),
        ("Infidelity", "Relationships / Family"),
        ("Divorce", "Relationships / Family"),
        ("Family Conflict", "Relationships / Family"),
        ("Domestic", "Relationships / Family"),
        ("Pregnancy", "Reproductive / Perinatal"),
        ("Prenatal", "Reproductive / Perinatal"),
        ("Postpartum", "Reproductive / Perinatal"),
        ("Infertility", "Reproductive / Perinatal"),
        ("Sex Therapy", "Sexual Health"),
        ("Sexual Abuse", "Sexual Health"),
        ("Compulsive Sexual", "Sexual Health"),
        ("Body Positivity", "Body / Self Image"),
        ("Eating Disorder", "Body / Self Image"),
        ("Self Esteem", "Body / Self Image"),
        ("Career", "Performance / Achievement"),
        ("Sports Performance", "Performance / Achievement"),
        ("Life Transition", "Life Transitions / Adjustment"),
        ("Adjustment", "Life Transitions / Adjustment"),
        ("Coping", "Skills / Coping"),
        ("Social", "Skills / Coping"),
        ("Impulse", "Impulse / Control"),
        ("Oppositional", "Impulse / Control"),
        ("Codependency", "Relationships / Family"),
        ("Dual Diagnosis", "Co-occurring"),
        ("TBI", "Neurological"),
        ("Brain Injury", "Neurological"),
        ("Psychological Testing", "Assessment / Evaluation"),
        ("Other", "Other"),
    ]
    sc = None
    for substr, cat in spec_cat_rules:
        if substr.lower() in s.name.lower():
            sc = cat
            break
    if not sc:
        sc = "Other"
    changed = False
    if getattr(s, 'category', '') != sc:
        try:
            s.category = sc
            changed = True
        except Exception:
            pass
    if hasattr(s, 'sort_order') and s.sort_order != idx:
        s.sort_order = idx
        changed = True
    if changed:
        s.save()
print(f"Seeded {len(SPECIALTY_LOOKUP_VALUES)} specialty lookup values (canonical list).")

# --- Other Identity ---
# Concise, user-facing self-identification options (non-duplicative of race/ethnicity, gender, sexuality).
# Focused on lived experience / accessibility contexts. Avoid long medical condition tail.
OTHER_IDENTITY_RENAMES = {
    "Blind": "Blind / Low Vision",
    "Deaf": "Deaf / Hard of Hearing",
    "Immuno-disorders": "Immunocompromised",
}
try:
    for old, new in OTHER_IDENTITY_RENAMES.items():
        if OtherIdentity.objects.filter(name=old).exists():
            if not OtherIdentity.objects.filter(name=new).exists():
                OtherIdentity.objects.filter(name=old).update(name=new)
            else:
                # remove duplicate old if new already exists
                OtherIdentity.objects.filter(name=old).delete()
except Exception:
    pass

OTHER_IDENTITY_VALUES = [
    "Blind / Low Vision",
    "Deaf / Hard of Hearing",
    "Disabled",
    "Neurodivergent",
    "Immunocompromised",
    "Chronic Illness",
    "Single Parent",
    "Caregiver",
    "Veteran",
    "Survivor of Trauma",
    "Other",
]
for name in OTHER_IDENTITY_VALUES:
    OtherIdentity.objects.get_or_create(name=name)
print(f"Seeded {len(OTHER_IDENTITY_VALUES)} other identity values (canonical list).")

# ---------------------------------------------------------------------------
# Optional Purge Phase
# ---------------------------------------------------------------------------
# By default we DO NOT delete any legacy / extra lookup rows so historical
# data and references remain intact. To clean the database to ONLY the
# canonical values above, set PURGE_UNUSED = True (or export env var
# LOOKUP_PURGE=1) and re-run the script:
#   LOOKUP_PURGE=1 python manage.py shell < seed_lookups.py
# Safety: For lookup models that have related selection tables we only
# delete rows that are both (a) not in the canonical allowlist AND
# (b) have zero related selection references. This avoids breaking FKs.

import os as _os

PURGE_UNUSED = bool(int(_os.environ.get("LOOKUP_PURGE", "0")))  # or flip manually

if PURGE_UNUSED:
    print("[PURGE] Starting purge of non-canonical, unreferenced lookup rows...")
    from django.db.models import Count
    from users.models_profile import (
        Faith, Gender, InsuranceProvider, LGBTQIA, LicenseType, PaymentMethod,
        RaceEthnicity, TherapyType, Title, SpecialtyLookup, OtherIdentity,
        RaceEthnicitySelection, TherapyTypeSelection, Specialty as _SpecModel,
    )

    # Build canonical allowlists
    keep_faith = set(FAITH_VALUES)
    keep_gender = set(GENDER_VALUES)
    keep_insurance = set(INSURANCE_PROVIDER_VALUES)
    keep_lgbtq = set(LGBTQIA_VALUES)
    keep_license = {v[0] for v in LICENSE_TYPE_VALUES}
    keep_payment = set(PAYMENT_METHOD_VALUES)
    keep_race = set(RACE_ETHNICITY_VALUES)
    keep_therapy = set(THERAPY_TYPE_VALUES)
    keep_titles = set(TITLE_VALUES)
    keep_specialty = set(SPECIALTY_LOOKUP_VALUES)
    keep_other_identity = set(OTHER_IDENTITY_VALUES)

    # Direct purge (no selection dependency tables tracked here)
    def _purge_direct(model, keep_set, label):
        qs = model.objects.exclude(name__in=keep_set)
        count = qs.count()
        if count:
            print(f"[PURGE] Deleting {count} {label} rows: {[o.name for o in qs][:10]}{'...' if count>10 else ''}")
            qs.delete()
        else:
            print(f"[PURGE] No extra {label} rows to delete.")

    _purge_direct(Faith, keep_faith, "Faith")
    _purge_direct(Gender, keep_gender, "Gender")
    _purge_direct(LicenseType, keep_license, "LicenseType")
    _purge_direct(PaymentMethod, keep_payment, "PaymentMethod")
    _purge_direct(InsuranceProvider, keep_insurance, "InsuranceProvider")
    _purge_direct(LGBTQIA, keep_lgbtq, "LGBTQIA")
    _purge_direct(Title, keep_titles, "Title")
    _purge_direct(OtherIdentity, keep_other_identity, "OtherIdentity")

    # Purge only unreferenced rows for models with dependent selection usage
    def _purge_unreferenced(model, keep_set, rel_name, label):
        annotated = model.objects.annotate(refs=Count(rel_name))
        targets = annotated.filter(refs=0).exclude(name__in=keep_set)
        count = targets.count()
        if count:
            print(f"[PURGE] Deleting {count} unreferenced {label} rows: {[o.name for o in targets][:10]}{'...' if count>10 else ''}")
            targets.delete()
        else:
            print(f"[PURGE] No unreferenced extra {label} rows to delete.")

    # Relationship field names inferred from related_name / model usage
    _purge_unreferenced(RaceEthnicity, keep_race, 'raceethnicityselection', 'RaceEthnicity')
    _purge_unreferenced(TherapyType, keep_therapy, 'therapytypeselection', 'TherapyType')
    _purge_unreferenced(SpecialtyLookup, keep_specialty, 'specialty', 'SpecialtyLookup')

    print("[PURGE] Completed purge step.\n")
else:
    print("(Purge disabled – set LOOKUP_PURGE=1 to enable cleanup of non-canonical rows.)")
