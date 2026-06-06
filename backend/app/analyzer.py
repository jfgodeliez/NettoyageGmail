"""Regroupement des emails par thèmes."""

from collections import defaultdict
from dataclasses import dataclass, field

from .gmail_client import EmailMeta

GMAIL_LABEL_NAMES = {
    "CATEGORY_PERSONAL": "Personnels",
    "CATEGORY_SOCIAL": "Réseaux sociaux",
    "CATEGORY_PROMOTIONS": "Promotions",
    "CATEGORY_UPDATES": "Notifications",
    "CATEGORY_FORUMS": "Forums",
}

DOMAIN_THEMES: dict[str, str] = {
    "amazon.fr": "E-commerce", "amazon.com": "E-commerce",
    "cdiscount.com": "E-commerce", "fnac.com": "E-commerce",
    "darty.com": "E-commerce", "leboncoin.fr": "E-commerce",
    "vinted.fr": "E-commerce", "ebay.fr": "E-commerce",
    "aliexpress.com": "E-commerce",
    "paypal.com": "Finance", "paypal.fr": "Finance",
    "boursorama.com": "Finance", "labanquepostale.fr": "Finance",
    "credit-agricole.fr": "Finance", "bnpparibas.fr": "Finance",
    "sg.fr": "Finance",
    "linkedin.com": "Réseaux sociaux", "facebook.com": "Réseaux sociaux",
    "twitter.com": "Réseaux sociaux", "instagram.com": "Réseaux sociaux",
    "youtube.com": "Réseaux sociaux",
    "sncf.fr": "Voyage / Transport", "oui.sncf": "Voyage / Transport",
    "airfrance.fr": "Voyage / Transport", "booking.com": "Voyage / Transport",
    "airbnb.com": "Voyage / Transport", "blablacar.fr": "Voyage / Transport",
    "google.com": "Google", "accounts.google.com": "Google",
    "impots.gouv.fr": "Administratif", "ameli.fr": "Administratif",
    "pole-emploi.fr": "Administratif", "service-public.fr": "Administratif",
    "caf.fr": "Administratif",
}


@dataclass
class EmailGroup:
    group_id: int
    theme: str
    category: str
    emails: list[EmailMeta] = field(default_factory=list)
    sample_senders: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.emails)

    @property
    def ids(self) -> list[str]:
        return [e.msg_id for e in self.emails]

    @property
    def size_mb(self) -> float:
        return sum(e.size_estimate for e in self.emails) / (1024 * 1024)


def analyze(emails: list[EmailMeta]) -> list[EmailGroup]:
    buckets: dict[str, list[EmailMeta]] = defaultdict(list)
    for email in emails:
        buckets[_classify(email)].append(email)

    result = []
    for gid, (theme, mails) in enumerate(
        sorted(buckets.items(), key=lambda x: -len(x[1])), start=1
    ):
        result.append(EmailGroup(
            group_id=gid,
            theme=theme,
            category=_infer_category(theme, mails),
            emails=mails,
            sample_senders=_top_senders(mails),
        ))
    return result


def merge_small_groups(groups: list[EmailGroup], min_count: int = 5) -> list[EmailGroup]:
    main = [g for g in groups if g.count >= min_count]
    small = [g for g in groups if g.count < min_count]
    if not small:
        return main
    divers = []
    for g in small:
        divers.extend(g.emails)
    next_id = max((g.group_id for g in main), default=0) + 1
    main.append(EmailGroup(
        group_id=next_id,
        theme="Divers (petits groupes)",
        category="autre",
        emails=divers,
        sample_senders=_top_senders(divers),
    ))
    return main


def _classify(email: EmailMeta) -> str:
    domain_theme = DOMAIN_THEMES.get(email.sender_domain)
    if domain_theme:
        return domain_theme
    if email.is_newsletter:
        return f"Newsletter – {email.sender_domain}"
    for label in email.labels:
        if label.startswith("CATEGORY_"):
            return GMAIL_LABEL_NAMES.get(label, label)
    return f"Domaine – {email.sender_domain}"


def _infer_category(theme: str, mails: list[EmailMeta]) -> str:
    if any(m.is_newsletter for m in mails):
        return "newsletter"
    if theme in ("Réseaux sociaux", "Google"):
        return "social"
    if theme in ("E-commerce", "Finance"):
        return "commercial"
    if theme == "Administratif":
        return "admin"
    if "Newsletter" in theme or "Promotions" in theme:
        return "newsletter"
    if "Réseaux sociaux" in theme or "Forums" in theme:
        return "social"
    return "autre"


def _top_senders(mails: list[EmailMeta], n: int = 3) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for m in mails:
        counts[m.sender_domain] += 1
    return [d for d, _ in sorted(counts.items(), key=lambda x: -x[1])[:n]]
