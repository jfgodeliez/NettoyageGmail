"""Tests unitaires du module analyzer (sans appel API)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.gmail_client import EmailMeta, _extract_domain
from app.analyzer import EmailGroup, _classify, analyze, merge_small_groups


def make_email(
    sender: str = "test@example.com",
    subject: str = "Hello",
    labels: list | None = None,
    is_newsletter: bool = False,
    size_estimate: int = 1024,
) -> EmailMeta:
    domain = sender.split("@")[-1] if "@" in sender else sender
    return EmailMeta(
        msg_id="id_" + sender[:8],
        thread_id="t_" + sender[:8],
        sender=sender,
        sender_domain=domain,
        subject=subject,
        date="Mon, 01 Jan 2024 00:00:00 +0000",
        labels=labels or ["INBOX"],
        is_newsletter=is_newsletter,
        size_estimate=size_estimate,
    )


class TestExtractDomain:
    def test_plain_email(self):
        assert _extract_domain("user@amazon.fr") == "amazon.fr"

    def test_display_name(self):
        assert _extract_domain("Amazon <order@amazon.fr>") == "amazon.fr"

    def test_no_at(self):
        assert _extract_domain("unknown-sender") == "unknown-sender"


class TestClassify:
    def test_known_domain(self):
        assert _classify(make_email("order@amazon.fr")) == "E-commerce"

    def test_newsletter_detection(self):
        e = make_email("news@shop.io", is_newsletter=True)
        assert "Newsletter" in _classify(e)

    def test_gmail_category_label(self):
        e = make_email("p@x.com", labels=["CATEGORY_PROMOTIONS"])
        assert _classify(e) == "Promotions"

    def test_fallback_domain(self):
        assert _classify(make_email("c@mystartup.io")) == "Domaine – mystartup.io"

    def test_linkedin(self):
        assert _classify(make_email("n@linkedin.com")) == "Réseaux sociaux"


class TestAnalyze:
    def test_groups_by_theme(self):
        emails = [make_email("a@amazon.fr"), make_email("b@amazon.fr"), make_email("x@paypal.com")]
        groups = analyze(emails)
        themes = {g.theme for g in groups}
        assert "E-commerce" in themes
        assert "Finance" in themes

    def test_sorted_by_count_desc(self):
        emails = [make_email("a@amazon.fr")] * 3 + [make_email("x@paypal.com")]
        groups = analyze(emails)
        counts = [g.count for g in groups]
        assert counts == sorted(counts, reverse=True)

    def test_empty_input(self):
        assert analyze([]) == []


class TestMergeSmallGroups:
    def test_small_groups_merged(self):
        big = EmailGroup(1, "Big Group", "autre", [make_email() for _ in range(10)])
        small = EmailGroup(2, "Tiny", "autre", [make_email()])
        result = merge_small_groups([big, small], min_count=5)
        themes = {g.theme for g in result}
        assert "Big Group" in themes
        assert "Divers (petits groupes)" in themes
        assert "Tiny" not in themes

    def test_no_small_groups(self):
        big = EmailGroup(1, "Big", "autre", [make_email() for _ in range(10)])
        assert len(merge_small_groups([big], min_count=5)) == 1


class TestEmailGroupProperties:
    def test_count(self):
        g = EmailGroup(1, "T", "autre", [make_email() for _ in range(5)])
        assert g.count == 5

    def test_size_mb(self):
        g = EmailGroup(1, "T", "autre", [make_email(size_estimate=1024 * 1024) for _ in range(2)])
        assert abs(g.size_mb - 2.0) < 0.01

    def test_ids(self):
        g = EmailGroup(1, "T", "autre", [make_email("a@x.com"), make_email("b@x.com")])
        assert len(g.ids) == 2
