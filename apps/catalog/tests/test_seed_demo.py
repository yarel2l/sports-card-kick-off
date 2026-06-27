from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.catalog.models import Card, CardSet, PriceObservation
from apps.portfolio.models import PortfolioHolding, PriceAlert, WatchlistItem

User = get_user_model()


class SeedDemoCommandTests(TestCase):
    def test_seed_creates_navigable_dataset(self):
        call_command("seed_demo")

        self.assertGreaterEqual(Card.objects.count(), 6)
        self.assertGreater(PriceObservation.objects.count(), 100)
        # Mix of kinds so the feed and price stats are meaningful.
        kinds = set(PriceObservation.objects.values_list("kind", flat=True))
        self.assertIn(PriceObservation.Kind.SOLD, kinds)
        self.assertIn(PriceObservation.Kind.LISTING, kinds)

        # Demo user with a populated portfolio.
        demo = User.objects.get(email="demo@sportscardkickoff.com")
        self.assertTrue(demo.check_password("demo12345"))
        self.assertTrue(PortfolioHolding.objects.filter(user=demo).exists())
        self.assertTrue(WatchlistItem.objects.filter(user=demo).exists())
        self.assertTrue(PriceAlert.objects.filter(user=demo).exists())

    def test_seed_is_idempotent(self):
        call_command("seed_demo")
        cards = Card.objects.count()
        obs = PriceObservation.objects.count()
        call_command("seed_demo")
        # Re-running updates in place rather than duplicating.
        self.assertEqual(Card.objects.count(), cards)
        self.assertEqual(PriceObservation.objects.count(), obs)

    def test_flush_resets(self):
        call_command("seed_demo")
        call_command("seed_demo", flush=True)
        self.assertGreaterEqual(Card.objects.count(), 6)

    def test_display_name_dedupes_brand(self):
        call_command("seed_demo")
        fleer = CardSet.objects.filter(brand="Fleer").first()
        if fleer:
            self.assertNotIn("Fleer Fleer", fleer.display_name)
        bowman = CardSet.objects.filter(name__icontains="Bowman Chrome").first()
        if bowman:
            self.assertNotIn("Bowman Bowman", bowman.display_name)
