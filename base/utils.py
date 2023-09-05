
import random
import string
from .models import *
from decimal import Decimal
from django.core.mail import send_mail
def generate_random_string(length):
    letters = string.ascii_letters  
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

def get_user(user_id):
    return Profile.objects.select_for_update().get(uid=user_id)


def Notify_buyer(buyer_email):
    subject = "Transaction Notification"
    message = "I have received your funds and have released your crypto"
    from_email = "noreply@bit.com"
    recipient_list = [buyer_email]

    send_mail(subject, message, from_email, recipient_list)



def Notify_seller( seller_email):
    subject = "Transaction Notification"
    message = "You have received a notification from  your recent buyer."
    from_email = "noreply@ybit.com"
    recipient_list = [seller_email]

    send_mail(subject, message, from_email, recipient_list)



