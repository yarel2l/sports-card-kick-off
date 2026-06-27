"""
Seed the catalog with a realistic demo dataset so the whole app is navigable
without live scraping: canonical cards, price observations across grades/sources
spread over time (so history + trends populate), plus a demo user with a
portfolio, watchlist and a price alert.

    python manage.py seed_demo            # create/refresh demo data
    python manage.py seed_demo --flush    # wipe catalog + demo user first

This exercises the real resolver/ingest path, not hand-built rows.
"""

from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import (
    Card,
    CardSet,
    GradingCompany,
    Player,
    PriceObservation,
)
from apps.catalog.services import constants
from apps.catalog.services.resolver import CardResolver

User = get_user_model()

# Marquee cards with a per-grade baseline market value (USD).
CARDS = [
    {
        "title": "2018-19 Panini Prizm Luka Doncic #280 Rookie",
        "sport": constants.SPORT_BASKETBALL,
        "grades": {"PSA 10": 1500, "PSA 9": 600, "BGS 9.5": 1100, "RAW": 250},
    },
    {
        "title": "2018-19 Panini Prizm Luka Doncic #280 Silver Rookie",
        "sport": constants.SPORT_BASKETBALL,
        "grades": {"PSA 10": 4200, "PSA 9": 1800, "BGS 9.5": 3200},
    },
    {
        "title": "2003 Topps Chrome LeBron James #111 Refractor Rookie",
        "sport": constants.SPORT_BASKETBALL,
        "grades": {"PSA 10": 9000, "PSA 9": 3500, "BGS 9.5": 6000},
    },
    {
        "title": "1986 Fleer Michael Jordan #57 Rookie",
        "sport": constants.SPORT_BASKETBALL,
        "grades": {"PSA 10": 60000, "PSA 9": 9000, "PSA 8": 3200, "RAW": 1200},
    },
    {
        "title": "2019-20 Panini Prizm Zion Williamson #248 Rookie",
        "sport": constants.SPORT_BASKETBALL,
        "grades": {"PSA 10": 700, "PSA 9": 250, "BGS 9.5": 500},
    },
    {
        "title": "2020 Donruss Optic Justin Jefferson #168 Rated Rookie",
        "sport": constants.SPORT_FOOTBALL,
        "grades": {"PSA 10": 220, "PSA 9": 90, "RAW": 40},
    },
    {
        "title": "2011 Topps Update Mike Trout #US175 Rookie",
        "sport": constants.SPORT_BASEBALL,
        "grades": {"PSA 10": 1900, "PSA 9": 500, "BGS 9.5": 1300},
    },
    {
        "title": "2021 Bowman Chrome Julio Rodriguez #BCP50 Auto Rookie",
        "sport": constants.SPORT_BASEBALL,
        "grades": {"PSA 10": 800, "BGS 9.5": 650, "RAW": 300},
    },
]

# (source, kind) for each observation flavour.
SOLD_SOURCES = [("130point", PriceObservation.Kind.SOLD), ("goldin", PriceObservation.Kind.SOLD)]
LISTING_SOURCES = [("ebay", PriceObservation.Kind.LISTING), ("comc", PriceObservation.Kind.LISTING)]

GRADE_COMPANY_NAMES = {
    "PSA": "Professional Sports Authenticator",
    "BGS": "Beckett Grading Services",
}


class Command(BaseCommand):
    help = "Seed the catalog with a realistic demo dataset."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Wipe catalog + demo user first")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(42)  # deterministic

        if options["flush"]:
            PriceObservation.objects.all().delete()
            Card.objects.all().delete()
            CardSet.objects.all().delete()
            Player.objects.all().delete()
            User.objects.filter(email="demo@sportscardkickoff.com").delete()
            self.stdout.write(self.style.WARNING("Flushed catalog + demo user."))

        companies = {
            code: GradingCompany.objects.get_or_create(
                code=code, defaults={"name": name}
            )[0]
            for code, name in GRADE_COMPANY_NAMES.items()
        }

        now = timezone.now()
        cards_created = 0
        obs_created = 0

        for spec in CARDS:
            resolver = CardResolver(sport=spec["sport"])
            result = resolver.resolve(spec["title"])
            card = result.card
            if card is None:
                self.stdout.write(self.style.ERROR(f"Could not resolve: {spec['title']}"))
                continue
            cards_created += 1

            for grade_label, base in spec["grades"].items():
                company = None
                grade_value = ""
                if grade_label != "RAW":
                    code, grade_value = grade_label.split(" ")
                    company = companies.get(code) or GradingCompany.objects.get_or_create(
                        code=code, defaults={"name": code}
                    )[0]

                # Historical SOLD comps over ~90 days with a mild upward drift.
                points = 10
                for i in range(points):
                    days_ago = int(90 * (points - 1 - i) / (points - 1))
                    drift = 1 + 0.12 * (i / (points - 1))  # up to +12% over the window
                    noise = rng.uniform(0.92, 1.08)
                    price = Decimal(str(round(base * drift * noise, 2)))
                    source, kind = rng.choice(SOLD_SOURCES)
                    ext = f"seed-{card.canonical_key}-{grade_label}-h{i}"
                    _, created = PriceObservation.objects.update_or_create(
                        source=source,
                        external_id=ext,
                        defaults={
                            "card": card,
                            "kind": kind,
                            "grading_company": company,
                            "grade": grade_value,
                            "price": price,
                            "currency": "USD",
                            "raw_title": spec["title"],
                            "match_confidence": result.confidence,
                            "observed_at": now - timedelta(days=days_ago),
                        },
                    )
                    obs_created += int(created)

                # A couple of current active listings (asking prices, a bit above).
                for source, kind in LISTING_SOURCES:
                    price = Decimal(str(round(base * rng.uniform(1.05, 1.25), 2)))
                    ext = f"seed-{card.canonical_key}-{grade_label}-{source}-live"
                    _, created = PriceObservation.objects.update_or_create(
                        source=source,
                        external_id=ext,
                        defaults={
                            "card": card,
                            "kind": kind,
                            "grading_company": company,
                            "grade": grade_value,
                            "price": price,
                            "currency": "USD",
                            "raw_title": spec["title"],
                            "match_confidence": result.confidence,
                            "observed_at": now - timedelta(hours=rng.randint(1, 48)),
                        },
                    )
                    obs_created += int(created)

        self._seed_demo_user()

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {cards_created} cards, {PriceObservation.objects.count()} "
            f"observations ({obs_created} new)."
        ))
        self.stdout.write(self.style.SUCCESS(
            "Demo login → email: demo@sportscardkickoff.com  password: demo12345"
        ))

    def _seed_demo_user(self):
        from apps.portfolio.models import PortfolioHolding, PriceAlert, WatchlistItem

        user, _ = User.objects.get_or_create(
            email="demo@sportscardkickoff.com",
            defaults={"username": "demo"},
        )
        user.set_password("demo12345")
        user.save()

        cards = list(Card.objects.select_related("card_set", "player")[:5])
        if not cards:
            return

        psa = GradingCompany.objects.filter(code="PSA").first()

        # Watchlist
        for card in cards[:3]:
            WatchlistItem.objects.get_or_create(user=user, card=card)

        # Holdings (cost basis below market -> positive P&L on the demo)
        PortfolioHolding.objects.get_or_create(
            user=user, card=cards[0], grade="10", grading_company=psa,
            defaults={"quantity": 1, "cost_basis": Decimal("900.00")},
        )
        if len(cards) > 1:
            PortfolioHolding.objects.get_or_create(
                user=user, card=cards[1], grade="9", grading_company=psa,
                defaults={"quantity": 2, "cost_basis": Decimal("150.00")},
            )

        # An active price alert (not yet triggered)
        PriceAlert.objects.get_or_create(
            user=user, card=cards[0], direction=PriceAlert.Direction.BELOW,
            threshold_price=Decimal("1000.00"), defaults={"grade": "10"},
        )
