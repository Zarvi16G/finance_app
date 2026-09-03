"""API views for profile settings (currency, custom categories and types)."""
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes

from ..models import Choice, CustomType, CustomCategory, UserSetting
from ..services import two_factor


def _identity(user, setting):
    """Personal details. Names live on the Django user, not duplicated here."""
    return {
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': setting.phone_number,
        'phone_verified': setting.phone_verified,
    }


def _vocabulary(user):
    """Built-in choices plus the ones this user created."""
    visible = Choice.objects.visible_to(user)
    type_choices = visible.filter(choice_type=Choice.TYPE).order_by('sort_order', 'name')
    cat_choices = visible.filter(choice_type=Choice.CATEGORY).order_by('sort_order', 'name')
    return {
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
        return Response({
            'currency': setting.currency,
            **_identity(request.user, setting),
            'two_factor': two_factor.public_status(setting),
            **_vocabulary(request.user),
        })

    def put(self, request):
        setting, _ = UserSetting.objects.get_or_create(owner=request.user)

        currency = request.data.get('currency')
        if currency:
            setting.currency = currency
            setting.save(update_fields=['currency', 'updated_at'])

        # Personal details. Only these fields are writable here — the second
        # factor has its own endpoints so it can require a fresh password.
        user_fields = {}
        for field in ('first_name', 'last_name'):
            if field in request.data:
                user_fields[field] = str(request.data[field]).strip()[:150]
        if 'email' in request.data:
            user_fields['email'] = str(request.data['email']).strip()
        if user_fields:
            for field, value in user_fields.items():
                setattr(request.user, field, value)
            request.user.save(update_fields=list(user_fields))

        if 'phone_number' in request.data:
            phone = str(request.data['phone_number']).strip()[:20]
            if phone != setting.phone_number:
                # A changed number has to be verified again before it could
                # ever carry an SMS code.
                setting.phone_number = phone
                setting.phone_verified = False
                setting.save(update_fields=['phone_number', 'phone_verified', 'updated_at'])

        type_name = request.data.get('new_type', '').strip()
        if type_name:
            CustomType.objects.get_or_create(owner=request.user, name=type_name)
        cat_name = request.data.get('new_category', '').strip()
        cat_type = request.data.get('new_category_type', 'expense')
        if cat_name:
            CustomCategory.objects.get_or_create(
                owner=request.user, name=cat_name,
                defaults={'transaction_type': cat_type},
            )
        return Response({
            'currency': setting.currency,
            **_identity(request.user, setting),
            'two_factor': two_factor.public_status(setting),
            **_vocabulary(request.user),
        })
