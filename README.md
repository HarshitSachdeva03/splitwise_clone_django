# Splitwise Design

## Models
- **Database normalization** eliminates redundant data and prevents anomalies during inserts, updates, or deletes.
    - **1NF (Atomic Values):** Each database cell must hold a single scalar value. Instead of storing a comma-separated string of users inside an expense row, each user gets their own row.
    - **2NF (No Partial Dependencies):** Every non-key column must depend on the _entire_ primary key.
    - **3NF (No Transitive Dependencies):** A non-key column must depend _only_ on the primary key, not on another non-key column.
> **The primary key should determine the facts in that table directly.**

So: `KEY → non-key attribute` is good. 
But: `KEY → non-key attribute → another non-key attribute` is a 3NF violation.

Example- If we stored the `group_name` inside the `Expense` table alongside `group_id`, `group_name` depends on `group_id`, not on `expense_id`. If the group name changed, we would have to update hundreds of expense rows. Splitting `Group` into its own table guarantees 3NF.

### **Model Anatomy & Thought Process**
  
**1. `User` Model & `AbstractUser`**
- **What is `AbstractUser`?** Django ships with a pre-built authentication system. `AbstractUser` is the base Python class containing all built-in fields (`username`, `email`, `password`, `first_name`, `is_staff`).     
- **Why extend it?** Inheriting `AbstractUser` creates a custom table in your database while retaining Django's native authentication, hashing, and session management. If you use Django’s default `User` model directly, adding custom fields (like `phone_number` or `profile_pic`) later requires destructive database migrations.

**2. `Group` Model**
- `members = models.ManyToManyField(User)`: Creates a hidden SQL join table linking `User` IDs and `Group` IDs. A user can belong to multiple groups, and a group contains multiple users.
    
**3. `Expense` Model**

- `paid_by = models.ForeignKey(User, ...)`: Represents a One-to-Many relationship (one user pays for many expenses).
- `null=True, blank=True`: `null=True` allows the underlying SQL column to store `NULL` values (for individual expenses outside any group). `blank=True` allows Django forms and APIs to accept empty payloads for this field.
- `DecimalField`: Uses fixed-point arithmetic instead of floating-point to prevent monetary rounding errors (e.g., $0.10 + $0.20 \neq$0.30 in binary float).
    
**4. `ExpenseParticipant` Model (Junction Table with Metadata)**

- When a Many-to-Many relationship needs additional attributes (such as `amount_owed`), standard `ManyToManyField` cannot be used. We explicit create a bridge table containing Foreign Keys to both parent entities (`Expense` and `User`) alongside the custom payload (`amount_owed`).

**Key Django Field Parameters**
- **`ForeignKey`**: Stores the Primary Key of a target table as a Foreign Key column in the current table.   
- **`on_delete=models.CASCADE`**: Referential integrity rule. If a `User` row is deleted, SQL automatically deletes all child `ExpenseParticipant` rows linked to that user. Alternatives include `PROTECT` (prevents deletion of parent if children exist) or `SET_NULL`.
- **`related_name`**: Defines the reverse relationship attribute on the target model. Given a user instance `u`, `u.expenses_paid.all()` uses the `related_name='expenses_paid'` to query all expenses paid by `u`, replacing Django's default `u.expense_set.all()` syntax.
- **`class Meta`**: Inner configuration class used to set model-level options rather than database columns. 
    - **`unique_together = ('expense', 'user')`**: Adds a composite unique database constraint preventing the same user from being added twice to the exact same expense split.

**How to Decide Schema Structure for Any App**
1. **Identify Entities:** List the nouns in your problem domain (User, Group, Expense).
2. **Determine Cardinality:** Ask "How many X belong to Y?" (One-to-Many vs. Many-to-Many). 
3. **Attach Payload:** If a relationship carries data (like an owe amount), turn the relationship into an explicit mapping table.
    
