from django.shortcuts import render
# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, HttpResponse
from django.db import transaction
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST,require_GET
from .models import Escrow,Profile,BTC,escrow_transaction_history
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password,check_password
from .utils import generate_random_string, add_fees
from django.middleware import csrf
from decimal import Decimal
from django.utils import timezone

import logging
from django.db.models import F
logger = logging.getLogger(__name__)


@csrf_exempt
def register_user(request):
    if request.method == "POST":
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
            "seller_id":data["seller_id"]
            
        }
        existing_escrow = Escrow.objects.filter(name=name)
        if existing_escrow.exists():
            return JsonResponse({"status": "error", "message":"An escrow already exists using the name provided"})
        else:
            Escrow.objects.create(**escrow_data)
            return JsonResponse({"status": "success", "message":"Escrow created successfully"})
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
        escrow = Escrow.objects.select_for_update().get(escrow_uid =escrow_id)
        seller =Profile.objects.select_for_update().get(wallet_address=seller_wallet)
        amounts = Decimal(amount)
        btc_price = BTC.objects.values("crypto").filter(fiat="USD").latest("date")
        btc_value = amounts * Decimal(btc_price["crypto"])
        escrow.usd_amount = escrow.btc_balance * Decimal(btc_price["crypto"])

        if seller.btc_balance >= btc_value:
            escrow.Funds += amounts
            escrow.btc_balance += btc_value
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

        escrow = Escrow.objects.select_for_update().get(escrow_uid=escrow_id)
        buyer =Profile.objects.select_for_update().get(uid=buyer_id)
        amounts = Decimal(amount)
        btc_price = BTC.objects.values("crypto").filter(fiat="USD").latest("date")
        btc_value = amounts * Decimal(btc_price["crypto"])
        if buyer.balance >= btc_value:
            escrow.is_complete = True
            escrow.Funds += amounts
            escrow.btc_balance -= btc_value
            escrow.usd_amount -= amounts
            escrow.usd_amount -= btc_value
            buyer.btc_balance += btc_value
            buyer.balance -= amounts
            escrow.save()
            buyer.save()

            escrow_history = {
            "escrow_id":escrow_id,
            "buyer_id":buyer_id,
            "seller_id":escrow.seller_id,
            "amount":amount,
            "btc_balance":btc_value,
            "is_complete":  escrow.is_complete,
            "is_held": escrow.is_held,
            "created_at":escrow.created_at,
            "completed_at":escrow.completed_at,
            }
            escrow_transaction_history.objects.create(**escrow_history)
            return JsonResponse({"status": "success"})
        else:
            escrow.is_complete = False
            return JsonResponse(
                {"status": "failure", "message": "Insufficient BTC balance"}
            )

    except Exception as e:
        return JsonResponse({"status":"error","message":str(e)})

@require_POST
@transaction.atomic
def withdraw_from_escrow(request):
    try:
        data = json.loads(request.body)
        escrow_id = data["escrow_id"]
        amount = data["amount"]
        seller_id = data["seller_id"]
    
        escrow = Escrow.objects.select_for_update().get(escrow_uid=escrow_id)
        seller =Profile.objects.select_for_update().get(uid=seller_id)
        print(type(seller.uid))
        print(type(escrow.seller_id))
        amounts = Decimal(amount)
        btc_price = BTC.objects.values("crypto").filter(fiat="USD").latest("date")
        btc_value = amounts * Decimal(btc_price["crypto"])

        if  str(seller.uid) == escrow.seller_id and escrow.Funds >= amounts:
            escrow.Funds -= amounts
            seller.balance += amounts
            escrow.btc_balance -= btc_value
            escrow.save()
            seller.save()
            return JsonResponse({"status": "success"})
        else:
            return JsonResponse(
                {"status": "failure", "message": "Insufficient funds","seller_id":escrow.seller_id,"seller":seller.uid}
            )
    except Exception as e:
        return JsonResponse({"status":"error","message":str(e)}, status=400)
    

@require_POST
@csrf_exempt
@transaction.atomic
def complete_escrow(request, escrow_id):
    try:
        escrow = Escrow.objects.select_for_update().get(escrow_uid=escrow_id)
    except Exception as e:
        logger.warning(str(e))
        return JsonResponse({"status": "failure", "message": "Escrow not found."})

    if not escrow.is_complete:
        # Mark escrow as complete
        escrow.is_complete = True
        escrow.completed_at = timezone.now()
        escrow.save()

        return JsonResponse({"status": "success"})
    else:
        return JsonResponse({"status": "failure", "message": "Escrow is already completed."})

@require_GET
def get_escrow_by_user_id(request, user_id):
    try:
        escrow = Escrow.objects.select_for_update().get(seller_id=user_id)
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
        escrow = Escrow.objects.select_for_update().get(escrow_uid=escrow_id)
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
