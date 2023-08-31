from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager,PermissionsMixin
import uuid
from django.utils import timezone

from django.contrib.auth.models import User



class CustomUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    uid = models.UUIDField(default=uuid.uuid4, editable=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    balance = models.DecimalField(max_digits=10, decimal_places=2,default=0.00)
    btc_balance = models.DecimalField(max_digits=18, decimal_places=8,default=0)
    wallet_address = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    def __str__(self):
        return self.first_name


class Escrow(models.Model):
    name = models.CharField(max_length=100)
    buyer_id = models.CharField(max_length=100,blank=True,null=True)
    seller_id = models.CharField(max_length=100,blank=True,null=True)
    usd_amount = models.DecimalField(max_digits=18, decimal_places=2,default=0)
    Funds = models.DecimalField(max_digits=18, decimal_places=2,default=0)
    btc_balance = models.DecimalField(max_digits=18, decimal_places=8,default=0)
    is_complete = models.BooleanField(default=False)
    is_held = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    escrow_uid = models.UUIDField(default=uuid.uuid4, editable=True)
    
    def complete(self):
        self.is_complete = True
        self.completed_at = timezone.now()
        self.save()

    def __str__(self):
        return self.name


class BTC(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    fiat = models.CharField(max_length=10)
    crypto = models.DecimalField(decimal_places=8, max_digits=18, default=0)

    def __str__(self):
        return self.fiat
    
class escrow_transaction_history(models.Model):
    escrow_id = models.UUIDField(default=uuid.uuid4, editable=True)
    buyer_id = models.CharField(max_length=100,blank=True,null=True)
    seller_id = models.CharField(max_length=100,blank=True,null=True)
    amount = models.DecimalField(max_digits=18, decimal_places=8,default=0)
    btc_balance = models.DecimalField(max_digits=18, decimal_places=8,default=0)
    is_complete = models.BooleanField(default=False)
    is_held = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    escrow_uid = models.UUIDField(default=uuid.uuid4, editable=True)
    
    def complete(self):
        self.is_complete = True
        self.completed_at = timezone.now()
        self.save()
