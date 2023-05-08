from django.db import models


# Create your models here.
class File(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    ext = models.CharField(max_length=255, verbose_name='Расширение')
    path = models.FileField(verbose_name='Путь до файла')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания / загрузки")
    metatag = models.CharField(max_length=255, verbose_name='Метатэг')

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"

    def __str__(self):
        return self.name