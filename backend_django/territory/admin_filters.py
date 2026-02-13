"""
Reusable dropdown (select) filters for Regione/Provincia/Comune.

Django's default FK list_filter renders all values as a long clickable list,
which is unusable with hundreds of comuni. These filters use <select> widgets.

Provincia cascades from regione, comune cascades from provincia (shows
options only when a provincia is selected).

Usage:
    from territory.admin_filters import make_territory_filters

    class SezioneElettoraleAdmin(admin.ModelAdmin):
        list_filter = [*make_territory_filters('comune'), ...]

    class DatiSezioneAdmin(admin.ModelAdmin):
        list_filter = [*make_territory_filters('sezione__comune'), ...]

For models that ARE Provincia (direct regione FK):
    list_filter = [*make_territory_filters(regione='regione'), ...]
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from territory.models import Regione, Provincia, Comune


def make_territory_filters(comune_path=None, *, regione=None, provincia=None, comune=None):
    """
    Build a list of [RegioneFilter, ProvinciaFilter, ComuneFilter] for the
    given ORM path to the Comune FK.

    Args:
        comune_path: ORM path to the Comune FK from the model being filtered.
            e.g. 'comune', 'sezione__comune', or '' if the model IS Comune.
        regione/provincia/comune: explicit ORM lookup overrides.
            Pass only the ones you need, e.g. regione='regione' on Provincia model.

    Returns:
        List of filter classes. Include only the levels that make sense.
    """
    filters = []

    if regione is not None or comune_path is not None:
        r_lookup = regione
        if r_lookup is None:
            r_lookup = f'{comune_path}__provincia__regione' if comune_path else 'provincia__regione'
        filters.append(_make_regione_filter(r_lookup))

    if provincia is not None or comune_path is not None:
        p_lookup = provincia
        if p_lookup is None:
            p_lookup = f'{comune_path}__provincia' if comune_path else 'provincia'
        # Derive the regione parameter_name to cascade
        r_param = filters[0].parameter_name if filters else 'regione'
        filters.append(_make_provincia_filter(p_lookup, r_param))

    if comune is not None or (comune_path is not None and comune_path != ''):
        c_lookup = comune or comune_path
        p_param = filters[-1].parameter_name if len(filters) >= 2 else 'provincia'
        filters.append(_make_comune_filter(c_lookup, p_param))

    return filters


def _make_regione_filter(lookup_field):
    param = lookup_field.replace('__', '_')

    class Filter(admin.SimpleListFilter):
        title = _('regione')
        parameter_name = param

        def lookups(self, request, model_admin):
            return [(r.pk, r.nome) for r in Regione.objects.order_by('nome')]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(**{lookup_field: self.value()})
            return queryset

    Filter.__name__ = f'RegioneFilter_{param}'
    return Filter


def _make_provincia_filter(lookup_field, regione_param):
    param = lookup_field.replace('__', '_')

    class Filter(admin.SimpleListFilter):
        title = _('provincia')
        parameter_name = param

        def lookups(self, request, model_admin):
            qs = Provincia.objects.select_related('regione').order_by('regione__nome', 'nome')
            regione_id = request.GET.get(regione_param)
            if regione_id:
                qs = qs.filter(regione_id=regione_id)
            return [(p.pk, f'{p.nome} ({p.sigla})') for p in qs]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(**{lookup_field: self.value()})
            return queryset

    Filter.__name__ = f'ProvinciaFilter_{param}'
    return Filter


def _make_comune_filter(lookup_field, provincia_param):
    param = lookup_field.replace('__', '_')

    class Filter(admin.SimpleListFilter):
        title = _('comune')
        parameter_name = param

        def lookups(self, request, model_admin):
            provincia_id = request.GET.get(provincia_param)
            if not provincia_id:
                return []
            return [
                (c.pk, c.nome)
                for c in Comune.objects.filter(provincia_id=provincia_id).order_by('nome')
            ]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(**{lookup_field: self.value()})
            return queryset

    Filter.__name__ = f'ComuneFilter_{param}'
    return Filter
