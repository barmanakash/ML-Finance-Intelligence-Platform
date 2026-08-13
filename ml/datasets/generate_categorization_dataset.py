"""Synthetic transaction-description dataset generator for categorization
training.

No real user or bank data is used anywhere. Merchant names below are
generic, publicly-known brand names used purely as realistic-looking
examples of transaction narrations (matching the style of common
Indian UPI/bank statement exports, per the project's sample schema).
Noise templates (reference numbers, "UPI/", "POS", city codes) are added
so the classifier learns to generalize past exact-string matching rather
than memorizing clean merchant names.

Usage:
    python -m ml.datasets.generate_categorization_dataset
"""

import csv
import random
from pathlib import Path

from ml.common.config import DATA_DIR

random.seed(42)

CATEGORY_MERCHANTS: dict[str, list[str]] = {
    "Food": [
        "SWIGGY", "ZOMATO", "DOMINOS PIZZA", "MCDONALDS", "KFC",
        "PIZZA HUT", "BURGER KING", "STARBUCKS", "CAFE COFFEE DAY", "BARISTA",
    ],
    "Groceries": [
        "BIGBASKET", "GROFERS", "DMART", "RELIANCE FRESH",
        "MORE SUPERMARKET", "BLINKIT", "ZEPTO", "SPENCERS RETAIL",
    ],
    "Transportation": [
        "UBER", "OLA CABS", "RAPIDO", "METRO CARD RECHARGE",
        "INDIAN OIL PETROL", "HP PETROL PUMP", "BPCL FUEL STATION",
    ],
    "Travel": [
        "MAKEMYTRIP", "GOIBIBO", "INDIGO AIRLINES", "IRCTC",
        "AIRBNB", "OYO ROOMS", "YATRA ONLINE",
    ],
    "Shopping": ["AMAZON", "FLIPKART", "MYNTRA", "AJIO", "NYKAA", "MEESHO"],
    "Entertainment": [
        "BOOKMYSHOW", "PVR CINEMAS", "INOX MOVIES", "HOTSTAR", "SPOTIFY PREMIUM",
    ],
    "Bills": [
        "ELECTRICITY BILL PAYMENT", "BSES RAJDHANI", "TATA POWER",
        "PIPED GAS PAYMENT", "WATER BOARD BILL",
    ],
    "Utilities": [
        "AIRTEL POSTPAID", "JIO RECHARGE", "VODAFONE IDEA",
        "ACT FIBERNET", "BROADBAND BILL PAYMENT",
    ],
    "Healthcare": [
        "APOLLO PHARMACY", "MEDPLUS", "PRACTO CONSULTATION",
        "FORTIS HEALTHCARE", "1MG ORDER",
    ],
    "Education": [
        "BYJUS", "UNACADEMY", "COURSERA", "UDEMY",
        "COLLEGE FEE PAYMENT", "SCHOOL FEES PAYMENT",
    ],
    "Rent": ["HOUSE RENT NEFT", "RENT PAYMENT TO LANDLORD", "MONTHLY RENT TRANSFER"],
    "Salary": ["SALARY CREDIT", "PAYROLL CREDIT", "MONTHLY SALARY NEFT"],
    "Investment": ["ZERODHA", "GROWW", "UPSTOX", "MUTUAL FUND SIP", "NPS CONTRIBUTION"],
    "Transfer": ["UPI TRANSFER TO", "NEFT TRANSFER TO", "IMPS TRANSFER TO", "FUNDS TRANSFER"],
    "Subscription": [
        "NETFLIX SUBSCRIPTION", "AMAZON PRIME MEMBERSHIP",
        "GOOGLE ONE STORAGE", "YOUTUBE PREMIUM", "ICLOUD STORAGE",
    ],
    "Cash Withdrawal": ["ATM CASH WITHDRAWAL", "ATM WDL", "CASH WITHDRAWAL"],
    "Other": ["MISC PAYMENT", "SERVICE CHARGE", "BANK FEE", "UNKNOWN MERCHANT PAYMENT"],
}

NOISE_TEMPLATES = [
    "{merchant}",
    "{merchant} REF{ref}",
    "UPI/{merchant}/{ref}",
    "POS {merchant} {city}",
    "{merchant}*{ref}",
    "NEFT-{merchant}-{ref}",
    "{merchant} TXN{ref}",
]

CITIES = ["MUMBAI", "DELHI", "BANGALORE", "PUNE", "RAIPUR", "HYDERABAD", "CHENNAI", "KOLKATA"]

SAMPLES_PER_MERCHANT = 25


def generate(output_path: Path) -> int:
    rows = []
    for category, merchants in CATEGORY_MERCHANTS.items():
        for merchant in merchants:
            for _ in range(SAMPLES_PER_MERCHANT):
                template = random.choice(NOISE_TEMPLATES)
                description = template.format(
                    merchant=merchant,
                    ref=random.randint(100000, 999999),
                    city=random.choice(CITIES),
                )
                rows.append({"description": description, "category": category})

    random.shuffle(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["description", "category"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    output = DATA_DIR / "training" / "categorization_dataset.csv"
    count = generate(output)
    print(f"Generated {count} synthetic labeled rows across {len(CATEGORY_MERCHANTS)} categories -> {output}")
