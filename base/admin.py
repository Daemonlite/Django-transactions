from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Profile)
admin.site.register(Escrow)
admin.site.register(BTC)
admin.site.register(escrow_transaction_history)
admin.site.register(Held_Coin)
