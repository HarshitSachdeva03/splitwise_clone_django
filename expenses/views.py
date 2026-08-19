from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import GroupSerializer, ExpenseCreateSerializer
from .services import create_expense_with_splits, simplify_group_debts, calculate_pairwise_debts

class GroupListCreateView(APIView):
    def post(self, request):
        serializer = GroupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExpenseCreateView(APIView):
    def post(self, request):
        serializer = ExpenseCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            expense = create_expense_with_splits(
                description=data['description'],
                amount=data['amount'],
                paid_by_id=data['paid_by_id'],
                group_id=data.get('group_id'),
                splits=data['splits']
            )
            return Response({"message": "Expense created", "expense_id": expense.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GroupBalancesView(APIView):
    def get(self, request, group_id):
        # Read query parameter: ?simplify=true or ?simplify=false
        simplify = request.query_params.get('simplify', 'true').lower() == 'true'
        
        if simplify:
            settlements = simplify_group_debts(group_id)
        else:
            settlements = calculate_pairwise_debts(group_id)

        return Response({
            "group_id": group_id, 
            "simplified": simplify, 
            "settlements": settlements
        })