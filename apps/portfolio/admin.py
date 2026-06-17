from django.contrib import admin

from .models import PortfolioHolding, PriceAlert, WatchlistItem


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'card', 'created_at')
    search_fields = ('user__email', 'card__canonical_key')
    raw_id_fields = ('user', 'card')


@admin.register(PortfolioHolding)
class PortfolioHoldingAdmin(admin.ModelAdmin):
    list_display = ('user', 'card', 'grade', 'quantity', 'cost_basis', 'currency')
    list_filter = ('grade', 'currency')
    search_fields = ('user__email', 'card__canonical_key')
    raw_id_fields = ('user', 'card', 'grading_company')


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'card', 'direction', 'threshold_price', 'grade',
        'is_active', 'triggered_at',
    )
    list_filter = ('direction', 'is_active')
    search_fields = ('user__email', 'card__canonical_key')
    raw_id_fields = ('user', 'card')
