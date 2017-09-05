import json

from django.core import serializers
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from courseware.access import has_access
from courseware.courses import get_course_by_id
from courseware.models import StudentModule
from opaque_keys.edx.keys import CourseKey, UsageKey

from xmodule.modulestore.django import modulestore
from xmodule.modulestore.inheritance import own_metadata

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
                    'state': module.state,
                    'grade': module.grade,     
                    'max_grade': module.max_grade
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
                if grade is not None and grade>=0:
                    grade = float(grade)
                    block_key = UsageKey.from_string(block_id)
                    student = User.objects.get(pk=user_id)
                    module_type = request.data.get("module_type", block_key.block_type)
                    if ()
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
                        if not isinstance(state, dict):
                            state = json.loads(state)
                        old_state.update(state)
                        module.state = json.dumps(old_state)
                    module.save()
                    return Response({'status':'success', 'message':'Updated StudentModule record!'})
                else:
                    return Response({'status':'error', 'message':'You need to send grade!'})
            else:
                return Response({'status':'error', 'message':'You need to be instructor or staff on course!'})
        else:
            return Response({'status':'error', 'message':'You need to logged in!'})

class CourseViewList(APIView):
    def post(self, request, course_id):
        if request.user.is_authenticated:
            course_key = CourseKey.from_string(course_id)
            course = get_course_by_id(course_key)

            access = False
            for level in ['instructor', 'staff']:
                if has_access(request.user, level, course):
                    access=True
                    break

            if access:
                module_store = modulestore()
                modules_metadata={}
                modules_list = []
                for grade_data in request.data.get("users", {}).itervalues():
                    grade = grade_data.get("grade", None)
                    if grade is not None and grade>=0:
                        grade = float(grade)
                        block_key = UsageKey.from_string(grade_data.get("block_id", None))
                        if not modules_metadata.get(str(block_key)):
                            modules_metadata[str(block_key)]=own_metadata(module_store.get_item(block_key))
                        student = User.objects.get(pk=grade_data.get("user_id", None))
                        if block_key.block_type=="edx_sg_block":
                            max_grade=modules_metadata.get("points",None)
                        module_type = grade_data.get("module_type", block_key.block_type)
                        state = request.data.get("state", '{}')
                        defaults={
                                'state': state,
                                'module_type': module_type,
                                'grade': grade
                            }
                        if not max_grade:
                            max_grade = float(grade_data.get("max_grade", 100))
                        defaults["max_grade"]=max_grade
                        module, created = StudentModule.objects.get_or_create(
                            course_id=course_key,
                            module_state_key=block_key,
                            student=student,
                            defaults=defaults)
                        if created:
                            modules_list.append(module)
                            continue
                        module.grade = grade
                        if not (module.max_grade == max_grade):
                            module.max_grade = max_grade
                        if not state == '{}':
                            old_state = json.loads(module.state)
                            if not isinstance(state, dict):
                                state = json.loads(state)
                            old_state.update(state)
                            module.state = json.dumps(old_state)
                        module.save()
                        modules_list.append(module)
                    else:
                        return Response({'status':'error', 'message':'You need to send grade!'})
                data_saved = serializers.serialize('json', modules_list)
                return Response({'status':'success', 'message':'All grades are updated!', 'data': data_saved})
            else:
                return Response({'status':'error', 'message':'You need to be instructor or staff on course!'})
        else:
            return Response({'status':'error', 'message':'You need to logged in!'})

class CourseViewPurge(APIView):
    def delete(self, request, course_id, block_id):
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
                try:
                    modules = StudentModule.objects.filter(
                        course_id=course_key,
                        module_state_key=block_key)
                    print modules
                    if len(modules)>0:
                        print "will delete!"
                        modules.delete()
                except:
                    return Response({'status':'error', 'message':'There was an error with deleting students module data!'})
                return Response({'status':'success', 'message':'All students data for block {} in a course {} were successfully deleted!'.format(course_id, block_id)})

