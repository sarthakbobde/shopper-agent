"""Writes customers.csv and products.csv next to this file: fake data for the Shoppers Stop client.

    uv run python clients/shoppers_stop/seed/generate.py

The random generator has a fixed seed, so running this again gives identical files. The CSVs are
committed; rerun this only when you want to change the data (ADR-011).

Everything is invented: names are common Indian names, emails use example.com (reserved for
examples, so they can never reach a real person), brands are made up, and prices are made up.
"""

import csv
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
RNG = random.Random(42)

# ---- customers -------------------------------------------------------------------------------

FIRST_NAMES = [
    "Priya", "Rahul", "Ananya", "Arjun", "Sneha", "Vikram", "Kavya", "Rohan", "Isha", "Aditya",
    "Meera", "Karan", "Pooja", "Siddharth", "Neha", "Amit", "Divya", "Nikhil", "Riya", "Varun",
]  # fmt: skip
LAST_NAMES = [
    "Sharma", "Shah", "Patel", "Iyer", "Reddy", "Nair", "Gupta", "Mehta", "Kulkarni", "Banerjee",
    "Singh", "Desai", "Rao", "Joshi", "Menon",
]  # fmt: skip
CITIES = ["Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]

# Spends (in rupees) right on the tier edges, so the tier rule can be tested on seed data:
# Low below 3,000; Medium 3,000 to 10,000; High above 10,000 (ADR-005).
BOUNDARY_SPENDS = [2999, 3000, 10000, 10001]

NUM_CUSTOMERS = 50

# ---- products --------------------------------------------------------------------------------

# category: (code prefix, item types, price range in rupees)
CATEGORIES = {
    "Men's Wear": ("MEN", ["Shirt", "T-Shirt", "Jeans", "Chinos", "Kurta", "Blazer"], (799, 5999)),
    "Women's Wear": ("WMN", ["Kurta", "Saree", "Dress", "Top", "Jeans", "Palazzo"], (899, 8999)),
    "Kids": ("KID", ["T-Shirt", "Shorts", "Frock", "Hoodie"], (399, 1999)),
    "Footwear": ("FTW", ["Sneakers", "Sandals", "Loafers", "Heels", "Running Shoes"], (999, 6999)),
    "Beauty": ("BTY", ["Lipstick", "Face Wash", "Perfume", "Moisturiser"], (249, 3499)),
    "Accessories": ("ACC", ["Handbag", "Wallet", "Watch", "Sunglasses", "Belt"], (499, 9999)),
    "Home": ("HOM", ["Bedsheet", "Cushion Cover", "Towel Set", "Mug Set"], (399, 3999)),
}
CLOTHING = {"Men's Wear", "Women's Wear", "Kids"}
COLOURS = ["Blue", "Black", "White", "Red", "Green", "Navy", "Maroon", "Beige", "Pink", "Grey"]
MATERIALS = ["Cotton", "Linen", "Denim", "Silk", "Rayon"]
BRANDS = ["Urbano", "Kesari", "Tara Lane", "Northline", "Saanjh", "Brightloom", "Coastal Thread", "Indigo Row"]

NUM_PRODUCTS = 200
OUT_OF_STOCK_SHARE = 0.10


def make_customers() -> list[dict]:
    customers = []
    used_emails = set()
    for number in range(1, NUM_CUSTOMERS + 1):
        first = RNG.choice(FIRST_NAMES)
        last = RNG.choice(LAST_NAMES)
        email = f"{first}.{last}@example.com".lower()
        suffix = 2
        while email in used_emails:
            email = f"{first}.{last}{suffix}@example.com".lower()
            suffix += 1
        used_emails.add(email)

        if number <= len(BOUNDARY_SPENDS):
            spend_rupees = BOUNDARY_SPENDS[number - 1]
        else:
            spend_rupees = RNG.randint(200, 40000)

        customers.append({
            "customer_id": f"C{number:04d}",
            "name": f"{first} {last}",
            "email": email,
            "city": RNG.choice(CITIES),
            "age_group": RNG.choice(AGE_GROUPS),
            "preferred_category": RNG.choice(list(CATEGORIES)),
            "total_spend_paise": spend_rupees * 100,
        })  # fmt: skip
    return customers


def make_products() -> list[dict]:
    products = []
    counters = {category: 0 for category in CATEGORIES}
    for number in range(1, NUM_PRODUCTS + 1):
        category = RNG.choice(list(CATEGORIES))
        prefix, items, (low, high) = CATEGORIES[category]
        counters[category] += 1

        item = RNG.choice(items)
        colour = RNG.choice(COLOURS)
        if category in CLOTHING:
            name = f"{colour} {RNG.choice(MATERIALS)} {item}"
        else:
            name = f"{colour} {item}"

        # Prices end in 9, like most shop prices: 1299, 2499 ...
        price_rupees = (RNG.randint(low, high) // 100) * 100 + 99
        if RNG.random() < OUT_OF_STOCK_SHARE:
            stock = 0
        else:
            stock = RNG.randint(1, 120)

        products.append({
            "product_id": f"P{number:04d}",
            "code": f"SS-{prefix}-{counters[category]:04d}",
            "name": name,
            "brand": RNG.choice(BRANDS),
            "category": category,
            "price_paise": price_rupees * 100,
            "stock_qty": stock,
        })  # fmt: skip
    return products


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {path}")


if __name__ == "__main__":
    write_csv(HERE / "customers.csv", make_customers())
    write_csv(HERE / "products.csv", make_products())
