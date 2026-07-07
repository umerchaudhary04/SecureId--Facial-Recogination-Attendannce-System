"""
Management command: python manage.py seed_demo
Creates demo departments, students, and attendance records for testing.
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import Department, Student, AttendanceLog


DEPARTMENTS = [
    ('Computer Science', 'CS'),
    ('Electrical Engineering', 'EE'),
    ('Mechanical Engineering', 'ME'),
    ('Business Administration', 'BBA'),
]

STUDENTS = [
    ('Ahmed Ali Khan',       'CS-2024-001', 'ahmed@uni.edu',    1),
    ('Fatima Zahra Siddiqui','CS-2024-002', 'fatima@uni.edu',   1),
    ('Muhammad Usman',       'CS-2024-003', 'usman@uni.edu',    2),
    ('Ayesha Tariq',         'CS-2024-004', 'ayesha@uni.edu',   2),
    ('Bilal Hassan',         'EE-2024-001', 'bilal@uni.edu',    1),
    ('Sara Malik',           'EE-2024-002', 'sara@uni.edu',     3),
    ('Hamza Raza',           'ME-2024-001', 'hamza@uni.edu',    4),
    ('Zara Iqbal',           'BBA-2024-001','zara@uni.edu',     2),
    ('Ali Imran',            'CS-2023-001', 'ali@uni.edu',      3),
    ('Nadia Hussain',        'CS-2023-002', 'nadia@uni.edu',    4),
]


class Command(BaseCommand):
    help = 'Seed demo data: departments, students, and 30 days of attendance'

    def handle(self, *args, **kwargs):
        self.stdout.write('🌱 Seeding demo data…')

        # Superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@secureid.com', 'admin123')
            self.stdout.write('  ✅ Superuser created  →  admin / admin123')

        # Departments
        dept_objs = {}
        for name, code in DEPARTMENTS:
            dept, _ = Department.objects.get_or_create(code=code, defaults={'name': name})
            dept_objs[code] = dept
        self.stdout.write(f'  ✅ {len(DEPARTMENTS)} departments ready')

        # Students
        for name, roll, email, year in STUDENTS:
            prefix = roll.split('-')[0]
            dept   = dept_objs.get(prefix, dept_objs['CS'])
            student, created = Student.objects.get_or_create(
                roll_number=roll,
                defaults={'name': name, 'email': email, 'department': dept, 'year': year},
            )
            if created:
                self.stdout.write(f'  👤 Created: {name}')
        self.stdout.write(f'  ✅ {len(STUDENTS)} students ready')

        # Attendance – last 30 days
        today    = date.today()
        students = list(Student.objects.filter(is_active=True))
        created_count = 0

        for i in range(30, 0, -1):
            d = today - timedelta(days=i)
            if d.weekday() >= 5:  # skip weekends
                continue
            for student in students:
                rand = random.random()
                if rand < 0.05:     # 5% absent
                    status = 'absent'
                elif rand < 0.20:   # 15% late
                    status = 'late'
                else:
                    status = 'present'

                entry_h = random.randint(8, 9) if status == 'present' else random.randint(9, 11)
                entry_m = random.randint(0, 59)
                exit_h  = random.randint(15, 17)
                exit_m  = random.randint(0, 59)

                from datetime import time as dtime
                obj, c = AttendanceLog.objects.get_or_create(
                    student=student, date=d, status=status,
                    defaults={
                        'entry_time': dtime(entry_h, entry_m) if status != 'absent' else None,
                        'exit_time':  dtime(exit_h,  exit_m)  if status != 'absent' else None,
                        'marked_via': random.choice(['face', 'face', 'face', 'manual']),
                    }
                )
                if c:
                    created_count += 1

        self.stdout.write(f'  ✅ {created_count} attendance records created')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🚀 Demo data ready!'))
        self.stdout.write('   URL:      http://127.0.0.1:8000/')
        self.stdout.write('   Username: admin')
        self.stdout.write('   Password: admin123')
