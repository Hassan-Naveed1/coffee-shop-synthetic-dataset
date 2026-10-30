from pathlib import Path
import pandas as pd

# ============================================================
# 1. PROJECT SETUP AND DATA LOADING
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

# Dataset paths
SALES_FILE = DATA_DIR / "sales_transactions.csv"
PRODUCTS_FILE = DATA_DIR / "products.csv"
INVENTORY_FILE = DATA_DIR / "daily_inventory.csv"

# Load datasets
sales_df = pd.read_csv(SALES_FILE)
products_df = pd.read_csv(PRODUCTS_FILE)
inventory_df = pd.read_csv(INVENTORY_FILE)

print("=" * 65)
print("COFFEE SHOP SALES & INVENTORY ANALYSIS")
print("=" * 65)

print("\nAll datasets loaded successfully.")


# ============================================================
# 2. INITIAL DATASET AUDIT
# ============================================================

def inspect_dataset(name, dataframe):

    print("\n" + "=" * 65)
    print(f"{name.upper()} DATASET")
    print("=" * 65)

    print(f"Number of records: {len(dataframe):,}")
    print(f"Number of columns: {len(dataframe.columns)}")

    print("\nCOLUMN NAMES:")
    print(dataframe.columns.tolist())

    print("\nDATA TYPES:")
    print(dataframe.dtypes.to_string())

    print("\nMISSING VALUES:")
    missing = dataframe.isnull().sum()

    if missing.sum() == 0:
        print("No missing values found.")
    else:
        print(missing[missing > 0].to_string())

    print("\nDUPLICATE ROWS:")
    print(f"Total duplicates: {dataframe.duplicated().sum():,}")


# Inspect all three datasets
inspect_dataset("Sales Transactions", sales_df)
inspect_dataset("Products", products_df)
inspect_dataset("Daily Inventory", inventory_df)


print("\n" + "=" * 65)
print("INITIAL DATASET AUDIT COMPLETED")
print("=" * 65)


# ============================================================
# 3. DATA INTEGRITY AND BUSINESS RULE VALIDATION
# ============================================================

print("\n" + "=" * 65)
print("DATA INTEGRITY AND BUSINESS RULE VALIDATION")
print("=" * 65)


def report_check(description, issue_count):

    status = "PASS" if issue_count == 0 else "REVIEW"

    print(f"{status}: {description}: {issue_count:,} issue(s)")


# ------------------------------------------------------------
# 3.1 UNIQUE IDENTIFIERS
# ------------------------------------------------------------

print("\n3.1 IDENTIFIER VALIDATION")

duplicate_line_ids = sales_df["line_id"].duplicated().sum()
duplicate_product_ids = products_df["product_id"].duplicated().sum()

duplicate_inventory_keys = inventory_df.duplicated(
    subset=["inventory_date", "product_id"]
).sum()

report_check("Duplicate sales line IDs", duplicate_line_ids)
report_check("Duplicate product IDs", duplicate_product_ids)
report_check("Duplicate inventory date/product combinations",
             duplicate_inventory_keys)

print(f"Unique orders: {sales_df['transaction_id'].nunique():,}")
print(f"Unique sales lines: {sales_df['line_id'].nunique():,}")


# ------------------------------------------------------------
# 3.2 PRODUCT REFERENCE VALIDATION
# ------------------------------------------------------------

print("\n3.2 PRODUCT REFERENCE VALIDATION")

valid_product_ids = set(products_df["product_id"])

sales_unmatched_products = (
    ~sales_df["product_id"].isin(valid_product_ids)
).sum()

inventory_unmatched_products = (
    ~inventory_df["product_id"].isin(valid_product_ids)
).sum()

report_check("Sales records referencing unknown products",
             sales_unmatched_products)

report_check("Inventory records referencing unknown products",
             inventory_unmatched_products)


# ------------------------------------------------------------
# 3.3 SALES VALUE VALIDATION
# ------------------------------------------------------------

print("\n3.3 SALES VALUE VALIDATION")

invalid_quantities = (sales_df["quantity"] <= 0).sum()

invalid_unit_prices = (sales_df["unit_price_gbp"] <= 0).sum()

invalid_discounts = (
    ~sales_df["discount_percent"].isin([0, 5, 10, 15])
).sum()

report_check("Invalid quantities", invalid_quantities)
report_check("Invalid unit prices", invalid_unit_prices)
report_check("Unexpected discount percentages", invalid_discounts)


# Check payment methods and order channels

valid_payment_methods = {
    "Card",
    "Mobile Wallet",
    "Cash"
}

valid_order_channels = {
    "Takeaway",
    "Dine-in",
    "Delivery"
}

invalid_payment_methods = (
    ~sales_df["payment_method"].isin(valid_payment_methods)
).sum()

invalid_order_channels = (
    ~sales_df["order_channel"].isin(valid_order_channels)
).sum()

report_check("Unexpected payment methods", invalid_payment_methods)
report_check("Unexpected order channels", invalid_order_channels)


# ------------------------------------------------------------
# 3.4 PRODUCT CATALOGUE VALIDATION
# ------------------------------------------------------------

print("\n3.4 PRODUCT CATALOGUE VALIDATION")

invalid_product_costs = (
    products_df["unit_cost_gbp"] <= 0
).sum()

invalid_product_prices = (
    products_df["list_price_gbp"] <= products_df["unit_cost_gbp"]
).sum()

report_check("Invalid product costs", invalid_product_costs)
report_check("Selling prices not exceeding product costs",
             invalid_product_prices)


# Check whether sales prices match the product catalogue

price_lookup = products_df.set_index("product_id")["list_price_gbp"]

expected_unit_prices = sales_df["product_id"].map(price_lookup)

price_mismatches = (
    sales_df["unit_price_gbp"] != expected_unit_prices
).sum()

report_check("Sales prices inconsistent with product catalogue",
             price_mismatches)


# ------------------------------------------------------------
# 3.5 SALES CALCULATION VALIDATION
# ------------------------------------------------------------

print("\n3.5 SALES CALCULATION VALIDATION")

# Recalculate gross sales using quantity and unit price.
# Python rounding is used to match the original generation method.

expected_gross_sales = sales_df.apply(
    lambda row: round(
        row["quantity"] * row["unit_price_gbp"], 2
    ),
    axis=1
)

gross_sales_mismatches = (
    expected_gross_sales != sales_df["gross_sales_gbp"]
).sum()

report_check("Gross sales calculation mismatches",
             gross_sales_mismatches)


# Recalculate net sales before rounding the gross amount.
expected_net_sales = sales_df.apply(
    lambda row: round(
        row["quantity"] *
        row["unit_price_gbp"] *
        (1 - row["discount_percent"] / 100),
        2
    ),
    axis=1
)

net_sales_mismatches = (
    expected_net_sales != sales_df["net_sales_gbp"]
).sum()

report_check("Net sales calculation mismatches",
             net_sales_mismatches)


# Validate estimated costs against the product catalogue.
cost_lookup = products_df.set_index("product_id")["unit_cost_gbp"]

expected_costs = (
    sales_df["quantity"] *
    sales_df["product_id"].map(cost_lookup)
).round(2)

cost_mismatches = (
    expected_costs != sales_df["estimated_cost_gbp"]
).sum()

report_check("Estimated cost calculation mismatches",
             cost_mismatches)


# Validate estimated gross profit.
expected_profit = (
    sales_df["net_sales_gbp"] -
    sales_df["estimated_cost_gbp"]
).round(2)

profit_mismatches = (
    expected_profit != sales_df["estimated_gross_profit_gbp"]
).sum()

report_check("Estimated gross profit calculation mismatches",
             profit_mismatches)


# ------------------------------------------------------------
# 3.6 DATE VALIDATION
# ------------------------------------------------------------

print("\n3.6 DATE VALIDATION")

sales_datetime = pd.to_datetime(
    sales_df["transaction_datetime"],
    errors="coerce"
)

sales_date = pd.to_datetime(
    sales_df["transaction_date"],
    errors="coerce"
)

inventory_date = pd.to_datetime(
    inventory_df["inventory_date"],
    errors="coerce"
)

invalid_sales_dates = (
    sales_datetime.isna().sum() +
    sales_date.isna().sum()
)

invalid_inventory_dates = inventory_date.isna().sum()

report_check("Invalid sales dates or timestamps", invalid_sales_dates)
report_check("Invalid inventory dates", invalid_inventory_dates)

valid_dates = sales_datetime.notna() & sales_date.notna()

date_mismatches = (
    sales_datetime[valid_dates].dt.strftime("%Y-%m-%d") !=
    sales_date[valid_dates].dt.strftime("%Y-%m-%d")
).sum()

report_check("Transaction datetime/date inconsistencies",
             date_mismatches)

print(
    f"Sales date range: {sales_date.min().date()} "
    f"to {sales_date.max().date()}"
)


# ------------------------------------------------------------
# 3.7 INVENTORY VALIDATION
# ------------------------------------------------------------

print("\n3.7 INVENTORY VALIDATION")

expected_closing_stock = (
    inventory_df["opening_stock_units"] +
    inventory_df["units_received"] -
    inventory_df["units_sold"] -
    inventory_df["wastage_units"]
)

inventory_balance_mismatches = (
    expected_closing_stock != inventory_df["closing_stock_units"]
).sum()

report_check("Inventory balance calculation mismatches",
             inventory_balance_mismatches)


stock_columns = [
    "opening_stock_units",
    "units_received",
    "units_sold",
    "wastage_units",
    "closing_stock_units",
    "reorder_level_units"
]

negative_stock_values = (
    inventory_df[stock_columns] < 0
).sum().sum()

report_check("Negative inventory values", negative_stock_values)


# Validate reorder trigger logic.
expected_reorder = (
    inventory_df["opening_stock_units"] -
    inventory_df["units_sold"] -
    inventory_df["wastage_units"]
) < inventory_df["reorder_level_units"]

reorder_mismatches = (
    expected_reorder != inventory_df["reorder_triggered"]
).sum()

report_check("Reorder trigger inconsistencies", reorder_mismatches)


# ------------------------------------------------------------
# 3.8 DAILY INVENTORY VS SALES TRANSACTIONS
# ------------------------------------------------------------

print("\n3.8 INVENTORY AND SALES RECONCILIATION")

daily_sales = sales_df.groupby(
    ["transaction_date", "product_id"],
    as_index=False
)["quantity"].sum()

daily_sales = daily_sales.rename(
    columns={
        "transaction_date": "inventory_date",
        "quantity": "sales_units_from_transactions"
    }
)

inventory_reconciliation = inventory_df.merge(
    daily_sales,
    on=["inventory_date", "product_id"],
    how="left",
    validate="one_to_one"
)

inventory_reconciliation["sales_units_from_transactions"] = (
    inventory_reconciliation["sales_units_from_transactions"]
    .fillna(0)
    .astype(int)
)

sales_inventory_mismatches = (
    inventory_reconciliation["units_sold"] !=
    inventory_reconciliation["sales_units_from_transactions"]
).sum()

report_check("Inventory sales inconsistent with transaction records",
             sales_inventory_mismatches)


# ------------------------------------------------------------
# 3.9 INVENTORY COVERAGE
# ------------------------------------------------------------

print("\n3.9 INVENTORY COVERAGE")

unique_inventory_dates = inventory_df["inventory_date"].nunique()
unique_inventory_products = inventory_df["product_id"].nunique()

expected_inventory_records = (
    unique_inventory_dates * unique_inventory_products
)

inventory_coverage_difference = abs(
    len(inventory_df) - expected_inventory_records
)

report_check("Incomplete product/date inventory coverage",
             inventory_coverage_difference)

print(f"Unique inventory dates: {unique_inventory_dates:,}")
print(f"Products with inventory records: {unique_inventory_products:,}")
print(f"Expected inventory records: {expected_inventory_records:,}")


# ------------------------------------------------------------
# 3.10 INVESTIGATION COMPLETED
# ------------------------------------------------------------

print("\n" + "=" * 65)
print("DATA INTEGRITY INVESTIGATION COMPLETED")
print("=" * 65)


# ============================================================
# 4. EXPLORATORY DATA ANALYSIS (EDA)
# ============================================================

import matplotlib.pyplot as plt

print("\n" + "=" * 65)
print("4. EXPLORATORY DATA ANALYSIS")
print("=" * 65)

# ------------------------------------------------------------
# 4.1 PREPARE DATA FOR ANALYSIS
# ------------------------------------------------------------

sales_df["transaction_datetime"] = pd.to_datetime(
    sales_df["transaction_datetime"]
)

sales_df["transaction_date"] = pd.to_datetime(
    sales_df["transaction_date"]
)

sales_df["hour"] = sales_df["transaction_datetime"].dt.hour
sales_df["month"] = sales_df["transaction_datetime"].dt.month_name()
sales_df["month_number"] = sales_df["transaction_datetime"].dt.month

# ------------------------------------------------------------
# 4.2 KEY BUSINESS PERFORMANCE INDICATORS
# ------------------------------------------------------------

print("\n4.2 KEY BUSINESS PERFORMANCE INDICATORS")

total_revenue = sales_df["net_sales_gbp"].sum()
total_orders = sales_df["transaction_id"].nunique()
total_units = sales_df["quantity"].sum()
total_profit = sales_df["estimated_gross_profit_gbp"].sum()

order_values = sales_df.groupby("transaction_id")[
    "net_sales_gbp"
].sum()

average_order_value = order_values.mean()

profit_margin = (total_profit / total_revenue) * 100

print(f"Total Revenue: £{total_revenue:,.2f}")
print(f"Total Transactions: {total_orders:,}")
print(f"Total Units Sold: {total_units:,}")
print(f"Estimated Gross Profit: £{total_profit:,.2f}")
print(f"Average Order Value: £{average_order_value:,.2f}")
print(f"Estimated Gross Profit Margin: {profit_margin:.2f}%")

# ------------------------------------------------------------
# 4.3 MONTHLY SALES PERFORMANCE
# ------------------------------------------------------------

print("\n4.3 MONTHLY SALES PERFORMANCE")

monthly_sales = sales_df.groupby(
    "month_number"
).agg(
    revenue=("net_sales_gbp", "sum"),
    transactions=("transaction_id", "nunique"),
    units_sold=("quantity", "sum")
).reset_index()

monthly_sales["month"] = monthly_sales["month_number"].apply(
    lambda x: pd.Timestamp(
        year=2025, month=x, day=1
    ).strftime("%B")
)

print(monthly_sales.to_string(index=False))

# ------------------------------------------------------------
# 4.4 PRODUCT PERFORMANCE
# ------------------------------------------------------------

print("\n4.4 TOP 10 PRODUCTS BY REVENUE")

product_performance = sales_df.groupby(
    "product_id"
).agg(
    units_sold=("quantity", "sum"),
    revenue=("net_sales_gbp", "sum"),
    transactions=("transaction_id", "nunique")
).reset_index()

product_performance = product_performance.merge(
    products_df[["product_id", "product_name", "category"]],
    on="product_id",
    how="left"
)

top_products = product_performance.sort_values(
    "revenue", ascending=False
).head(10)

print(
    top_products[
        ["product_name", "category", "units_sold", "revenue"]
    ].to_string(index=False)
)

print("\nBOTTOM 10 PRODUCTS BY REVENUE")

bottom_products = product_performance.sort_values(
    "revenue", ascending=True
).head(10)

print(
    bottom_products[
        ["product_name", "category", "units_sold", "revenue"]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 4.5 CATEGORY PERFORMANCE
# ------------------------------------------------------------

print("\n4.5 PRODUCT CATEGORY PERFORMANCE")

category_performance = sales_df.merge(
    products_df[["product_id", "category"]],
    on="product_id",
    how="left"
).groupby("category").agg(
    revenue=("net_sales_gbp", "sum"),
    units_sold=("quantity", "sum"),
    transactions=("transaction_id", "nunique")
).sort_values(
    "revenue", ascending=False
)

print(category_performance.to_string())

# ------------------------------------------------------------
# 4.6 PAYMENT METHOD PERFORMANCE
# ------------------------------------------------------------

print("\n4.6 PAYMENT METHOD PERFORMANCE")

payment_performance = sales_df.groupby(
    "payment_method"
).agg(
    revenue=("net_sales_gbp", "sum"),
    transactions=("transaction_id", "nunique")
).sort_values(
    "revenue", ascending=False
)

print(payment_performance.to_string())

# ------------------------------------------------------------
# 4.7 ORDER CHANNEL PERFORMANCE
# ------------------------------------------------------------

print("\n4.7 ORDER CHANNEL PERFORMANCE")

channel_performance = sales_df.groupby(
    "order_channel"
).agg(
    revenue=("net_sales_gbp", "sum"),
    transactions=("transaction_id", "nunique")
).sort_values(
    "revenue", ascending=False
)

print(channel_performance.to_string())

# ------------------------------------------------------------
# 4.8 PEAK TRADING HOURS
# ------------------------------------------------------------

print("\n4.8 HOURLY SALES PERFORMANCE")

hourly_performance = sales_df.groupby(
    "hour"
).agg(
    revenue=("net_sales_gbp", "sum"),
    transactions=("transaction_id", "nunique"),
    units_sold=("quantity", "sum")
)

print(hourly_performance.to_string())

peak_hour = hourly_performance["revenue"].idxmax()

print(f"\nPeak revenue hour: {peak_hour:02d}:00")

# ------------------------------------------------------------
# 4.9 GENERATE BUSINESS CHARTS
# ------------------------------------------------------------

print("\n4.9 GENERATING CHARTS")

CHART_DIR = PROJECT_DIR / "charts"
CHART_DIR.mkdir(exist_ok=True)

# Chart 1: Monthly revenue

plt.figure(figsize=(11, 6))

plt.plot(
    monthly_sales["month"],
    monthly_sales["revenue"],
    marker="o"
)

plt.title("Monthly Coffee Shop Revenue - 2025")
plt.xlabel("Month")
plt.ylabel("Revenue (£)")
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()

plt.savefig(CHART_DIR / "monthly_revenue.png", dpi=300)
plt.close()

# Chart 2: Top 10 products

plt.figure(figsize=(11, 6))

plt.barh(
    top_products["product_name"],
    top_products["revenue"]
)

plt.title("Top 10 Products by Revenue")
plt.xlabel("Revenue (£)")
plt.ylabel("Product")
plt.gca().invert_yaxis()
plt.tight_layout()

plt.savefig(CHART_DIR / "top_products.png", dpi=300)
plt.close()

# Chart 3: Revenue by category

plt.figure(figsize=(9, 6))

plt.bar(
    category_performance.index,
    category_performance["revenue"]
)

plt.title("Revenue by Product Category")
plt.xlabel("Category")
plt.ylabel("Revenue (£)")
plt.xticks(rotation=35)
plt.tight_layout()

plt.savefig(CHART_DIR / "category_revenue.png", dpi=300)
plt.close()

# Chart 4: Hourly revenue

plt.figure(figsize=(11, 6))

plt.bar(
    hourly_performance.index,
    hourly_performance["revenue"]
)

plt.title("Revenue by Trading Hour")
plt.xlabel("Hour of Day")
plt.ylabel("Revenue (£)")
plt.xticks(range(0, 24))
plt.grid(axis="y")
plt.tight_layout()

plt.savefig(CHART_DIR / "hourly_revenue.png", dpi=300)
plt.close()

# Chart 5: Daily revenue trend

daily_revenue = sales_df.groupby(
    "transaction_date"
)["net_sales_gbp"].sum()

plt.figure(figsize=(13, 6))

plt.plot(
    daily_revenue.index,
    daily_revenue.values
)

plt.title("Daily Revenue Trend - 2025")
plt.xlabel("Date")
plt.ylabel("Revenue (£)")
plt.grid(True)
plt.tight_layout()

plt.savefig(CHART_DIR / "daily_revenue.png", dpi=300)
plt.close()

print(f"Five charts saved successfully in: {CHART_DIR}")

print("\n" + "=" * 65)
print("SECTION 4 EDA COMPLETED")
print("=" * 65)



# ============================================================
# 5. INVENTORY AND STOCK MANAGEMENT ANALYSIS
# ============================================================

print("\n" + "=" * 65)
print("5. INVENTORY AND STOCK MANAGEMENT ANALYSIS")
print("=" * 65)

# ------------------------------------------------------------
# 5.1 PREPARE INVENTORY DATA
# ------------------------------------------------------------

inventory_df["inventory_date"] = pd.to_datetime(
    inventory_df["inventory_date"]
)

inventory_analysis = inventory_df.merge(
    products_df[["product_id", "product_name", "category"]],
    on="product_id",
    how="left"
)

inventory_analysis["month"] = (
    inventory_analysis["inventory_date"].dt.month
)

inventory_analysis["month_name"] = (
    inventory_analysis["inventory_date"].dt.month_name()
)

inventory_analysis["available_stock"] = (
    inventory_analysis["opening_stock_units"] +
    inventory_analysis["units_received"]
)

inventory_analysis["wastage_rate"] = (
    inventory_analysis["wastage_units"] /
    inventory_analysis["available_stock"].replace(0, float("nan"))
) * 100

# ------------------------------------------------------------
# 5.2 OVERALL INVENTORY KPIs
# ------------------------------------------------------------

print("\n5.2 OVERALL INVENTORY KPIs")

total_received = inventory_df["units_received"].sum()
total_inventory_sold = inventory_df["units_sold"].sum()
total_wastage = inventory_df["wastage_units"].sum()

# Count initial stock only once per product.
first_day_stock = (
    inventory_analysis.sort_values("inventory_date")
    .groupby("product_id")["opening_stock_units"]
    .first()
    .sum()
)

total_available_stock = first_day_stock + total_received

overall_wastage_rate = (
    total_wastage / total_available_stock
) * 100

reorder_events = inventory_df["reorder_triggered"].sum()

stockout_days = (
    inventory_df["closing_stock_units"] == 0
).sum()

low_stock_days = (
    inventory_df["closing_stock_units"] <=
    inventory_df["reorder_level_units"]
).sum()

print(f"Total Units Received: {total_received:,}")
print(f"Total Units Sold: {total_inventory_sold:,}")
print(f"Total Units Wasted: {total_wastage:,}")
print(f"Overall Wastage Rate: {overall_wastage_rate:.2f}%")
print(f"Total Reorder Events: {reorder_events:,}")
print(f"Product-days with Zero Closing Stock: {stockout_days:,}")
print(f"Product-days at or Below Reorder Level: {low_stock_days:,}")

# ------------------------------------------------------------
# 5.3 MONTHLY INVENTORY PERFORMANCE
# ------------------------------------------------------------

print("\n5.3 MONTHLY INVENTORY PERFORMANCE")

monthly_inventory = inventory_analysis.groupby(
    ["month", "month_name"]
).agg(
    units_received=("units_received", "sum"),
    units_sold=("units_sold", "sum"),
    wastage=("wastage_units", "sum"),
    reorder_events=("reorder_triggered", "sum")
).reset_index().sort_values("month")

print(monthly_inventory.to_string(index=False))

# ------------------------------------------------------------
# 5.4 PRODUCTS WITH HIGHEST WASTAGE
# ------------------------------------------------------------

print("\n5.4 TOP 10 PRODUCTS BY WASTAGE")

product_inventory = inventory_analysis.groupby(
    ["product_id", "product_name", "category"]
).agg(
    units_received=("units_received", "sum"),
    units_sold=("units_sold", "sum"),
    wastage=("wastage_units", "sum"),
    reorder_events=("reorder_triggered", "sum"),
    average_closing_stock=("closing_stock_units", "mean"),
    zero_stock_days=(
        "closing_stock_units",
        lambda x: (x == 0).sum()
    )
).reset_index()

product_inventory["wastage_rate"] = (
    product_inventory["wastage"] /
    (
        product_inventory["units_received"] +
        inventory_analysis.groupby("product_id")[
            "opening_stock_units"
        ].sum().reindex(product_inventory["product_id"]).values
    ).replace(0, float("nan"))
) * 100

top_wastage = product_inventory.sort_values(
    "wastage", ascending=False
).head(10)

print(
    top_wastage[
        ["product_name", "category", "wastage",
         "units_sold", "wastage_rate"]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 5.5 PRODUCTS WITH MOST REORDER EVENTS
# ------------------------------------------------------------

print("\n5.5 TOP 10 PRODUCTS BY REORDER EVENTS")

top_reorders = product_inventory.sort_values(
    "reorder_events", ascending=False
).head(10)

print(
    top_reorders[
        ["product_name", "category", "reorder_events",
         "average_closing_stock", "zero_stock_days"]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 5.6 INVENTORY AVAILABILITY BY PRODUCT
# ------------------------------------------------------------

print("\n5.6 PRODUCTS WITH MOST ZERO-STOCK DAYS")

stockout_products = product_inventory.sort_values(
    "zero_stock_days", ascending=False
).head(10)

print(
    stockout_products[
        ["product_name", "category", "zero_stock_days",
         "average_closing_stock", "units_sold"]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 5.7 GENERATE INVENTORY CHARTS
# ------------------------------------------------------------

print("\n5.7 GENERATING INVENTORY CHARTS")

# Chart 6: Monthly wastage

plt.figure(figsize=(11, 6))

plt.bar(
    monthly_inventory["month_name"],
    monthly_inventory["wastage"]
)

plt.title("Monthly Inventory Wastage - 2025")
plt.xlabel("Month")
plt.ylabel("Wasted Units")
plt.xticks(rotation=45)
plt.tight_layout()

plt.savefig(CHART_DIR / "monthly_wastage.png", dpi=300)
plt.close()

# Chart 7: Top products by wastage

plt.figure(figsize=(11, 6))

plt.barh(
    top_wastage["product_name"],
    top_wastage["wastage"]
)

plt.title("Top 10 Products by Inventory Wastage")
plt.xlabel("Wasted Units")
plt.ylabel("Product")
plt.gca().invert_yaxis()
plt.tight_layout()

plt.savefig(CHART_DIR / "top_wastage_products.png", dpi=300)
plt.close()

# Chart 8: Reorder events by product

plt.figure(figsize=(11, 6))

plt.barh(
    top_reorders["product_name"],
    top_reorders["reorder_events"]
)

plt.title("Top 10 Products by Reorder Events")
plt.xlabel("Number of Reorder Events")
plt.ylabel("Product")
plt.gca().invert_yaxis()
plt.tight_layout()

plt.savefig(CHART_DIR / "top_reorder_products.png", dpi=300)
plt.close()

# Chart 9: Monthly units sold vs wastage

plt.figure(figsize=(11, 6))

plt.plot(
    monthly_inventory["month_name"],
    monthly_inventory["units_sold"],
    marker="o",
    label="Units Sold"
)

plt.plot(
    monthly_inventory["month_name"],
    monthly_inventory["wastage"],
    marker="o",
    label="Wastage"
)

plt.title("Monthly Inventory Sales vs Wastage")
plt.xlabel("Month")
plt.ylabel("Units")
plt.xticks(rotation=45)
plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig(CHART_DIR / "inventory_sales_vs_wastage.png", dpi=300)
plt.close()

print("Four inventory charts generated successfully.")

print("\n" + "=" * 65)
print("SECTION 5 INVENTORY ANALYSIS COMPLETED")
print("=" * 65)



# ============================================================
# 6. DEMAND VS INVENTORY ANALYSIS
# ============================================================

print("\n" + "=" * 65)
print("6. DEMAND VS INVENTORY ANALYSIS")
print("=" * 65)

# ------------------------------------------------------------
# 6.1 AGGREGATE SALES PERFORMANCE BY PRODUCT
# ------------------------------------------------------------

print("\n6.1 PRODUCT DEMAND")

product_demand = sales_df.groupby("product_id").agg(
    total_units_sold=("quantity", "sum"),
    total_revenue=("net_sales_gbp", "sum"),
    total_transactions=("transaction_id", "nunique")
).reset_index()

# ------------------------------------------------------------
# 6.2 AGGREGATE INVENTORY PERFORMANCE BY PRODUCT
# ------------------------------------------------------------

print("\n6.2 PRODUCT INVENTORY PERFORMANCE")

product_stock = inventory_analysis.groupby("product_id").agg(
    total_units_received=("units_received", "sum"),
    total_inventory_sold=("units_sold", "sum"),
    total_wastage=("wastage_units", "sum"),
    average_closing_stock=("closing_stock_units", "mean"),
    average_reorder_level=("reorder_level_units", "mean"),
    reorder_events=("reorder_triggered", "sum"),
    low_stock_days=(
        "closing_stock_units",
        lambda x: (
            x <= inventory_analysis.loc[
                x.index, "reorder_level_units"
            ]
        ).sum()
    ),
    zero_stock_days=(
        "closing_stock_units",
        lambda x: (x == 0).sum()
    )
).reset_index()

# ------------------------------------------------------------
# 6.3 COMBINE SALES AND INVENTORY DATA
# ------------------------------------------------------------

demand_inventory = product_demand.merge(
    product_stock,
    on="product_id",
    how="inner",
    validate="one_to_one"
)

demand_inventory = demand_inventory.merge(
    products_df[["product_id", "product_name", "category"]],
    on="product_id",
    how="left",
    validate="one_to_one"
)

# ------------------------------------------------------------
# 6.4 CALCULATE DEMAND AND STOCK INDICATORS
# ------------------------------------------------------------

days_in_period = inventory_analysis["inventory_date"].nunique()

demand_inventory["average_daily_sales"] = (
    demand_inventory["total_units_sold"] / days_in_period
)

demand_inventory["stock_cover_days"] = (
    demand_inventory["average_closing_stock"] /
    demand_inventory["average_daily_sales"].replace(0, float("nan"))
)

demand_inventory["received_to_sales_ratio"] = (
    demand_inventory["total_units_received"] /
    demand_inventory["total_units_sold"].replace(0, float("nan"))
)

demand_inventory["wastage_per_100_sold"] = (
    demand_inventory["total_wastage"] /
    demand_inventory["total_units_sold"].replace(0, float("nan"))
) * 100

demand_inventory["reorder_frequency"] = (
    demand_inventory["reorder_events"] / days_in_period
) * 100

demand_inventory["stock_received_minus_sold"] = (
    demand_inventory["total_units_received"] -
    demand_inventory["total_units_sold"]
)

# ------------------------------------------------------------
# 6.5 HIGHEST DEMAND PRODUCTS
# ------------------------------------------------------------

print("\n6.5 TOP 10 PRODUCTS BY CUSTOMER DEMAND")

top_demand = demand_inventory.sort_values(
    "total_units_sold", ascending=False
).head(10)

print(
    top_demand[
        [
            "product_name",
            "category",
            "total_units_sold",
            "total_revenue",
            "average_daily_sales"
        ]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 6.6 DEMAND VS REPLENISHMENT
# ------------------------------------------------------------

print("\n6.6 DEMAND VS STOCK RECEIVED")

print(
    top_demand[
        [
            "product_name",
            "total_units_sold",
            "total_units_received",
            "stock_received_minus_sold",
            "received_to_sales_ratio"
        ]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 6.7 STOCK COVER ANALYSIS
# ------------------------------------------------------------

print("\n6.7 PRODUCTS WITH LOWEST STOCK COVER")

lowest_stock_cover = demand_inventory.sort_values(
    "stock_cover_days", ascending=True
).head(10)

print(
    lowest_stock_cover[
        [
            "product_name",
            "total_units_sold",
            "average_daily_sales",
            "average_closing_stock",
            "stock_cover_days"
        ]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 6.8 WASTAGE RELATIVE TO DEMAND
# ------------------------------------------------------------

print("\n6.8 PRODUCTS WITH HIGHEST WASTAGE PER 100 UNITS SOLD")

highest_relative_wastage = demand_inventory.sort_values(
    "wastage_per_100_sold", ascending=False
).head(10)

print(
    highest_relative_wastage[
        [
            "product_name",
            "category",
            "total_units_sold",
            "total_wastage",
            "wastage_per_100_sold"
        ]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 6.9 REORDER FREQUENCY VS CUSTOMER DEMAND
# ------------------------------------------------------------

print("\n6.9 REORDER FREQUENCY VS DEMAND")

reorder_analysis = demand_inventory.sort_values(
    "reorder_events", ascending=False
).head(10)

print(
    reorder_analysis[
        [
            "product_name",
            "total_units_sold",
            "average_daily_sales",
            "reorder_events",
            "low_stock_days"
        ]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 6.10 GENERATE DEMAND AND INVENTORY CHARTS
# ------------------------------------------------------------

print("\n6.10 GENERATING DEMAND VS INVENTORY CHARTS")

# Chart 10: Demand vs stock received

chart_demand = top_demand.sort_values(
    "total_units_sold", ascending=True
)

y = range(len(chart_demand))
bar_height = 0.4

plt.figure(figsize=(12, 7))

plt.barh(
    [i - bar_height / 2 for i in y],
    chart_demand["total_units_sold"],
    height=bar_height,
    label="Units Sold"
)

plt.barh(
    [i + bar_height / 2 for i in y],
    chart_demand["total_units_received"],
    height=bar_height,
    label="Units Received"
)

plt.yticks(y, chart_demand["product_name"])

plt.title("Top 10 Products: Demand vs Stock Received")
plt.xlabel("Units")
plt.ylabel("Product")
plt.legend()
plt.tight_layout()

plt.savefig(
    CHART_DIR / "demand_vs_stock_received.png",
    dpi=300
)
plt.close()

# Chart 11: Average daily demand vs average closing stock

plt.figure(figsize=(10, 7))

plt.scatter(
    demand_inventory["average_daily_sales"],
    demand_inventory["average_closing_stock"]
)

for _, row in demand_inventory.iterrows():
    plt.annotate(
        row["product_name"],
        (
            row["average_daily_sales"],
            row["average_closing_stock"]
        ),
        fontsize=7,
        alpha=0.8
    )

plt.title("Average Daily Demand vs Average Closing Stock")
plt.xlabel("Average Daily Units Sold")
plt.ylabel("Average Closing Stock")
plt.grid(True)
plt.tight_layout()

plt.savefig(CHART_DIR / "demand_vs_average_stock.png", dpi=300)
plt.close()

# Chart 12: Wastage vs demand

plt.figure(figsize=(10, 7))

plt.scatter(
    demand_inventory["total_units_sold"],
    demand_inventory["total_wastage"]
)

for _, row in demand_inventory.iterrows():
    plt.annotate(
        row["product_name"],
        (row["total_units_sold"], row["total_wastage"]),
        fontsize=7,
        alpha=0.8
    )

plt.title("Product Demand vs Inventory Wastage")
plt.xlabel("Total Units Sold")
plt.ylabel("Total Units Wasted")
plt.grid(True)
plt.tight_layout()

plt.savefig(CHART_DIR / "demand_vs_wastage.png", dpi=300)
plt.close()

print("Three demand and inventory charts generated successfully.")

# ------------------------------------------------------------
# 6.11 FINAL ANALYTICAL SUMMARY
# ------------------------------------------------------------

print("\n6.11 ANALYTICAL SUMMARY")

highest_demand_product = demand_inventory.loc[
    demand_inventory["total_units_sold"].idxmax()
]

lowest_stock_product = demand_inventory.loc[
    demand_inventory["stock_cover_days"].idxmin()
]

highest_wastage_product = demand_inventory.loc[
    demand_inventory["wastage_per_100_sold"].idxmax()
]

print(
    f"Highest demand product: "
    f"{highest_demand_product['product_name']} "
    f"({highest_demand_product['total_units_sold']:,} units)"
)

print(
    f"Lowest stock cover: "
    f"{lowest_stock_product['product_name']} "
    f"({lowest_stock_product['stock_cover_days']:.2f} days)"
)

print(
    f"Highest relative wastage: "
    f"{highest_wastage_product['product_name']} "
    f"({highest_wastage_product['wastage_per_100_sold']:.2f} "
    f"units per 100 sold)"
)

print("\n" + "=" * 65)
print("SECTION 6 DEMAND VS INVENTORY ANALYSIS COMPLETED")
print("=" * 65)


# ============================================================
# 7. BUSINESS INSIGHTS AND RECOMMENDATIONS
# ============================================================

print("\n" + "=" * 65)
print("7. BUSINESS INSIGHTS AND RECOMMENDATIONS")
print("=" * 65)


# ------------------------------------------------------------
# 7.1 PREPARE PRODUCT PERFORMANCE DATA
# ------------------------------------------------------------

sales_product_summary = (
    sales_df.groupby("product_id")
    .agg(
        total_units_sold=("quantity", "sum"),
        total_revenue=("net_sales_gbp", "sum")
    )
    .reset_index()
)

inventory_product_summary = (
    inventory_df.groupby("product_id")
    .agg(
        total_wastage=("wastage_units", "sum"),
        average_closing_stock=("closing_stock_units", "mean"),
        reorder_events=("reorder_triggered", "sum"),
        low_stock_days=(
            "closing_stock_units",
            lambda x: (
                x <= inventory_df.loc[x.index, "reorder_level_units"]
            ).sum()
        ),
        zero_stock_days=(
            "closing_stock_units",
            lambda x: (x == 0).sum()
        )
    )
    .reset_index()
)

business_analysis = (
    products_df
    .merge(sales_product_summary, on="product_id", how="left")
    .merge(inventory_product_summary, on="product_id", how="left")
)

number_of_days = inventory_df["inventory_date"].nunique()

business_analysis["average_daily_sales"] = (
    business_analysis["total_units_sold"] / number_of_days
)

business_analysis["stock_cover_days"] = (
    business_analysis["average_closing_stock"] /
    business_analysis["average_daily_sales"]
)

business_analysis["wastage_per_100_sold"] = (
    business_analysis["total_wastage"] /
    business_analysis["total_units_sold"] * 100
)


# ------------------------------------------------------------
# 7.2 KEY BUSINESS FINDINGS
# ------------------------------------------------------------

print("\n7.2 KEY BUSINESS FINDINGS")

highest_demand = business_analysis.loc[
    business_analysis["total_units_sold"].idxmax()
]

highest_wastage = business_analysis.loc[
    business_analysis["wastage_per_100_sold"].idxmax()
]

lowest_stock_cover = business_analysis.loc[
    business_analysis["stock_cover_days"].idxmin()
]

most_reordered = business_analysis.loc[
    business_analysis["reorder_events"].idxmax()
]

total_reorder_events = inventory_df["reorder_triggered"].sum()

low_stock_product_days = (
    inventory_df["closing_stock_units"] <=
    inventory_df["reorder_level_units"]
).sum()

zero_stock_product_days = (
    inventory_df["closing_stock_units"] == 0
).sum()

print(
    f"Highest demand: {highest_demand['product_name']} "
    f"({highest_demand['total_units_sold']:,} units sold)"
)

print(
    f"Highest relative wastage: {highest_wastage['product_name']} "
    f"({highest_wastage['wastage_per_100_sold']:.2f} "
    f"units wasted per 100 sold)"
)

print(
    f"Lowest estimated stock cover: {lowest_stock_cover['product_name']} "
    f"({lowest_stock_cover['stock_cover_days']:.2f} days)"
)

print(
    f"Most frequently reordered: {most_reordered['product_name']} "
    f"({most_reordered['reorder_events']:.0f} events)"
)

print(f"Total reorder events: {total_reorder_events:,}")
print(f"Product-days at or below reorder level: {low_stock_product_days:,}")
print(f"Product-days with zero closing stock: {zero_stock_product_days:,}")


# ------------------------------------------------------------
# 7.3 BUSINESS RECOMMENDATIONS
# ------------------------------------------------------------

print("\n7.3 BUSINESS RECOMMENDATIONS")

print("""
RECOMMENDATION 1 – IMPROVE REPLENISHMENT PLANNING

Prioritise high-demand products such as Latte, Cappuccino and
Flat White when reviewing replenishment levels. Monitor daily
sales and stock cover to help maintain sufficient inventory.

RECOMMENDATION 2 – REDUCE PRODUCT WASTAGE

Review preparation quantities for products with high relative
wastage, particularly Chocolate Muffin. Adjust daily preparation
based on historical demand and monitor wastage trends.

RECOMMENDATION 3 – REVIEW REORDER THRESHOLDS

Review reorder levels and replenishment frequency for products
with frequent reorder events or repeated low-stock days.
Use demand patterns to support more appropriate stock levels.
""")


# ------------------------------------------------------------
# 7.4 ANALYTICAL LIMITATIONS
# ------------------------------------------------------------

print("\n7.4 ANALYTICAL LIMITATIONS")

print("""
1. The datasets are synthetic and may not represent actual
   coffee shop trading conditions.

2. Estimated gross profit excludes operating expenses such as
   rent, wages, utilities and other overheads.

3. Stock cover is an indicative measure based on average
   closing stock and average daily sales, not a live forecast.

4. Zero closing-stock records do not prove that no customer
   demand was lost. The dataset does not record attempted
   purchases or lost sales.

5. Annual stock received and units sold should not be compared
   in isolation because opening and closing inventory also
   affect stock balances.
""")


print("\n" + "=" * 65)
print("SECTION 7 BUSINESS INSIGHTS COMPLETED")
print("=" * 65)