from django.contrib import admin
from .models import Diagnosis, MainService, Medicine, Service

admin.site.register(Diagnosis)
admin.site.register(Medicine)


class ServiceInline(admin.TabularInline):
	model = Service
	extra = 1


@admin.register(MainService)
class MainServiceAdmin(admin.ModelAdmin):
	list_display = ("name", "is_active")
	list_filter = ("is_active",)
	search_fields = ("name",)
	inlines = [ServiceInline]