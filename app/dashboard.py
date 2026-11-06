import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px

# ---------------------------------------------------------
# Page Configuration & Header
# ---------------------------------------------------------
st.set_page_config(
    page_title="European & Global Coffee Trade Analysis",
    page_icon="☕",
    layout="wide",
)

st.title("☕ European & Global Coffee Trade Analysis")
st.caption("FAOSTAT Green Coffee (`item_code = 656`, Unit: Tonnes) | 10-Year Trade Balances")

# ---------------------------------------------------------
# Database Engine (Container-Aware via .env)
# ---------------------------------------------------------
@st.cache_resource
def get_engine():
    user = os.getenv("MYSQL_USER", "team_user")
    password = os.getenv("MYSQL_PASSWORD", "secret")
    host = os.getenv("MYSQL_HOST", "db")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "coffee_trade")
    
    db_url = os.getenv("DATABASE_URL", f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
    return create_engine(db_url)

engine = get_engine()

# ---------------------------------------------------------
# Dynamic Parameter & Mapping
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_latest_year():
    query = """
    SELECT MAX(year) AS latest_year
    FROM raw_trade
    WHERE item = 'Coffee, green'
      AND element_code IN (5610, 5910)
      AND unit = 't';
    """
    with engine.connect() as conn:
        res = conn.execute(text(query)).scalar()
    return int(res) if res else 2023

EUROPE_M49_CODES = (
    112, 100, 203, 348, 616, 498, 642, 643, 703, 804,
    248, 208, 233, 234, 246, 831, 352, 372, 833, 832,
    428, 440, 578, 744, 752, 826,
    8, 20, 70, 191, 292, 300, 336, 380, 470, 499,
    807, 620, 674, 688, 705, 724,
    40, 56, 250, 276, 438, 442, 492, 528, 756
)

# ---------------------------------------------------------
# Query 1: Giulia's European Top 5 Net Exporters & Importers
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_european_rankings(latest_yr):
    codes_str = ", ".join(map(str, EUROPE_M49_CODES))
    query = f"""
    WITH country_totals AS (
        SELECT
            area,
            SUM(CASE WHEN element_code = 5910 THEN value ELSE 0 END) AS exports_t,
            SUM(CASE WHEN element_code = 5610 THEN value ELSE 0 END) AS imports_t
        FROM raw_trade
        WHERE item = 'Coffee, green'
          AND unit = 't'
          AND element_code IN (5610, 5910)
          AND year BETWEEN {latest_yr - 9} AND {latest_yr}
          AND CAST(REPLACE(area_code_m49, CHAR(39), '') AS UNSIGNED) IN ({codes_str})
        GROUP BY area
    ),
    ranked AS (
        SELECT
            area,
            exports_t - imports_t AS net_trade_t,
            ROW_NUMBER() OVER (ORDER BY exports_t - imports_t DESC) AS export_rank,
            ROW_NUMBER() OVER (ORDER BY exports_t - imports_t ASC) AS import_rank
        FROM country_totals
    )
    SELECT 'Exporter' AS category, export_rank AS position, area, ROUND(net_trade_t, 2) AS net_trade_t
    FROM ranked
    WHERE export_rank <= 5 AND net_trade_t > 0
    UNION ALL
    SELECT 'Importer' AS category, import_rank AS position, area, ROUND(net_trade_t, 2) AS net_trade_t
    FROM ranked
    WHERE import_rank <= 5 AND net_trade_t < 0
    ORDER BY category, position;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

# ---------------------------------------------------------
# Query 2: Serena's Worldwide Top 5 Net Exporters & Importers
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_world_rankings(latest_yr):
    query = f"""
    WITH country_totals AS (
        SELECT
            area,
            SUM(CASE WHEN element_code = 5910 THEN value ELSE 0 END) AS exports_t,
            SUM(CASE WHEN element_code = 5610 THEN value ELSE 0 END) AS imports_t
        FROM raw_trade
        WHERE item = 'Coffee, green'
          AND unit = 't'
          AND element_code IN (5610, 5910)
          AND year BETWEEN {latest_yr - 9} AND {latest_yr}
          AND area_code < 5000
          AND area_code NOT IN (265, 351)
        GROUP BY area
    ),
    ranked AS (
        SELECT
            area,
            exports_t - imports_t AS net_trade_t,
            ROW_NUMBER() OVER (ORDER BY exports_t - imports_t DESC) AS export_rank,
            ROW_NUMBER() OVER (ORDER BY exports_t - imports_t ASC) AS import_rank
        FROM country_totals
    )
    SELECT 'Exporter' AS category, export_rank AS position, area, ROUND(net_trade_t, 2) AS net_trade_t
    FROM ranked
    WHERE export_rank <= 5 AND net_trade_t > 0
    UNION ALL
    SELECT 'Importer' AS category, import_rank AS position, area, ROUND(net_trade_t, 2) AS net_trade_t
    FROM ranked
    WHERE import_rank <= 5 AND net_trade_t < 0
    ORDER BY category, position;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

# ---------------------------------------------------------
# Query 3: Giulia's 10-Year European Trajectory
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_european_trajectory(latest_yr):
    formatted_codes = ", ".join(f"'{str(c).zfill(3)}'" for c in EUROPE_M49_CODES)
    query = f"""
    SELECT
        area,
        year,
        SUM(CASE WHEN element_code = 5910 THEN value ELSE 0 END) AS exports_t,
        SUM(CASE WHEN element_code = 5610 THEN value ELSE 0 END) AS imports_t,
        SUM(CASE
            WHEN element_code = 5910 THEN value
            WHEN element_code = 5610 THEN -value
            ELSE 0
        END) AS net_trade_t
    FROM raw_trade
    WHERE item = 'Coffee, green'
      AND unit = 't'
      AND element_code IN (5610, 5910)
      AND year BETWEEN {latest_yr - 9} AND {latest_yr}
      AND REPLACE(area_code_m49, CHAR(39), '') IN ({formatted_codes})
    GROUP BY area, year
    ORDER BY area, year;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


# ---------------------------------------------------------
# Query 4: World 10-Year Trajectory
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_world_trajectory(latest_yr):
    query = f"""
    SELECT
        area,
        year,
        SUM(CASE WHEN element_code = 5910
                 THEN value ELSE 0 END) AS exports_t,
        SUM(CASE WHEN element_code = 5610
                 THEN value ELSE 0 END) AS imports_t,
        SUM(CASE
            WHEN element_code = 5910 THEN value
            WHEN element_code = 5610 THEN -value
            ELSE 0
        END) AS net_trade_t

    FROM raw_trade

    WHERE item = 'Coffee, green'
      AND unit = 't'
      AND element_code IN (5610, 5910)
      AND year BETWEEN {latest_yr - 9} AND {latest_yr}
      AND area_code < 5000
      AND area_code NOT IN (265, 351)

    GROUP BY area, year
    ORDER BY area, year;
    """

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

# ---------------------------------------------------------
# Application UI & Views
# ---------------------------------------------------------
try:
    latest_year = get_latest_year()
    st.sidebar.header("Navigation & Scope")
    st.sidebar.info(f"**Ten-Year Window:** {latest_year - 9} – {latest_year}")
    scope = st.sidebar.radio("Ranking Scope", ["Europe ", "World "])

    st.subheader(f"📊 Top 5 Net Exporters & Importers ({latest_year - 9} – {latest_year})")

    df_rankings = get_european_rankings(latest_year) if "Europe" in scope else get_world_rankings(latest_year)

    if not df_rankings.empty:
        exporters = df_rankings[df_rankings['category'] == 'Exporter']
        importers = df_rankings[df_rankings['category'] == 'Importer']

        col1, col2 = st.columns(2)
        with col1:
            st.success("🟢 **Top 5 Net Exporters**")
            st.dataframe(exporters[['position', 'area', 'net_trade_t']], hide_index=True, use_container_width=True)
            fig_exp = px.bar(
                exporters, x='area', y='net_trade_t',
                labels={'area': 'Country', 'net_trade_t': 'Net Exports (Tonnes)'},
                color_discrete_sequence=['#2E7D32']
            )
            st.plotly_chart(fig_exp, use_container_width=True)

        with col2:
            st.error("🔴 **Top 5 Net Importers**")
            st.dataframe(importers[['position', 'area', 'net_trade_t']], hide_index=True, use_container_width=True)
            fig_imp = px.bar(
                importers, x='area', y='net_trade_t',
                labels={'area': 'Country', 'net_trade_t': 'Net Importers (Tonnes)'},
                color_discrete_sequence=['#C62828']
            )
            st.plotly_chart(fig_imp, use_container_width=True)
    else:
        st.warning("No trade records found. Make sure the database is populated.")

    # ---------------------------------------------------------
    # Trajectory Analysis
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("📈 10-Year Trade Trajectory")

    df_traj = (
        get_european_trajectory(latest_year)
        if "Europe" in scope
        else get_world_trajectory(latest_year)
    )

    if not df_traj.empty:
        all_countries = sorted(df_traj['area'].unique().tolist())

        if "Europe" in scope:
            defaults = ['Germany', 'Italy', 'France', 'Spain', 'Netherlands']
        else:
            defaults = ['Brazil', 'Vietnam', 'Colombia', 'Germany', 'Italy']

        default_countries = [c for c in defaults if c in all_countries]

        if not default_countries and len(all_countries) > 0:
            default_countries = all_countries[:3]

        selected_countries = st.multiselect(
            "Select Countries to Compare:",
            options=all_countries,
            default=default_countries
        )

        if selected_countries:
            filtered_traj = df_traj[df_traj['area'].isin(selected_countries)]
            fig_line = px.line(
                filtered_traj, x='year', y='net_trade_t', color='area',
                markers=True,
                labels={'year': 'Year', 'net_trade_t': 'Net Trade (Tonnes)', 'area': 'Country'},
                title="Historical Net Trade Trajectory (Exports - Imports)"
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
            with st.expander("View Underlying Trajectory Data"):
                st.dataframe(filtered_traj, use_container_width=True)
    else:
        st.info("No trajectory data available.")

except Exception as e:
    st.error(f"Error querying database: {e}")
    st.info("Ensure the `db` service is healthy and `raw_trade` table is populated.")