# Generated by Django 3.1.7 on 2021-08-11 07:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0014_project_discount'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='area',
            index=models.Index(fields=['room'], name='projects_ar_room_id_c63827_idx'),
        ),
        migrations.AddIndex(
            model_name='areaitem',
            index=models.Index(fields=['area'], name='projects_ar_area_id_1f5804_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['title'], name='projects_pr_title_ba614c_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['status'], name='projects_pr_status_f023cb_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['owner'], name='projects_pr_owner_i_dea3a1_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['client'], name='projects_pr_client__06571b_idx'),
        ),
        migrations.AddIndex(
            model_name='room',
            index=models.Index(fields=['project'], name='projects_ro_project_977522_idx'),
        ),
    ]
