# Failure Report

Total failing tests: **9**

## Test `0b9085b7c969`
- Query: `Show revenue versus budgeted revenue by region.`
- Status: ok
- SQL Correct: True
- SQL Diff: No differences.
- Chart Correct: False
- Chart Mismatches: (ANZ, Actual Revenue) missing in ground truth; chart=37213333.12
(APAC, Actual Revenue) missing in ground truth; chart=37105031.76
(AMER, Actual Revenue) missing in ground truth; chart=37090487.9
(EMEA, Actual Revenue) missing in ground truth; chart=35205353.7
(ANZ, Budgeted Revenue) missing in ground truth; chart=35732844.0
(APAC, Budgeted Revenue) missing in ground truth; chart=35560659.0
(AMER, Budgeted Revenue) missing in ground truth; chart=35822701.0
(EMEA, Budgeted Revenue) missing in ground truth; chart=33982845.0

## Test `7c9f4f70158e`
- Query: `Compare actual sales and budgeted revenue by quarter.`
- Status: ok
- SQL Correct: True
- SQL Diff: No differences.
- Chart Correct: False
- Chart Mismatches: (2024-Q3, Actual Sales) missing in ground truth; chart=2303677.91
(2024-Q4, Actual Sales) missing in ground truth; chart=31409296.04
(2025-Q1, Actual Sales) missing in ground truth; chart=29637896.53
(2025-Q2, Actual Sales) missing in ground truth; chart=30881978.79
(2025-Q3, Actual Sales) missing in ground truth; chart=32909009.25
(2025-Q4, Actual Sales) missing in ground truth; chart=19472347.96
(2024-Q3, Budgeted Revenue) missing in ground truth; chart=2308360.0
(2024-Q4, Budgeted Revenue) missing in ground truth; chart=31395558.0
(2025-Q1, Budgeted Revenue) missing in ground truth; chart=29620904.0
(2025-Q2, Budgeted Revenue) missing in ground truth; chart=30791379.0

## Test `8d517c8281bd`
- Query: `Compare total sales by region and salesperson.`
- Status: ok
- SQL Correct: True
- SQL Diff: No differences.
- Chart Correct: False
- Chart Mismatches: (APAC, Ken Tanaka) gt=18777689.38, chart=18327342.38
(ANZ, Alex Morgan) gt=18679990.19, chart=18533342.93
(AMER, Taylor Reese) gt=18570770.35, chart=18519717.55
(EMEA, Lara Schmidt) gt=17608120.49, chart=17597233.21

## Test `92fe792ef175`
- Query: `How do total units sold and overall revenue compare year over year?`
- Status: ok
- SQL Correct: True
- SQL Diff: No differences.
- Chart Correct: False
- Chart Mismatches: (2024, Units Sold) missing in ground truth; chart=43747.0
(2025, Units Sold) missing in ground truth; chart=159990.0
(2024, Actual Revenue) missing in ground truth; chart=33712973.95
(2025, Actual Revenue) missing in ground truth; chart=112901232.53

## Test `9a720866e909`
- Query: `How do actual sales by product category compare to the budget?`
- Status: ok
- SQL Correct: True
- SQL Diff: No differences.
- Chart Correct: False
- Chart Mismatches: (Computers, Actual Sales) missing in ground truth; chart=75491450.59
(Electronics, Actual Sales) missing in ground truth; chart=52860091.05
(Peripherals, Actual Sales) missing in ground truth; chart=11013378.22
(Wearables, Actual Sales) missing in ground truth; chart=4738342.51
(Accessories, Actual Sales) missing in ground truth; chart=2510944.11
(Computers, Budget) missing in ground truth; chart=72818912.0
(Electronics, Budget) missing in ground truth; chart=50993252.0
(Peripherals, Budget) missing in ground truth; chart=10519295.0
(Wearables, Budget) missing in ground truth; chart=4454352.0
(Accessories, Budget) missing in ground truth; chart=2313238.0

## Test `d082a13b00a5`
- Query: `Which salesperson achieved the highest profit margin this month?`
- Status: ok
- SQL Correct: True
- SQL Diff: No differences.
- Chart Correct: False
- Chart Mismatches: (Jordan Diaz, Gross Margin) missing in ground truth; chart=221537826.23

## Test `dfea1e7674bb`
- Query: `What were our total income and profit by month over the last 90 days?`
- Status: ok
- SQL Correct: True
- SQL Diff: No differences.
- Chart Correct: False
- Chart Mismatches: (2025-08-01, actual_revenue) missing in ground truth; chart=3700692.78
(2025-09-01, actual_revenue) missing in ground truth; chart=11839221.52
(2025-10-01, actual_revenue) missing in ground truth; chart=15429808.7
(2025-11-01, actual_revenue) missing in ground truth; chart=4042539.26
(2025-08-01, gross_margin) missing in ground truth; chart=3693111.98
(2025-09-01, gross_margin) missing in ground truth; chart=11809156.07
(2025-10-01, gross_margin) missing in ground truth; chart=15384281.36
(2025-11-01, gross_margin) missing in ground truth; chart=4031057.63

## Test `5515e06cd441`
- Query: `Which product category underperformed against its budget last month?`
- Status: ok
- SQL Correct: True
- SQL Diff: No differences.
- Chart Correct: False
- Chart Mismatches: (Accessories, Actual Revenue) missing in ground truth; chart=587657.89
(Wearables, Actual Revenue) missing in ground truth; chart=778457.6
(Peripherals, Actual Revenue) missing in ground truth; chart=1397343.73
(Electronics, Actual Revenue) missing in ground truth; chart=5322111.58
(Computers, Actual Revenue) missing in ground truth; chart=7344237.9
(Accessories, Budget Revenue) missing in ground truth; chart=590845.0
(Wearables, Budget Revenue) missing in ground truth; chart=783860.0
(Peripherals, Budget Revenue) missing in ground truth; chart=1404834.0
(Electronics, Budget Revenue) missing in ground truth; chart=5383350.0
(Computers, Budget Revenue) missing in ground truth; chart=7349052.0

## Test `62d4a6e5b8e4`
- Query: `Which region exceeded its sales targets last quarter?`
- Status: ok
- SQL Correct: True
- SQL Diff: No differences.
- Chart Correct: False
- Chart Mismatches: (AMER, Actual Revenue) missing in ground truth; chart=8163015.47
(APAC, Actual Revenue) missing in ground truth; chart=7997054.8
(ANZ, Actual Revenue) missing in ground truth; chart=7596997.44
(AMER, Budget Revenue) missing in ground truth; chart=8119077.0
(APAC, Budget Revenue) missing in ground truth; chart=7986147.0
(ANZ, Budget Revenue) missing in ground truth; chart=7590984.0
