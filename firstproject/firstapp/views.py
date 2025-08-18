from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views import View
from .forms import ReservationForm
from .models import TAform
# Create your views here.
def hello_world(request):
    return HttpResponse("Again Hello World")


class HelloEthiopia(View):
    def get(self, request):
        return HttpResponse("Again Hello Ethiopia")
    

def home(request):
    form = ReservationForm()            

    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse("success")
        
    return render(request, 'index.html', {'form' : form})

from django.shortcuts import render, redirect
from .models import TAform

def taform_view(request):
    if request.method == 'POST':
        TAform.objects.create(
            introduction=request.POST.get('introduction'),
            goals=request.POST.get('goals'),
            materials=request.POST.get('materials'),
            instructions=request.POST.get('instructions'),
            observation=request.POST.get('observation'),
            tips=request.POST.get('tips'),
            extensions=request.POST.get('extensions'),
            resources=request.POST.get('resources'),
            comments=request.POST.get('comments'),
            status_tracking=request.POST.get('status_tracking'),
            current_status=request.POST.get('current_status'),
        )
        return redirect('taform')  # Redirect to the same page after submission

    return render(request, 'taform.html')