from django.urls import path
from base.views import transfer_funds,register_user,login_user,logout_user

urlpatterns = [
    path('register/',register_user,name='register_user'),
    path('login/',login_user,name='login'),
    path('logout/',logout_user,name='logout'),
    path('transfer_funds/', transfer_funds,name='transfer_funds'),
]