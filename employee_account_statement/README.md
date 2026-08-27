# Employee Account Statement - Odoo 19

## What this module adds

1. **Employee** on `account.move.line` (Journal Items).
2. Employee selection/search by **employee name or Saudi National / IQAMA ID** directly in the dropdown.
3. **Accounting > Reporting > Employee Statement** wizard.
4. Required wizard parameters: Employee, Account, Date From, Date To.
5. Statement logic: posted entries only, opening balance before Date From, period transactions, running balance and closing balance.
6. Professional **PDF** with company logo/name, employee/IQAMA information, statement details, print user and print time.
7. Formatted **Excel (XLSX)** with the same information.
8. Employee filter and Group By on Journal Items.

## Security design

The accounting field links to `hr.employee.public`, not directly to the private HR model. This lets accounting users select employees without being granted broad HR access. The Saudi National / IQAMA ID is read internally with `sudo()` only for the dedicated accounting lookup/report.

## Dependencies

- Accounting (`account`)
- Employees (`hr`)
- Saudi Arabia - Payroll (`l10n_sa_hr_payroll`)

## Install

Copy the `employee_account_statement` folder into your custom addons path, update the Apps list, then install **Employee Account Statement**.

## Test

1. Open a draft Journal Entry.
2. In **Journal Items**, assign an Employee on the employee-loan account line.
3. In the Employee dropdown, type either the employee name or the Saudi National / IQAMA ID.
4. Post the Journal Entry.
5. Go to **Accounting > Reporting > Employee Statement**.
6. Select Employee, Account, From/To dates.
7. Test **Export PDF** and **Export Excel**.


Build 19.0.1.0.2: corrected Odoo 19 PO translation metadata.
