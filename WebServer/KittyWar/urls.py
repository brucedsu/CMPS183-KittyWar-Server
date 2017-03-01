from django.conf.urls import url

from . import views

app_name = 'kittywar'
urlpatterns = [

    url(r'^$',                         views.index_view,           name='index'),
    url(r'kittywar/register/$',        views.register_view,        name='register'),
    url(r'kittywar/register/mobile/$', views.register_mobile_view, name='register_mobile'),
    url(r'kittywar/login/$',           views.login_view,           name='login'),
    url(r'kittywar/login/mobile/$',    views.login_mobile_view,    name='login_mobile'),
    url(r'kittywar/logout/$',          views.logout_view,          name='logout'),
    url(r'kittywar/home/$',            views.home_view,            name='home'),
    url(r'kittywar/chance/$',          views.chance_view,          name='chance'),
    url(r'kittywar/play/$',            views.play_view,            name='play'),
    url(r'kittywar/ability/$',         views.ability_view,            name='ability'),
]
