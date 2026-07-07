from django import forms
from django.utils import timezone
from .models import Student, AttendanceLog, Department


class StudentRegistrationForm(forms.ModelForm):
    class Meta:
        model  = Student
        fields = ['roll_number', 'name', 'email', 'department', 'year', 'photo']
        widgets = {
            'roll_number': forms.TextInput(attrs={'placeholder': 'e.g. CS-2021-001'}),
            'name':        forms.TextInput(attrs={'placeholder': 'Full Name'}),
            'email':       forms.EmailInput(attrs={'placeholder': 'student@college.edu'}),
        }

    def clean_roll_number(self):
        rn = self.cleaned_data['roll_number'].strip().upper()
        return rn


class AttendanceFilterForm(forms.Form):
    date_from  = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to    = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    student    = forms.ModelChoiceField(queryset=Student.objects.filter(is_active=True),
                                        required=False, empty_label='All Students')
    department = forms.ModelChoiceField(queryset=Department.objects.all(),
                                        required=False, empty_label='All Departments')
    status     = forms.ChoiceField(
        choices=[('', 'All Statuses')] + AttendanceLog.STATUS_CHOICES,
        required=False
    )


class ManualAttendanceForm(forms.ModelForm):
    class Meta:
        model  = AttendanceLog
        fields = ['student', 'date', 'entry_time', 'exit_time', 'status', 'note']
        widgets = {
            'date':       forms.DateInput(attrs={'type': 'date'}),
            'entry_time': forms.TimeInput(attrs={'type': 'time'}),
            'exit_time':  forms.TimeInput(attrs={'type': 'time'}),
            'note':       forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.now().date()
