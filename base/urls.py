from django.urls import path
from base.views import *

urlpatterns = [
    path('register/',register_user,name='register_user'),
    path('login/',login_user,name='login'),
    path('logout/',logout_user,name='logout'),
    path('transfer_funds/', transfer_funds,name='transfer_funds'),
    path('create_escrow/', create_escrow,name='create_escrow'),
    path('buyer_complete_escrow/', buyer_complete_escrow,name='complete_escrow'),
    path('seller_release_coin/', seller_release_coin,name='release_escrow'),
    path('deposit_escrow/', deposit_escrow,name='deposit_escrow'),
    path('buy_from_escrow/', buy_from_escrow,name='buy_from_escrow'),
    # path('withdraw_from_escrow/', withdraw_from_escrow,name='withdraw_from_escrow'),
    path('get_user_escrow/<str:user_id>/', get_escrow_by_user_id,name='user_escrow'),
    path('get_all_escrows/', get_all_escrows,name='get_all_escrows'),
    path('get_escrow_by_id/<str:escrow_id>/', get_escrow_by_id,name='get_escrow_by_id'),
    path('get_users/', get_all_users,name='get_users'),


]