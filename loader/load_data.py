from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile, is_zipfile
import os
import pandas as pd
from sqlalchemy import create_engine

# FAOSTAT download URL
DATA_URL = (
    "https://fenixservices.fao.org/faostat/static/bulkdownloads/Trade_CropsLivestock_E_All_Data_(Normalized).zip"
)

# Project folder and destination for downloaded data
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

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

                print(
                    f"\rDownloaded: {downloaded / (1024 ** 2):.1f} MB",
                    end="",
                    flush=True,
                )

    print()

    if not is_zipfile(temporary_path):
        raise ValueError("The downloaded file is not a ZIP archive.")

    temporary_path.replace(zip_path)

    print("Download completed:", zip_path)
    return zip_path

def load_data_to_db(zip_path, engine):
    """Read specific CSV inside ZIP file in chunks and load into the database."""
    print("Loading data into DB...", flush=True)
    chunksize = 50000

    with ZipFile(zip_path, 'r') as z:
        # Find the main normalized CSV file
        csv_filename = [f for f in z.namelist() if f.endswith('(Normalized).csv')][0]

        with z.open(csv_filename) as f:
            for chunk in pd.read_csv(f, chunksize=chunksize, encoding='latin-1'):

                # Normalize CSV column names to match MySQL
                chunk.columns = (
                    chunk.columns
                    .str.strip()
                    .str.lower()
                    .str.replace(r"[^a-z0-9]+", "_", regex=True)
                    .str.strip("_")
                )

                chunk.to_sql(
                    'raw_trade',
                    con=engine,
                    if_exists='append',
                    index=False
                )

    print("Data successfully loaded into DB!")

if __name__ == "__main__":

 DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///faostat_trade.db")
 engine = create_engine(DATABASE_URL)

 zip_file = download_zip()
 load_data_to_db(zip_file, engine)