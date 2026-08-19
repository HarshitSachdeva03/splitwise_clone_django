from django.urls import path
from .views import GroupListCreateView, ExpenseCreateView, GroupBalancesView

urlpatterns = [
    path('groups/', GroupListCreateView.as_view(), name='group-create'),
    path('expenses/', ExpenseCreateView.as_view(), name='expense-create'),
    path('groups/<int:group_id>/balances/', GroupBalancesView.as_view(), name='group-balances'),
]