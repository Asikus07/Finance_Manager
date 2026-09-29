import json
from dataclasses import asdict
from core.domain import Transaction

def load_data():
    with open("data/seed.json", "r", encoding="utf-8") as file:
        return json.load(file)
    
def save_data(data):
    with open("data/seed.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    
def create_transaction():
    transaction_id = input("Введите ID транзакции:")
    account_id = input("Введите ID аккаунта:")
    cat_id  = input("Введите ID категории:")
    amount = int(input("Введите сумму:"))
    ts = input("Введите дату:")
    note = input("Введите описание:")

    transaction = Transaction(
        id=transaction_id,
        account_id=account_id,
        cat_id=cat_id,
        amount=amount,
        ts=ts,
        note=note
    )

    transaction_dict = asdict(transaction)

    return transaction_dict

    

if __name__ == "__main__":
    data = load_data()
    transaction_dict = create_transaction()

    data["transactions"].append(transaction_dict)
    save_data(data)
    