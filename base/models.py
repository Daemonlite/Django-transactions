from django.db import models
import uuid

# Create your models here.
class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    password = models.CharField(max_length=100)
    age = models.IntegerField(default=0)
    id_number = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    btc_wallet_address = models.CharField(max_length=100, unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2,default=0.00)
    phone_number = models.CharField(max_length=15)
    bio = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name



class Escrow_account(models.Model):
    user_id = models.ForeignKey(Profile, on_delete=models.CASCADE)
    escrow_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    btc_balance = models.DecimalField(max_digits=10, decimal_places=2)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    is_held = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.escrow_id 

