"""Downloads NASA data with earthaccess. (Data role)

Optional: the current data were generated with Giovanni (see data/giovanni/).
This script is a starting point for downloading full files instead.

Before running it:
  1. Create an account at https://urs.earthdata.nasa.gov
  2. pip install -r requirements.txt

Not tested yet: adjust the product, dates and region.
"""

import earthaccess

# Approximate bounding box of Mexico: (lon_min, lat_min, lon_max, lat_max)
MEXICO = (-118.5, 14.5, -86.5, 32.8)

# Example product: MERRA-2 monthly surface variables (includes T2M)
PRODUCT = "M2TMNXSLV"
PERIOD = ("1990-01-01", "2025-12-31")


def main():
    earthaccess.login()  # asks for your Earthdata username and password the first time

    results = earthaccess.search_data(
        short_name=PRODUCT,
        temporal=PERIOD,
        bounding_box=MEXICO,
    )
    print(f"Files found: {len(results)}")

    earthaccess.download(results, f"data/raw/{PRODUCT}")

    # TODO: open with xarray, crop to MEXICO, keep the variable
    #       and save something light to data/processed/


if __name__ == "__main__":
    main()
