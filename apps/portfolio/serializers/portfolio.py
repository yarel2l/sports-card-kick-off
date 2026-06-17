from rest_framework import serializers

from apps.catalog.models import Card, GradingCompany
from apps.catalog.serializers import CardSerializer

from ..models import PortfolioHolding, PriceAlert, WatchlistItem


class WatchlistItemSerializer(serializers.ModelSerializer):
    card = serializers.PrimaryKeyRelatedField(queryset=Card.objects.all())
    card_detail = CardSerializer(source='card', read_only=True)

    class Meta:
        model = WatchlistItem
        fields = ['id', 'card', 'card_detail', 'created_at']
        read_only_fields = ['id', 'created_at']


class PortfolioHoldingSerializer(serializers.ModelSerializer):
    card = serializers.PrimaryKeyRelatedField(queryset=Card.objects.all())
    card_detail = CardSerializer(source='card', read_only=True)
    grading_company = serializers.PrimaryKeyRelatedField(
        queryset=GradingCompany.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = PortfolioHolding
        fields = [
            'id', 'card', 'card_detail', 'grading_company', 'grade', 'quantity',
            'cost_basis', 'currency', 'acquired_at', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError('Quantity must be at least 1.')
        return value


class PriceAlertSerializer(serializers.ModelSerializer):
    card = serializers.PrimaryKeyRelatedField(queryset=Card.objects.all())
    card_detail = CardSerializer(source='card', read_only=True)

    class Meta:
        model = PriceAlert
        fields = [
            'id', 'card', 'card_detail', 'grade', 'direction', 'threshold_price',
            'is_active', 'triggered_at', 'triggered_price', 'created_at',
        ]
        read_only_fields = ['id', 'triggered_at', 'triggered_price', 'created_at']

    def validate_threshold_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Threshold price must be positive.')
        return value
