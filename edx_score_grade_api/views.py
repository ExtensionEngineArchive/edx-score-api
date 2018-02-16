import json

from django.core import serializers
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from xblock.runtime import KvsFieldData

from courseware.access import has_access
from courseware.courses import get_course_by_id
from courseware.model_data import DjangoKeyValueStore, FieldDataCache
from courseware.models import StudentModule
from lms.djangoapps.lms_xblock.models import XBlockAsidesConfig
from opaque_keys.edx.keys import CourseKey, UsageKey
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.inheritance import own_metadata

class CourseView(APIView):
    def get(self, request, course_id, user_id, block_id):
        if request.user.is_authenticated:
            course, course_key = get_course_from_course_id(course_id)

            if check_user_access(request.user, course):
                block_key = UsageKey.from_string(block_id)
                student = User.objects.get(pk=user_id)
                module_type = block_key.block_type
                try:
                    module_list = StudentModule.objects.filter(
                        course_id=course_key,
                        module_state_key=block_key,
                        student=student)

                    if len(module_list) > 0:
                        data = {
                            'user_id':user_id,
                            'course_id': course_id,
                            'module_type': module_type,
                            'state': module_list[0].state,
                            'grade': module_list[0].grade,
                            'max_grade': module_list[0].max_grade
                        }
                    else:
                        data = {}

                    return Response({'status':'success', 'data':data})
                except:
                    return Response({'status':'error', 'message':'There was an error with fetching student module data!'})

    def post(self, request, course_id, user_id, block_id):
        if request.user.is_authenticated:
            course, course_key = get_course_from_course_id(course_id)

            if check_user_access(request.user, course):
                grade = request.data.get("grade", None)
                if grade is not None and grade>=0:
                    module_store = modulestore()
                    grade = float(grade)
                    block_key = UsageKey.from_string(block_id)
                    student = User.objects.get(pk=user_id)
                    module_type = request.data.get("module_type", block_key.block_type)
                    metadata = own_metadata(module_store.get_item(block_key))
                    if metadata.get("points"):
                        max_grade = float(metadata.get("points",100))
                    else:
                        max_grade = float(request.data.get("max_grade", 100))
                    state = request.data.get("state")
                    module, created = StudentModule.objects.get_or_create(
                        course_id=course_key,
                        module_state_key=block_key,
                        student=student,
                        defaults={
                            'state': state or '{}',
                            'module_type': module_type,
                            'grade': grade,
                            'max_grade': max_grade
                        })
                    if created:
                        return Response({'status':'success', 'message':'Created new StudentModule record!'})
                    module.grade = grade
                    if not (module.max_grade == max_grade):
                        module.max_grade = max_grade
                    module = student_module_state_updater(module, state)
                    module.save()
                    return Response({'status':'success', 'message':'Updated StudentModule record!'})
                else:
                    return Response({'status': 'error', 'message': 'Empty manual grade cells are not permitted.'})
            else:
                return Response({'status':'error', 'message':'You need to be instructor or staff on course!'})
        else:
            return Response({'status':'error', 'message':'You need to logged in!'})


class CourseViewList(APIView):
    def _toggle_grades_published(self, course, student, descriptor, is_published):
        """ Publish/unpublish grades that were given by an XBlock. """
        field_data_cache_real_user = FieldDataCache.cache_for_descriptor_descendents(
            course.id,
            student,
            descriptor,
            asides=XBlockAsidesConfig.possible_asides()
        )
        student_data_real_user = KvsFieldData(DjangoKeyValueStore(field_data_cache_real_user))
        student_data_real_user.set(descriptor, 'grades_published', is_published)

    def post(self, request, course_id):
        if request.user.is_authenticated:
            course, course_key = get_course_from_course_id(course_id)

            if check_user_access(request.user, course):
                module_store = modulestore()
                modules_metadata = {}
                modules_list = []

                for grade_data in request.data.get("users", {}).itervalues():
                    grade = grade_data.get("grade", None)

                    if grade is not None and grade >= 0:
                        block_key = UsageKey.from_string(grade_data.get('block_id', None))
                        grade = float(grade)
                        max_grade = float(grade_data.get('max_grade', None))
                        module_type = grade_data.get('module_type', block_key.block_type)
                        state = grade_data.get('state', {})
                        student = User.objects.get(pk=grade_data.get('user_id', None))

                        if grade_data.get('remove_adjusted_grade', False):
                            section_block_id = grade_data.get('section_block_id', None)
                            section_block_key = UsageKey.from_string(section_block_id) if section_block_id else block_key

                            StudentModule.objects.filter(
                                course_id=course_key,
                                module_state_key=section_block_key,
                                student=student,
                            ).delete()

                            if not section_block_id:
                                continue

                        if not modules_metadata.get(str(block_key)):
                            modules_metadata[str(block_key)] = own_metadata(module_store.get_item(block_key))

                        if not max_grade and block_key.block_type == "edx_sg_block":
                            max_grade = modules_metadata.get(str(block_key)).get("points", None)

                        if not max_grade:
                            max_grade = 100

                        defaults = {
                                'state': json.dumps(state, ensure_ascii=True) or '{}',
                                'module_type': module_type,
                                'grade': grade,
                                'max_grade': max_grade
                            }
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

                        module = student_module_state_updater(module, state)
                        module.save()
                        modules_list.append(module)
                    else:
                        return Response({'status': 'error', 'message': 'Empty manual grade cells are not permitted.'})
                data_saved = serializers.serialize('json', modules_list)

                visibility_data = request.data.get('visibility')
                if visibility_data:
                    block_key = UsageKey.from_string(visibility_data.get('block_id'))
                    descriptor = module_store.get_item(block_key)
                    is_published = json.loads(visibility_data.get('visibility'))
                    self._toggle_grades_published(course, request.user, descriptor, is_published)

                return Response({'status': 'success', 'message': 'All grades are updated!', 'data': data_saved})
            else:
                return Response({'status': 'error', 'message': 'You need to be instructor or staff on course!'})
        else:
            return Response({'status': 'error', 'message': 'You need to logged in!'})

class CourseViewPurge(APIView):
    def delete(self, request, course_id, block_id):
        if request.user.is_authenticated:
            course, course_key = get_course_from_course_id(course_id)

            if check_user_access(request.user, course):
                block_key = UsageKey.from_string(block_id)
                try:
                    modules = StudentModule.objects.filter(
                        course_id=course_key,
                        module_state_key=block_key)
                    print modules
                    if len(modules)>0:
                        modules.delete()
                except:
                    return Response({'status':'error', 'message':'There was an error with deleting students module data!'})
                return Response({'status':'success', 'message':'All students data for block {} in a course {} were successfully deleted!'.format(course_id, block_id)})

def student_module_state_updater(module, state):
    if state:
        try:
            old_state = json.loads(module.state)
        except Exception as e:
            old_state = {}
        try:
            if not isinstance(state, dict):
                state = json.loads(state)
        except Exception as e:
            return module
        old_state.update(state)
        module.state = json.dumps(old_state, ensure_ascii=True)
    return module

def check_user_access(user, course):
    for level in ['instructor', 'staff']:
        if has_access(user, level, course):
            return True
    return False

def get_course_from_course_id(course_id):
    course_key = CourseKey.from_string(course_id)
    course = get_course_by_id(course_key)
    return course, course_key
