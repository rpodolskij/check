from django.db import models


# Create your models here.

class Synchronization(models.Model):
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата начала')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата окончания')
    success = models.BooleanField(default=False, verbose_name='Успешно')
    is_running = models.BooleanField(default=False, verbose_name='В процессе')

    class Meta:
        verbose_name = "Синхронизация"
        verbose_name_plural = "Синхронизации"
        ordering = ['-started_at']

    def __str__(self):
        status = 'ОШИБКА'
        if self.success:
            status = 'УСПЕШНО'
        elif self.is_running:
            status = 'В ПРОЦЕССЕ'
        return f'[{status}] Дата начала: {self.started_at}, Дата окончания: {self.ended_at}'
