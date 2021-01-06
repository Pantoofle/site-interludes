from django.views.generic import RedirectView
from django.urls import path
from . import views

urlpatterns = [
	path('', views.static_view, {"slug":"home"}, name = 'home'),
	path('inscription/', views.static_view, {"slug":"inscription"}, name = 'inscription'),
	path('activites/', views.static_view, {"slug":"activites"}, name = 'activites'),
	path('faq/', views.static_view, {"slug":"faq"}, name = 'FAQ'),
	path('favicon.ico', RedirectView.as_view(url='/static/imgs/favicon.ico')),
]