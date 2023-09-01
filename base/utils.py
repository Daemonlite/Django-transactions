
import random
import string
from .models import *
from decimal import Decimal

def generate_random_string(length):
    letters = string.ascii_letters  # Includes both lowercase and uppercase alphabets
    return "".join(random.choice(letters) for _ in range(length))



def add_fees(amount):
    if amount >= 100:
        return amount * 0.1
    elif amount < 100:
        return amount * 0.05
    return


def get_held_coin(order_id):
    return Held_Coin.objects.select_for_update().get(order_id=order_id)


def get_escrow(escrow_id):
    return Escrow.objects.select_for_update().get(escrow_uid=escrow_id)


def get_buyer(buyer_id):
    return Profile.objects.select_for_update().get(uid=buyer_id)


def calculate_btc_value(usd_amount):
    btc_price = BTC.objects.values("crypto").filter(fiat="USD").latest("date")
    btc_value = Decimal(usd_amount) * Decimal(btc_price["crypto"])
    return btc_value


def complete_transaction(held_coin, escrow, buyer, btc_value):
    held_coin.seller_is_complete = True
    escrow.is_held = False
    escrow.is_complete = True
    buyer.btc_balance += btc_value
    held_coin.completed_at = timezone.now()
    buyer.save()
    escrow.save()
    held_coin.save()