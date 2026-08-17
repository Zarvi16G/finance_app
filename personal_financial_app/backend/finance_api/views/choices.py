"""API views for choice/dropdown management (categories and types)."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Choice, CustomCategory, CustomType


class ChoiceView(APIView):
    def get(self, request):
        choices = Choice.objects.all().order_by('choice_type', 'sort_order', 'name')
        return Response([
            {
                'id': c.id,
                'name': c.name,
                'choice_type': c.choice_type,
                'transaction_type': c.transaction_type,
                'builtin': c.builtin,
            }
            for c in choices
        ])

    def delete(self, request, pk=None):
        try:
            choice = Choice.objects.get(id=pk)
            if choice.custom_category:
                choice.custom_category.delete()
            elif choice.custom_type:
                choice.custom_type.delete()
            else:
                return Response({'error': 'Cannot delete built-in choice'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Choice.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


class CustomCategoryView(APIView):
    def get(self, request):
        choices = Choice.objects.filter(choice_type=Choice.CATEGORY).order_by('sort_order', 'name')
        return Response([
            {'id': c.custom_category_id, 'name': c.name, 'type': c.transaction_type, 'builtin': c.builtin}
            for c in choices
        ])

    def post(self, request):
        name = request.data.get('name', '').strip()
        ttype = request.data.get('type', 'expense')
        if not name:
            return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
        obj, created = CustomCategory.objects.get_or_create(name=name, transaction_type=ttype)
        return Response({'id': obj.id, 'name': obj.name, 'type': obj.transaction_type, 'created': created})

    def put(self, request, pk=None):
        try:
            obj = CustomCategory.objects.get(id=pk)
        except CustomCategory.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        name = request.data.get('name', '').strip()
        ttype = request.data.get('type')
        if name:
            obj.name = name
        if ttype:
            obj.transaction_type = ttype
        obj.save()
        return Response({'id': obj.id, 'name': obj.name, 'type': obj.transaction_type})

    def delete(self, request, pk=None):
        try:
            obj = CustomCategory.objects.get(id=pk)
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CustomCategory.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


class CustomTypeView(APIView):
    def get(self, request):
        choices = Choice.objects.filter(choice_type=Choice.TYPE).order_by('sort_order', 'name')
        return Response([
            {'id': c.custom_type_id, 'name': c.name, 'builtin': c.builtin}
            for c in choices
        ])

    def post(self, request):
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
        obj, created = CustomType.objects.get_or_create(name=name)
        return Response({'id': obj.id, 'name': obj.name, 'created': created})

    def put(self, request, pk=None):
        try:
            obj = CustomType.objects.get(id=pk)
        except CustomType.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        name = request.data.get('name', '').strip()
        if name:
            obj.name = name
            obj.save()
        return Response({'id': obj.id, 'name': obj.name})

    def delete(self, request, pk=None):
        try:
            obj = CustomType.objects.get(id=pk)
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CustomType.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)