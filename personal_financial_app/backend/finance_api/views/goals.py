"""API views for financial goals."""
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import ExpectedGoal
from ..serializers import ExpectedGoalSerializer


class ExpectedGoalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ExpectedGoal model (financial tracking goals).
    Provides CRUD functionality to set, track, and update goal statuses.
    """
    queryset = ExpectedGoal.objects.all()
    serializer_class = ExpectedGoalSerializer


class GoalsAnalysisView(APIView):
    """
    API endpoint that provides financial goals analysis grouped by category.
    Returns progress per category with overall summary statistics.
    """
    def get(self, request, *args, **kwargs):
        goals = ExpectedGoal.objects.all()

        # Group goals by category
        category_map = {}
        for goal in goals:
            category = goal.category or 'Uncategorized'
            if category not in category_map:
                category_map[category] = {
                    'category': category,
                    'total_target': 0,
                    'total_current': 0,
                    'goals_count': 0,
                    'achieved_count': 0,
                    'goals': []
                }

            cat = category_map[category]
            cat['total_target'] += float(goal.target_amount)
            cat['total_current'] += float(goal.current_amount)
            cat['goals_count'] += 1
            if goal.status == 'achieved':
                cat['achieved_count'] += 1

            progress = (float(goal.current_amount) / float(goal.target_amount) * 100) if goal.target_amount > 0 else 0
            cat['goals'].append({
                'id': goal.id,
                'title': goal.title,
                'target_amount': float(goal.target_amount),
                'current_amount': float(goal.current_amount),
                'progress_percentage': round(progress, 2),
                'status': goal.status,
                'start_date': goal.start_date.strftime('%Y-%m-%d'),
                'end_date': goal.end_date.strftime('%Y-%m-%d'),
                'description': goal.description,
            })

        # Calculate overall progress per category
        categories = []
        for cat_data in category_map.values():
            overall_progress = (cat_data['total_current'] / cat_data['total_target'] * 100) if cat_data['total_target'] > 0 else 0
            categories.append({
                **cat_data,
                'overall_progress': round(overall_progress, 2),
            })

        # Overall summary
        total_target = sum(c['total_target'] for c in categories)
        total_current = sum(c['total_current'] for c in categories)
        total_goals = sum(c['goals_count'] for c in categories)
        total_achieved = sum(c['achieved_count'] for c in categories)
        overall_progress = (total_current / total_target * 100) if total_target > 0 else 0

        return Response({
            'summary': {
                'total_target': total_target,
                'total_current': total_current,
                'overall_progress': round(overall_progress, 2),
                'total_goals': total_goals,
                'achieved_goals': total_achieved,
            },
            'categories': categories,
        }, status=status.HTTP_200_OK)