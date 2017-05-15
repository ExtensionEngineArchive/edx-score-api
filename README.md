# edx-score-api
Simple way to grade edX content using api

Instalation:
 - add the repo in requirement list and install it: "-e git+https://github.com/kotky/edx-score-api.git@v0.1#egg=edx-score-api"
 - add the application in the lms/envs/common.py list as "edx_score_grade_api"
 - add the url in the lms/urls.py list as like this:
 
    urlpatterns += (
        url(r'^api/score/', include('edx_score_grade_api.urls')),
    )

Usage:
 - the api accepts POST requests in form like this:
 
 URI: /api/score/courses/<course_id>/users/<student_id>/blocks/<block_id>
 
 POST data in JSON:
   {"grade":99, "max_grade":100, "module_type":"edx_sg_block"}
 
 
 - you only need the grade in post data, the max_grade is 100 default and module_type is "edx_sg_block" by default (since this is used in connection with my other repo edx-sga that is changed to be manual placeholder hor score)
