import os
import sqlite3
import pandas as pd
from pathlib import Path

def main():
    # Define paths relative to this script
    project_root = Path(__file__).resolve().parent.parent
    raw_data_dir = project_root / "data" / "raw"
    db_path = project_root / "data" / "olist.db"

    print(f"Connecting to SQLite database at: {db_path}")
    
    # Create a connection to the database
    # This will create the file olist.db if it doesn't exist
    conn = sqlite3.connect(db_path)
    
    try:
        # Check if raw data directory exists
        if not raw_data_dir.exists():
            print(f"Error: Raw data directory not found at {raw_data_dir}")
            return

        # Find all CSV files
        csv_files = list(raw_data_dir.glob("*.csv"))
        if not csv_files:
            print("No CSV files found in the raw data directory.")
            return

        # Iterate over all CSV files in the raw data directory
        for csv_file in csv_files:
            # We use the filename (without .csv) as the table name
            table_name = csv_file.stem
            print(f"Processing {csv_file.name} -> Table: {table_name}")
            
            # Read CSV using pandas
            df = pd.read_csv(csv_file)
            
            # Write the data to SQLite
            # if_exists='replace' makes this script idempotent (safe to run multiple times)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            
            print(f"  Successfully loaded {len(df)} rows into '{table_name}'.")
            
        print("\nAll files processed successfully!")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()
