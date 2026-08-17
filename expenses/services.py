import heapq
from collections import defaultdict
from decimal import Decimal
from .models import Expense, ExpenseParticipant
from django.db import transaction

def calculate_net_balances(group_id):
    """
    Computes the net credit/debit balance for every user in a specific group.
    Returns a dictionary: {user_id: net_balance_decimal}
    """
    balances = defaultdict(Decimal)
    
    # Fetch all expenses belonging to this group
    expenses = Expense.objects.filter(group_id=group_id)

    for expense in expenses:
        # Credit the person who paid the total bill
        balances[expense.paid_by_id] += expense.amount

        # Debit every participant according to their owed share
        participants = ExpenseParticipant.objects.filter(expense=expense)
        for participant in participants:
            balances[participant.user_id] -= participant.amount_owed

    return balances


def simplify_group_debts(group_id):
    """
    Min Cash Flow Algorithm (Simplify Debts ENABLED).
    Greedily matches the largest creditor with the largest debtor.
    """
    balances = calculate_net_balances(group_id)

    creditor_heap = [] # Max-Heap of (amount_owed_to_user, user_id)
    debtor_heap = []   # Max-Heap of (amount_user_owes, user_id)

    for user_id, net_amount in balances.items():
        if net_amount > Decimal('0.00'):
            # Invert sign to simulate Max-Heap in Python's heapq
            heapq.heappush(creditor_heap, (-net_amount, user_id))
        elif net_amount < Decimal('0.00'):
            # Store positive debt magnitude for comparison
            heapq.heappush(debtor_heap, (net_amount, user_id))

    transactions = []

    # Greedily pair max creditor with max debtor
    while creditor_heap and debtor_heap:
        neg_credit, creditor_id = heapq.heappop(creditor_heap)
        neg_debt, debtor_id = heapq.heappop(debtor_heap)

        credit_amount = -neg_credit
        debt_amount = -neg_debt  # Since net_amount was negative

        # Settlement is the minimum of what creditor needs vs what debtor owes
        settlement_amount = min(credit_amount, debt_amount)

        transactions.append({
            'from_user': debtor_id,
            'to_user': creditor_id,
            'amount': round(settlement_amount, 2)
        })

        # Calculate remaining balances
        remaining_credit = credit_amount - settlement_amount
        remaining_debt = debt_amount - settlement_amount

        # Push back to heap if not fully settled
        if remaining_credit > Decimal('0.00'):
            heapq.heappush(creditor_heap, (-remaining_credit, creditor_id))
        if remaining_debt > Decimal('0.00'):
            heapq.heappush(debtor_heap, (-remaining_debt, debtor_id))

    return transactions

def calculate_pairwise_debts(group_id):
    """
    Direct Pairwise Netting (Simplify Debts DISABLED).
    Preserves exact buyer-seller relationships without graph simplification.
    """
    # Map structure: pairwise_matrix[debtor_id][creditor_id] = total_owed
    pairwise_matrix = defaultdict(lambda: defaultdict(Decimal))

    expenses = Expense.objects.filter(group_id=group_id)

    for expense in expenses:
        payer_id = expense.paid_by_id
        participants = ExpenseParticipant.objects.filter(expense=expense)

        for participant in participants:
            borrower_id = participant.user_id
            if borrower_id != payer_id:
                pairwise_matrix[borrower_id][payer_id] += participant.amount_owed

    transactions = []
    processed_pairs = set()

    # Net bidirectional edges between every unique user pair (A, B)
    users = list(pairwise_matrix.keys())
    for u1 in users:
        for u2 in pairwise_matrix[u1].keys():
            pair_key = tuple(sorted([u1, u2]))
            if pair_key in processed_pairs:
                continue

            u1_owes_u2 = pairwise_matrix[u1][u2]
            u2_owes_u1 = pairwise_matrix[u2][u1]

            net_difference = u1_owes_u2 - u2_owes_u1

            if net_difference > Decimal('0.00'):
                transactions.append({'from_user': u1, 'to_user': u2, 'amount': round(net_difference, 2)})
            elif net_difference < Decimal('0.00'):
                transactions.append({'from_user': u2, 'to_user': u1, 'amount': round(abs(net_difference), 2)})

            processed_pairs.add(pair_key)

    return transactions

def create_expense_with_splits(description, amount, paid_by_id, group_id, splits):
    """
    Atomically creates an Expense and its ExpenseParticipant breakdown rows.
    'splits' is a list of dicts: [{'user_id': 1, 'amount_owed': Decimal('33.33')}, ...]
    """
    with transaction.atomic():
        # Step 1: Create the parent Expense record
        expense = Expense.objects.create(
            description=description,
            amount=amount,
            paid_by_id=paid_by_id,
            group_id=group_id
        )

        # Step 2: Prepare participant rows in memory
        participant_objects = [
            ExpenseParticipant(
                expense=expense,
                user_id=item['user_id'],
                amount_owed=item['amount_owed']
            )
            for item in splits
        ]

        # Step 3: Insert all participant rows in a single batch query
        ExpenseParticipant.objects.bulk_create(participant_objects)

        return expense