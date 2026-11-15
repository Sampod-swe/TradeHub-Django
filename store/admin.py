from django.contrib import admin
from .models import Category, Product, Comment, Notification, UserProfile
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
admin.site.register(Product)
admin.site.register(Comment)
admin.site.register(Notification)
admin.site.register(UserProfile)