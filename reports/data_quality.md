# Data Quality Report

The project used three datasets: `cell_sites.csv`, `sessions.csv`, and `complaints.csv`.

### Cell Sites
- 229 sites and 7 columns.
- No missing values or duplicate rows were found.
- Contains 3G, 4G, and 5G sites.

### Sessions
- 242,200 sessions and 9 columns.
- 400 duplicate session records were identified.
- The `dropped` column contained inconsistent values (`TRUE/yes` and `FALSE/no`), which were normalized.
- Timestamps in `started_at` were cleaned and converted to datetime.

### Throughput
- Throughput contained impossible and extreme values, including negative values and a maximum of 99,999 Mbps.
- Site `CS-0077` was identified as faulty and excluded from the corrected throughput analysis.
- After exclusion, the throughput remained right-skewed, so the median was used as the main summary statistic.

### Complaints
- 9,000 complaint records were found.
- 809 `resolved_days` values were missing.
- No duplicate complaint rows were found.

The data was cleaned and quality issues were documented before analysis. The faulty site `CS-0077` was explicitly excluded from corrected throughput analysis to avoid distorting the results.