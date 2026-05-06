"""Tests for the TLD-preserving company-identity resolver.

Run from the market-ontology root with stdlib unittest:

    python3 -m unittest tests.test_identity -v

The resolver is the *single* place email/domain become a route slug, a
canonical domain string, and a Graphiti group_id. All three forms agree:
`person@ibm.com` -> ('ibm.com', 'ibm_com', 'spice_ibm_com'). Two users
from the same domain land in the same group_id; users at different TLDs
of the same brand (`ibm.com` vs `ibm.ai`) land in different groups.
"""
import unittest



class TestEmailToSlug(unittest.TestCase):
    def test_email_round_trip(self):
        from poc_v1.ontology.identity import email_to_slug

        ident = email_to_slug("avi@ibm.com")
        self.assertEqual(ident.canonical_domain, "ibm.com")
        self.assertEqual(ident.route_slug, "ibm_com")
        self.assertEqual(ident.group_id, "spice_ibm_com")

    def test_email_lowercases_input(self):
        from poc_v1.ontology.identity import email_to_slug

        # Pick a domain without PSL ambiguity: `openai.com` is just a
        # standard registrable domain, no subdomain to collapse.
        ident = email_to_slug("Founder@OPENAI.COM")
        self.assertEqual(ident.canonical_domain, "openai.com")
        self.assertEqual(ident.route_slug, "openai_com")

    def test_email_strips_subaddress(self):
        """`founder+demo@ibm.com` resolves to `ibm.com` — the +tag is the
        local part, not the domain."""
        from poc_v1.ontology.identity import email_to_slug

        ident = email_to_slug("founder+demo@ibm.com")
        self.assertEqual(ident.canonical_domain, "ibm.com")

    def test_hyphenated_domain(self):
        from poc_v1.ontology.identity import email_to_slug

        ident = email_to_slug("ceo@acme-demo.com")
        self.assertEqual(ident.canonical_domain, "acme-demo.com")
        self.assertEqual(ident.route_slug, "acme_demo_com")
        self.assertEqual(ident.group_id, "spice_acme_demo_com")

    def test_email_without_at_raises(self):
        from poc_v1.ontology.identity import email_to_slug

        with self.assertRaises(ValueError):
            email_to_slug("no-at-sign")

    def test_empty_email_raises(self):
        from poc_v1.ontology.identity import email_to_slug

        with self.assertRaises(ValueError):
            email_to_slug("")

    def test_local_part_only_raises(self):
        from poc_v1.ontology.identity import email_to_slug

        with self.assertRaises(ValueError):
            email_to_slug("alice@")


class TestDomainToSlug(unittest.TestCase):
    """`domain_to_slug` accepts a bare domain (`ibm.com`) — the slug-
    generation path used when the input to `./run.sh` is just a domain."""

    def test_basic_domain(self):
        from poc_v1.ontology.identity import domain_to_slug

        ident = domain_to_slug("apple.com")
        self.assertEqual(ident.canonical_domain, "apple.com")
        self.assertEqual(ident.route_slug, "apple_com")

    def test_domain_drops_protocol(self):
        from poc_v1.ontology.identity import domain_to_slug

        ident = domain_to_slug("https://www.notion.so/")
        self.assertEqual(ident.canonical_domain, "notion.so")
        self.assertEqual(ident.route_slug, "notion_so")

    def test_domain_drops_www(self):
        from poc_v1.ontology.identity import domain_to_slug

        ident = domain_to_slug("www.openai.com")
        self.assertEqual(ident.canonical_domain, "openai.com")

    def test_two_letter_tld(self):
        from poc_v1.ontology.identity import domain_to_slug

        ident = domain_to_slug("subconscious.ai")
        self.assertEqual(ident.canonical_domain, "subconscious.ai")
        self.assertEqual(ident.route_slug, "subconscious_ai")

    def test_distinct_tlds_distinct_groups(self):
        """Plan invariant: ibm.com and ibm.ai are different companies."""
        from poc_v1.ontology.identity import domain_to_slug

        com = domain_to_slug("ibm.com")
        ai = domain_to_slug("ibm.ai")
        self.assertNotEqual(com.group_id, ai.group_id)


class TestSlugToIdentity(unittest.TestCase):
    """The resolver round-trips its own route-slug output. `./run.sh ibm_com`
    after the rename must produce the same identity as `./run.sh ibm.com`."""

    def test_route_slug_idempotent(self):
        from poc_v1.ontology.identity import to_identity

        first = to_identity("ibm.com")
        second = to_identity(first.route_slug)
        self.assertEqual(first, second)

    def test_legacy_tld_stripped_input_keeps_old_behavior(self):
        """`./run.sh notion` (legacy form, no TLD) should NOT silently
        guess `.com`. We require explicit TLD now — fall back to a plain
        slug with no TLD suffix instead of pretending."""
        from poc_v1.ontology.identity import to_identity

        ident = to_identity("notion")
        # The route_slug is just the legacy slug; canonical_domain is the
        # same string (no TLD to surface). Group_id mirrors.
        self.assertEqual(ident.route_slug, "notion")
        self.assertEqual(ident.canonical_domain, "notion")
        self.assertEqual(ident.group_id, "spice_notion")


class TestPSLAwareNormalization(unittest.TestCase):
    """tldextract-backed behavior: subdomain collapse, multi-part TLD,
    URL parsing, IDN punycode. These are the gaps the original regex
    resolver had that this round closes."""

    def test_subdomain_collapses_to_brand(self):
        """`mail.acme.io` should land in the same group as `acme.io` —
        every email at acme.io is one company graph."""
        from poc_v1.ontology.identity import to_identity

        bare = to_identity("acme.io")
        sub = to_identity("mail.acme.io")
        self.assertEqual(bare, sub)

    def test_deep_subdomain_collapses(self):
        from poc_v1.ontology.identity import to_identity

        bare = to_identity("ibm.com")
        deep = to_identity("careers.api.v2.ibm.com")
        self.assertEqual(bare, deep)

    def test_multi_part_tld_preserved(self):
        from poc_v1.ontology.identity import to_identity

        ident = to_identity("lloyds.co.uk")
        self.assertEqual(ident.canonical_domain, "lloyds.co.uk")
        self.assertEqual(ident.route_slug, "lloyds_co_uk")
        self.assertEqual(ident.group_id, "spice_lloyds_co_uk")

    def test_multi_part_tld_with_subdomain(self):
        from poc_v1.ontology.identity import to_identity

        bare = to_identity("tabcorp.com.au")
        sub = to_identity("careers.tabcorp.com.au")
        self.assertEqual(bare, sub)

    def test_url_with_path_strips_path(self):
        from poc_v1.ontology.identity import to_identity

        ident = to_identity("https://www.openai.com/about?x=1#frag")
        self.assertEqual(ident.canonical_domain, "openai.com")
        self.assertEqual(ident.route_slug, "openai_com")

    def test_url_without_protocol_strips_path(self):
        from poc_v1.ontology.identity import to_identity

        ident = to_identity("acme.io/about")
        self.assertEqual(ident.canonical_domain, "acme.io")

    def test_idn_punycode_encodes(self):
        """Unicode domains punycode-encode at the boundary so FalkorDB
        and filesystem paths only see ASCII. `café.fr` -> `xn--caf-dma.fr`."""
        from poc_v1.ontology.identity import to_identity

        ident = to_identity("café.fr")
        self.assertTrue(ident.route_slug.startswith("xn__"))
        self.assertNotIn("é", ident.route_slug)
        self.assertNotIn("é", ident.group_id)

    def test_email_at_subdomain_collapses(self):
        """Plan invariant: `support@careers.ibm.com` and `boss@ibm.com`
        land in the same company graph."""
        from poc_v1.ontology.identity import email_to_slug

        a = email_to_slug("boss@ibm.com")
        b = email_to_slug("support@careers.ibm.com")
        self.assertEqual(a, b)


class TestRejectsBadInput(unittest.TestCase):
    def test_path_traversal_rejected(self):
        from poc_v1.ontology.identity import to_identity

        for bad in ["../etc/passwd", "ibm/../passwd", "/abs/path"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                to_identity(bad)

    def test_shell_meta_rejected(self):
        from poc_v1.ontology.identity import to_identity

        for bad in ["ibm;rm", "ibm$x", "ibm`y`", "ibm|cat", "ibm&x"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                to_identity(bad)

    def test_whitespace_rejected(self):
        from poc_v1.ontology.identity import to_identity

        with self.assertRaises(ValueError):
            to_identity("   ")

    def test_too_long_rejected(self):
        from poc_v1.ontology.identity import to_identity

        with self.assertRaises(ValueError):
            to_identity("a" * 200 + ".com")


class TestNormalizeSlugBoundary(unittest.TestCase):
    """`normalize_slug` is the FastAPI route-boundary validator. Accepts
    pre-cleaned slugs/domains; rejects unsafe input. Subset of `to_identity`
    (no PSL/IDN handling) — useful when the producer has already
    canonicalized the input."""

    def test_clean_slug_passes(self):
        from poc_v1.ontology.identity import normalize_slug

        ident = normalize_slug("ibm_com")
        self.assertEqual(ident.route_slug, "ibm_com")
        self.assertEqual(ident.group_id, "spice_ibm_com")

    def test_canonical_domain_passes(self):
        from poc_v1.ontology.identity import normalize_slug

        ident = normalize_slug("ibm.com")
        self.assertEqual(ident.route_slug, "ibm_com")

    def test_empty_rejected(self):
        from poc_v1.ontology.identity import normalize_slug

        for bad in [None, "", "   "]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                normalize_slug(bad)

    def test_path_traversal_rejected(self):
        from poc_v1.ontology.identity import normalize_slug

        for bad in ["..", "../etc", "ibm/../passwd"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                normalize_slug(bad)

    def test_shell_meta_rejected(self):
        from poc_v1.ontology.identity import normalize_slug

        for bad in ["ibm;rm", "ibm$x", "ibm`y`", "ibm|cat"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                normalize_slug(bad)

    def test_subdomain_NOT_collapsed(self):
        """Boundary validator does not run PSL — `mail_acme_com` passes
        through as a literal slug, distinct from `acme_com`. Producers
        should call `to_identity` upstream if they want subdomains
        collapsed; this validator is for the hot HTTP path."""
        from poc_v1.ontology.identity import normalize_slug

        sub = normalize_slug("mail_acme_com")
        bare = normalize_slug("acme_com")
        self.assertNotEqual(sub.route_slug, bare.route_slug)


if __name__ == "__main__":
    unittest.main(verbosity=2)
