from django.shortcuts import render
# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, HttpResponse
from django.db import transaction
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST,require_GET
from .models import Escrow,Profile,BTC,escrow_transaction_history,Held_Coin
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password,check_password
from .utils import *
from django.middleware import csrf
from decimal import Decimal
from django.utils import timezone

import logging
from django.db.models import F
logger = logging.getLogger(__name__)

@require_POST
@csrf_exempt
def register_user(request):
    data = json.loads(request.body)
    wallet_address = generate_random_string(30)

    try:
        user_data = {
            "email": data["email"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "password": make_password(data["password"]),
            "wallet_address": wallet_address,
        }
        user =Profile.objects.create(**user_data)
        return JsonResponse(
            {
                "message": "User created successfully",
                "user": {
                    "id": user.id,
                    "uid": user.uid,
                    "email": user.email,
                    "password": user.password,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "wallet_address": user.wallet_address,
                    "balance": user.balance,
                    "btc_balance": user.btc_balance,
                    "csrf_token": csrf.get_token(request),
                },
            },
            status=201,
        )

    except Exception as e:
        return JsonResponse({"message": "Enter required fields","error": str(e)}, status=400)


@csrf_exempt
@require_POST
def login_user(request):
    try:
        data = json.loads(request.body)
        email = data["email"]
        password = data["password"]

        user = Profile.objects.get(email=email)
        checker = check_password(password,user.password)
        print(user)
        print(checker)
        if user and checker:
            login(request, user)
            return JsonResponse({
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "uid": user.uid,
                    "email": user.email,
                    "password":user.password,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "wallet_address": user.wallet_address,
                    "balance": user.balance,
                    "btc_balance": user.btc_balance,
                    "csrf_token": csrf.get_token(request),
                },
            })
        else:
            return JsonResponse({"message": "Invalid email or password"}, status=400)
    except Exception as e:
        return JsonResponse({"status":"failure", "message": str(e)})



def logout_user(request):
    logout(request)
    return JsonResponse({"message": "Logged out successfully"})



@csrf_exempt
@require_POST
def transfer_funds(request):
    try:
        data = json.loads(request.body)
        from_wallet_address = data["from_wallet_address"]
        to_wallet_address = data["to_wallet_address"]
        amount = Decimal(data["amount"])

        with transaction.atomic():
            try:
                # select_for_update() is used to lock the selected rows for the duration of the transaction
                from_user =Profile.objects.select_for_update().get(
                    wallet_address=from_wallet_address
                )
                to_user =Profile.objects.select_for_update().get(
                    wallet_address=to_wallet_address
                )
            except Exception as e:
                return JsonResponse(
                    {"status": "failure", "message": "Invalid wallet addresses"}
                )

            if from_user.balance >= amount:
                # F expressions are used to update the balances atomically.
                amount_float = float(amount)
                fee = add_fees(amount_float)
                fee_float = float(fee)
                
                Profile.objects.filter(wallet_address=from_wallet_address).update(
                    balance=F("balance") - amount_float
                )
                
                Profile.objects.filter(wallet_address=from_wallet_address).update(
                    balance=F("balance") - fee_float
                )
                
                Profile.objects.filter(wallet_address=to_wallet_address).update(
                    balance=F("balance") + amount_float
                )
   

                message = f"An amount of {amount} has been transferred from {from_wallet_address} to {to_wallet_address}"

                return JsonResponse({"status": "success", "message": message, "fee": fee})
            else:
                return JsonResponse(
                    {"status": "failure", "message": "Insufficient balance"}
                )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})



@require_POST
def create_escrow(request):
    try:
        data = json.loads(request.body)
        name = data["name"]
        escrow_data = {
            "name":data["name"],
            "seller_id":data["seller_id"],
            "seller_contact":data["seller_contact"],
            "payment_method":data["payment_method"],
            "rate":data["rate"],
            
        }
        existing_escrow = Escrow.objects.filter(name=name)
        if existing_escrow.exists():
            return JsonResponse({"status": "error", "message":"An escrow already exists using the name provided"})
        else:
            Escrow.objects.create(**escrow_data)
            return JsonResponse({"status": "success", "message":f"Escrow {name} created successfully"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
    
    


@require_POST
@transaction.atomic
def deposit_escrow(request):
    data = json.loads(request.body)
    escrow_id = data["escrow_id"]
    seller_wallet = data["seller_wallet"]
    amount = data["amount"]
    try:
        escrow = get_escrow(escrow_id)
        seller =Profile.objects.select_for_update().get(wallet_address=seller_wallet)
        amounts = Decimal(amount)
        btc_price = BTC.objects.values("crypto").filter(fiat="USD").latest("date")
        btc_value = amounts * Decimal(btc_price["crypto"])
        escrow.usd_amount = escrow.btc_balance * Decimal(btc_price["crypto"])

        if seller.btc_balance >= btc_value:
            escrow.Funds += amounts
            escrow.btc_balance += btc_value
            escrow.usd_amount += amounts
            seller.btc_balance -= btc_value
            escrow.save()
            seller.save()
            return JsonResponse({"status": "success","message": " Escrow Deposit successful"})
        else:
            return JsonResponse(
                {"status": "failure", "message": "Insufficient BTC balance"}
            )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@require_POST
@transaction.atomic
def buy_from_escrow(request):
    try:
        data = json.loads(request.body)
        escrow_id = data["escrow_id"]
        amount = data["amount"]
        buyer_id = data["buyer_id"]
        payment_method = data["payment_method"]
        escrow = get_escrow(escrow_id)
        buyer =get_user(buyer_id)
        seller_id = escrow.seller_id
        amounts = Decimal(amount)
        btc_price = BTC.objects.values("crypto").filter(fiat="USD").latest("date")
        btc_value = amounts * Decimal(btc_price["crypto"])
        seller = get_user(seller_id)
        escrow.is_held = True
        
        held_coin = {
        "escrow_id":escrow_id,
        "buyer_id":buyer_id,
        "seller_id":seller_id,
        "usd_amount":amounts,
        "btc_amount":btc_value,
        "payment_method":payment_method,
        }
        Held_Coin.objects.create(**held_coin)
        Notify_seller(seller.email)
        
        return JsonResponse({"status": "success","message":f"Btc Purchase of {amount}$ from {escrow.name} has been initiated successfully"})
      

    except Exception as e:
        return JsonResponse({"status":"error","message":str(e)})

@require_POST
@transaction.atomic
def buyer_complete_escrow(request):

    data = json.loads(request.body)
    buyer_id = data["buyer_id"]
    seller_id = data["seller_id"]
    order_id = data["order_id"]
    try:
        held_coin= get_held_coin(order_id)
        seller =  get_user(seller_id)
    except Exception as e:
        logger.warning(str(e))
        return JsonResponse({"status": "failure", "message": "Transaction not found."})

    if not held_coin.buyer_is_complete:
        # Mark held_coin as complete
        held_coin.buyer_is_complete = True
        held_coin.completed_at = timezone.now()
        seller.isNotified = True
        seller.save()
        held_coin.save()
        Notify_seller(seller.email)

        return JsonResponse({"status": "success", "message": "Seller Notified, Your btc will be released once seller accepts."})
    else:
        return JsonResponse({"status": "failure", "message": "Transaction is already completed."})
    

@require_POST
@transaction.atomic
def seller_release_coin(request):
    data = json.loads(request.body)
    seller_id = data["seller_id"]
    order_id = data["order_id"]

    try:
        held_coin = get_held_coin(order_id)
        escrow_id = held_coin.escrow_id

        if seller_id == held_coin.seller_id:
            escrow = get_escrow(escrow_id)
            buyer = get_buyer(held_coin.buyer_id)
            btc_value = calculate_btc_value(held_coin.usd_amount)

            if not held_coin.seller_is_complete:
                complete_transaction(held_coin, escrow, buyer, btc_value)
                Notify_buyer(buyer.email)
                return JsonResponse({"status": "success", "message": "Coin released successfully."})
            else:
                return JsonResponse({"status": "failure", "message": "Transaction is already completed."})
        else:
            return JsonResponse({"status": "failure", "message": "Transaction not found."})
    except Exception as e:
        return JsonResponse({"status": "failure", "message": str(e)})



@require_GET
def get_escrow_by_user_id(request, user_id):
    try:
        escrow = get_escrow(user_id)
        response = {
            "escrow_id": escrow.escrow_uid,
            "escrow_name":escrow.name,
            "usd_amount": escrow.usd_amount,
            "seller_id": escrow.seller_id,
            "btc_balance": escrow.btc_balance,
            "withdrawable_funds": escrow.Funds,
            "is_complete": escrow.is_complete,
            "is_held": escrow.is_held,
            "created_at": escrow.created_at,
            "completed_at": escrow.completed_at,
        }
        return JsonResponse(response)
    except Escrow.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Escrow not found"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
    

@require_GET
def get_all_escrows(request):
    try:
        escrows = Escrow.objects.all()
        response = []
        for escrow in escrows:
            response.append(
                {
                    "escrow_id": escrow.escrow_uid,
                    "escrow_name": escrow.name,
                    "usd_amount": escrow.usd_amount,
                    "seller_id": escrow.seller_id,
                    "btc_balance": escrow.btc_balance,
                    "withdrawable_funds": escrow.Funds,
                    "rate":escrow.rate,
                    "payment_method":escrow.payment_method,
                    "is_complete": escrow.is_complete,
                    "is_held": escrow.is_held,
                    "created_at": escrow.created_at,
                    "completed_at": escrow.completed_at,
                }
            )
        return JsonResponse({"status": "success", "escrows": response})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
    

@require_GET
def get_escrow_by_id(request, escrow_id):
    try:
        escrow = get_escrow(escrow_id)
        merchant = get_user(escrow.seller_id)
        response = {
            "escrow_id": escrow.escrow_uid,
            "escrow_name":escrow.name,
            "usd_amount": escrow.usd_amount,
            "seller_id": escrow.seller_id,
            "btc_balance": escrow.btc_balance,
            "withdrawable_funds": escrow.Funds,
            "rate":escrow.rate,
            "payment_method":escrow.payment_method,
            "merchant": f"{merchant.first_name} {merchant.last_name}",
            "is_complete": escrow.is_complete,
            "is_held": escrow.is_held,
            "created_at": escrow.created_at,
            "completed_at": escrow.completed_at,
        }
        return JsonResponse(response)
    except Escrow.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Escrow not found"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
    
@require_GET
def get_all_users(request):
    try:
        users =Profile.objects.all()
        response = []
        for user in users:
            response.append(
                {
                    "id": user.id,
                    "uid": user.uid,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "wallet_address": user.wallet_address,
                    "balance": user.balance,
                    "btc_balance": user.btc_balance,
                }
            )
        return JsonResponse({"status": "success", "users": response})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
