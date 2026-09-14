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
        # use delayed order counts per state
        state_delays['delays'] = state_delays['state'].apply(lambda s: (delays_counts.get(s, 0) / total_counts.get(s, 0) * 100) if total_counts.get(s, 0) > 0 else 0)
        # Identify top 3 states with delays
        top_3_states = state_delays[state_delays['delays'] > 0].head(3)['state'].tolist()

        

        
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
        
        # State coordinates for the dots
        state_coords = {
            'AC': (-9.02, -70.81), 'AL': (-9.53, -36.75), 'AM': (-3.41, -65.85), 'AP': (1.41, -51.77),
            'BA': (-12.57, -41.70), 'CE': (-5.20, -39.53), 'DF': (-15.79, -47.86), 'ES': (-19.18, -40.30),
            'GO': (-15.82, -49.83), 'MA': (-4.96, -45.27), 'MG': (-18.51, -44.55), 'MS': (-20.77, -54.78),
            'MT': (-12.68, -56.92), 'PA': (-1.99, -54.93), 'PB': (-7.23, -36.78), 'PE': (-8.81, -36.95),
            'PI': (-7.71, -42.72), 'PR': (-25.25, -52.02), 'RJ': (-22.90, -43.20), 'RN': (-5.79, -36.56),
            'RO': (-11.50, -63.58), 'RR': (2.73, -62.07), 'RS': (-30.03, -51.21), 'SC': (-27.24, -50.21),
            'SE': (-10.57, -37.38), 'SP': (-23.55, -46.63), 'TO': (-10.17, -48.29)
        }
        
        state_delays['lat'] = state_delays['state'].map(lambda x: state_coords.get(x, (0,0))[0])
        state_delays['lon'] = state_delays['state'].map(lambda x: state_coords.get(x, (0,0))[1])
        
        import json
        import os
        import plotly.express as px
        import plotly.graph_objects as go
        
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
                hover_data={'delayed_orders': True, 'delays': False, 'lat': False, 'lon': False, 'color': False, 'state': False},
                projection="mercator"
            )
            
            top_3_df = state_delays[state_delays['color'] == 'Top 3']
            fig.add_trace(go.Scattergeo(
                lon=top_3_df['lon'],
                lat=top_3_df['lat'],
                mode='markers+text',
                text=top_3_df['delays'].astype(str),
                textposition="top center",
                textfont=dict(color='red', size=14, weight='bold'),
                marker=dict(size=10, color='red'),
                name='Delayed Orders',
                hoverinfo='skip'
            ))
            
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
    def load_revenue_data():
        import os
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'olist.db')
        conn = sqlite3.connect(db_path)
        query = """
        SELECT 
            o.order_id,
            o.order_purchase_timestamp,
            p.payment_value
        FROM olist_orders_dataset o
        JOIN olist_order_payments_dataset p ON o.order_id = p.order_id
        WHERE o.order_status = 'delivered'
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
        daily = df.groupby(df['order_purchase_timestamp'].dt.date).agg(
            revenue=('payment_value', 'sum'),
            orders=('order_id', 'nunique')
        ).reset_index()
        daily['date'] = pd.to_datetime(daily['order_purchase_timestamp'])
        return daily
    
    rev_df = load_revenue_data()
    if not rev_df.empty:
        rev_long = rev_df.melt(id_vars='date', value_vars=['revenue', 'orders'], var_name='Metric', value_name='Value')
        fig = px.line(
            rev_long,
            x='date',
            y='Value',
            color='Metric',
            labels={'date': 'Date', 'Value': 'Value', 'Metric': 'Metric'},
            title='Daily Revenue and Orders',
            hover_data={'Value': ':.2f'}
        )
        fig.update_traces(hovertemplate='%{x|%Y-%m-%d}<br>%{y:,.2f}')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('No revenue data available for the selected period.')

# Duplicate code removed to avoid widget ID conflicts


st.set_page_config(page_title="Olist KPI Dashboard", layout="wide")

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
date_filter_type = st.sidebar.selectbox("Filter by which date?", list(date_type_map.keys()), key = "date_filter_type_1")
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
        key = "date_range_2"
    )
else:
    start_date, end_date = None, None

# 3. State Filter
states = sorted(df_raw['customer_state'].dropna().unique())
selected_states = st.sidebar.multiselect("State (Destination)", states, key = "state_filter_1")

# 4. City Filter
if selected_states:
    cities = sorted(df_raw[df_raw['customer_state'].isin(selected_states)]['customer_city'].dropna().unique())
else:
    cities = sorted(df_raw['customer_city'].dropna().unique())
selected_cities = st.sidebar.multiselect("City (Destination)", cities, key = "city_filter_1")

# 5. Category Filter
categories = sorted(df_raw['product_category_name'].dropna().unique())
selected_categories = st.sidebar.multiselect("Product Category", categories, key = "category_filter_1")

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
# (Because an order might have multiple items/categories)
df_orders = df_filtered.drop_duplicates(subset=['order_id']).copy()

# --- CALCULATE KPI ---
total_orders = len(df_orders)

if total_orders > 0:
    # Delayed if customer delivery date is greater than estimated date
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
        
    all_states = [
        'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
        'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 
        'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO'
    ]
    
    delays_counts = delayed_df[state_col].value_counts().to_dict()
    
    state_delays = pd.DataFrame({'state': all_states})
    state_delays['delays'] = state_delays['state'].map(lambda x: delays_counts.get(x, 0))
    state_delays = state_delays.sort_values(by='delays', ascending=False)
    
    top_3_states = state_delays[state_delays['delays'] > 0].head(3)['state'].tolist()
    
    def get_color(row):
        if row['delays'] == 0:
            return 'No Data'
        elif row['state'] in top_3_states:
            return 'Top 3'
        else:
            return 'Others'
            
    state_delays['color'] = state_delays.apply(get_color, axis=1)
    state_delays['delayed_orders'] = state_delays['delays'].apply(lambda x: str(int(x)) if x > 0 else 'no data')
    
    # State coordinates for the dots
    state_coords = {
        'AC': (-9.02, -70.81), 'AL': (-9.53, -36.75), 'AM': (-3.41, -65.85), 'AP': (1.41, -51.77),
        'BA': (-12.57, -41.70), 'CE': (-5.20, -39.53), 'DF': (-15.79, -47.86), 'ES': (-19.18, -40.30),
        'GO': (-15.82, -49.83), 'MA': (-4.96, -45.27), 'MG': (-18.51, -44.55), 'MS': (-20.77, -54.78),
        'MT': (-12.68, -56.92), 'PA': (-1.99, -54.93), 'PB': (-7.23, -36.78), 'PE': (-8.81, -36.95),
        'PI': (-7.71, -42.72), 'PR': (-25.25, -52.02), 'RJ': (-22.90, -43.20), 'RN': (-5.79, -36.56),
        'RO': (-11.50, -63.58), 'RR': (2.73, -62.07), 'RS': (-30.03, -51.21), 'SC': (-27.24, -50.21),
        'SE': (-10.57, -37.38), 'SP': (-23.55, -46.63), 'TO': (-10.17, -48.29)
    }
    
    state_delays['lat'] = state_delays['state'].map(lambda x: state_coords.get(x, (0,0))[0])
    state_delays['lon'] = state_delays['state'].map(lambda x: state_coords.get(x, (0,0))[1])
    
    import json
    import os
    import plotly.express as px
    import plotly.graph_objects as go
    
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
            hover_data={'delayed_orders': True, 'delays': False, 'lat': False, 'lon': False, 'color': False, 'state': False},
            projection="mercator"
        )
        
        # Add dots with the number of delayed orders for top 3 states
        top_3_df = state_delays[state_delays['color'] == 'Top 3']
        fig.add_trace(go.Scattergeo(
            lon=top_3_df['lon'],
            lat=top_3_df['lat'],
            mode='markers+text',
            text=top_3_df['delays'].astype(str),
            textposition="top center",
            textfont=dict(color='red', size=14, weight='bold'),
            marker=dict(size=10, color='red'),
            name='Delayed Orders',
            hoverinfo='skip'
        ))
        
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

# -----------------------------------------------------------------
# Revenue & Orders over Time
# -----------------------------------------------------------------
import plotly.express as px

@st.cache_data
def load_revenue_data():
    import os
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'olist.db')
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        o.order_id,
        o.order_purchase_timestamp,
        p.payment_value
    FROM olist_orders_dataset o
    JOIN olist_order_payments_dataset p ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
    daily = df.groupby(df['order_purchase_timestamp'].dt.date).agg(
        revenue=('payment_value', 'sum'),
        orders=('order_id', 'nunique')
    ).reset_index()
    daily['date'] = pd.to_datetime(daily['order_purchase_timestamp'])
    return daily

# Load and plot revenue data
rev_df = load_revenue_data()
if not rev_df.empty:
    rev_long = rev_df.melt(id_vars='date', value_vars=['revenue', 'orders'], var_name='Metric', value_name='Value')
    fig = px.line(
        rev_long,
        x='date',
        y='Value',
        color='Metric',
        labels={'date': 'Date', 'Value': 'Value', 'Metric': 'Metric'},
        title='Daily Revenue and Orders',
        hover_data={'Value': ':.2f'}
    )
    fig.update_traces(hovertemplate='%{x|%Y-%m-%d}<br>%{y:,.2f}')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info('No revenue data available for the selected period.')
