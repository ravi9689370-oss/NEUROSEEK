"""
NCERT Dataset Downloader — Hugging Face se
Direct API se download karta hai bina datasets library ke
"""

import json
import os
import urllib.request
import urllib.parse
from typing import Optional


class NCERTDownloader:
    """Hugging Face se NCERT datasets download karta hai"""

    def __init__(self):
        self.base_url = "https://huggingface.co/api/datasets"
        self.download_dir = os.path.join(os.path.dirname(__file__), "hf_data")
        os.makedirs(self.download_dir, exist_ok=True)

    def search_datasets(self, query: str = "NCERT") -> list:
        """Hugging Face par NCERT datasets search karta hai"""
        try:
            url = f"{self.base_url}?search={urllib.parse.quote(query)}&limit=50"
            req = urllib.request.Request(url, headers={"User-Agent": "NeuroSeekAI/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def download_dataset(self, dataset_id: str, max_rows: int = 1000) -> Optional[str]:
        """Dataset download karta hai aur local file mein save karta hai"""
        try:
            # Dataset info get karo
            info_url = f"https://huggingface.co/api/datasets/{dataset_id}"
            req = urllib.request.Request(info_url, headers={"User-Agent": "NeuroSeekAI/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                info = json.loads(response.read().decode("utf-8"))

            # Dataset files list karo
            siblings = info.get("siblings", [])
            files = [s.get("rfilename", "") for s in siblings if s.get("rfilename")]

            # Parquet ya CSV file dhundo
            data_files = [f for f in files if f.endswith(".parquet") or f.endswith(".csv") or f.endswith(".json")]

            if not data_files:
                return None

            # Pehli data file download karo
            filename = data_files[0]
            download_url = f"https://huggingface.co/datasets/{dataset_id}/resolve/main/{filename}"

            local_path = os.path.join(self.download_dir, f"{dataset_id.replace('/', '_')}.json")

            # Download karo
            req = urllib.request.Request(download_url, headers={"User-Agent": "NeuroSeekAI/1.0"})
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()

            # Save karo
            with open(local_path, "wb") as f:
                f.write(data)

            return local_path

        except Exception as e:
            print(f"Download error for {dataset_id}: {e}")
            return None

    def download_all_ncert(self) -> dict:
        """Saare NCERT datasets download karta hai"""
        results = {}

        # Important NCERT datasets
        datasets = [
            "ParthKadam2003/NCERT_Dataset",
            "Aadishesh/ncerts",
            "GokulWork/ncert_physics",
            "manasa21/mathematics_ncert",
            "lokeshe09/mathematics_ncert_12",
            "KadamParth/NCERT_Biology_12th",
            "KadamParth/NCERT_Chemistry_12th",
            "KadamParth/NCERT_Physics_12th",
            "KadamParth/NCERT_History_12th",
            "KadamParth/NCERT_Economics_12th",
        ]

        for dataset_id in datasets:
            print(f"Downloading {dataset_id}...")
            path = self.download_dataset(dataset_id)
            if path:
                results[dataset_id] = path
                print(f"  ✅ Saved to {path}")
            else:
                print(f"  ❌ Failed")

        return results


if __name__ == "__main__":
    downloader = NCERTDownloader()
    results = downloader.download_all_ncert()
    print(f"\nTotal downloaded: {len(results)}")
    for k, v in results.items():
        print(f"  {k}: {v}")
