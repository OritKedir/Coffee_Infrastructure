from pathlib import Path
from urllib.request import urlopen
from zipfile import is_zipfile

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

if __name__ == "__main__":
    download_zip()