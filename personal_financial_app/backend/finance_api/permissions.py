"""Custom DRF permission classes shared across the API.

Phase 0 (multi-tenancy) relies on two complementary mechanisms:

1. Every ``ViewSet.get_queryset()`` is filtered by ``owner=request.user``. This
   is what makes list endpoints show only your rows, and what makes a detail
   request for someone else's id return **404** (``get_object()`` looks the row
   up *inside* that filtered queryset and raises ``Http404`` when it is absent).

2. :class:`IsOwner` below is the second line of defense. It is checked by
   ``has_object_permission`` whenever a view calls ``get_object()`` (detail
   routes and ``@action(detail=True)`` methods), and it also lets custom actions
   that fetch rows directly (bypassing ``get_queryset``) assert ownership
   explicitly instead of trusting the caller-supplied id.
"""
from rest_framework import permissions


class IsOwner(permissions.IsAuthenticated):
    """Allow access only to the authenticated user that owns the object.

    Subclasses :class:`~rest_framework.permissions.IsAuthenticated`, so the
    "must be logged in" check still applies at the view level; this class adds
    the per-object ownership check on top.

    The object is expected to expose an ``owner`` attribute pointing at a
    ``User``. Objects without an ``owner`` (e.g. shared catalog rows) are
    rejected by this permission on purpose - use a different permission class
    for those endpoints.
    """
    
    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "owner", None)
        return owner is not None and owner == request.user
