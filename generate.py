import json
import random
from datetime import date, timedelta

random.seed(42)
data = json.load(open("data/seed.json", encoding="utf-8"))

account_ids = [a["id"] for a in data["accounts"]]
expense_cats = [c["id"] for c in data["categories"] if c["type"] == "expense"]
income_cats = [c["id"] for c in data["categories"] if c["type"] == "income"]


def make_tx(i):
    is_income = random.random() < 0.1  # примерно 10% — доходы
    return {
        "id": f"tr_{i:03d}",
        "account_id": random.choice(account_ids),
        "cat_id": random.choice(income_cats if is_income else expense_cats),
        "amount": (
            random.randint(100000, 400000) if is_income else -random.randint(200, 20000)
        ),
        "ts": str(date(2026, 9, 1) + timedelta(days=random.randint(0, 36))),
        "note": "Доход" if is_income else "Расход",
    }


data["transactions"] = [make_tx(i) for i in range(1, 101)]
json.dump(
    data, open("data/seed.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2
)
