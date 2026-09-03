"""Smart financial analysis: Ollama/DeepSeek with a rule-based fallback."""
import json

import requests

from ..models import FinancialRecord, ExpectedGoal

OLLAMA_URL = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'deepseek-r1:7b'

_SYSTEM_INSTRUCTIONS = (
    "You are an expert Certified Financial Planner (CFP) and wealth management AI assistant. "
    "Analyze the client's financial records, identify budgeting concerns, evaluate savings goals, "
    "and suggest highly actionable wealth-building tips. Keep answers structured, professional, "
    "direct, and encouraging."
)


def run_financial_analysis(records, goals, base_currency=None):
    """Aggregate financial context and ask Ollama (or the rule fallback).

    `records` should be a pre-filtered FinancialRecord queryset. Every figure
    handed to the model is expressed in `base_currency`, so advice is never
    based on pesos and dollars added together.
    Returns {'analysis': str, 'used_fallback': bool}.
    """
    context, category_breakdown, goals_data = _build_financial_context(
        records, goals, base_currency
    )

    response_text, used_fallback = _ask_ollama(_SYSTEM_INSTRUCTIONS, context['prompt_body'])
    if used_fallback:
        response_text = _build_fallback_response(
            context, category_breakdown, goals_data
        )

    return {'analysis': response_text, 'used_fallback': used_fallback}


def _build_financial_context(records, goals, base_currency=None):
    from . import currency_service

    base = currency_service.normalize(base_currency or currency_service.DEFAULT_BASE)

    total_income = float(currency_service.sum_in(records.filter(type='income'), base))
    total_expense = float(currency_service.sum_in(records.filter(type='expense'), base))
    net_savings = total_income - total_expense
    savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0

    expenses = records.filter(type='expense')
    category_totals = {
        category: float(currency_service.sum_in(expenses.filter(category=category), base))
        for category in expenses.values_list('category', flat=True).distinct()
    }
    category_breakdown = [
        {'category': category, 'total': total}
        for category, total in sorted(category_totals.items(), key=lambda item: -item[1])
    ]
    category_breakdown_formatted = dict(category_totals)

    goals_data = []
    for goal in goals:
        progress = (float(goal.current_amount) / float(goal.target_amount) * 100) if goal.target_amount > 0 else 0
        goals_data.append({
            'title': goal.title,
            'target_amount': float(
                currency_service.convert_safe(goal.target_amount, goal.currency or base, base)
            ),
            'current_amount': float(
                currency_service.convert_safe(goal.current_amount, goal.currency or base, base)
            ),
            'progress_percentage': round(progress, 2),
            'status': goal.status,
            'end_date': goal.end_date.strftime('%Y-%m-%d')
        })

    financial_context = {
        "total_income": total_income,
        "total_expenses": total_expense,
        "net_savings": net_savings,
        "savings_rate_percentage": round(savings_rate, 2),
        "expense_by_category": category_breakdown_formatted,
        "financial_goals": goals_data
    }

    prompt_body = (
        f"Here is my personal financial data:\n"
        f"{json.dumps(financial_context, indent=2)}\n\n"
        f"Please structure your reply with the following sections:\n"
        f"1. **Executive Financial Health Audit** (Briefly diagnose current state and savings rate)\n"
        f"2. **Category Budget Leak Analysis** (Identify which categories are drains and recommend specific % reductions)\n"
        f"3. **Milestone Goal Projection** (Assess recent progress vs future targets for goals, and suggest if on track)\n"
        f"4. **Actionable Action Steps** (3 short, bulleted, high-impact strategies to improve cash flow immediately)"
    )

    return {
        'total_income': total_income,
        'total_expense': total_expense,
        'net_savings': net_savings,
        'savings_rate': savings_rate,
        'prompt_body': prompt_body,
    }, category_breakdown_formatted, goals_data


def _ask_ollama(system_instructions, prompt_body):
    """Query local Ollama; returns (text, used_fallback)."""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{system_instructions}\n\n{prompt_body}",
            "stream": False
        }
        ollama_response = requests.post(OLLAMA_URL, json=payload, timeout=4)
        if ollama_response.status_code == 200:
            return ollama_response.json().get('response', ''), False
        raise Exception("Ollama endpoint responded with non-200 status code.")
    except Exception:
        return '', True


def _build_fallback_response(context, category_breakdown, goals_data):
    """Rule-based fallback expertise when Ollama is offline."""
    total_income = context['total_income']
    total_expense = context['total_expense']
    savings_rate = context['savings_rate']

    status_summary = "Healthy" if savings_rate >= 20 else "Tight" if savings_rate >= 0 else "Critical Deficit"

    top_expense_msg = ""
    if category_breakdown:
        top_cat = max(category_breakdown, key=category_breakdown.get)
        top_expense_msg = f"Your highest expense category is **{top_cat}** at ${category_breakdown[top_cat]:,.2f}."
    else:
        top_expense_msg = "No recent expenses were logged, making it an excellent time to start budgeting."

    goals_advice = []
    for g in goals_data:
        on_track = "on track" if g['progress_percentage'] >= 50 else "needs attention"
        goals_advice.append(f"- **{g['title']}** ({g['status']}): Currently at {g['progress_percentage']}% of the ${g['target_amount']:,.2f} target. This target {on_track} with end-date set for {g['end_date']}.")
    goals_advice_str = "\n".join(goals_advice) if goals_advice else "- No savings goals are currently active. Setting clear goals is the first step toward long-term security."

    if savings_rate >= 20:
        action_bullets = (
            "- **Automate Investments:** Since you have a healthy savings rate, automate transferring 15% of savings directly into diversified index funds.\n"
            "- **Review Subscriptions:** Squeeze another 2-3% savings by auditing recurring credit card memberships.\n"
            "- **Optimize Goals:** Consider accelerating target dates for high-priority goals."
        )
    elif savings_rate >= 0:
        action_bullets = (
            "- **Establish a 50/30/20 Budget:** Allocate 50% to needs, 30% to wants, and 20% directly to your goals.\n"
            "- **Cut Dining Out/Leisure:** Trim leisure or food dining costs by 15% to buffer your emergency reserve.\n"
            "- **Increase Current Goal Contributions:** Direct any windfalls (bonuses/tax returns) immediately toward active milestones."
        )
    else:
        action_bullets = (
            "- **Immediate Freeze on Discretionary Expenses:** Pause all shopping and entertainment logs until cash flow enters positive territory.\n"
            "- **Negotiate Fixed Bills:** Call internet, insurance, and utilities providers to request loyalty rate adjustments or down-tier plans.\n"
            "- **Emergency Fund Safeguarding:** Ensure any available liquidity is parked in a High-Yield Savings Account (HYSA) to survive short-term shortfalls."
        )

    return (
        f"### 1. **Executive Financial Health Audit**\n"
        f"- **Financial Health Index:** `{status_summary}`\n"
        f"- **Total Monthly Income:** `${total_income:,.2f}`\n"
        f"- **Total Monthly Expense:** `${total_expense:,.2f}`\n"
        f"- **Calculated Savings Rate:** `{savings_rate:.2f}%` of your total income is saved.\n"
        f"- *Analysis:* " + (
            "Excellent! Saving over 20% is the golden threshold for accelerated wealth compounding. Keep this momentum."
            if savings_rate >= 20 else
            "You are currently staying afloat, but your safety buffer is low. Aim to bring savings rate closer to 20%."
            if savings_rate >= 0 else
            "WARNING: Your expenses exceed your income. You are operating in a budget deficit. Immediate action is required to avoid mounting debt."
        ) + "\n\n"
        f"### 2. **Category Budget Leak Analysis**\n"
        f"- {top_expense_msg}\n"
        f"- **Budget Leaks Assessment:**\n"
        + "\n".join([f"  - **{cat}**: `${val:,.2f}` ({val/total_expense*100:.1f}% of entire expense budget)" for cat, val in list(category_breakdown.items())[:3]]) + "\n"
        f"- **Recommendation:** Seek to reduce category spending on your top discretionary areas by `10% to 15%` next month to free up substantial breathing room.\n\n"
        f"### 3. **Milestone Goal Projection**\n"
        f"- **Active Goal Projections (Recent Status vs Future Status):**\n"
        f"{goals_advice_str}\n\n"
        f"### 4. **Actionable Action Steps**\n"
        f"{action_bullets}\n\n"
        f"--- \n"
        f"*Note: Ollama local node was not detected (offline/not installed). Running smart fallback expert model.*"
    )