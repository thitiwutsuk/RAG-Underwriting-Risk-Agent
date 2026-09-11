"""Re-download the real specimen policy PDFs used in data/policies/.

These files are gitignored (they are real, copyrighted documents published
by RBC Insurance for public consumer reference -- see data/README.md), so a
fresh clone of this repo needs to fetch them again before running ingest.py.

Run: python scripts/download_real_policies.py
"""

import urllib.request
from pathlib import Path

POLICIES_DIR = Path(__file__).resolve().parent.parent / "data" / "policies"

# filename -> source URL (also documented in data/README.md)
SOURCES = {
    "rbc_term_life.pdf": "https://www.rbcinsurance.com/samplepolicy/pdf/your-term-sample-policy.pdf",
    "your-term-rider.pdf": "https://www.rbcinsurance.com/samplepolicy/pdf/your-term-rider.pdf",
    "t100-policy.pdf": "https://www.rbcinsurance.com/samplepolicy/pdf/t100-policy.pdf",
    "rbc-ul-policy.pdf": "https://www.rbcinsurance.com/samplepolicy/pdf/rbc-ul-policy.pdf",
    "rbc-ul-policy-bonus.pdf": "https://www.rbcinsurance.com/samplepolicy/pdf/rbc-ul-policy-bonus.pdf",
    "ul-rider-package.pdf": "https://www.rbcinsurance.com/samplepolicy/pdf/ul-rider-package.pdf",
    "rbc_critical_illness.pdf": "https://www.rbcinsurance.com/health-insurance/pdf/critical-illness-insurance-plan-sample-policy.pdf",
    "rbc_disability_income.pdf": "https://assets.rbcinsurance.com/m/ab8e41544b7cee55/original/The-Fundamental-Series-Disability-Income-Protection.pdf",
}


def main():
    POLICIES_DIR.mkdir(parents=True, exist_ok=True)
    request_headers = {"User-Agent": "Mozilla/5.0"}

    for filename, url in SOURCES.items():
        dest = POLICIES_DIR / filename
        print(f"Downloading {filename} ...")
        req = urllib.request.Request(url, headers=request_headers)
        with urllib.request.urlopen(req) as response, open(dest, "wb") as f:
            f.write(response.read())
        size_kb = dest.stat().st_size / 1024
        print(f"  saved {dest} ({size_kb:.0f} KB)")

    print(f"\nDone. Run 'python ingest.py' next to rebuild the ChromaDB collection.")


if __name__ == "__main__":
    main()
