from django.shortcuts import render

# Create your views here.

from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Escrow_account, Profile
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from .utils import generate_random_string


@csrf_exempt
def register_user(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            age = data.get("age")
            email = data.get("email")
            passw = data.get("password")
            full_name = data.get("full_name")
            id_number = data.get("id_number")
            address = data.get("address")
            phone_number = data.get("phone_number")

        except json.JSONDecodeError:
            return JsonResponse(
                {"message": "Invalid JSON data in the request body"}, status=400
            )

        password = make_password(passw)
        # Check if all required fields are provided and not empty
        if email and password and full_name and password:
            try:
                # Check if the provided email is valid
                validate_email(email)
            except ValidationError:
                return JsonResponse({"message": "Invalid email format"}, status=400)
            wallet_address = generate_random_string(30)
            user = Profile.objects.create(
                email=email,
                password=password,
                full_name=full_name,
                age=age,
                id_number=id_number,
                address=address,
                phone_number=phone_number,
                btc_wallet_address=wallet_address,
            )
            response_data = {
                "message": "User created successfully",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "password": user.password,
                    "age": user.age,
                    "id_number": user.id_number,
                    "address": user.address,
                    "phone_number": user.phone_number,
                    "btc_wallet_address": user.btc_wallet_address,
                    "balance": user.balance
                },
            }
            return JsonResponse(response_data)
        else:
            return JsonResponse({"message": "All fields are required"}, status=400)

    # Return a 405 Method Not Allowed response for other request methods
    return HttpResponse(status=405)


@csrf_exempt
@require_POST
def transfer_funds(request):
    try:
        data = json.loads(request.body)
        from_wallet_address = data["from_wallet_address"]
        to_wallet_address = data["to_wallet_address"]
        amount = float(data["amount"])

        with transaction.atomic():
            from_wallet_address = get_object_or_404(
                Profile, btc_wallet_address=from_wallet_address
            )
            to_wallet_address = get_object_or_404(
                Profile, btc_wallet_address=to_wallet_address
            )

            if from_wallet_address.balance >= amount:
                from_wallet_address.balance -= amount
                to_wallet_address.balance += amount

                from_wallet_address.save()
                to_wallet_address.save()

                return JsonResponse({"status": "success"})
            else:
                return JsonResponse(
                    {"status": "failure", "message": "Insufficient balance"}
                )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


def deposit_escrow(request):
    try:
        data = json.loads(request.body)
        escrow_id = data["escrow_id"]
        amount = float(data["amount"])

        with transaction.atomic():
            escrow = get_object_or_404(Escrow_account, escrow_id=escrow_id)
            escrow.usdt_balance += amount
            escrow.save()

            user = get_object_or_404(Profile, id=data["user_id"])
            user.account_balance -= amount
            user.save()

            return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
