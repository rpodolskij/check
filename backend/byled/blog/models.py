from django.db import models
from django.utils.translation import ugettext_lazy as _
from users.models import User

# Create your models here.


class Categories(models.Model):
    title = models.CharField(max_length=255,unique=True, verbose_name="Название категории")
    picture = models.CharField(verbose_name='Изображение', max_length=255, null=True, blank=True, default=None)
    created_at = models.DateTimeField(verbose_name="Дата создания")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.title


class Post(models.Model):
    class Statuses(models.TextChoices):
        PUBLISHED = 'PUBLISHED', _('Опубликовано')
        DRAFT = 'DRAFT', _('Неактивно')

    categories = models.ManyToManyField(Categories, default=None, blank=True, verbose_name="Категории")
    title = models.CharField(max_length=255, verbose_name="Название поста")
    slug = models.SlugField(unique=True, verbose_name="удобочитаемый идентификатор")
    status = models.CharField(max_length=9, choices=Statuses.choices, default=Statuses.DRAFT, blank=True,
                              verbose_name="Статус поста")
    text = models.TextField(blank=True, verbose_name="Текст статьи")
    picture = models.CharField(verbose_name='Изображение', max_length=255, null=True, blank=True, default=None)
    author = models.ForeignKey(User, on_delete=models.CASCADE, default=None, null=True, verbose_name="Автор поста")

    created_at = models.DateTimeField(verbose_name="Дата создания")

    class Meta:
        verbose_name = "Пост"
        verbose_name_plural = "Посты"
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title}'


class Comment(models.Model):
    text = models.TextField(verbose_name="Текст комментария")
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, null=True, verbose_name="Пользователь")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, default=None, null=True, verbose_name="Пост")

    created_at = models.DateTimeField(verbose_name="Дата создания")

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return f'Пост: {self.post.title}, Пользователь: {self.user.email}, Текст: {self.text[:80]}'
