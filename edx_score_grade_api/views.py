from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from courseware.access import has_access
from courseware.courses import get_course_by_id
from courseware.models import StudentModule
from opaque_keys.edx.keys import CourseKey

class CourseView(APIView):
    def post(self, request, course_id, user_id, block_id):
        if request.user.is_authenticated:
            course = get_course_by_id(CourseKey.from_string(course_id))
            
            access = False
            for level in ['instructor', 'staff']:
                if has_access(request.user, level, course):
                    access=True
                    break

            if access:
                grade = request.POST.get("grade", None)
                if grade:
                    student = User.objects.get(pk=user_id)
                    module_type = request.POST.get("module_type", "edx_sg_block")
                    max_grade = request.POST.get("max_grade", 100)
                    module, created = StudentModule.objects.get_or_create(
                        course_id=course_id,
                        module_state_key=block_id,
                        student=student,
                        defaults={
                            'state': '{}',
                            'module_type': module_type,
                            'grade': grade,     
                            'max_grade': max_grade
                        })
                    if created:
                        return Response({'status':'success', 'message':'Created new StudentModule record!'})
                    module.grade = int(grade)
                    module.save()
                    return Response({'status':'success', 'message':'Updated StudentModule record!'})
                else:
                    return Response({'status':'error', 'message':'You need to send grade!'})
            else:
                return Response({'status':'error', 'message':'You need to be instructor or staff on course!'})
        else:
            return Response({'status':'error', 'message':'You need to logged in!'})

