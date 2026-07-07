from django.contrib import admin
from .models import Student, AttendanceLog, Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display  = ['roll_number', 'name', 'department', 'year', 'is_active', 'has_face_registered', 'registered_at']
    list_filter   = ['department', 'year', 'is_active']
    search_fields = ['name', 'roll_number', 'email']
    readonly_fields = ['registered_at']

    def has_face_registered(self, obj):
        return obj.has_face_registered()
    has_face_registered.boolean = True
    has_face_registered.short_description = 'Face'


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display  = ['student', 'date', 'entry_time', 'exit_time', 'status', 'marked_via']
    list_filter   = ['status', 'marked_via', 'date']
    search_fields = ['student__name', 'student__roll_number']
    date_hierarchy = 'date'
