from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from event_app.models import User, Event, Registration, Category, Location
from django.utils import timezone
from datetime import datetime
import json


def index(request):
    events = Event.objects.select_related('organizer', 'location').all()
    events_data = [{
        'id': e.id, 'title': e.title, 'start_date': e.start_date.isoformat(),
        'organizer_name': e.organizer.login, 'location_name': e.location.name if e.location else '',
        'participants_count': e.registrations.count(), 'max_participants': e.max_participants,
        'is_organizer': e.organizer_id == request.session.get('user_id')
    } for e in events]
    return render(request, 'index.html', {'events_json': json.dumps(events_data)})


def events(request):
    events = Event.objects.select_related('organizer', 'category', 'location').order_by('start_date')
    search_query = request.GET.get('search', '')
    if search_query:
        events = events.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
    if request.GET.get('category'):
        events = events.filter(category_id=request.GET.get('category'))
    if request.GET.get('date_from'):
        events = events.filter(start_date__date__gte=request.GET.get('date_from'))
    user_id = request.session.get('user_id')
    for e in events:
        e.is_registered = Registration.objects.filter(event=e, participant_id=user_id).exists() if user_id else False
        e.participants_count = e.registrations.count()
    paginator = Paginator(events, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'events.html', {
        'page_obj': page_obj, 'events': page_obj, 'categories': Category.objects.all(),
        'search_query': search_query, 'category_id': request.GET.get('category'),
        'date_from': request.GET.get('date_from')
    })


def event_detail(request, event_id):
    event = get_object_or_404(Event.objects.select_related('organizer', 'category', 'location'), id=event_id)
    registrations = Registration.objects.filter(event=event).select_related('participant')
    is_registered = Registration.objects.filter(event=event, participant_id=request.session.get(
        'user_id')).exists() if request.session.get('user_id') else False
    return render(request, 'event_detail.html', {
        'event': event, 'registrations': registrations, 'participants_count': registrations.count(),
        'is_registered': is_registered
    })


def create_event(request):
    if request.session.get('user_role') != 'organizer':
        messages.error(request, 'Только организаторы могут создавать мероприятия')
        return redirect('home')
    if request.method == 'POST':
        try:
            Event.objects.create(
                title=request.POST.get('title'), description=request.POST.get('description'),
                start_date=datetime.fromisoformat(request.POST.get('start_date')),
                end_date=datetime.fromisoformat(request.POST.get('end_date')),
                organizer_id=request.session['user_id'], category_id=request.POST.get('category'),
                location_id=request.POST.get('location'),
                max_participants=int(request.POST.get('max_participants') or 0)
            )
            messages.success(request, 'Мероприятие создано!')
            return redirect('events')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    return render(request, 'create_event.html',
                  {'categories': Category.objects.all(), 'locations': Location.objects.all()})


def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.session.get('user_role') != 'admin' and event.organizer_id != request.session.get('user_id'):
        messages.error(request, 'Нет прав на редактирование')
        return redirect('event_detail', event_id=event_id)

    if request.method == 'POST':
        event.title = request.POST.get('title', event.title)
        event.description = request.POST.get('description', event.description)
        if request.POST.get('start_date'): event.start_date = datetime.fromisoformat(request.POST.get('start_date'))
        if request.POST.get('end_date'): event.end_date = datetime.fromisoformat(request.POST.get('end_date'))
        event.category_id = request.POST.get('category', event.category_id)
        event.location_id = request.POST.get('location', event.location_id)
        event.max_participants = request.POST.get('max_participants', event.max_participants)
        event.save()
        messages.success(request, 'Мероприятие обновлено')
        return redirect('event_detail', event_id=event.id)

    return render(request, 'edit_event.html',
                  {'event': event, 'categories': Category.objects.all(), 'locations': Location.objects.all()})


def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.session.get('user_role') != 'admin' and event.organizer_id != request.session.get('user_id'):
        messages.error(request, 'Нет прав на удаление')
        return redirect('event_detail', event_id=event_id)
    event.delete()
    messages.success(request, 'Мероприятие удалено')
    return redirect('events')


def register_view(request):
    if request.method == 'POST':
        if User.objects.filter(login=request.POST.get('login')).exists():
            messages.error(request, 'Логин занят')
        else:
            user = User(login=request.POST.get('login'), email=request.POST.get('email'),
                        role=request.POST.get('role', 'participant'))
            user.set_password(request.POST.get('password'))
            user.save()
            messages.success(request, 'Регистрация успешна!')
            return redirect('login')
    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        user = User.objects.filter(login=request.POST.get('login')).first()
        if user and user.check_password(request.POST.get('password')):
            request.session.update({'user_id': user.id, 'user_login': user.login, 'user_role': user.role})
            messages.success(request, f'Добро пожаловать, {user.login}!')
            return redirect('index')
        messages.error(request, 'Неверный логин или пароль')
    return render(request, 'login.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')


def my_events(request):
    if not request.session.get('user_id'):
        messages.error(request, 'Необходимо войти')
        return redirect('login')
    registrations = Registration.objects.filter(participant_id=request.session['user_id']).select_related(
        'event__organizer', 'event__location')
    return render(request, 'my_events.html', {'registrations': registrations})


def register_for_event(request, event_id):
    if not request.session.get('user_id'):
        messages.error(request, 'Необходимо войти')
        return redirect('login')
    event = get_object_or_404(Event, id=event_id)
    if Registration.objects.filter(event=event, participant_id=request.session['user_id']).exists():
        messages.info(request, 'Вы уже записаны')
    elif event.max_participants > 0 and event.registrations.count() >= event.max_participants:
        messages.error(request, 'Мест нет')
    else:
        Registration.objects.create(event=event, participant_id=request.session['user_id'])
        messages.success(request, 'Вы записаны!')
    return redirect('event_detail', event_id=event_id)


def cancel_registration(request, event_id):
    if not request.session.get('user_id'):
        return redirect('login')
    registration = Registration.objects.filter(event_id=event_id, participant_id=request.session['user_id']).first()
    if registration:
        registration.delete()
        messages.success(request, 'Регистрация отменена')
    return redirect('event_detail', event_id=event_id)