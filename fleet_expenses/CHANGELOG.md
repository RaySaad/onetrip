# Changelog

## 19.0.2.0.3

- Added complete Saudi Arabic translation coverage for the statement menu, wizard, PDF, and XLSX workbook.
- Made dynamically generated Excel labels and expense-source labels language-aware.
- Displayed translated Asset and journal-entry status/method selections.

## 19.0.2.0.2

- Rebuilt directly from the working V1.0.1 translation-fix source.
- Restored all original V1 technical field names, XML IDs, actions, menus, views, submit validation, constraints, and accounting propagation.
- Switched the report dependency to Odoo's native `account_asset_fleet` bridge.

## 19.0.2.0.1

- Restored the V1 `vehicle_odometer` technical field for upgrade compatibility and preservation of existing odometer values.
- Retained `fleet_odometer` as a writable compatibility alias.

## 19.0.2.0.0

- Added Vehicle Account Statement wizard, PDF report, and multi-sheet XLSX export.
- Added asset/depreciation, operating expense, transaction, fuel, service, GL, source, lifetime, odometer, and cost/km sections.
- Reused native Asset–Vehicle and accounting-line Vehicle links; no duplicate asset field.
- Kept Fleet Service values informational to prevent accounting double counting.
- Preserved V1 Fleet Expense fields, workflow, accounting propagation, and native Expense security groups.
