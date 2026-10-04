from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [
    # Redirecionamento para a página de login
    path('accounts/login/', RedirectView.as_view(pattern_name='login', permanent=False)),
    
    # Rota principal que verifica o status de autenticação
    path('', views.home, name='home'),
    
    path('menu/', views.menu, name='menu'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('deposito/', views.deposito, name='deposito'),
    path('saque/', views.saque, name='saque'),
    path('tarefa/', views.tarefa, name='tarefa'),
    path('process-level-task/', views.process_task, name='process_level_task'),
    path('nivel/', views.nivel, name='nivel'),
    path('equipa/', views.equipa, name='equipa'),
    path('roleta/', views.roleta, name='roleta'),
    path('spin-roulette/', views.spin_roulette, name='spin_roulette'),
    path('sobre/', views.sobre, name='sobre'),
    path('perfil/', views.perfil, name='perfil'),
    path('renda/', views.renda, name='renda'),
    
    # URLs para alteração de senha
    path('change_password/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html',
        success_url='change_password_done/'
    ), name='change_password'),
    path('change_password_done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='change_password_done'),
]
