import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Olist KPI Dashboard", layout="wide")

# -----------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------
# Create two tabs: one for delay delivery KPI, another for revenue & orders over time
tabs = st.tabs(["Delay Delivery Rate", "Revenue & Orders"])

# =================================================================
# Tab 1: Delay Delivery Rate (existing KPI)
# =================================================================
with tabs[0]:
    @st.cache_data
    def load_data():
        import os
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'olist.db')
        conn = sqlite3.connect(db_path)
        query = """
        SELECT 
            o.order_id,
            o.order_status,
            o.order_purchase_timestamp,
            o.order_approved_at,
            o.order_delivered_carrier_date,
            o.order_delivered_customer_date,
            o.order_estimated_delivery_date,
            c.customer_state,
            c.customer_city,
            s.seller_state,
            p.product_category_name
        FROM olist_orders_dataset o
        JOIN olist_customers_dataset c ON o.customer_id = c.customer_id
        LEFT JOIN olist_order_items_dataset oi ON o.order_id = oi.order_id
        LEFT JOIN olist_products_dataset p ON oi.product_id = p.product_id
        LEFT JOIN olist_sellers_dataset s ON oi.seller_id = s.seller_id
        WHERE o.order_status = 'delivered'
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert date columns to datetime
        date_cols = [
            'order_purchase_timestamp', 'order_approved_at', 
            'order_delivered_carrier_date', 'order_delivered_customer_date', 
            'order_estimated_delivery_date'
        ]
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
        return df
    
    st.title("KPI 1: Delay Delivery Rate")
    st.markdown("Monitoring Olist delivery delays.")
    
    df_raw = load_data()
    
    # --- FILTERS ---
    st.sidebar.header("Filters")
    
    # 1. Date Type Selector
    date_type_map = {
        "Purchase Date": "order_purchase_timestamp",
        "Approval Date": "order_approved_at",
        "Carrier Delivery Date": "order_delivered_carrier_date",
        "Customer Delivery Date": "order_delivered_customer_date",
        "Estimated Delivery Date": "order_estimated_delivery_date"
    }
    date_filter_type = st.sidebar.selectbox("Filter by which date?", list(date_type_map.keys()), key = "date_filter_type_2")
    date_col = date_type_map[date_filter_type]
    
    # 2. Date Range Filter
    min_date = df_raw[date_col].min()
    max_date = df_raw[date_col].max()
    
    if pd.notnull(min_date) and pd.notnull(max_date):
        start_date, end_date = st.sidebar.date_input(
            "Period",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
            key = "date_range_1"
        )
    else:
        start_date, end_date = None, None
    
    # 3. State Filter
    states = sorted(df_raw['customer_state'].dropna().unique())
    selected_states = st.sidebar.multiselect("State (Destination)", states, key="state_filter_2")
    
    # 4. City Filter
    if selected_states:
        cities = sorted(df_raw[df_raw['customer_state'].isin(selected_states)]['customer_city'].dropna().unique())
    else:
        cities = sorted(df_raw['customer_city'].dropna().unique())
    selected_cities = st.sidebar.multiselect("City (Destination)", cities, key="city_filter_2")
    
    # 5. Category Filter
    categories = sorted(df_raw['product_category_name'].dropna().unique())
    selected_categories = st.sidebar.multiselect("Product Category", categories, key = "category_filter_2")
    
    # --- APPLY FILTERS ---
    df_filtered = df_raw.copy()
    
    if start_date and end_date:
        mask = (df_filtered[date_col].dt.date >= start_date) & (df_filtered[date_col].dt.date <= end_date)
        df_filtered = df_filtered[mask]
    
    if selected_states:
        df_filtered = df_filtered[df_filtered['customer_state'].isin(selected_states)]
    
    if selected_cities:
        df_filtered = df_filtered[df_filtered['customer_city'].isin(selected_cities)]
    
    if selected_categories:
        df_filtered = df_filtered[df_filtered['product_category_name'].isin(selected_categories)]
    
    # Drop duplicates on order_id to calculate order-level KPIs correctly
    df_orders = df_filtered.drop_duplicates(subset=['order_id']).copy()
    
    # --- CALCULATE KPI ---
    total_orders = len(df_orders)
    
    if total_orders > 0:
        df_orders['is_delayed'] = df_orders['order_delivered_customer_date'] > df_orders['order_estimated_delivery_date']
        df_orders['delay_days'] = (df_orders['order_delivered_customer_date'] - df_orders['order_estimated_delivery_date']).dt.days
        
        delayed_orders = df_orders['is_delayed'].sum()
        on_time_orders = total_orders - delayed_orders
        otdr = (on_time_orders / total_orders) * 100
        delay_rate = (delayed_orders / total_orders) * 100
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Orders", f"{total_orders:,}")
        col2.metric("On-Time Delivery Rate", f"{otdr:.2f}%")
        col3.metric("Delay Delivery Rate", f"{delay_rate:.2f}%")
        
        st.markdown("### Delayed Orders Sample")
        delayed_df = df_orders[df_orders['is_delayed']].sort_values(by='delay_days', ascending=False)
        st.dataframe(delayed_df[['order_id', 'customer_state', 'seller_state', 'customer_city', 'product_category_name', 'order_estimated_delivery_date', 'order_delivered_customer_date', 'delay_days']].head(50))
        
        st.markdown("---")
        st.markdown("### Top Delayed States Map")
        
        map_view = st.radio("Show delays by:", ("Customer State (Destination)", "Seller State (Origin)"), horizontal=True)
        state_col = 'customer_state' if map_view == "Customer State (Destination)" else 'seller_state'
        
        # Calculate total orders per state
        total_counts = df_orders[state_col].dropna().value_counts().to_dict()
        # Calculate delayed orders per state
        delays_counts = delayed_df[state_col].dropna().value_counts().to_dict()
        # Compute delay rate (%) per state, handling division by zero
        all_states = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
        'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
        state_delays = pd.DataFrame({'state': all_states})
        # Number of delayed orders per state
        state_delays['delays'] = state_delays['state'].apply(
            lambda s: delays_counts.get(s, 0)
        )

        # Identify the top 3 states by number of delayed orders
        top_3_states = (
            state_delays[state_delays['delays'] > 0]
            .nlargest(3, 'delays')['state']
            .tolist()
        )

        

        
        def get_color(row):
            if row['delays'] == 0:
                return 'No Data'
            elif row['state'] in top_3_states:
                return 'Top 3'
            else:
                return 'Others'
        
        state_delays['color'] = state_delays.apply(get_color, axis=1)
        # format delayed order count for hover
        def format_delayed(state):
            cnt = delays_counts.get(state, 0)
            return str(int(cnt)) if cnt > 0 else 'no data'
        state_delays['delayed_orders'] = state_delays['state'].apply(format_delayed)
        
        import json
        import os
        import plotly.express as px
        
        geojson_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'brazil_states.geojson')
        
        try:
            with open(geojson_path) as f:
                brazil_geojson = json.load(f)
                
            fig = px.choropleth(
                state_delays,
                geojson=brazil_geojson,
                locations='state',
                featureidkey='properties.sigla',
                color='color',
                color_discrete_map={'Top 3': 'black', 'Others': 'white', 'No Data': 'lightgray'},
                hover_name='state',
                hover_data={'delayed_orders': True},
                projection="mercator"
            )
            
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0},
                geo=dict(bgcolor='rgba(0,0,0,0)', showcoastlines=False),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Map could not be rendered. Error: {e}")
    else:
        st.warning("No orders found with the selected filters.")

# =================================================================
# Tab 2: Revenue & Orders over Time
# =================================================================
with tabs[1]:
    @st.cache_data
    def load_revenue_data(df_filtered):
        import os

        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data',
            'olist.db'
        )

        conn = sqlite3.connect(db_path)

        order_ids = tuple(df_filtered['order_id'].unique())

        if not order_ids:
            conn.close()
            return pd.DataFrame()

        placeholders = ','.join(['?'] * len(order_ids))

        query = f"""
            SELECT 
                order_id,
                payment_value
            FROM olist_order_payments_dataset
            WHERE order_id IN ({placeholders})
            """

        payments = pd.read_sql_query(
            query,
            conn,
            params=list(order_ids)
        )

        conn.close()

        df = df_filtered[['order_id', 'order_purchase_timestamp']].drop_duplicates(
            subset=['order_id']
        )

        df = df.merge(payments, on='order_id', how='left')

        df['payment_value'] = df['payment_value'].fillna(0)

        daily = df.groupby(
            df['order_purchase_timestamp'].dt.date
        ).agg(
            revenue=('payment_value', 'sum'),
            orders=('order_id', 'nunique')
        ).reset_index()

        daily['date'] = pd.to_datetime(daily['order_purchase_timestamp'])

        daily['revenue'] = daily['revenue'].cumsum()
        daily['orders'] = daily['orders'].cumsum()

        return daily
    
    rev_df = load_revenue_data(df_filtered)
    if not rev_df.empty:
        # Cumulative Revenue
        fig_revenue = px.line(
            rev_df,
            x='date',
            y='revenue',
            labels={'date': 'Date', 'revenue': 'Cumulative Revenue'},
            title='Cumulative Revenue'
        )

        fig_revenue.update_traces(
            hovertemplate='%{x|%Y-%m-%d}<br>Revenue: R$ %{y:,.2f}'
        )

        st.plotly_chart(fig_revenue, use_container_width=True)

        # Cumulative Orders
        fig_orders = px.line(
            rev_df,
            x='date',
            y='orders',
            labels={'date': 'Date', 'orders': 'Cumulative Orders'},
            title='Cumulative Orders'
        )

        fig_orders.update_traces(
            hovertemplate='%{x|%Y-%m-%d}<br>Orders: %{y:,.0f}'
        )

        st.plotly_chart(fig_orders, use_container_width=True)
    else:
        st.info('No revenue data available for the selected period.')

