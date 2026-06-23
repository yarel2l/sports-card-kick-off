from rest_framework import serializers

from ..models import Card, CardSet, GradingCompany, Player, PriceObservation


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id', 'name', 'slug', 'sport', 'aliases']
        read_only_fields = ['id', 'slug']


class CardSetSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = CardSet
        fields = ['id', 'year', 'brand', 'name', 'sport', 'slug', 'display_name']
        read_only_fields = ['id', 'slug', 'display_name']


class GradingCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingCompany
        fields = ['id', 'code', 'name']
        read_only_fields = ['id']


class CardSerializer(serializers.ModelSerializer):
    player = PlayerSerializer(read_only=True)
    card_set = CardSetSerializer(read_only=True)

    class Meta:
        model = Card
        fields = [
            'id', 'canonical_key', 'card_set', 'player', 'card_number',
            'parallel', 'is_rookie', 'is_autograph', 'is_memorabilia',
            'serial_limit', 'attributes',
        ]
        read_only_fields = fields


class PriceObservationSerializer(serializers.ModelSerializer):
    grading_company = serializers.CharField(source='grading_company.code', read_only=True, default=None)

    class Meta:
        model = PriceObservation
        fields = [
            'id', 'card', 'source', 'kind', 'grading_company', 'grade',
            'price', 'currency', 'url', 'match_confidence', 'observed_at',
        ]
        read_only_fields = fields


class FeedObservationSerializer(serializers.ModelSerializer):
    """A price observation with its full card, for the recent-sales feed."""

    grading_company = serializers.CharField(
        source="grading_company.code", read_only=True, default=None
    )
    card = CardSerializer(read_only=True)

    class Meta:
        model = PriceObservation
        fields = [
            "id", "card", "source", "kind", "grading_company", "grade",
            "price", "currency", "url", "observed_at",
        ]
        read_only_fields = fields
