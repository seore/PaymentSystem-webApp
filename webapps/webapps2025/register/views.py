from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.urls import reverse
from .forms import RegisterForm


def home(request):
    if request.user.is_authenticated:
        return render(request, 'registration/home_loggedUsers.html')
    else:
        return render(request, 'registration/home_notLogged.html')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


class CustomLogin(LoginView):
    template_name = 'registration/login.html'

    def get_redirect_url(self):
        if self.request.user.is_authenticated:
            if self.request.user.is_superuser:
                return reverse('admin_dashboard')
            else:
                return reverse('dashboard')
        return super().get_redirect_url()
