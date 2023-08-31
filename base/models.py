from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager,PermissionsMixin
import uuid
from django.utils import timezone



class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Hash the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    uid = models.UUIDField(default=uuid.uuid4, editable=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    balance = models.DecimalField(max_digits=10, decimal_places=2,default=0.00)
    btc_balance = models.DecimalField(max_digits=18, decimal_places=8,default=0)
    wallet_address = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='customuser_set',  # Use a unique related_name
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='customuser_set',  # Use a unique related_name
        related_query_name='user',
    )

    def __str__(self):
        return self.first_name



# models.py

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
