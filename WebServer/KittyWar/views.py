from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .forms import RegistrationForm, LoginForm
from .models import *

import json, os, base64


# Index View - redirects to registration
def index_view(request):
    return HttpResponseRedirect('/kittywar/register/')


# Registration View
def register_view(request):

    if request.method == 'POST':

        form = RegistrationForm(request.POST)
        if form.is_valid():

            # Check if username already exist
            username = form.cleaned_data['username']
            if User.objects.filter(username=username).exists():

                # Warn user the username is already taken
                message = 'Username already exists'
                context = {'register_form': form, 'message': message}
                return render(request, 'register.html', context)

            # If everything is valid create user and redirect to login
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = User.objects.create_user(username, email, password)
            userprofile = UserProfile(user=user)
            userprofile.save()

            # Adds the default cards to the userprofile
            catcards = CatCard.objects.filter(default=1)

            for default_cat in catcards:
                userprofile.cats.add(default_cat.cat_id)

            return HttpResponseRedirect('/kittywar/login/?s=Registration Successful')

        else:
            message = 'Passwords fields must match'
            context = {'register_form': form, 'message': message}
            return render(request, 'register.html', context)

    else:

        # If not POST then render blank form
        form = RegistrationForm()
        return render(request, 'register.html', {'register_form': form})

@csrf_exempt
def register_mobile_view(request):

    if request.method == 'POST':

        json_data = json.loads(request.body.decode('utf-8'))

        username = json_data['username']
        if User.objects.filter(username=username).exists():
            return JsonResponse(dict(status='409'))

        email = json_data['email']
        password = json_data['password']
        user = User.objects.create_user(username, email, password)
        userprofile = UserProfile(user=user)
        userprofile.save()

        # Adds the default cards to the userprofile
        catcards = CatCard.objects.filter(default=1)

        for default_cat in catcards:
            userprofile.cats.add(default_cat.cat_id)

        return JsonResponse(dict(status='201'))

    else:
        return HttpResponseBadRequest("Bad Request - 409")


# Login View
def login_view(request):

    if request.method == 'POST':

        form = LoginForm(request.POST)
        if form.is_valid():

            # Authenticate user
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = auth.authenticate(username=username, password=password)

            if user is not None:

                auth.login(request, user)
                return HttpResponseRedirect('/kittywar/home/')
            else:
                message = 'Invalid username or password'
                context = {'login_form': form, 'message': message}
                return render(request, 'login.html', context)

    else:

        # If not POST then render blank form
        message = request.GET.get('s', '')
        form = LoginForm()
        context = {'login_form': form, 'message': message}
        return render(request, 'login.html', context)


@csrf_exempt
def login_mobile_view(request):

    if request.method == 'POST':

        json_data = json.loads(request.body.decode('utf-8'))

        username = json_data['username']
        password = json_data['password']
        user = auth.authenticate(username=username, password=password)

        if user is not None:

            userquery = UserProfile.objects.filter(user_id=user.id)
            userprofile = userquery[0]

            if userprofile is not None and not userprofile.logged_in():

                while True:

                    token = base64.b64encode(os.urandom(16)).decode('utf-8')
                    tokenquery = UserProfile.objects.filter(token=token)
                    if len(tokenquery) == 0: break

                userprofile.token = token
                userprofile.save()
                return JsonResponse(dict(status='200', token=token))

        return JsonResponse(dict(status='400'))

    else:
        return HttpResponseBadRequest("Bad Request - 400")


# Home View
@login_required(login_url='/kittywar/login/')
def home_view(request):
    template = 'home.html'
    user_profile = UserProfile.objects.get(user=request.user)
    print(request.user)
    context = {'myvar': user_profile.cats.all()}
    return render(request, template, context)

# Chance Card View
@login_required(login_url='/kittywar/login/')
def chance_view(request):

    return render(request, 'chance.html')

# play View
@login_required(login_url='/kittywar/login/')
def play_view(request):
    return render(request, 'play.html')

# ability VIew
@login_required(login_url='/kittywar/login/')
def ability_view(request):
    template = 'ability.html'
    user_profile = UserProfile.objects.get(user=request.user)
    usercats = user_profile.cats.all()
    cat_ability = []
    for cat in usercats:
        ability = AbilityCards.objects.get(ability_id=cat.ability_id)
        print(ability)
        cat_ability.append(ability)

    context = {'myvar': cat_ability}
    return render(request, template, context)

# Logout View
def logout_view(request):

    auth.logout(request)
    return HttpResponseRedirect('/kittywar/login/')
