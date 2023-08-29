from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Escrow, CustomUser,BTC,escrow_transaction_history
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
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
            user = CustomUser.objects.create_user(**user_data)
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
                    },
                },
                status=201,
            )

        except Exception as e:
            logger.warning(str(e))
            return JsonResponse({"message": "Enter required fields"}, status=400)





@csrf_exempt
def login_user(request):
    if request.method != "POST":
        return JsonResponse({"message": "Method Not Allowed"}, status=405)

    try:
        data = json.loads(request.body)
        email = data["email"]
        password = data["password"]
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON format"}, status=400)

    if not email or not password:
        return JsonResponse({"message": "Email and password are required"}, status=400)

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return JsonResponse({"message": "User with the provided email does not exist"}, status=401)

    authenticated_user = authenticate(request, email=email, password=password)
    if authenticated_user is not None:
        login(request, authenticated_user)

        response_data = {
            "message": "Logged in successfully",
            "user": {
                "id": authenticated_user.id,
                "email": authenticated_user.email,
                "first_name": authenticated_user.first_name,
                "last_name": authenticated_user.last_name,
                "balance": authenticated_user.balance,
                "wallet_address": authenticated_user.wallet_address,
            },
        }
        return JsonResponse(response_data)
    else:
        return JsonResponse({"message": "Invalid credentials"}, status=401)


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
                from_user = CustomUser.objects.select_for_update().get(
                    wallet_address=from_wallet_address
                )
                to_user = CustomUser.objects.select_for_update().get(
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
                
                CustomUser.objects.filter(wallet_address=from_wallet_address).update(
                    balance=F("balance") - amount_float
                )
                
                CustomUser.objects.filter(wallet_address=from_wallet_address).update(
                    balance=F("balance") - fee_float
                )
                
                CustomUser.objects.filter(wallet_address=to_wallet_address).update(
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
        seller = CustomUser.objects.select_for_update().get(wallet_address=seller_wallet)
        amounts = Decimal(amount)
        btc_price = BTC.objects.values("crypto").filter(fiat="USD").latest("date")
        btc_value = amounts * Decimal(btc_price["crypto"])

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
        buyer = CustomUser.objects.select_for_update().get(uid=buyer_id)
        amounts = Decimal(amount)
        btc_price = BTC.objects.values("crypto").filter(fiat="USD").latest("date")
        btc_value = amounts * Decimal(btc_price["crypto"])
        if buyer.balance >= btc_value:
            escrow.Funds += amounts
            escrow.btc_balance -= btc_value
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
        seller = CustomUser.objects.select_for_update().get(uid=seller_id)
        print(type(seller.uid))
        print(type(escrow.seller_id))
        amounts = Decimal(amount)
        btc_price = BTC.objects.values("crypto").filter(fiat="USD").latest("date")
        btc_value = amounts * Decimal(btc_price["crypto"])
        if  str(seller.uid) == escrow.seller_id and escrow.Funds >= amounts:
            escrow.Funds -= amounts
            seller.balance += amounts
            escrow.save()
            seller.save()
            return JsonResponse({"status": "success"})
        else:
            return JsonResponse(
                {"status": "failure", "message": "Insufficient funds","seller_id":escrow.seller_id,"seller":seller.uid}
            )
    except Exception as e:
        return JsonResponse({"status":"error","message":str(e)}, status=400)

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
