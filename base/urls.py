from django.urls import path
from base.views import *

urlpatterns = [
    path('register/',register_user,name='register_user'),
    path('login/',login_user,name='login'),
    path('logout/',logout_user,name='logout'),
    path('transfer_funds/', transfer_funds,name='transfer_funds'),
    path('create_escrow/', create_escrow,name='create_escrow'),
    path('complete_escrow/<str:escrow_id>/', complete_escrow,name='complete_escrow'),
    path('deposit_escrow/', deposit_escrow,name='deposit_escrow'),
    path('buy_from_escrow/', buy_from_escrow,name='buy_from_escrow'),
    path('withdraw_from_escrow/', withdraw_from_escrow,name='withdraw_from_escrow'),


]