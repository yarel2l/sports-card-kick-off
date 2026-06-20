from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Card, CardSet, GradingCompany, PriceObservation
from apps.catalog.services import constants
from apps.catalog.services.resolver import CardResolver


class DiscoveryAPITests(APITestCase):
    def setUp(self):
        resolver = CardResolver(sport=constants.SPORT_BASKETBALL)
        self.luka = resolver.resolve("2018 Panini Prizm Luka Doncic #280 Silver").card
        self.zion = resolver.resolve("2019 Panini Prizm Zion Williamson #248").card
        psa = GradingCompany.objects.create(code="PSA", name="PSA")

        # Luka gets more observations -> should trend higher.
        for price in ("200", "300", "400"):
            PriceObservation.objects.create(
                card=self.luka, source="ebay", price=Decimal(price), grade="10",
                grading_company=psa,
            )
        PriceObservation.objects.create(
            card=self.zion, source="comc", price=Decimal("150"), grade="9",
        )

    def test_endpoints_public(self):
        for name in ("catalog:trending", "catalog:feed"):
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_trending_orders_by_recent_activity(self):
        resp = self.client.get(reverse("catalog:trending"))
        results = resp.data["results"]
        self.assertGreaterEqual(len(results), 2)
        # Luka (3 comps) should come before Zion (1 comp).
        ids = [r["card"]["id"] for r in results]
        self.assertLess(ids.index(str(self.luka.id)), ids.index(str(self.zion.id)))
        self.assertEqual(results[0]["market"]["count"], 3)

    def test_trending_excludes_cards_without_recent_comps(self):
        # An old observation should not make a card trend.
        old_card = CardSet.objects.create(year=1990, brand="Fleer", name="x", sport="BASKETBALL")
        cold = Card.objects.create(card_set=old_card, canonical_key="cold-1", card_number="1")
        obs = PriceObservation.objects.create(card=cold, source="ebay", price=Decimal("5"))
        PriceObservation.objects.filter(pk=obs.pk).update(
            observed_at=timezone.now() - timedelta(days=200)
        )
        resp = self.client.get(reverse("catalog:trending"))
        ids = [r["card"]["id"] for r in resp.data["results"]]
        self.assertNotIn(str(cold.id), ids)

    def test_feed_returns_recent_first_with_card(self):
        resp = self.client.get(reverse("catalog:feed"), {"limit": 5})
        results = resp.data["results"]
        self.assertEqual(len(results), 4)
        self.assertIn("card", results[0])
        self.assertIn("kind", results[0])

    def test_autocomplete_matches_player_and_cards(self):
        resp = self.client.get(reverse("catalog:autocomplete"), {"q": "Luka"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in resp.data["players"]]
        self.assertIn("Luka Doncic", names)
        self.assertGreaterEqual(len(resp.data["cards"]), 1)

    def test_autocomplete_short_query_returns_empty(self):
        resp = self.client.get(reverse("catalog:autocomplete"), {"q": "L"})
        self.assertEqual(resp.data["players"], [])
        self.assertEqual(resp.data["cards"], [])
