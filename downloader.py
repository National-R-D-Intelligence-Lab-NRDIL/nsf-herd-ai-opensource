import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path
from urllib.parse import urljoin
import zipfile
import io
import re

class HERDDownloader:
    def __init__(self, output_dir):
        self.base_url = 'https://ncses.nsf.gov/explore-data/microdata/higher-education-research-development'
        self.output_dir = Path(output_dir)
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def run(self, start_year=2010):
        print(f"⬇️  Starting automated download to {self.output_dir}...")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Fetch the page
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Error accessing NSF website: {e}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. Find all ZIP links
        zip_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Look for standard HERD zip files
            if 'higher_education_r_and_d_' in href and href.endswith('.zip') and '_short' not in href:
                year_match = re.search(r'_(\d{4})\.zip', href)
                if year_match:
                    year = int(year_match.group(1))
                    if year >= start_year:
                        zip_links.append((year, urljoin('https://ncses.nsf.gov', href)))

        print(f"🔎 Found {len(zip_links)} datasets from {start_year} to present.")

        # 3. Download and Extract
        for year, link in zip_links:
            self._process_year(year, link)

    def _process_year(self, year, link):
        # Check if we already have the csv to avoid re-downloading
        expected_file = self.output_dir / f"herd_{year}.csv"
        
        # We look for any file starting with herd_{year} because the raw names vary
        existing = list(self.output_dir.glob(f"herd_{year}*.csv"))
        if existing:
            print(f"   ✓ Data for {year} already exists. Skipping.")
            return

        print(f"   ⏳ Downloading {year} data...")
        try:
            r = requests.get(link, headers=self.headers, stream=True)
            r.raise_for_status()
            
            # Unzip in memory
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                # Find the main CSV (usually starts with 'herd_')
                csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                for csv_file in csv_files:
                    # Save it with a clean name to preserve your ETL logic
                    # We keep the original name to be safe, or you can rename it here
                    source = z.open(csv_file)
                    target_path = self.output_dir / f"herd_{year}_{csv_file}"
                    
                    with open(target_path, 'wb') as f:
                        f.write(source.read())
                    print(f"   ✅ Extracted: {target_path.name}")
                    
        except Exception as e:
            print(f"   ❌ Failed to download {year}: {e}")

if __name__ == "__main__":
    # Test run
    downloader = HERDDownloader("data/raw")
    downloader.run()