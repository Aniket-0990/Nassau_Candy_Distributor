# ============================================================
# NASSAU CANDY DISTRIBUTOR
# Data Science Internship Project
# Route Efficiency & Distribution Analysis Dashboard
# ============================================================

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------
# PAGE CONFIG + STYLE
# ------------------------------------------------------------
st.set_page_config(page_title="Nassau Candy Analytics", page_icon="🍬",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
div[data-testid="stMetric"] {
    background: rgba(128,128,128,0.08); border: 1px solid rgba(128,128,128,0.25);
    border-radius: 12px; padding: 14px 18px;
}
</style>
""", unsafe_allow_html=True)

FILES = {
    "main": "Nassau_Candy_Cleaned.csv",
    "route": "Route_Analysis.csv",
    "factory": "Factory_Analysis.csv",
    "state": "State_Bottleneck_Analysis.csv",
}

US_STATES = dict(zip(
    "Alabama,Alaska,Arizona,Arkansas,California,Colorado,Connecticut,Delaware,Florida,"
    "Georgia,Hawaii,Idaho,Illinois,Indiana,Iowa,Kansas,Kentucky,Louisiana,Maine,Maryland,"
    "Massachusetts,Michigan,Minnesota,Mississippi,Missouri,Montana,Nebraska,Nevada,"
    "New Hampshire,New Jersey,New Mexico,New York,North Carolina,North Dakota,Ohio,"
    "Oklahoma,Oregon,Pennsylvania,Rhode Island,South Carolina,South Dakota,Tennessee,"
    "Texas,Utah,Vermont,Virginia,Washington,West Virginia,Wisconsin,Wyoming".split(","),
    "AL,AK,AZ,AR,CA,CO,CT,DE,FL,GA,HI,ID,IL,IN,IA,KS,KY,LA,ME,MD,MA,MI,MN,MS,MO,MT,NE,NV,"
    "NH,NJ,NM,NY,NC,ND,OH,OK,OR,PA,RI,SC,SD,TN,TX,UT,VT,VA,WA,WV,WI,WY".split(","),
))


# ------------------------------------------------------------
# DATA LOADING (all four files)
# ------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(FILES["main"])
    for col in ("Order Date", "Ship Date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return (df, pd.read_csv(FILES["route"]),
            pd.read_csv(FILES["factory"]), pd.read_csv(FILES["state"]))


try:
    df, route_ref, factory_ref, state_ref = load_data()
except FileNotFoundError:
    st.error("A required CSV file was not found. Place these files next to app.py:")
    st.code("\n".join(FILES.values()))
    st.stop()


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
money = lambda v: f"${v:,.2f}"
number = lambda v: f"{v:,.0f}"


def summarize(data, by):
    """Group data and compute the standard set of business metrics."""
    out = data.groupby(by, as_index=False).agg(
        Shipments=("Order ID", "count"),
        Orders=("Order ID", "nunique"),
        Units=("Units", "sum"),
        Sales=("Sales", "sum"),
        Cost=("Cost", "sum"),
        Gross_Profit=("Gross Profit", "sum"),
        Avg_Lead_Time=("Shipping Lead Time", "mean"),
        Median_Lead_Time=("Shipping Lead Time", "median"),
    )
    out["Profit Margin %"] = np.where(out["Sales"] != 0,
                                      out["Gross_Profit"] / out["Sales"] * 100, 0)
    return out.round(2)


def hbar(data, x, y, title, top=10, height=450, color=None):
    """Horizontal top-N bar chart."""
    d = data.sort_values(x, ascending=False).head(top)
    fig = px.bar(d, x=x, y=y, orientation="h", title=title, color=color,
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(height=height, yaxis=dict(categoryorder="total ascending"),
                      margin=dict(l=10, r=10, t=50, b=10))
    return fig


def show(fig):
    st.plotly_chart(fig, use_container_width=True)


def table(data, name, key):
    """Dataframe + CSV download button."""
    st.dataframe(data, use_container_width=True, hide_index=True)
    st.download_button("⬇ Download CSV", data.to_csv(index=False).encode("utf-8"),
                       file_name=name, mime="text/csv", key=key)


# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------
st.sidebar.title("🍬 Dashboard Controls")


def multi(label, column, expanded=True):
    opts = sorted(df[column].dropna().unique().tolist())
    with st.sidebar.expander(label, expanded=expanded):
        return st.multiselect(label, opts, default=opts, label_visibility="collapsed")


sel_factory = multi("Factory", "Factory")
sel_region = multi("Region", "Region")
sel_mode = multi("Ship Mode", "Ship Mode")
sel_product = multi("Product", "Product Name", expanded=False)

mask = (df["Factory"].isin(sel_factory) & df["Region"].isin(sel_region)
        & df["Ship Mode"].isin(sel_mode) & df["Product Name"].isin(sel_product))

if "Order Date" in df.columns and df["Order Date"].notna().any():
    dmin, dmax = df["Order Date"].min().date(), df["Order Date"].max().date()
    picked = st.sidebar.date_input("Order Date Range", (dmin, dmax),
                                   min_value=dmin, max_value=dmax)
    if isinstance(picked, tuple) and len(picked) == 2:
        mask &= df["Order Date"].between(pd.Timestamp(picked[0]), pd.Timestamp(picked[1]))

fdf = df[mask].copy()

st.sidebar.markdown("---")
st.sidebar.info(
    "**Data Quality Note:** The dataset has unusually large gaps between Order Date "
    "and Ship Date. The calculated lead time should not be treated as a validated "
    "standard delivery duration."
)

# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------
st.title("🍬 Nassau Candy Distribution Analytics")
st.caption("Sales, profitability, products, factories, regions and distribution routes.")

if fdf.empty:
    st.warning("No records match the selected filters. Adjust the sidebar controls.")
    st.stop()

tabs = st.tabs(["📊 Executive", "🚚 Routes", "🗺️ Geography", "📦 Shipping",
                "🏭 Products & Factories", "🔎 Order Drill-Down", "📁 Reference Data"])

# ============================================================
# TAB 1 - EXECUTIVE
# ============================================================
with tabs[0]:
    sales, profit = fdf["Sales"].sum(), fdf["Gross Profit"].sum()
    margin = profit / sales * 100 if sales else 0

    c = st.columns(6)
    c[0].metric("Total Sales", money(sales))
    c[1].metric("Gross Profit", money(profit))
    c[2].metric("Profit Margin", f"{margin:.2f}%")
    c[3].metric("Orders", number(fdf["Order ID"].nunique()))
    c[4].metric("Units", number(fdf["Units"].sum()))
    c[5].metric("Avg Lead Time", f"{fdf['Shipping Lead Time'].mean():.0f} days")

    st.markdown("---")
    left, right = st.columns(2)
    with left:
        show(hbar(summarize(fdf, "Product Name"), "Sales", "Product Name",
                  "Top 10 Products by Sales", height=480))
    with right:
        reg = summarize(fdf, "Region")
        fig = px.bar(reg, x="Region", y="Sales", color="Region", text_auto=".3s",
                     title="Sales by Region", color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(height=480, showlegend=False)
        show(fig)

    fac = summarize(fdf, "Factory")
    fig = px.bar(fac, x="Factory", y=["Sales", "Gross_Profit"], barmode="group",
                 title="Sales vs Gross Profit by Factory", text_auto=".2s")
    fig.update_layout(height=420)
    show(fig)

    if fdf["Order Date"].notna().any():
        monthly = (fdf.dropna(subset=["Order Date"])
                   .set_index("Order Date")[["Sales", "Gross Profit"]]
                   .resample("MS").sum().reset_index())
        show(px.line(monthly, x="Order Date", y=["Sales", "Gross Profit"],
                     markers=True, title="Monthly Sales & Gross Profit Trend"))

# ============================================================
# TAB 2 - ROUTES (Factory -> Region)
# ============================================================
with tabs[1]:
    st.subheader("Route Efficiency")
    routes = summarize(fdf, ["Factory", "Region"])
    routes["Route"] = routes["Factory"] + " → " + routes["Region"]

    c = st.columns(3)
    c[0].metric("Routes", number(len(routes)))
    c[1].metric("Total Shipments", number(routes["Shipments"].sum()))
    c[2].metric("Avg Lead Time", f"{routes['Avg_Lead_Time'].mean():.0f} days")

    fig = px.scatter(routes, x="Avg_Lead_Time", y="Shipments", size="Sales",
                     color="Region", hover_name="Route",
                     hover_data=["Orders", "Gross_Profit", "Median_Lead_Time", "Profit Margin %"],
                     title="Route Volume vs Calculated Lead Time (bubble = sales)")
    fig.update_layout(height=550)
    show(fig)

    a, b = st.columns(2)
    with a:
        show(hbar(routes, "Shipments", "Route", "Busiest Routes", top=12, height=480))
    with b:
        slow = routes.sort_values("Avg_Lead_Time", ascending=False).head(12)
        show(hbar(slow, "Avg_Lead_Time", "Route", "Slowest Routes (Avg Lead Time)",
                  top=12, height=480))

    table(routes.drop(columns="Route"), "filtered_route_analysis.csv", "dl_route")

# ============================================================
# TAB 3 - GEOGRAPHY
# ============================================================
with tabs[2]:
    st.subheader("Geographic Analysis")
    states = summarize(fdf, "State/Province")

    a, b = st.columns(2)
    with a:
        show(hbar(states, "Sales", "State/Province", "Top 15 States by Sales",
                  top=15, height=550))
    with b:
        show(hbar(states, "Avg_Lead_Time", "State/Province",
                  "Top 15 States by Avg Calculated Date Gap", top=15, height=550))

    metric = st.radio("Map metric", ["Sales", "Gross_Profit", "Shipments", "Avg_Lead_Time"],
                      horizontal=True)
    states["Code"] = states["State/Province"].map(US_STATES)
    mapped = states.dropna(subset=["Code"])
    if mapped.empty:
        st.info("State names could not be matched to US state abbreviations.")
    else:
        fig = px.choropleth(mapped, locations="Code", locationmode="USA-states",
                            color=metric, scope="usa", hover_name="State/Province",
                            hover_data=["Shipments", "Sales", "Gross_Profit", "Avg_Lead_Time"],
                            color_continuous_scale="Blues", title=f"{metric} by US State")
        fig.update_layout(height=550, margin=dict(l=0, r=0, t=50, b=0))
        show(fig)

    table(states.drop(columns="Code").sort_values("Sales", ascending=False),
          "state_analysis.csv", "dl_state")

# ============================================================
# TAB 4 - SHIPPING
# ============================================================
with tabs[3]:
    st.subheader("Shipping Analysis")
    ship = summarize(fdf, "Ship Mode")

    a, b, c = st.columns(3)
    for col, y, title, fmt in [(a, "Shipments", "Shipments by Ship Mode", True),
                               (b, "Avg_Lead_Time", "Avg Lead Time by Ship Mode", ".1f"),
                               (c, "Sales", "Sales by Ship Mode", ".3s")]:
        with col:
            fig = px.bar(ship, x="Ship Mode", y=y, color="Ship Mode", text_auto=fmt,
                         title=title, color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(showlegend=False, height=380)
            show(fig)

    fig = px.box(fdf, x="Ship Mode", y="Shipping Lead Time", color="Ship Mode",
                 title="Lead Time Distribution by Ship Mode")
    fig.update_layout(showlegend=False, height=450)
    show(fig)

    table(ship, "ship_mode_summary.csv", "dl_ship")

# ============================================================
# TAB 5 - PRODUCTS & FACTORIES
# ============================================================
with tabs[4]:
    st.subheader("Product Performance")
    prod = summarize(fdf, "Product Name")

    a, b = st.columns(2)
    with a:
        show(hbar(prod, "Sales", "Product Name", "Top Products by Sales", top=15, height=550))
    with b:
        show(hbar(prod, "Gross_Profit", "Product Name", "Top Products by Gross Profit",
                  top=15, height=550))

    fig = px.scatter(prod, x="Sales", y="Profit Margin %", size="Units",
                     hover_name="Product Name", title="Sales vs Profit Margin (bubble = units)")
    fig.update_layout(height=450)
    show(fig)

    st.subheader("Factory Performance")
    fac = summarize(fdf, "Factory").sort_values("Sales", ascending=False)
    fig = px.bar(fac, x="Factory", y="Sales", color="Factory", title="Sales by Factory",
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(showlegend=False, height=420)
    show(fig)
    table(fac, "factory_summary.csv", "dl_factory")

# ============================================================
# TAB 6 - ORDER DRILL-DOWN
# ============================================================
with tabs[5]:
    st.subheader("Order-Level Drill-Down")
    order_ids = sorted(fdf["Order ID"].dropna().unique().tolist())
    chosen = st.selectbox("Select Order ID", ["All Orders"] + order_ids)
    od = fdf if chosen == "All Orders" else fdf[fdf["Order ID"] == chosen]

    c = st.columns(4)
    c[0].metric("Records", number(len(od)))
    c[1].metric("Sales", money(od["Sales"].sum()))
    c[2].metric("Gross Profit", money(od["Gross Profit"].sum()))
    c[3].metric("Units", number(od["Units"].sum()))

    wanted = ["Order ID", "Order Date", "Ship Date", "Shipping Lead Time", "Ship Mode",
              "Product Name", "Factory", "Region", "State/Province",
              "Units", "Sales", "Cost", "Gross Profit"]
    table(od[[col for col in wanted if col in od.columns]], "order_details.csv", "dl_order")

# ============================================================
# TAB 7 - REFERENCE DATA (the three pre-computed CSV files)
# ============================================================
with tabs[6]:
    st.subheader("Pre-computed Analysis Files")
    st.caption("These files are not affected by the sidebar filters.")

    def reference_section(title, frame, key):
        """Show a pre-computed file with an auto-built chart (works with any columns)."""
        st.markdown(f"#### {title}")
        text_cols = frame.select_dtypes(exclude="number").columns.tolist()
        num_cols = frame.select_dtypes(include="number").columns.tolist()
        if text_cols and num_cols:
            metric = st.selectbox("Metric to chart", num_cols, key=f"{key}_metric")
            view = frame.copy()
            view["Label"] = view[text_cols].astype(str).agg(" → ".join, axis=1)
            show(hbar(view, metric, "Label", f"Top 15 by {metric}", top=15, height=500))
        table(frame, f"{key}.csv", f"dl_ref_{key}")

    reference_section("Route Analysis", route_ref, "route_analysis")
    st.markdown("---")
    reference_section("Factory Analysis", factory_ref, "factory_analysis")
    st.markdown("---")
    reference_section("State Bottleneck Analysis", state_ref, "state_bottleneck")

# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------
st.markdown("---")
st.caption("Nassau Candy Distributor · Data Science Internship Project")
