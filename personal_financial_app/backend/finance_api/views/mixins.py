"""Shared view mixins.

`OwnerScopedMixin` is the single place that enforces multi-tenancy for the
ViewSets: it narrows every queryset to the authenticated user and stamps the
owner on creation, so no view can accidentally serve another user's rows.

Filtering (rather than checking ownership after lookup) is deliberate: an id
belonging to somebody else falls out of the queryset and DRF answers 404, which
does not reveal whether that id exists at all.
"""


class OwnerScopedMixin:
    """Restrict a ModelViewSet to rows owned by `request.user`.

    `owner_lookup` may traverse relations (e.g. 'statement__owner') for models
    that inherit their owner from a parent row. Those models have no owner
    column of their own, so they set `owner_field = None` and nothing is
    stamped on create.
    """

    owner_field = 'owner'
    owner_lookup = None
    # Models that hold money default a missing currency to the user's base one.
    currency_field = None

    def get_queryset(self):
        lookup = self.owner_lookup or self.owner_field
        return super().get_queryset().filter(**{lookup: self.request.user})

    def perform_create(self, serializer):
        extra = {}
        if self.owner_field is not None:
            extra[self.owner_field] = self.request.user
        if self.currency_field and not serializer.validated_data.get(self.currency_field):
            from ..services.snapshot_service import base_currency_for
            extra[self.currency_field] = base_currency_for(self.request.user)
        serializer.save(**extra)
