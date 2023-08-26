from django.urls import path
from base.views import transfer_funds,register_user

urlpatterns = [
    path('register/',register_user,name='register_user'),
    path('transfer_funds/', transfer_funds,name='transfer_funds'),
]