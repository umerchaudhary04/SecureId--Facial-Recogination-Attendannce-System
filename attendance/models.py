from django.db import models
from django.utils import timezone
import json


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Student(models.Model):
    YEAR_CHOICES = [
        (1, '1st Year'),
        (2, '2nd Year'),
        (3, '3rd Year'),
        (4, '4th Year'),
    ]

    roll_number   = models.CharField(max_length=20, unique=True)
    name          = models.CharField(max_length=100)
    email         = models.EmailField(unique=True, blank=True, null=True)
    department    = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    year          = models.IntegerField(choices=YEAR_CHOICES, default=1)
    photo         = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    face_encoding = models.TextField(blank=True, null=True)   # JSON-serialised list[float]
    is_active     = models.BooleanField(default=True)
    registered_at = models.DateTimeField(default=timezone.now)

    def set_face_encoding(self, encoding_list):
        """Save a numpy face-encoding as JSON."""
        self.face_encoding = json.dumps(encoding_list)

    def get_face_encoding(self):
        """Return the face-encoding as a Python list (or None)."""
        if self.face_encoding:
            return json.loads(self.face_encoding)
        return None

    def has_face_registered(self):
        return bool(self.face_encoding)

    def attendance_percentage(self, month=None, year=None):
        """Calculate attendance % for a given month/year (defaults to current month)."""
        now = timezone.now()
        month = month or now.month
        year  = year  or now.year
        total  = AttendanceLog.objects.filter(student=self, date__month=month, date__year=year).count()
        present = AttendanceLog.objects.filter(
            student=self, date__month=month, date__year=year,
            status__in=['present', 'late']
        ).count()
        return round((present / total * 100), 1) if total else 0

    def __str__(self):
        return f"{self.name} ({self.roll_number})"

    class Meta:
        ordering = ['name']


class AttendanceLog(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('late',    'Late'),
        ('absent',  'Absent'),
        ('exit',    'Exit'),
    ]

    MARKED_VIA_CHOICES = [
        ('face',   'Face Recognition'),
        ('manual', 'Manual'),
    ]

    student    = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='logs')
    date       = models.DateField(default=timezone.now)
    entry_time = models.TimeField(null=True, blank=True)
    exit_time  = models.TimeField(null=True, blank=True)
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    marked_via = models.CharField(max_length=10, choices=MARKED_VIA_CHOICES, default='face')
    note       = models.TextField(blank=True)

    class Meta:
        ordering  = ['-date', '-entry_time']
        unique_together = ('student', 'date', 'status')  # prevent duplicate same-day same-status

    def duration(self):
        """Return hours in class (if both entry and exit are recorded)."""
        if self.entry_time and self.exit_time:
            from datetime import datetime
            entry = datetime.combine(self.date, self.entry_time)
            exit_ = datetime.combine(self.date, self.exit_time)
            diff  = exit_ - entry
            hours = diff.seconds // 3600
            mins  = (diff.seconds % 3600) // 60
            return f"{hours}h {mins}m"
        return "—"

    def __str__(self):
        return f"{self.student.name} | {self.date} | {self.status}"
