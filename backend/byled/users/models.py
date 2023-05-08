import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from store.models import Product, Basket


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The given email must be set')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        basket = Basket(user=user)
        basket.save()

        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class PriceLevels(models.TextChoices):
        OPT1 = 'OPT1', _('Уровень 1')
        OPT2 = 'OPT2', _('Уровень 2')
        OPT3 = 'OPT3', _('Уровень 3')
        OPT4 = 'OPT4', _('Уровень 4')
        RETAIL_NDS = 'RETAIL_NDS', _('Розница с НДС')
        RETAIL_NO_NDS = 'RETAIL_NO_NDS', _('Розница без НДС')

    class AccountTypes(models.TextChoices):
        CLIENT = 'CLIENT', _('Клиент')
        MANAGER = 'MANAGER', _('Мэнеджер')
        ADMIN = 'ADMIN', _('Администратор')

    manager = models.ForeignKey('self', on_delete=models.SET_NULL, default=None, null=True, blank=True)
    account_type = models.CharField(max_length=7, choices=AccountTypes.choices, default=AccountTypes.CLIENT,
                                    verbose_name="Тип аккаунта")
    # price_level = models.ForeignKey(
    #     'store.PriceLevel',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     verbose_name="Уровень цены",
    #     default=None
    # )
    price_level = models.CharField(
        max_length=13,
        choices=PriceLevels.choices,
        default=None,
        blank=True,
        verbose_name="Уровень цены",
        null=True
    )
    username = None
    email = models.EmailField(_('email address'), unique=True)
    is_confirmed = models.BooleanField(verbose_name="Подтвержден", default=False)
    middle_name = models.CharField(max_length=150, blank=True, verbose_name="Отчество")
    phone = models.CharField(max_length=32, blank=True, verbose_name="Номер телефона")
    company_name = models.CharField(max_length=255, blank=True, verbose_name="Название компании")
    company_address = models.CharField(max_length=255, blank=True, verbose_name="Адрес компании")
    position = models.CharField(max_length=255, blank=True, verbose_name="Должность")
    avatar = models.URLField(verbose_name='Аватар', max_length=255, null=True, blank=True, default=None)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()


class ActionEnum(models.TextChoices):
    restore = 'restore'
    confirm = 'confirm'


class KeyManager(models.Manager):
    use_in_migrations = True

    def create_key(self, email, action: ActionEnum = ActionEnum.restore):
        try:
            user = User.objects.get(email=email)
            user_action_keys = ActionKey.objects.filter(user=user)
            if user_action_keys.count() > 0:  # Удалить старые ключи, если они есть
                user_action_keys.delete()
            action_key = ActionKey(
                user=user,
                action=action,
                key=str(uuid.uuid4()),
                created_at=timezone.now(),
            )
            action_key.save()
            return action_key

        except User.DoesNotExist:
            return None


class ActionKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='action_keys', verbose_name="Пользователь")
    action = models.CharField(choices=ActionEnum.choices, max_length=64, verbose_name="Тип ключа")
    key = models.CharField(unique=True, max_length=64, verbose_name="Ключ")
    created_at = models.DateTimeField(verbose_name="Дата создания")
    objects = KeyManager()

    def __str__(self):
        return f'{self.user}: {self.action}'

    class Meta:
        verbose_name = "Секретный ключ"
        verbose_name_plural = "Секретные ключи"
