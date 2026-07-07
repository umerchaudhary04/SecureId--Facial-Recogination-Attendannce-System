from django.urls import path
from . import views

urlpatterns = [
    # Root
    path('',                     views.mark_attendance_page, name='home'),
    path('dashboard/',           views.dashboard,            name='dashboard'),

    # Students
    path('students/',                      views.student_list,       name='student_list'),
    path('students/register/',             views.register_student,   name='register_student'),
    path('students/<int:student_id>/edit/',   views.edit_student,    name='edit_student'),
    path('students/<int:student_id>/delete/', views.delete_student,  name='delete_student'),
    path('students/<int:student_id>/face/',   views.capture_face,    name='capture_face'),
    path('students/<int:student_id>/report/', views.student_report,  name='student_report'),

    # Face recognition APIs
    path('api/save-face/',         views.save_face_encoding, name='save_face_encoding'),
    path('api/recognize/',         views.recognize_face_api, name='recognize_face_api'),
    path('api/confirm-attendance/', views.confirm_attendance, name='confirm_attendance'),

    # Attendance
    path('attendance/',            views.attendance_logs,     name='attendance_logs'),
    path('attendance/manual/',     views.manual_attendance,   name='manual_attendance'),
    path('attendance/export/',     views.export_csv,          name='export_csv'),
]
