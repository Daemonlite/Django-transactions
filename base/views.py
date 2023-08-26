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
from .utils import generate_random_string
from django.middleware import csrf
from decimal import Decimal
from django.utils import timezone

@csrf_exempt
def register_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data['email']
        password = data['password']
        first_name = data['first_name']
        last_name = data['last_name']
        address = generate_random_string(30)

        
        user = CustomUser.objects.create_user(email=email, password=password, first_name=first_name, last_name=last_name,wallet_address=address)
        
        response_data = {
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                 'uid':user.uid,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'balance':user.balance,
                'wallet_address':user.wallet_address
            }
        }
        return JsonResponse(response_data)


@csrf_exempt
def login_user(request):
   
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON data in the request body'}, status=400)

    if not email or not password:
        return JsonResponse({'message': 'Email and password are required'}, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'message': 'Invalid email format'}, status=400)

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return JsonResponse({'message': 'User with the provided email does not exist'}, status=401)

    if user.check_password(password):
        login(request, user)
        
        csrf_token = csrf.get_token(request)
        response_data = {
            'message': 'Logged in successfully',
            'user': {
                'id': user.id,
                'uid':user.uid,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'password':user.password,
                'csrf_token':csrf_token,
                'balance':user.balance,
                'wallet_address':user.wallet_address
            }
        }
        return JsonResponse(response_data)
    else:
        return JsonResponse({'message': 'Invalid credentials'}, status=401)

def logout_user(request):
    logout(request)
    return JsonResponse({'message': 'Logged out successfully'})





@csrf_exempt
@require_POST
def transfer_funds(request):
    try:
        data = json.loads(request.body)
        from_wallet_address = data["from_wallet_address"]
        to_wallet_address = data["to_wallet_address"]
        amount = Decimal(data["amount"])

        with transaction.atomic():
            from_wallet_address = get_object_or_404(
                CustomUser, wallet_address=from_wallet_address
            )
            to_wallet_address = get_object_or_404(
                CustomUser, wallet_address=to_wallet_address
            )

            if from_wallet_address.balance >= amount:
                from_wallet_address.balance -= amount
                to_wallet_address.balance += amount

                from_wallet_address.save()
                to_wallet_address.save()

                return JsonResponse({
                    "status": "success",
                    "message":f"an amount of {amount} has been transferred from {from_wallet_address.wallet_address} to {to_wallet_address.wallet_address}"
                                     })

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

        buyer = get_object_or_404(CustomUser, uid=buyer_id)
        seller = get_object_or_404(CustomUser, uid=seller_id)

        if seller.btc_balance >= btc_amount:
            escrow = Escrow.objects.create(
                buyer=buyer,
                seller=seller,
                amount=btc_amount
            )

            # Update balances
            seller.btc_balance -= btc_amount
            seller.balance += usd_amount
            buyer.btc_balance += btc_amount

            seller.save()
            buyer.save()

            return JsonResponse({"status": "success", "escrow_id": escrow.escrow_uid})
        else:
            return JsonResponse({"status": "failure", "message": "Insufficient BTC balance"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


def complete_escrow(request, escrow_id):
    escrow = get_object_or_404(Escrow, id=escrow_id)

    if not escrow.is_complete:
        # Mark escrow as complete
        escrow.is_complete = True
        escrow.completed_at = timezone.now()
        escrow.save()

        return JsonResponse({"status": "success"})
    else:
        return JsonResponse({"status": "failure", "message": "Escrow is already completed."})

