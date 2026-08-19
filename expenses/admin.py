from django.contrib import admin
from .models import User, Group, Expense, ExpenseParticipant
# Register your models here.
admin.site.register(User)
admin.site.register(Group)
admin.site.register(Expense)
admin.site.register(ExpenseParticipant)