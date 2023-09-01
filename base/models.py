from django.db import models
import uuid
from django.utils import timezone

class Profile(models.Model):
    email = models.EmailField(unique=True)
    uid = models.UUIDField(default=uuid.uuid4, editable=True)
    password = models.CharField(max_length=100,default="")
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    btc_balance = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    wallet_address = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    isNotified = models.BooleanField(default=False)
    first_login = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.first_name


class Escrow(models.Model):
    name = models.CharField(max_length=100)
    seller_id = models.CharField(max_length=100,blank=True,null=True)
    usd_amount = models.DecimalField(max_digits=18, decimal_places=2,default=0)
    Funds = models.DecimalField(max_digits=18, decimal_places=2,default=0)
    seller_contact = models.CharField(max_length=100,blank=True,null=True)
    btc_balance = models.DecimalField(max_digits=18, decimal_places=8,default=0)
    is_complete = models.BooleanField(default=False)
    is_held = models.BooleanField(default=False)
    escrow_uid = models.UUIDField(default=uuid.uuid4, editable=True)
    payment_method = models.CharField(max_length=100,blank=True,null=True)
    rate = models.DecimalField(max_digits=18, decimal_places=2,default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
 
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

class Held_Coin(models.Model):
    seller_id = models.CharField(max_length=100,blank=True,null=True)
    buyer_id = models.CharField(max_length=100,blank=True,null=True)
    escrow_id = models.CharField(max_length=100,blank=True,null=True)
    usd_amount = models.DecimalField(max_digits=18, decimal_places=2,default=0)
    btc_amount = models.DecimalField(max_digits=18, decimal_places=8,default=0)
    payment_method = models.CharField(max_length=100,blank=True,null=True)
    seller_is_complete = models.BooleanField(default=False)
    buyer_is_complete = models.BooleanField(default=False)
    order_id = models.UUIDField(default=uuid.uuid4, editable=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(auto_now=True)



