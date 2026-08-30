"""API views for profile settings (currency, custom categories and types).

Everything here is scoped to ``request.user``: their own ``UserSetting`` row and
their own custom vocabulary, merged with the shared built-in choices for display.
"""
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes

from ..models import Choice, CustomType, CustomCategory, UserSetting, CurrencyRate
from ..services.currency import get_rate_map


def _payload(setting, user):
    visible = Choice.objects.filter(Q(builtin=True) | Q(owner=user))
    type_choices = visible.filter(choice_type=Choice.TYPE).order_by('sort_order', 'name')
    cat_choices = visible.filter(choice_type=Choice.CATEGORY).order_by('sort_order', 'name')
    return {
        'currency': setting.currency,
        'exchange_rates': dict(get_rate_map()),
        'types': [
            {'id': c.custom_type_id, 'name': c.name, 'builtin': c.builtin}
            for c in type_choices
        ],
        'categories': [
            {'id': c.custom_category_id, 'name': c.name, 'type': c.transaction_type, 'builtin': c.builtin}
            for c in cat_choices
        ],
    }


@extend_schema_view(
    get=extend_schema(
        responses={200: OpenApiTypes.OBJECT},
        description='Returns the profile: currency code plus all custom types and categories.',
    ),
    put=extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT},
        description='Updates currency and/or creates custom types and categories (new_type, new_category, new_category_type).',
    ),
)
class ProfileSettingsView(APIView):
    def get(self, request):
        setting, _ = UserSetting.objects.get_or_create(owner=request.user)
        return Response(_payload(setting, request.user))

    def put(self, request):
        setting, _ = UserSetting.objects.get_or_create(owner=request.user)
        currency = request.data.get('currency')
        if currency:
            setting.currency = currency
            setting.save()
        type_name = request.data.get('new_type', '').strip()
        if type_name:
            CustomType.objects.get_or_create(owner=request.user, name=type_name)
        cat_name = request.data.get('new_category', '').strip()
        cat_type = request.data.get('new_category_type', 'expense')
        if cat_name:
            CustomCategory.objects.get_or_create(
                owner=request.user, name=cat_name, defaults={'transaction_type': cat_type}
            )
        return Response(_payload(setting, request.user))
