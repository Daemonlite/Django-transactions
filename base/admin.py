from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(CustomUser)
admin.site.register(Escrow)
admin.site.register(BTC)
admin.site.register(escrow_transaction_history)
