from random import randint

from django import forms
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.base import TemplateView, View
from django.views.generic import ListView
from .models import Request, Volunteer, DistrictManager, Contributor, DistrictNeed
from .models import ReliefCenter, ReliefCampDemand, CollectionCenterSupply, SupplyTransaction, SupplyTransactionLog
import django_filters
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.http import HttpResponseRedirect


class CreateRequest(CreateView):
    model = Request
    template_name = 'mainapp/request_form.html'
    fields = [
        'district',
        'location',
        'requestee',
        'requestee_phone',
        'is_request_for_others',
        'latlng',
        'latlng_accuracy',
        'needrescue',
        'detailrescue',
        'needwater',
        'detailwater',
        'needfood',
        'detailfood',
        'needcloth',
        'detailcloth',
        'needmed',
        'detailmed',
        'needkit_util',
        'detailkit_util',
        'needtoilet',
        'detailtoilet',
        'needothers'
    ]
    success_url = '/req_sucess'


class RegisterVolunteer(CreateView):
    model = Volunteer
    fields = ['name', 'district', 'phone', 'organisation', 'area', 'address']
    success_url = '/reg_success'


class RegisterContributor(CreateView):
    model = Contributor
    fields = ['name', 'district', 'phone', 'address', 'commodities']
    success_url = '/contrib_success'


class HomePageView(TemplateView):
    template_name = "home.html"


class ReqSuccess(TemplateView):
    template_name = "mainapp/req_success.html"


class RegSuccess(TemplateView):
    template_name = "mainapp/reg_success.html"


class ContribSuccess(TemplateView):
    template_name = "mainapp/contrib_success.html"


class DisclaimerPage(TemplateView):
    template_name = "mainapp/disclaimer.html"


class AboutIEEE(TemplateView):
    template_name = "mainapp/aboutieee.html"


class DistNeeds(TemplateView):
    template_name = "mainapp/district_needs.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['district_data'] = DistrictNeed.objects.all()
        return context


class RequestFilter(django_filters.FilterSet):
    class Meta:
        model = Request
        # fields = ['district', 'status', 'needwater', 'needfood', 'needcloth', 'needmed', 'needkit_util', 'needtoilet', 'needothers',]

        fields = {
            'district': ['exact'],
            'requestee': ['icontains'],
            'requestee_phone': ['exact'],
            'location': ['exact']
        }

    def __init__(self, *args, **kwargs):
        super(RequestFilter, self).__init__(*args, **kwargs)
        # at startup user doen't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()


def request_list(request):
    filter = RequestFilter(request.GET, queryset=Request.objects.all())
    req_data = filter.qs.order_by('-dateadded')
    paginator = Paginator(req_data, 100)
    page = request.GET.get('page')
    req_data = paginator.get_page(page)
    return render(request, 'mainapp/request_list.html', {'filter': filter, "data": req_data})


class DistrictManagerFilter(django_filters.FilterSet):
    class Meta:
        model = DistrictManager
        fields = ['district']

    def __init__(self, *args, **kwargs):
        super(DistrictManagerFilter, self).__init__(*args, **kwargs)
        # at startup user doen't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()


def districtmanager_list(request):
    filter = DistrictManagerFilter(request.GET, queryset=DistrictManager.objects.all())
    return render(request, 'mainapp/districtmanager_list.html', {'filter': filter})


class Maintenance(TemplateView):
    template_name = "mainapp/maintenance.html"


def mapdata(request):
    data = Request.objects.exclude(latlng__exact="").values()

    return JsonResponse(list(data), safe=False)


def mapview(request):
    return render(request, "map.html")


def dmodash(request):
    return render(request, "dmodash.html")


def dmoinfo(request):
    if ("district" not in request.GET.keys()): return HttpResponseRedirect("/")
    dist = request.GET.get("district")
    reqserve = Request.objects.all().filter(status="sup", district=dist).count()
    reqtotal = Request.objects.all().filter(district=dist).count()
    volcount = Volunteer.objects.all().filter(district=dist).count()
    conserve = Contributor.objects.all().filter(status="ful", district=dist).count()
    contotal = Contributor.objects.all().filter(district=dist).count()
    return render(request, "dmoinfo.html",
                  {"reqserve": reqserve, "reqtotal": reqtotal, "volcount": volcount, "conserve": conserve,
                   "contotal": contotal})


class AddReliefCenter(CreateView):
    model = ReliefCenter
    fields = [
        'name',
        'district',
        'center_type',
        'address',
        'latlng',
        'phone1',
        'phone2',
        'phone3',
        'no_volunteers'
    ]
    success_url = '/relief_success'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['heading'] = "Add Relief Center"
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.login_pin = randint(1000, 9999)
        obj.save()
        return HttpResponseRedirect(reverse('add_relief_success', kwargs={'pk': obj.pk}))


class AddReliefCenterSuccess(TemplateView):
    template_name = 'mainapp/relief_success.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        relief_id = self.kwargs['pk']
        response.set_cookie("id", relief_id)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        relief_id = self.kwargs['pk']
        relief_center = ReliefCenter.objects.get(pk=relief_id)
        context["id"] = relief_id
        context["pin"] = relief_center.login_pin
        return context


class ReliefCenterLoginForm(forms.Form):
    id = forms.CharField(max_length=10)
    pin = forms.IntegerField()


class ReliefCenterLogin(TemplateView):

    template_name = 'mainapp/relief_center_login.html'

    def post(self, request, *args, **kwargs):

        form = ReliefCenterLoginForm(request.POST)
        messages = []

        if form.is_valid():
            relief_id = request.POST.get("id")
            pin = request.POST.get("pin")
            relief_center = None

            try:
                relief_center = ReliefCenter.objects.get(id=id)
                if pin == relief_center.pin:
                    # TODO return to the correct page
                    pass
                else:
                    messages = ["Login error, pin is wrong"]
            except ReliefCenter.DoesNotExist:
                messages = ["Login error, id is wrong"]
        return render(request, self.template_name, {'form': form, 'messages': messages})

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['form'] = ReliefCenterLoginForm()
        return context


class UpdateReliefCenter(UpdateView):
    model = ReliefCenter
    fields = [
        'name',
        'district',
        'center_type',
        'address',
        'latlng',
        'phone1',
        'phone2',
        'phone3',
        'no_volunteers'
    ]
    success_url = '/relief_success'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['heading'] = "Update Relief Center"
        return context

    def get(self, request, *args, **kwargs):
        relief_id = request.COOKIES.get('id', None)
        if relief_id is not None:
            try:
                relief_id = ReliefCenter.objects.get(id=relief_id)
                if relief_id.pk == self.kwargs.get("id", None):
                    return super().get(self, request, args, kwargs)
                else:
                    return HttpResponseRedirect(reverse('relief_center_login'))
            except ReliefCenter.DoesNotExist:
                return HttpResponseRedirect(reverse('relief_center_login'))


# TODO doesnt work 
class ListReliefCenters(ListView):
    model = ReliefCenter
    paginate_by = 25
    template_name = 'mainapp/relief_center_list.html'

    def get_context_data(self, **kwargs):
        context =  super().get_context_data()
        context['heading'] = "List Relief Centers"
        return context

    def get_queryset(self):
        result = ReliefCenter.objects.all()
        print ("get_queryset")
        if self.request.GET.get("filter"):
            selection = self.request.GET.get("filter")
            if selection == "all":
                result = ReliefCenter.objects.all()
            else:
                result = ReliefCenter.objects.filter(district=selection)
        return result

class AddReliefCampDemand(CreateView):
    model = ReliefCampDemand
    template_name = 'mainapp/relief_camp_demand_form.html'
    fields = [
        'centerid',
        'category',
        'quantity',
        'critical',
        'quantity_type',
    ]
    success_url = '/req_sucess'


class AddCollectionCenterSupply(CreateView):
    model = CollectionCenterSupply
    template_name = 'mainapp/collection_center_supply_form.html'
    fields = [
        'centerid',
        'category',
        'quantity',
    ]
    success_url = '/req_sucess'


def relief_supply_request_list(request):
    filter = RequestFilter(request.GET, queryset=ReliefCampDemand.objects.all())
    req_data = filter.qs.order_by('-center_id')
    paginator = Paginator(req_data, 100)
    page = request.GET.get('page')
    req_data = paginator.get_page(page)
    return render(request, 'mainapp/supply_request_list.html', {'filter': filter, "data": req_data})


def relief_supply_stock_list(request):
    filter = RequestFilter(request.GET, queryset=CollectionCenterSupply.objects.all())
    req_data = filter.qs.order_by('-center_id')
    paginator = Paginator(req_data, 100)
    page = request.GET.get('page')
    req_data = paginator.get_page(page)
    return render(request, 'mainapp/supply_stock_list.html', {'filter': filter, "data": req_data})
