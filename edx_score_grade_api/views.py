import json
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from courseware.access import has_access
from courseware.courses import get_course_by_id
from courseware.models import StudentModule
from opaque_keys.edx.keys import CourseKey, UsageKey

class CourseView(APIView):
    def get(self, request, course_id, user_id, block_id):
        if request.user.is_authenticated:
            course_key = CourseKey.from_string(course_id)
            course = get_course_by_id(course_key)
            
            access = False
            for level in ['instructor', 'staff']:
                if has_access(request.user, level, course):
                    access=True
                    break

            if access:
                block_key = UsageKey.from_string(block_id)
                student = User.objects.get(pk=user_id)
                module_type = block_key.block_type
                try:
                    module = StudentModule.objects.get(
                        course_id=course_key,
                        module_state_key=block_key,
                        student=student)
                except:
                    return Response({'status':'error', 'message':'There was an error with fetching student module data!'})
                data = {
                    'user_id':user_id,
                    'course_id': course_id,
                    'module_type': module_type,
                    'state': modue.state
                }
                return Response({'status':'success', 'data':data})

    def post(self, request, course_id, user_id, block_id):
        if request.user.is_authenticated:
            course_key = CourseKey.from_string(course_id)
            course = get_course_by_id(course_key)
            
            access = False
            for level in ['instructor', 'staff']:
                if has_access(request.user, level, course):
                    access=True
                    break

            if access:
                grade = request.data.get("grade", None)
                if grade:
                    grade = float(grade)
                    block_key = UsageKey.from_string(block_id)
                    student = User.objects.get(pk=user_id)
                    module_type = request.data.get("module_type", block_key.block_type)
                    max_grade = float(request.data.get("max_grade", 100))
                    state = request.data.get("state", '{}')
                    module, created = StudentModule.objects.get_or_create(
                        course_id=course_key,
                        module_state_key=block_key,
                        student=student,
                        defaults={
                            'state': state,
                            'module_type': module_type,
                            'grade': grade,     
                            'max_grade': max_grade
                        })
                    if created:
                        return Response({'status':'success', 'message':'Created new StudentModule record!'})
                    module.grade = grade
                    if not state == '{}':
                        old_state = json.loads(module.state)
                        new_state = json.loads(state)
                        old_state.update(new_state)
                        module.state = json.dumps(old_state)
                    module.save()
                    return Response({'status':'success', 'message':'Updated StudentModule record!'})
                else:
                    return Response({'status':'error', 'message':'You need to send grade!'})
            else:
                return Response({'status':'error', 'message':'You need to be instructor or staff on course!'})
        else:
            return Response({'status':'error', 'message':'You need to logged in!'})

