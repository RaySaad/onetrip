# Fleet Expenses - Odoo 19

Technical name: `fleet_expenses`

## Purpose
Connect Odoo Expenses, Fleet, and Accounting around the vehicle as a common cost dimension.

## V1 workflow
- Employee-paid / petty-cash vehicle costs: create a Fleet Expense.
- Approval, reimbursement, taxes, receipt attachments, and accounting remain native Odoo Expenses.
- Vehicle is copied to the generated accounting expense line using Odoo 19 `account_fleet`'s native `account.move.line.vehicle_id` field.
- Supplier maintenance/workshop invoices continue to use Vendor Bills with Vehicle on the bill line. Odoo's native `account_fleet` module creates the Fleet Service when the bill is posted.
- Fleet Expense records do NOT automatically create Fleet Service records, preventing fuel/toll/parking records from flooding maintenance history.

## Added fields on hr.expense
- Fleet Expense
- Vehicle
- Odometer
- Fuel Quantity (L)
- Cost / Liter (computed)

## Dependencies
- fleet
- hr_expense
- account_fleet

## Validation
A vehicle is required before a Fleet Expense can be submitted. Drafts created from receipt uploads can be completed later.
