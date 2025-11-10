# services/intent.py
import re
from langdetect import detect

INTENTS = [
    "PrivateJobs", "GovernmentJobs", "SkillDevelopment",
    "ForeignCounseling", "JobMela", "RegistrationHelp",
    "EligibilityQuery", "DocumentChecklist", "PortalNavigation", "GeneralFAQ"
]

KEYWORDS = {
    "GovernmentJobs": ["gov", "government", "sarkari", "punjab govt", "ssc", "psssb"],
    "PrivateJobs": ["private", "company", "hiring", "walk-in", "internship"],
    "SkillDevelopment": ["skill", "training", "course", "upskill", "pmkvy"],
    "ForeignCounseling": ["foreign", "abroad", "ielts", "ielts", "study visa", "counsel"],
    "JobMela": ["mela", "job fair", "campus drive"],
    "RegistrationHelp": ["register", "signup", "login", "password", "otp"],
    "EligibilityQuery": ["eligible", "eligibility", "criteria", "age limit", "qualification"],
    "DocumentChecklist": ["document", "docs", "certificate", "upload", "resume"],
    "PortalNavigation": ["where", "how to find", "navigate", "page", "link"],
}

def detect_lang(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "en"

def rule_intent(text: str) -> str:
    t = text.lower()
    for intent, words in KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(w)}\b", t) for w in words):
            return intent
    # fallback heuristics
    if "job" in t or "vacancy" in t:
        return "PrivateJobs"
    return "GeneralFAQ"
