from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Escrow, CustomUser
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from .utils import generate_random_string, send_receipient_email, send_sender_email,add_fees
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
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        email = data["email"]
        password = data["password"]
    except Exception as e:
        return JsonResponse({"message": "Invalid Credentials"}, status=400)

    if not email or not password:
        return JsonResponse({"message": "Email and password are required"}, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"message": "Invalid email format"}, status=400)

    try:
        user = CustomUser.objects.get(email=email)
    except Exception as e:
        logger.warning(str(e))
        return JsonResponse(
            {"message": "User with the provided email does not exist"}, status=401
        )

    if user.check_password(password):
        login(request, user)

        csrf_token = csrf.get_token(request)
        response_data = {
            "message": "Logged in successfully",
            "user": {
                "id": user.id,
                "uid": user.uid,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "password": user.password,
                "csrf_token": csrf_token,
                "balance": user.balance,
                "wallet_address": user.wallet_address,
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
                send_receipient_email(recipient=to_user.email, message=message)
                send_sender_email(sender=from_user.email, message=message)

                return JsonResponse({"status": "success", "message": message})
            else:
                return JsonResponse(
                    {"status": "failure", "message": "Insufficient balance"}
                )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


# views.py


@require_POST
@transaction.atomic
def create_escrow(request):
    try:
        data = json.loads(request.body)
        buyer_id = data["buyer_id"]
        seller_id = data["seller_id"]
        usd_amount = Decimal(data["usd_amount"])

        btc_amount = usd_amount * Decimal("0.00003847")  # Conversion rate

        try:
            buyer = CustomUser.objects.select_for_update().get(uid=buyer_id)
            seller = CustomUser.objects.select_for_update().get(uid=seller_id)
        except Exception as e:
            return JsonResponse(
                {"status": "failure", "message": "Invalid buyer or seller ID"}
            )

        if seller.btc_balance >= btc_amount:
            Escrow.objects.create(buyer=buyer, seller=seller, amount=btc_amount)

            # Update balances atomically
            CustomUser.objects.filter(uid=buyer_id).update(
                btc_balance=F("btc_balance") + btc_amount
            )
            CustomUser.objects.filter(uid=seller_id).update(
                btc_balance=F("btc_balance") - btc_amount,
                balance=F("balance") + usd_amount,
            )

            return JsonResponse({"status": "success"})
        else:
            return JsonResponse(
                {"status": "failure", "message": "Insufficient BTC balance"}
            )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

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
