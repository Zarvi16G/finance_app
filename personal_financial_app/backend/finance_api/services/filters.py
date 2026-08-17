"""Shared queryset filtering used across records, exports and analysis views."""


def apply_filters_to_queryset(request, queryset):
    """
    Reusable helper function to filter a transaction queryset
    identically across regular endpoints, CSV exports, and PDF reports.
    """
    record_type = request.query_params.get('type')
    if record_type:
        queryset = queryset.filter(type=record_type)

    category = request.query_params.get('category')
    if category:
        queryset = queryset.filter(category=category)

    account_bank = request.query_params.get('account_bank')
    if account_bank:
        queryset = queryset.filter(account_bank=account_bank)

    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)

    min_amount = request.query_params.get('min_amount')
    max_amount = request.query_params.get('max_amount')
    if min_amount:
        queryset = queryset.filter(amount__gte=min_amount)
    if max_amount:
        queryset = queryset.filter(amount__lte=max_amount)

    return queryset