"""Rule-based categorization: keyword suggestions and learned-pattern memory."""
import re

from ..models import CategorizationMemory

STOP_WORDS = {'a', 'an', 'the', 'to', 'for', 'of', 'with', 'from', 'at', 'by', 'and', 'or', 'in', 'on', 'is', 'it', 'as', 'be', 'this', 'that', 'was', 'are'}

CATEGORY_KEYWORDS = {
    'Salary': ['salary', 'payroll', 'wages', 'income', 'direct deposit', 'paycheck'],
    'Investment': ['dividend', 'interest', 'investment', 'vanguard', 'fidelity', 'robinhood', 'etrade'],
    'Food & Dining': ['restaurant', 'cafe', 'starbucks', 'mcdonald', 'subway', 'pizza', 'food', 'grocery', 'supermarket', 'whole foods', 'trader joe', 'kroger', 'safeway', 'aldi'],
    'Rent & Housing': ['rent', 'mortgage', 'hoa', 'property tax', 'apartment', 'lease'],
    'Utilities': ['electric', 'gas', 'water', 'internet', 'cable', 'phone', 'utility', 'verizon', 'att', 'comcast', 'spectrum'],
    'Entertainment & Leisure': ['netflix', 'spotify', 'hulu', 'disney', 'movie', 'theater', 'concert', 'game', 'steam', 'xbox', 'playstation'],
    'Transportation': ['uber', 'lyft', 'taxi', 'gas', 'fuel', 'shell', 'chevron', 'exxon', 'bp ', 'parking', 'metro', 'transit', 'bus', 'train'],
    'Healthcare': ['pharmacy', 'cvs', 'walgreens', 'doctor', 'hospital', 'clinic', 'dental', 'vision', 'medical', 'health', 'insurance'],
    'Education': ['tuition', 'school', 'university', 'college', 'course', 'udemy', 'coursera', 'book'],
    'Shopping': ['amazon', 'walmart', 'target', 'costco', 'best buy', 'apple', 'mall', 'shop', 'store'],
}


def suggest_category(description):
    """Suggest category based on description keywords."""
    desc_lower = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category

    return 'Other'


def extract_pattern(description):
    tokens = re.sub(r'[^a-z0-9\s]', '', description.lower()).split()
    tokens = [t for t in tokens if t not in STOP_WORDS and not t.isdigit()]
    return ' '.join(tokens[:4]) if tokens else description.lower()[:80]


def record_memory(description, category, txn_type):
    pattern = extract_pattern(description)
    if not pattern:
        return
    obj, created = CategorizationMemory.objects.get_or_create(
        pattern=pattern,
        category=category,
        transaction_type=txn_type,
        defaults={'hit_count': 1}
    )
    if not created:
        obj.hit_count += 1
        obj.save()
    return obj