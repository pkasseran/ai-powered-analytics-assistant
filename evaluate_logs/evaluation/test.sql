
WITH base AS (
      SELECT
        fact_sales.revenue,
        fact_sales.quantity,
        fact_sales.unit_price,
        fact_sales.budget_revenue,
        fact_sales.sales_cost,
        dim_region.region_name
      FROM public.fact_sales
      JOIN public.dim_region ON fact_sales.region_sk = dim_region.region_sk
      JOIN public.dim_date ON fact_sales.date_sk = dim_date.date_sk
      WHERE dim_date.date >= make_date(extract(year from current_date)::int - 2, 1, 1)
    ),
    agg AS (
      SELECT
        region_name,
        SUM(COALESCE(base.revenue, base.quantity * base.unit_price)) AS actual_revenue,
        SUM(base.budget_revenue) AS budget_revenue
      FROM base
      GROUP BY 1
    )
    SELECT
      region_name AS region,
      actual_revenue,
      budget_revenue
    FROM agg
    ORDER BY actual_revenue DESC;

