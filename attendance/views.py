"""
SecureID – Views
"""

import csv
import io
import json
import logging
from datetime import datetime, date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .face_utils import (
    encode_face_from_b64,
    encode_face_from_file,
    find_matching_student,
    check_face_quality,
    base64_to_numpy,
    FACE_RECOGNITION_AVAILABLE,
)
from .forms import StudentRegistrationForm, AttendanceFilterForm, ManualAttendanceForm
from .models import Student, AttendanceLog, Department

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    today = timezone.now().date()
    now   = timezone.now()

    total_students  = Student.objects.filter(is_active=True).count()
    registered_face = Student.objects.filter(is_active=True, face_encoding__isnull=False).exclude(face_encoding='').count()

    # Today's stats
    today_logs     = AttendanceLog.objects.filter(date=today)
    present_today  = today_logs.filter(status__in=['present', 'late']).values('student').distinct().count()
    late_today     = today_logs.filter(status='late').count()
    absent_today   = total_students - present_today

    # Recent logs (last 10)
    recent_logs = AttendanceLog.objects.select_related('student').order_by('-date', '-entry_time')[:10]

    # Weekly presence (last 7 days)
    weekly_data = []
    for i in range(6, -1, -1):
        d     = today - timedelta(days=i)
        count = AttendanceLog.objects.filter(date=d, status__in=['present', 'late']).values('student').distinct().count()
        weekly_data.append({'day': d.strftime('%a'), 'count': count, 'date': str(d)})

    # Department-wise attendance today
    dept_stats = []
    for dept in Department.objects.all():
        dept_students = Student.objects.filter(department=dept, is_active=True).count()
        dept_present  = today_logs.filter(
            student__department=dept, status__in=['present', 'late']
        ).values('student').distinct().count()
        if dept_students:
            dept_stats.append({
                'name': dept.name,
                'total': dept_students,
                'present': dept_present,
                'pct': round(dept_present / dept_students * 100),
            })

    context = {
        'total_students':  total_students,
        'registered_face': registered_face,
        'present_today':   present_today,
        'late_today':      late_today,
        'absent_today':    absent_today,
        'recent_logs':     recent_logs,
        'weekly_data':     json.dumps(weekly_data),
        'dept_stats':      dept_stats,
        'today':           today,
        'face_lib_status': FACE_RECOGNITION_AVAILABLE,
    }
    return render(request, 'attendance/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Student Management
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def student_list(request):
    students = Student.objects.select_related('department').filter(is_active=True)
    query    = request.GET.get('q', '')
    dept_id  = request.GET.get('dept', '')

    if query:
        students = students.filter(Q(name__icontains=query) | Q(roll_number__icontains=query))
    if dept_id:
        students = students.filter(department_id=dept_id)

    departments = Department.objects.all()
    today       = timezone.now().date()

    # Annotate each student with today's attendance status
    for student in students:
        log = AttendanceLog.objects.filter(student=student, date=today).first()
        student.today_status = log.status if log else 'absent'

    context = {
        'students':    students,
        'departments': departments,
        'query':       query,
        'dept_id':     dept_id,
    }
    return render(request, 'attendance/student_list.html', context)


@login_required
def register_student(request):
    """Step 1: Fill student info form."""
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save(commit=False)
            # If a photo was uploaded, try to encode directly
            if student.photo:
                encoding = encode_face_from_file(student.photo)
                if encoding:
                    student.set_face_encoding(encoding)
            student.save()
            messages.success(request, f'Student {student.name} registered! Now capture their face.')
            return redirect('capture_face', student_id=student.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = StudentRegistrationForm()

    return render(request, 'attendance/register_student.html', {'form': form})


@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            student = form.save(commit=False)
            if 'photo' in request.FILES:
                encoding = encode_face_from_file(student.photo)
                if encoding:
                    student.set_face_encoding(encoding)
            student.save()
            messages.success(request, f'Student {student.name} updated.')
            return redirect('student_list')
    else:
        form = StudentRegistrationForm(instance=student)

    return render(request, 'attendance/register_student.html', {'form': form, 'student': student})


@login_required
def delete_student(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    if request.method == 'POST':
        student.is_active = False
        student.save()
        messages.success(request, f'{student.name} removed from the system.')
    return redirect('student_list')


@login_required
def capture_face(request, student_id):
    """Step 2: Webcam face capture for a specific student."""
    student = get_object_or_404(Student, pk=student_id)
    return render(request, 'attendance/capture_face.html', {'student': student})


@login_required
@require_POST
@csrf_exempt
def save_face_encoding(request):
    """AJAX: receive base64 frame, encode face, save to student."""
    data       = json.loads(request.body)
    student_id = data.get('student_id')
    b64_frame  = data.get('frame')

    student = get_object_or_404(Student, pk=student_id)
    img     = base64_to_numpy(b64_frame)

    if img is None:
        return JsonResponse({'success': False, 'error': 'Could not decode image.'})

    quality = check_face_quality(img)
    if not quality['ok']:
        return JsonResponse({'success': False, 'error': ' | '.join(quality['issues'])})

    encoding = encode_face_from_b64(b64_frame)
    if encoding is None:
        return JsonResponse({'success': False, 'error': 'No face detected. Look directly at the camera.'})

    student.set_face_encoding(encoding)
    student.save()
    return JsonResponse({'success': True, 'message': f'Face registered for {student.name}!'})


# ─────────────────────────────────────────────────────────────────────────────
# Mark Attendance (Face Recognition)
# ─────────────────────────────────────────────────────────────────────────────

def mark_attendance_page(request):
    """Public-facing attendance terminal page."""
    return render(request, 'attendance/mark_attendance.html')


@csrf_exempt
@require_POST
def recognize_face_api(request):
    """
    AJAX endpoint for real-time face recognition.
    Receives base64 webcam frame → returns matched student info.
    """
    try:
        data      = json.loads(request.body)
        b64_frame = data.get('frame')

        if not b64_frame:
            return JsonResponse({'success': False, 'error': 'No frame data.'})

        students   = Student.objects.filter(is_active=True, face_encoding__isnull=False).exclude(face_encoding='')
        student, confidence = find_matching_student(b64_frame, students)

        if student is None:
            return JsonResponse({'success': False, 'error': 'Face not recognised. Please try again.'})

        # Check if already marked today
        today = timezone.now().date()
        now   = timezone.now().time()

        existing = AttendanceLog.objects.filter(student=student, date=today, status__in=['present', 'late']).first()

        if existing:
            # Check if this is an exit
            exit_log = AttendanceLog.objects.filter(student=student, date=today, status='exit').first()
            if not exit_log:
                return JsonResponse({
                    'success':     True,
                    'already_in':  True,
                    'student_id':  student.pk,
                    'name':        student.name,
                    'roll':        student.roll_number,
                    'photo':       student.photo.url if student.photo else None,
                    'status':      existing.status,
                    'entry_time':  existing.entry_time.strftime('%H:%M') if existing.entry_time else '',
                    'confidence':  confidence,
                })

        # Determine status
        late_hour = getattr(settings, 'LATE_ENTRY_THRESHOLD_HOUR', 9)
        late_min  = getattr(settings, 'LATE_ENTRY_THRESHOLD_MINUTE', 0)
        status = 'late' if (now.hour > late_hour or (now.hour == late_hour and now.minute > late_min)) else 'present'

        return JsonResponse({
            'success':    True,
            'already_in': False,
            'student_id': student.pk,
            'name':       student.name,
            'roll':       student.roll_number,
            'dept':       student.department.name if student.department else '',
            'year':       student.get_year_display(),
            'photo':      student.photo.url if student.photo else None,
            'status':     status,
            'confidence': confidence,
        })

    except Exception as e:
        logger.error(f"recognize_face_api error: {e}")
        return JsonResponse({'success': False, 'error': 'Server error. Please try again.'})


@csrf_exempt
@require_POST
def confirm_attendance(request):
    """
    AJAX: called after user confirms the matched face.
    Saves AttendanceLog entry.
    """
    try:
        data       = json.loads(request.body)
        student_id = data.get('student_id')
        action     = data.get('action', 'entry')   # 'entry' or 'exit'

        student = get_object_or_404(Student, pk=student_id)
        today   = timezone.now().date()
        now     = timezone.now().time()

        if action == 'exit':
            log = AttendanceLog.objects.filter(student=student, date=today).first()
            if log:
                try:
                    AttendanceLog.objects.create(
                        student=student, date=today,
                        exit_time=now, status='exit', marked_via='face'
                    )
                    log.exit_time = now
                    log.save()
                except Exception:
                    pass
            return JsonResponse({'success': True, 'message': f'Exit recorded for {student.name}.'})

        # Entry
        late_hour = getattr(settings, 'LATE_ENTRY_THRESHOLD_HOUR', 9)
        late_min  = getattr(settings, 'LATE_ENTRY_THRESHOLD_MINUTE', 0)
        status = 'late' if (now.hour > late_hour or (now.hour == late_hour and now.minute > late_min)) else 'present'

        obj, created = AttendanceLog.objects.get_or_create(
            student=student, date=today, status=status,
            defaults={'entry_time': now, 'marked_via': 'face'},
        )
        if not created:
            return JsonResponse({'success': True, 'message': f'Attendance already marked for {student.name}.'})

        return JsonResponse({
            'success': True,
            'message': f'✅ Attendance marked for {student.name} – {status.upper()}',
            'status':  status,
        })

    except Exception as e:
        logger.error(f"confirm_attendance error: {e}")
        return JsonResponse({'success': False, 'error': 'Server error.'})


# ─────────────────────────────────────────────────────────────────────────────
# Attendance Logs
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def attendance_logs(request):
    form = AttendanceFilterForm(request.GET or None)
    logs = AttendanceLog.objects.select_related('student', 'student__department').order_by('-date', '-entry_time')

    if form.is_valid():
        if form.cleaned_data.get('date_from'):
            logs = logs.filter(date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            logs = logs.filter(date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('student'):
            logs = logs.filter(student=form.cleaned_data['student'])
        if form.cleaned_data.get('department'):
            logs = logs.filter(student__department=form.cleaned_data['department'])
        if form.cleaned_data.get('status'):
            logs = logs.filter(status=form.cleaned_data['status'])

    # Paginate manually (keep simple for final year project)
    logs = logs[:200]

    context = {'form': form, 'logs': logs}
    return render(request, 'attendance/attendance_logs.html', context)


@login_required
def manual_attendance(request):
    if request.method == 'POST':
        form = ManualAttendanceForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.marked_via = 'manual'
            try:
                log.save()
                messages.success(request, 'Manual attendance saved.')
                return redirect('attendance_logs')
            except Exception:
                messages.error(request, 'Duplicate entry – this student already has this status for the selected date.')
    else:
        form = ManualAttendanceForm()

    return render(request, 'attendance/manual_attendance.html', {'form': form})


# ─────────────────────────────────────────────────────────────────────────────
# Reports & Export
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def export_csv(request):
    form = AttendanceFilterForm(request.GET or None)
    logs = AttendanceLog.objects.select_related('student', 'student__department').order_by('-date', '-entry_time')

    if form.is_valid():
        if form.cleaned_data.get('date_from'):
            logs = logs.filter(date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            logs = logs.filter(date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('student'):
            logs = logs.filter(student=form.cleaned_data['student'])
        if form.cleaned_data.get('department'):
            logs = logs.filter(student__department=form.cleaned_data['department'])
        if form.cleaned_data.get('status'):
            logs = logs.filter(status=form.cleaned_data['status'])

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="secureid_attendance.csv"'

    writer = csv.writer(response)
    writer.writerow(['Roll No', 'Name', 'Department', 'Year', 'Date', 'Entry Time', 'Exit Time', 'Status', 'Marked Via', 'Note'])

    for log in logs:
        writer.writerow([
            log.student.roll_number,
            log.student.name,
            log.student.department.name if log.student.department else '',
            log.student.get_year_display(),
            log.date,
            log.entry_time or '',
            log.exit_time  or '',
            log.status,
            log.marked_via,
            log.note,
        ])

    return response


@login_required
def student_report(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    today   = timezone.now().date()
    month   = int(request.GET.get('month', today.month))
    year    = int(request.GET.get('year',  today.year))

    logs = AttendanceLog.objects.filter(
        student=student, date__month=month, date__year=year
    ).order_by('date')

    total   = logs.count()
    present = logs.filter(status__in=['present', 'late']).count()
    late    = logs.filter(status='late').count()
    pct     = round(present / total * 100, 1) if total else 0

    context = {
        'student': student,
        'logs':    logs,
        'total':   total,
        'present': present,
        'late':    late,
        'pct':     pct,
        'month':   month,
        'year':    year,
    }
    return render(request, 'attendance/student_report.html', context)
