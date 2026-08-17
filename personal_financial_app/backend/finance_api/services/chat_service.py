"""AI chat assistant: prompt building, response parsing and rule-based fallback."""
import json
import re

from ..models import Choice, CustomCategory
from .categorization import record_memory

CHANGE_KEYWORDS = ['change', 'set', 'update', 'modify', 'categorize', 'reassign', 'add category', 'create category', 'new category', 'remember']
MEMORY_KEYWORDS = ['remember', 'learn', 'save', 'store', 'always', 'in future', 'from now on']


def build_chat_prompt(message, transactions, all_categories, all_types, memories, history):
    """Build the system prompt payload for the AI chat call."""
    memory_context = [{'pattern': m.pattern, 'category': m.category, 'type': m.transaction_type, 'hits': m.hit_count} for m in memories]

    txn_context = []
    for t in transactions:
        txn_context.append({
            'id': t.id,
            'description': t.cleaned_description,
            'amount': str(t.amount),
            'date': str(t.date),
            'current_category': t.user_confirmed_category or t.suggested_category,
            'current_type': t.user_confirmed_type or t.transaction_type,
            'suggested_category': t.suggested_category,
            'suggested_type': t.transaction_type,
            'is_reviewed': t.is_reviewed,
        })

    return (
        f"You are a financial transaction assistant. Help the user manage transaction categorizations.\n\n"
        f"Available categories: {', '.join(all_categories)}\n"
        f"Available types: {', '.join(all_types)}\n\n"
        f"User memory (patterns I have learned from past confirmations):\n{json.dumps(memory_context, indent=2)}\n\n"
        f"Current transactions:\n{json.dumps(txn_context, indent=2)}\n\n"
        f"When the user asks to change categories or types, include a JSON block at the end:\n"
        f"<actions>\n"
        f'[{{"transaction_id": <id>, "category": "<category>", "type": "<type>", "reason": "<why>"}}]\n'
        f"</actions>\n\n"
        f"To create a new category:\n"
        f'[{{"action": "create_category", "name": "new category name", "type": "income|expense"}}]\n\n'
        f"Conversation history:\n{json.dumps(history, indent=2)}"
    )


def parse_ai_reply(ai_reply):
    """Extract structured actions from the AI reply.

    Returns (reply_text, actions, created_category_names).
    """
    actions = []
    match = re.search(r'<actions>(.*?)</actions>', ai_reply, re.DOTALL)
    if match:
        try:
            actions = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    reply = re.sub(r'<actions>.*?</actions>', '', ai_reply, flags=re.DOTALL).strip()

    applied_create = []
    remaining = []
    for a in actions:
        if isinstance(a, dict) and a.get('action') == 'create_category':
            name = a.get('name', '').strip()
            ttype = a.get('type', 'expense')
            if name and ttype in ('income', 'expense'):
                CustomCategory.objects.get_or_create(name=name, transaction_type=ttype)
                applied_create.append(name)
        else:
            remaining.append(a)

    extra = ''
    if applied_create:
        extra = f"\n\nCreated new categor{'ies' if len(applied_create) > 1 else 'y'}: {', '.join(applied_create)}"
    return reply + extra, remaining


def fallback_chat(message, transactions, all_categories, all_types):
    """Rule-based chat assistant used when the AI provider is unavailable.

    Returns (reply_text, actions).
    """
    msg_lower = message.lower()
    actions = []
    reply_parts = []

    is_change_request = any(w in msg_lower for w in CHANGE_KEYWORDS)
    is_memory_request = any(w in msg_lower for w in MEMORY_KEYWORDS)

    # --- Handle category creation requests ---
    new_cat_match = re.search(r'(?:add|create|new)\s+category\s+["\']?([a-zA-Z0-9 &]+)["\']?', msg_lower, re.IGNORECASE)
    if new_cat_match:
        cat_name = new_cat_match.group(1).strip().title()
        guessed_type = 'expense' if any(w in msg_lower for w in ['expense', 'spend', 'cost', 'buy']) else 'income'
        CustomCategory.objects.get_or_create(name=cat_name, transaction_type=guessed_type)
        reply_parts.append(f"Created new category '{cat_name}' ({guessed_type}). You can now select it in the dropdowns.")

    # --- Handle memory training ---
    memory_cat = None
    memory_type = None
    for m in Choice.objects.filter(choice_type=Choice.CATEGORY):
        if m.name.lower() in msg_lower:
            memory_cat = m.name
            memory_type = m.transaction_type
            break
    if not memory_cat:
        for cat in all_categories:
            if cat.lower() in msg_lower:
                memory_cat = cat
                break
    for t in all_types:
        if t.lower() in msg_lower:
            memory_type = t
            break

    if is_memory_request and memory_cat:
        for t in transactions:
            clean = t.cleaned_description
            if clean and any(w in msg_lower for w in clean.lower().split()[:3]):
                record_memory(clean, memory_cat, memory_type or t.transaction_type)
        reply_parts.append(
            f"I'll remember to categorize matching transactions as '{memory_cat}' in the future."
        )

    # --- Handle bulk change requests ---
    if is_change_request or is_memory_request:
        matched_cat = None
        matched_type = None

        for cat in all_categories:
            if cat.lower() in msg_lower:
                matched_cat = cat
                break

        for t in all_types:
            if t.lower() in msg_lower:
                matched_type = t
                break

        if matched_cat or matched_type:
            for t in transactions:
                action = {'transaction_id': t.id, 'reason': f'User requested change via chat'}
                cats_match = not matched_cat or (t.user_confirmed_category or t.suggested_category) != matched_cat
                types_match = not matched_type or (t.user_confirmed_type or t.transaction_type) != matched_type
                if cats_match or types_match:
                    action['category'] = matched_cat or t.user_confirmed_category or t.suggested_category
                    action['type'] = matched_type or t.user_confirmed_type or t.transaction_type
                    actions.append(action)

            if is_memory_request and matched_cat:
                for t in transactions:
                    record_memory(t.cleaned_description, matched_cat, matched_type or t.transaction_type)

            if actions:
                reply_parts.append(
                    f"Found {len(actions)} transaction{'s' if len(actions) > 1 else ''} to update."
                    + (f" Setting category to '{matched_cat}'." if matched_cat else '')
                    + (f" Setting type to '{matched_type}'." if matched_type else '')
                )
            else:
                reply_parts.append("Selected transactions already have those values.")
        elif not new_cat_match:
            reply_parts.append(
                "Tell me which category to use. Examples:\n"
                '- "Set all food transactions to Food & Dining"\n'
                '- "Change entertainment to Entertainment & Leisure"\n'
                '- "Remember spotify as Entertainment & Leisure"\n'
                '- "Add category called Subscriptions"'
            )

    if not any([is_change_request, is_memory_request, new_cat_match]):
        reply_parts.append(
            "I can help you:\n"
            '- Change categories in bulk ("set all Uber to Transportation")\n'
            '- Remember patterns ("remember spotify as Entertainment")\n'
            '- Create new categories ("add category called Subscriptions")\n'
            '- Suggest categories using what I have learned'
        )

    return ' '.join(reply_parts), actions