"""API views for profile settings (currency, custom categories and types)."""
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Choice, CustomType, CustomCategory, UserSetting


class ProfileSettingsView(APIView):
    def get(self, request):
        setting, _ = UserSetting.objects.get_or_create(pk=1)
        type_choices = Choice.objects.filter(choice_type=Choice.TYPE).order_by('sort_order', 'name')
        cat_choices = Choice.objects.filter(choice_type=Choice.CATEGORY).order_by('sort_order', 'name')
        return Response({
            'currency': setting.currency,
            'types': [
                {'id': c.custom_type_id, 'name': c.name, 'builtin': c.builtin}
                for c in type_choices
            ],
            'categories': [
                {'id': c.custom_category_id, 'name': c.name, 'type': c.transaction_type, 'builtin': c.builtin}
                for c in cat_choices
            ],
        })

    def put(self, request):
        setting, _ = UserSetting.objects.get_or_create(pk=1)
        currency = request.data.get('currency')
        if currency:
            setting.currency = currency
            setting.save()
        type_name = request.data.get('new_type', '').strip()
        if type_name:
            CustomType.objects.get_or_create(name=type_name)
        cat_name = request.data.get('new_category', '').strip()
        cat_type = request.data.get('new_category_type', 'expense')
        if cat_name:
            CustomCategory.objects.get_or_create(name=cat_name, transaction_type=cat_type)
        type_choices = Choice.objects.filter(choice_type=Choice.TYPE).order_by('sort_order', 'name')
        cat_choices = Choice.objects.filter(choice_type=Choice.CATEGORY).order_by('sort_order', 'name')
        return Response({
            'currency': setting.currency,
            'types': [
                {'id': c.custom_type_id, 'name': c.name, 'builtin': c.builtin}
                for c in type_choices
            ],
            'categories': [
                {'id': c.custom_category_id, 'name': c.name, 'type': c.transaction_type, 'builtin': c.builtin}
                for c in cat_choices
            ],
        })