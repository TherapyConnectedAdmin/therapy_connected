"""
Seed script for all lookup tables.
Run with: python manage.py shell < seed_lookups.py
Works locally and on Heroku (as long as Django is set up and models are migrated).
Add more lookup values as needed in the appropriate sections.
"""
from users.models_profile import Faith, Gender, InsuranceProvider, LGBTQIA, LicenseType, PaymentMethod, RaceEthnicity, TherapyType, Title, AgeGroup, ParticipantType
# --- Participant Types ---
PARTICIPANT_TYPE_VALUES = [
    "Individuals",
    "Couples",
    "Family",
    "Group",
]
for name in PARTICIPANT_TYPE_VALUES:
    ParticipantType.objects.get_or_create(name=name)
print(f"Seeded {len(PARTICIPANT_TYPE_VALUES)} participant type values.")
# --- Age Groups ---
AGE_GROUP_VALUES = [
    "Toddler",
    "Children (6 to 10)",
    "Preteen",
    "Teen",
    "Adults",
    "Elders (65+)",
]
for name in AGE_GROUP_VALUES:
    AgeGroup.objects.get_or_create(name=name)
print(f"Seeded {len(AGE_GROUP_VALUES)} age group values.")

# --- Faith ---
FAITH_VALUES = [
    "Buddhist",
    "Christian",
    "Hindu",
    "Jewish",
    "Muslim",
    "Secular and Nonreligious",
    "Sikh",
    "The Church of Jesus Christ of Latter-day Saints",
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


# --- Insurance Providers ---
INSURANCE_PROVIDER_VALUES = [
    "1199SEIU",
    "Aetna",
    "Ambetter",
    "Anthem",
    "APS Healthcare",
    "BHS | Behavioral Health Systems",
    "Blue Cross",
    "Blue Shield",
    "BlueCross and BlueShield",
    "Carebridge EAP",
    "Carelon Behavioral Health",
    "CareSource",
    "Children's Health Insurance Program (CHIP)",
    "Cigna and Evernorth",
    "ComPsych",
    "Concern",
    "Coventry",
    "Dayforce",
    "First Health",
    "Government Employees Health Association (GEHA)",
    "Health Net",
    "HealthLink",
    "Humana",
    "Magellan",
    "MagnaCare",
    "Managed Health Network (MHN)",
    "Medicaid",
    "Medical Mutual",
    "Medicare",
    "Meridian",
    "Meritain Health",
    "MHNet Behavioral Health",
    "Military OneSource",
    "Molina Healthcare",
    "MultiPlan",
    "MultiPlan Private Healthcare Systems (PHCS)",
    "New Directions | Lucet",
    "Optum",
    "Oscar Health",
    "Oxford",
    "Paramount",
    "Passport Health Plan",
    "Reliant",
    "Sagamore",
    "TELUS Health",
    "TRICARE",
    "TriWest",
    "United Medical Resources (UMR)",
    "UnitedHealthcare UHC | UBH",
    "WellCare",
    "Wellfleet",
    "Wellpoint | Amerigroup",
    "Zelis Healthcare",
]
for name in INSURANCE_PROVIDER_VALUES:
    InsuranceProvider.objects.get_or_create(name=name)
print(f"Seeded {len(INSURANCE_PROVIDER_VALUES)} insurance provider values.")



# --- LGBTQIA ---
LGBTQIA_VALUES = [
    "Bisexual",
    "Gay",
    "Lesbian",
    "Transgender",
    "Other",
]
for name in LGBTQIA_VALUES:
    LGBTQIA.objects.get_or_create(name=name)
print(f"Seeded {len(LGBTQIA_VALUES)} LGBTQIA values.")


# --- License Types ---
LICENSE_TYPE_VALUES = [
    ("MD", "Medical Doctor trained in psychiatry. Can diagnose, treat, and prescribe medications for mental health conditions."),
    ("DO", "Doctor of Osteopathic Medicine. Similar scope to MDs with added emphasis on holistic care. Often practices psychiatry."),
    ("PhD", "Doctor of Philosophy in Psychology. Focuses on research, therapy, and psychological testing."),
    ("PsyD", "Doctor of Psychology. Clinical doctorate focused on therapeutic practice rather than research."),
    ("LCSW", "Licensed Clinical Social Worker. Provides therapy and case management, often in community or clinical settings."),
    ("LICSW", "Licensed Independent Clinical Social Worker. Similar to LCSW; title used in certain states. May indicate supervisory privileges."),
    ("LMFT", "Licensed Marriage and Family Therapist. Specializes in couples and family counseling."),
    ("MFT", "Marriage and Family Therapist. May be used interchangeably with LMFT depending on the state."),
    ("LPC", "Licensed Professional Counselor. Provides mental health counseling and support. Title used in many states."),
    ("LPCC", "Licensed Professional Clinical Counselor. Similar to LPC, often includes more advanced clinical training."),
    ("LCPC", "Licensed Clinical Professional Counselor. Title used in states like Illinois; equivalent to LPC/LPCC."),
    ("PMHNP-BC", "Psychiatric Mental Health Nurse Practitioner – Board Certified. Prescribes medications and provides psychiatric care."),
    ("BCBA", "Board Certified Behavior Analyst. Focuses on behavior therapy, especially for autism and developmental disorders."),
    ("CADC", "Certified Alcohol and Drug Counselor. Specializes in substance use and recovery support."),
    ("LADC", "Licensed Alcohol and Drug Counselor. Credential used in some states for substance use professionals."),
    ("CASAC", "Credentialed Alcoholism and Substance Abuse Counselor. Common title in New York and similar jurisdictions."),
    ("Psychiatric Technician", "Provides hands-on support and monitoring in inpatient or residential settings under supervision."),
    ("Mental Health Technician", "Assists in daily care and crisis intervention. Works closely with clinical teams but not independently licensed."),
]
for name, description in LICENSE_TYPE_VALUES:
    LicenseType.objects.get_or_create(name=name, defaults={"description": description})
print(f"Seeded {len(LICENSE_TYPE_VALUES)} license type values.")


# --- Payment Methods ---
PAYMENT_METHOD_VALUES = [
    "ACH Bank transfer",
    "American Express",
    "Apple Cash",
    "Cash",
    "Check",
    "Discover",
    "Health Savings Account",
    "Mastercard",
    "Paypal",
    "Venmo",
    "Visa",
    "Wire",
    "Zelle",
]
for name in PAYMENT_METHOD_VALUES:
    PaymentMethod.objects.get_or_create(name=name)
print(f"Seeded {len(PAYMENT_METHOD_VALUES)} payment method values.")


# --- Race/Ethnicity ---
RACE_ETHNICITY_VALUES = [
    "Black",
    "Hispanic and Latino",
    "Asian",
    "South Asian",
    "Native American",
    "Mixed Race Family",
    "Caribbean",
    "Middle Eastern",
    "Pacific Islander",
]
for name in RACE_ETHNICITY_VALUES:
    RaceEthnicity.objects.get_or_create(name=name)
print(f"Seeded {len(RACE_ETHNICITY_VALUES)} race/ethnicity values.")


# --- Therapy Types ---
THERAPY_TYPE_VALUES = [
    "Acceptance and Commitment (ACT)",
    "Adlerian",
    "AEDP",
    "Applied Behavioral Analysis (ABA)",
    "Art Therapy",
    "Attachment-based",
    "Biofeedback",
    "Brainspotting",
    "Christian Counseling",
    "Clinical Supervision and Licensed Supervisors",
    "Coaching",
    "Cognitive Behavioral (CBT)",
    "Cognitive Processing (CPT)",
    "Compassion Focused",
    "Culturally Sensitive",
    "Dance Movement Therapy",
    "Dialectical Behavior (DBT)",
    "Eclectic",
    "EMDR",
    "Emotionally Focused",
    "Energy Psychology",
    "Existential",
    "Experiential Therapy",
    "Exposure Response Prevention (ERP)",
    "Expressive Arts",
    "Family / Marital",
    "Family Systems",
    "Feminist",
    "Forensic Psychology",
    "Gestalt",
    "Gottman Method",
    "Humanistic",
    "Hypnotherapy",
    "Imago",
    "Integrative",
    "Internal Family Systems (IFS)",
    "Interpersonal",
    "Intervention",
    "Jungian",
    "Ketamine-Assisted",
    "Mindfulness-Based (MBCT)",
    "Motivational Interviewing",
    "Multicultural",
    "Music Therapy",
    "Narrative",
    "Neuro-Linguistic (NLP)",
    "Neurofeedback",
    "Parent-Child Interaction (PCIT)",
    "Person-Centered",
    "Play Therapy",
    "Positive Psychology",
    "Prolonged Exposure Therapy",
    "Psychoanalytic",
    "Psychobiological Approach Couple Therapy",
    "Psychodynamic",
    "Psychological Testing and Evaluation",
    "Rational Emotive Behavior (REBT)",
    "Reality Therapy",
    "Relational",
    "Sandplay",
    "Schema Therapy",
    "Solution Focused Brief (SFBT)",
    "Somatic",
    "Strength-Based",
    "Structural Family Therapy",
    "Transpersonal",
    "Trauma Focused",
]
for name in THERAPY_TYPE_VALUES:
    TherapyType.objects.get_or_create(name=name)
print(f"Seeded {len(THERAPY_TYPE_VALUES)} therapy type values.")


# --- Titles ---
TITLE_VALUES = [
    "Dr.",
    "Mr.",
    "Mrs.",
    "Miss.",
    "Ms.",
    "Mx.",
    "Prof.",
    "Rev.",
    "Rev. Dr.",
    "Rabbi",
    "Sister",
]
for name in TITLE_VALUES:
    Title.objects.get_or_create(name=name)
print(f"Seeded {len(TITLE_VALUES)} title values.")


from users.models_profile import SpecialtyLookup, OtherIdentity

# --- Specialty Lookup ---
SPECIALTY_LOOKUP_VALUES = [
    "Addiction",
    "ADHD",
    "Adoption",
    "Alcohol Use",
    "Anger Management",
    "Antisocial Personality",
    "Anxiety",
    "Asperger's Syndrome",
    "Autism",
    "Behavioral Issues",
    "Bipolar Disorder",
    "Body Positivity",
    "Borderline Personality (BPD)",
    "Cancer",
    "Career Counseling",
    "Caregivers",
    "Child",
    "Chronic Illness",
    "Chronic Impulsivity",
    "Chronic Pain",
    "Chronic Relapse",
    "Codependency",
    "Coping Skills",
    "Dementia",
    "Depression",
    "Developmental Disorders",
    "Dissociative Disorders (DID)",
    "Divorce",
    "Domestic Abuse ",
    "Domestic Violence",
    "Drug Abuse",
    "Dual Diagnosis",
    "Eating Disorders",
    "Education and Learning Disabilities",
    "Emotional Disturbance",
    "Family Conflict",
    "First Responders",
    "Gambling",
    "Geriatric and Seniors",
    "Grief",
    "Hoarding",
    "Infertility",
    "Infidelity",
    "Intellectual Disability",
    "Internet Addiction",
    "Life Coaching",
    "Life Transitions",
    "Marital and Premarital",
    "Medical Detox",
    "Medication Management",
    "Men's Issues",
    "Narcissistic Personality (NPD)",
    "Obesity",
    "Obsessive-Compulsive (OCD)",
    "Open Relationships Non-Monogamy",
    "Oppositional Defiance (ODD)",
    "Parenting",
    "Peer Relationships",
    "Personality Disorders",
    "Pregnancy, Prenatal, Postpartum",
    "Psychosis",
    "Racial Identity",
    "Relationship Issues",
    "School Issues",
    "Self Esteem",
    "Self-Harming",
    "Sex Therapy",
    "Sex-Positive, Kink Allied",
    "Sexual Abuse",
    "Sexual Addiction",
    "Sleep or Insomnia",
    "Spirituality",
    "Sports Performance",
    "Stress",
    "Substance Use",
    "Suicidal Ideation",
    "Teen Violence",
    "Testing and Evaluation",
    "Transgender",
    "Trauma and PTSD",
    "Traumatic Brain Injury (TBI)",
    "Veterans",
    "Video Game Addiction",
    "Weight Loss",
    "Women's Issues",
    "Impulse Control Disorders",
    "Mood Disorders",
    "Thinking Disorders",
    "Bisexual",
    "Lesbian",
    "LGBTQ+",
    "Other",
]
for name in SPECIALTY_LOOKUP_VALUES:
    SpecialtyLookup.objects.get_or_create(name=name)
print(f"Seeded {len(SPECIALTY_LOOKUP_VALUES)} specialty lookup values.")

# --- Other Identity ---
OTHER_IDENTITY_VALUES = [
    "Blind",
    "Deaf",
    "Disabled",
    "Immuno-disorders",
    "Single Parent",
    "Veteran",
]
for name in OTHER_IDENTITY_VALUES:
    OtherIdentity.objects.get_or_create(name=name)
print(f"Seeded {len(OTHER_IDENTITY_VALUES)} other identity values.")
