import os
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile, is_zipfile
import pandas as pd
from sqlalchemy import create_engine

# FAOSTAT bulk download URL
DATA_URL = "https://bulks-faostat.fao.org/production/Trade_CropsLivestock_E_All_Data_(Normalized).zip"

# Directories inside container
DATA_DIR = Path("/app/data")

COLUMN_MAPPING = {
    "Area Code": "area_code",
    "Area Code (M49)": "area_code_m49",
    "Area": "area",
    "Item Code": "item_code",
    "Item Code (CPC)": "item_code_cpc",
    "Item": "item",
    "Element Code": "element_code",
    "Element": "element",
    "Year Code": "year_code",
    "Year": "year",
    "Unit": "unit",
    "Value": "value",
    "Flag": "flag",
    "Note": "note"
}

def download_zip():
    """Download the FAOSTAT ZIP and return its local path."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DATA_DIR / "faostat_trade.zip"
    temporary_path = DATA_DIR / "faostat_trade.zip.part"

    if zip_path.exists() and is_zipfile(zip_path):
        print("ZIP already downloaded:", zip_path)
        return zip_path

    print("Downloading FAOSTAT data...", flush=True)
    with urlopen(DATA_URL, timeout=120) as response:
        with temporary_path.open("wb") as output:
            downloaded = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                print(f"\rDownloaded: {downloaded / (1024 ** 2):.1f} MB", end="", flush=True)

    print()
    if not is_zipfile(temporary_path):
        raise ValueError("The downloaded file is not a ZIP archive.")

    temporary_path.replace(zip_path)
    print("Download completed:", zip_path)
    return zip_path

def load_data_to_db(zip_path, engine):
    """Read CSV inside ZIP in chunks, rename columns, and insert into raw_trade."""
    print("Loading data into DB...", flush=True)
    chunksize = 50000

    with ZipFile(zip_path, "r") as z:
        # Locate the main normalized CSV
        csv_filename = [f for f in z.namelist() if f.endswith("(Normalized).csv")][0]
        
        with z.open(csv_filename) as f:
            total_rows = 0
            for chunk in pd.read_csv(f, chunksize=chunksize, encoding="latin-1", low_memory=False):
                # 1. Rename columns
                chunk = chunk.rename(columns=COLUMN_MAPPING)

                # 2. FILTER FOR COFFEE ONLY (Item Code 656 or Item containing Coffee)
                # This prevents filling up Docker's disk with 16 million irrelevant crop rows!
                chunk = chunk[chunk["item_code"] == 656]

                if chunk.empty:
                    continue

                # 3. Insert into MySQL
                chunk.to_sql("raw_trade", con=engine, if_exists="append", index=False)
                
                total_rows += len(chunk)
                print(f"\rCoffee rows inserted: {total_rows:,}", end="", flush=True)

    print("\nData successfully loaded into DB!")

if __name__ == "__main__":
    # Construct MySQL connection string from environment variables
    user = os.getenv("MYSQL_USER", "team_user")
    password = os.getenv("MYSQL_PASSWORD", "secret")
    host = os.getenv("MYSQL_HOST", "db")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "coffee_trade")

    db_url = os.getenv("DATABASE_URL", f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
    
    engine = create_engine(db_url)

    zip_file = download_zip()
    load_data_to_db(zip_file, engine)