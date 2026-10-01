import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import os
from dotenv import load_dotenv


def main():
    project_root = Path(__file__).resolve().parent.parent
    raw_data_dir = project_root / "data" / "raw"

    load_dotenv()

    db_host = os.getenv("OLIST_DB_HOST")
    db_port = os.getenv("OLIST_DB_PORT")
    db_name = os.getenv("OLIST_DB_NAME")
    db_user = os.getenv("OLIST_DB_USER")
    db_password = os.getenv("OLIST_DB_PASSWORD")

    connection_url = (
        f"postgresql+psycopg://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    print("Connecting to PostgreSQL...")

    engine = create_engine(connection_url)

    try:
        if not raw_data_dir.exists():
            print(f"Error: Raw data directory not found at {raw_data_dir}")
            return

        csv_files = list(raw_data_dir.glob("*.csv"))

        if not csv_files:
            print("No CSV files found.")
            return

        for csv_file in csv_files:
            table_name = csv_file.stem

            print(f"Processing {csv_file.name} -> raw.{table_name}")

            df = pd.read_csv(csv_file)

            df.to_sql(
                name=table_name,
                con=engine,
                schema="raw",
                if_exists="replace",
                index=False,
            )

            print(f"  Loaded {len(df)} rows into raw.{table_name}.")

        print("\nAll files processed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        engine.dispose()
        print("Database connection closed.")


if __name__ == "__main__":
    main()
