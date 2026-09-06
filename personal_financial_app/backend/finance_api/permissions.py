"""Custom DRF permission classes shared across the API.

Multi-tenancy rests on two mechanisms, and they are deliberately redundant:

1. Every ``ViewSet.get_queryset()`` is narrowed to ``owner=request.user`` by
   :class:`~finance_api.views.mixins.OwnerScopedMixin`. This is what makes
   list endpoints show only your rows, and what makes a detail request for
   someone else's id answer **404** — ``get_object()`` looks the row up
   *inside* the filtered queryset, so an id that is not yours is simply
   absent, and the response does not reveal whether it exists at all.

2. :class:`IsOwner` below is the second line. DRF checks it in
   ``has_object_permission`` whenever a view calls ``get_object()``, so a view
   that one day forgets the mixin, or fetches a row by id directly, still
   cannot hand it to the wrong user.

The first mechanism alone is sufficient today. The second exists because the
cost of this class of bug — one unfiltered queryset exposing every user's
financial records — is high enough to be worth catching twice.
"""
from rest_framework import permissions


class IsOwner(permissions.IsAuthenticated):
    """Allow access only to the authenticated user that owns the object.

    Subclasses :class:`~rest_framework.permissions.IsAuthenticated`, so the
    "must be logged in" check still applies at the view level; this adds the
    per-object ownership check on top.

    Ownership is resolved through the view's ``owner_lookup`` when it has one,
    because not every model carries the column: an extracted transaction
    belongs to whoever owns its statement, and a budget line to whoever owns
    its goal. Reading only a literal ``obj.owner`` would reject those rows
    from their rightful owner.

    A row whose owner cannot be resolved at all is denied. That is the safe
    direction: a shared catalog row that legitimately has no owner belongs on
    an endpoint with a different permission class, not on this one.
    """

    def has_object_permission(self, request, view, obj):
        owner = self._resolve_owner(view, obj)
        return owner is not None and owner == request.user

    @staticmethod
    def _resolve_owner(view, obj):
        """Walk the view's owner lookup, e.g. 'statement__owner', to the User."""
        lookup = getattr(view, 'owner_lookup', None) or getattr(view, 'owner_field', None) or 'owner'
        current = obj
        for part in lookup.split('__'):
            current = getattr(current, part, None)
            if current is None:
                return None
        return current
