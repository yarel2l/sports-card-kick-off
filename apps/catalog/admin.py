from django.contrib import admin

from .models import Card, CardSet, GradingCompany, Player, PriceObservation


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport', 'slug')
    list_filter = ('sport',)
    search_fields = ('name', 'slug', 'aliases')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(CardSet)
class CardSetAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'year', 'brand', 'name', 'sport')
    list_filter = ('sport', 'brand', 'year')
    search_fields = ('brand', 'name', 'slug')


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = (
        'canonical_key', 'card_set', 'player', 'card_number', 'parallel',
        'is_rookie', 'is_autograph',
    )
    list_filter = ('is_rookie', 'is_autograph', 'is_memorabilia')
    search_fields = ('canonical_key', 'card_number', 'player__name')
    raw_id_fields = ('card_set', 'player')


@admin.register(GradingCompany)
class GradingCompanyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(PriceObservation)
class PriceObservationAdmin(admin.ModelAdmin):
    list_display = (
        'card', 'source', 'kind', 'grading_company', 'grade', 'price',
        'currency', 'observed_at',
    )
    list_filter = ('source', 'kind', 'grade')
    search_fields = ('raw_title', 'external_id')
    raw_id_fields = ('card', 'grading_company')
    date_hierarchy = 'observed_at'
