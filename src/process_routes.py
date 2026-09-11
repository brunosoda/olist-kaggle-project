# src/process_routes.py
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import openrouteservice
import time
# -------------------------------------------------
# Configuration
# -------------------------------------------------
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "olist.db"   # project root / data
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
RATE_LIMIT = 2000                     # maximum API calls per run (free tier)


# -------------------------------------------------
# Load API key
# -------------------------------------------------
load_dotenv(dotenv_path=ENV_PATH, override=True)
ORS_API_KEY = os.getenv("ORS_API_KEY")
if not ORS_API_KEY:
    raise RuntimeError("ORS_API_KEY not found in .env")
client = openrouteservice.Client(key=ORS_API_KEY)

# -------------------------------------------------
# Helper functions
# -------------------------------------------------
def minutes(td):
    """Convert a datetime.timedelta to minutes (float)."""
    return td.total_seconds() / 60.0

def ensure_table(conn):
    """Create the results table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS order_distances (
            order_id               TEXT,
            seller_id              TEXT,
            seller_zip_code        INTEGER,
            customer_zip_code      INTEGER,
            distance_km            REAL,
            duration_min           REAL,
            pct_api_vs_estimated   REAL,
            pct_api_vs_real        REAL,
            processed_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
def ensure_failed_table(conn):
    """Create a table to store API call failures for later retry."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS failed_pairs (
            seller_zip_code   INTEGER,
            customer_zip_code INTEGER,
            error             TEXT,
            attempted_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
# -------------------------------------------------
# Main processing
# -------------------------------------------------
def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_table(conn)

    # 1. Select delayed orders (estimated < actual delivery)
    delayed_rows = conn.execute(
        """
        SELECT o.order_id,
               oi.seller_id,
               s.seller_zip_code_prefix AS seller_zip_code,
               c.customer_zip_code_prefix AS customer_zip_code,
               o.order_delivered_carrier_date,
               o.order_estimated_delivery_date,
               o.order_delivered_customer_date
        FROM olist_orders_dataset o
        JOIN olist_order_items_dataset oi ON o.order_id = oi.order_id
        JOIN olist_sellers_dataset s ON oi.seller_id = s.seller_id
        JOIN olist_customers_dataset c ON o.customer_id = c.customer_id
        WHERE o.order_estimated_delivery_date IS NOT NULL
          AND o.order_delivered_customer_date   IS NOT NULL
          AND datetime(o.order_estimated_delivery_date) <
              datetime(o.order_delivered_customer_date)
        ORDER BY datetime(o.order_delivered_customer_date) -
                 datetime(o.order_estimated_delivery_date) DESC
        """
    ).fetchall()

    if not delayed_rows:
        print("No delayed orders found.")
        return

    # 2. Group by (seller_zip, customer_zip) to reuse API calls
    pair_to_orders = {}
    for row in delayed_rows:
        pair = (row["seller_zip_code"], row["customer_zip_code"])
        pair_to_orders.setdefault(pair, []).append(row)

    # 3. Determine how many pairs have already been processed
    processed_pairs = set(
        conn.execute(
            "SELECT DISTINCT seller_zip_code, customer_zip_code FROM order_distances"
        ).fetchall()
    )
    processed_count = len(processed_pairs)
    remaining_quota = max(RATE_LIMIT - processed_count, 0)

    # 4. Order pairs by average delay severity (largest mean delay first)
    def pair_average_delay(pair):
        orders = pair_to_orders[pair]
        total = 0
        for o in orders:
            est = datetime.strptime(o["order_estimated_delivery_date"], "%Y-%m-%d %H:%M:%S")
            real = datetime.strptime(o["order_delivered_customer_date"], "%Y-%m-%d %H:%M:%S")
            total += minutes(real - est)
        return total / len(orders)

    ordered_pairs = sorted(pair_to_orders.keys(),
                          key=pair_average_delay,
                          reverse=True)

    # 5. Process while we have quota
    attempted_calls = 0  # track number of API attempts
    processed_this_run = 0
    for pair in ordered_pairs:
        # Hard stop if we have reached the daily quota of attempted API calls
        if attempted_calls >= RATE_LIMIT:
            print("Reached daily API call limit; stopping processing.")
            break
        attempted_calls += 1
        if processed_this_run >= remaining_quota:
            break
        if pair in processed_pairs:
            continue

        seller_zip, customer_zip = pair

        # Retrieve coordinates for seller zip
        seller_geo = conn.execute(
            "SELECT geolocation_lat, geolocation_lng FROM olist_geolocation_dataset "
            "WHERE geolocation_zip_code_prefix = ? LIMIT 1",
            (seller_zip,)
        ).fetchone()
        if not seller_geo:
            print(f"Missing coordinates for seller zip {seller_zip}, skipping.")
            continue
        seller_lat, seller_lng = seller_geo["geolocation_lat"], seller_geo["geolocation_lng"]

        # Retrieve coordinates for customer zip
        customer_geo = conn.execute(
            "SELECT geolocation_lat, geolocation_lng FROM olist_geolocation_dataset "
            "WHERE geolocation_zip_code_prefix = ? LIMIT 1",
            (customer_zip,)
        ).fetchone()
        if not customer_geo:
            print(f"Missing coordinates for customer zip {customer_zip}, skipping.")
            continue
        cust_lat, cust_lng = customer_geo["geolocation_lat"], customer_geo["geolocation_lng"]

        # Call OpenRouteService
        try:
            route = client.directions(
                coordinates=[(seller_lng, seller_lat), (cust_lng, cust_lat)],
                profile="driving-car",
                format="json",
                units="km",
                geometry=False,
                instructions=False,
            )
            # Respect per‑minute rate limit (~40 calls/min)
            time.sleep(1.5)
        except Exception as exc:
            print(f"API error for pair {pair}: {exc}")
            # Record failed pair for later retry
            conn.execute(
                "INSERT INTO failed_pairs (seller_zip_code, customer_zip_code, error) VALUES (?,?,?)",
                (seller_zip, customer_zip, str(exc))
            )
            conn.commit()
            continue

        summary = route["routes"][0]["summary"]
        distance_km = summary["distance"]
        duration_min = summary["duration"] / 60.0

        # Insert results for each order in the pair
        for order in pair_to_orders[pair]:
            est = datetime.strptime(order["order_estimated_delivery_date"], "%Y-%m-%d %H:%M:%S")
            carrier = datetime.strptime(order["order_delivered_carrier_date"], "%Y-%m-%d %H:%M:%S")
            real = datetime.strptime(order["order_delivered_customer_date"], "%Y-%m-%d %H:%M:%S")

            # Time between carrier → estimated and carrier → real (in minutes)
            delta_est = minutes(est - carrier) if (est - carrier).total_seconds() > 0 else 0
            delta_real = minutes(real - carrier) if (real - carrier).total_seconds() > 0 else 0

            pct_vs_est = (duration_min / delta_est * 100.0) if delta_est else None
            pct_vs_real = (duration_min / delta_real * 100.0) if delta_real else None

            conn.execute(
                """
                INSERT INTO order_distances (
                    order_id, seller_id, seller_zip_code, customer_zip_code,
                    distance_km, duration_min, pct_api_vs_estimated, pct_api_vs_real
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    order["order_id"],
                    order["seller_id"],
                    seller_zip,
                    customer_zip,
                    distance_km,
                    duration_min,
                    pct_vs_est,
                    pct_vs_real,
                ),
            )
        conn.commit()
        processed_this_run += 1
        # Throttle between successive pairs to stay under per‑minute limit
        time.sleep(1.5)
        print(f"Processed pair {pair}: {len(pair_to_orders[pair])} orders, "
              f"{distance_km:.2f} km, {duration_min:.1f} min")

    print(f"Finished: {processed_this_run} new pairs processed "
          f"(remaining quota: {remaining_quota - processed_this_run})")

if __name__ == "__main__":
    main()
