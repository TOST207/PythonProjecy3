from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password


class CustomUserManager(BaseUserManager):
    def create_user(self, login, email, password=None, **extra_fields):
        if not login:
            raise ValueError('Логин обязателен')
        if not email:
            raise ValueError('Email обязателен')
        user = self.model(login=login, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, login, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        return self.create_user(login, email, password, **extra_fields)


class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('organizer', 'Организатор'),
        ('participant', 'Участник'),
    ]
    login = models.CharField(max_length=50, unique=True, verbose_name="Логин")
    email = models.EmailField(verbose_name="Email")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant', verbose_name="Роль")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")
    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['email']
    objects = CustomUserManager()
    def __str__(self):
        return f"{self.login} ({self.role})"
    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"


class Location(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название места")
    address = models.CharField(max_length=200, verbose_name="Адрес")
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Место проведения"
        verbose_name_plural = "Места проведения"


class Event(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    start_date = models.DateTimeField(verbose_name="Начало")
    end_date = models.DateTimeField(verbose_name="Окончание")
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events', verbose_name="Организатор")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name="Категория")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, verbose_name="Место")
    max_participants = models.IntegerField(default=0, verbose_name="Макс. участников")
    def __str__(self):
        return self.title
    class Meta:
        verbose_name = "Мероприятие"
        verbose_name_plural = "Мероприятия"


class Registration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations', verbose_name="Мероприятие")
    participant = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Участник")
    registered_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата записи")
    def __str__(self):
        return f"{self.participant.login} на {self.event.title}"
    class Meta:
        verbose_name = "Регистрация"
        verbose_name_plural = "Регистрации"
        unique_together = ('event', 'participant')