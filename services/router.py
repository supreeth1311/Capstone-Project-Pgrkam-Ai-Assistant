# services/router.py
def deep_link_for_intent(intent: str) -> str:
    base = "https://www.pgrkam.com"
    mapping = {
        "GovernmentJobs": f"{base}/#govtJobs",
        "PrivateJobs":    f"{base}/#privateJobs",
        "SkillDevelopment": f"{base}/#skillDevelopment",
        "ForeignCounseling": f"{base}/#foreignCounseling",
        "JobMela": f"{base}/#jobMela",
        "RegistrationHelp": f"{base}/#register",
        "PortalNavigation": base,
        "GeneralFAQ": f"{base}/#faq"
    }
    return mapping.get(intent, base)
