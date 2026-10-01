import json
from dataclasses import asdict
from core.domain import Transaction

def load_data():
    with open("data/seed.json", "r", encoding="utf-8") as file:
        return json.load(file)
    
def save_data(data):
    with open("data/seed.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    
def create_transaction(data):
    transaction_id = input("Введите ID транзакции:")

    transaction_ids = [transaction["id"] for transaction in data["transactions"]]

    if transaction_id in transaction_ids:
        print("Транзакция с таким ID уже существует!")
        return None
    
    account_id = input("Введите ID аккаунта:")

    account_ids = [account["id"] for account in data["accounts"]]

    if account_id not in account_ids:
        print("Такого аккаунта не существует!")
        return None

    cat_id = input("Введите ID категории:")
    
    category_ids = [category["id"] for category in data["categories"]] 
    
    if cat_id not in category_ids:
        print("Такой категории не существует!")
        return None

    try:
        amount = int(input("Введите сумму:"))
    except ValueError:
        print("Сумма должна быть числом!")
        return None
    
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
    transaction_dict = create_transaction(data)
   
    if transaction_dict is not None:
        data["transactions"].append(transaction_dict)
        save_data(data)
        print("Транзакция успешно сохранена!")


    