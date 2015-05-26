import sqlite3
import os
import json
import requests
import exceptions
from pyodbc import *
from HTMLParser import HTMLParser
from sqlalchemy import create_engine, text, update, MetaData
from sqlalchemy.engine import reflection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from underscore import _
from time import sleep
from sqlalchemy.schema import (
    MetaData,
    Table,
    DropTable,
    ForeignKeyConstraint,
    DropConstraint,
    )

from models import *

# TODO: add support for pagination, or set a very high request per page
#Flag variable to collect all assessments or just narratives, etc
#True is set for pivot table information and False is set for the narrativites
collectAll = False


engine=create_engine('mssql+pyodbc://<yourDB>')

###PURGE OLD DATA
conn = engine.connect()

# the transaction only applies if the DB supports
# transactional DDL, i.e. Postgresql, MS SQL Server
trans = conn.begin()

inspector = reflection.Inspector.from_engine(engine)

# gather all data first before dropping anything.
# some DBs lock after things have been dropped in
# a transaction.

metadata = MetaData()

tbs = []
all_fks = []

for table_name in inspector.get_table_names():
    fks = []
    for fk in inspector.get_foreign_keys(table_name):
        if not fk['name']:
            continue
        fks.append(
            ForeignKeyConstraint((),(),name=fk['name'])
            )
    t = Table(table_name,metadata,*fks)
    tbs.append(t)
    all_fks.extend(fks)

for fkc in all_fks:
    conn.execute(DropConstraint(fkc))

for table in tbs:
    conn.execute(DropTable(table))

trans.commit()


###END PURGE


Session = sessionmaker(bind=engine)

session = Session()

Base.metadata.create_all(engine)


api_token = "<your canvas api token>"


#os.environ.get("CANVAS_API_KEY")
base_url = "https://YOURPREFIX.instructure.com/api/v1"
settings = {
    "params": {
        "per_page": 250
    },
    "headers": {
        "Authorization": "Bearer %s" % api_token
    }
}
#100 per page is the actual limit from Canvas

outcome_ids = []
narrative_ids = []
narrative_names = []
conduct_ids = []
conduct_names = []
attendance_ids = []
attendance_names = []
user_ids = []
user_names = []
sortable_names = []
user_sis_ids = []

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)


def getWeb(url, settings):
    read_timeout = 10.0
    success = False
    retries = 0
    while success == False:
        success = True
        try:
            r = requests.get(url, timeout=(1.0, read_timeout),
                                verify=False,
                                **settings)
        except requests.exceptions.ReadTimeout as e:
            print "                      Read Timeout, waited too long between bytes."
            success = False
            retries += 1
        except requests.exceptions.SSLError as e:
            print "                      SSL handshake timed out."
            success = False
            retries += 1
    if retries > 0:
        print "                      success after "+str(retries+1)+" attempts"
    return r

#Deactivated for testing
def strip_tags(html):
    s = MLStripper()
    try:
        s.feed(html)
        return s.get_data().encode('ascii', 'ignore')
    except:
        return html
    #html = html.encode('ascii', 'ignore')
    #return html

def parse_assessment(s, k, v, assignment, session, s_com):
    a = Assessment()
    if "narrative" in assignment.name.lower():
        a.a_type = "narrative"
    elif "conduct" in assignment.name.lower():
        a.a_type = "conduct"
    elif "academic behavior" in assignment.name.lower():
        a.a_type = "academic_behavior"
    elif "social communication" in assignment.name.lower():
        a.a_type = "social_communication"
    elif "attendance" in assignment.name.lower():
        a.a_type = "attendance"
    else:
        a.a_type = "assessment"
    a.assignment_name = assignment.name
    #a.assessment_id = assessment_id
    a.rubric_id = k
    #a.outcome_id = outcome_id
    a.assignment_id = s.assignment_id
    a.user_id = s.user_id
    a.grade = s.grade
    a.points = v["points"]
    a.comments = strip_tags(v["comments"])
    a.sub_comments = strip_tags(s_com)
    #print "   "+v["comments"]
    #if assignment:
    #    a.assignment_name = assignment.name
    temp_course = session.query(Course).filter(Course.id==assignment.course_id)
    if temp_course.count():
        a.course_name = temp_course[0].name
        #####MAKE 4th GRADE classes work
        if "4th grade room 209" in a.course_name.lower() or "4th grade room 208" in a.course_name.lower() or "4th grade room 210" in a.course_name.lower() or "4th grade room 206" in a.course_name.lower():
            if "social communication" not in a.assignment_name.lower() and "academic behavior" not in a.assignment_name.lower():
                a.course_name = "4th Grade "+a.assignment_name
        #####
        a.course_id = temp_course[0].id
        t = session.query(EnrollmentTerm).filter(EnrollmentTerm.id==temp_course[0].enrollment_term_id)
        if t.count():
            a.term = t[0].name
        e = session.query(Enrollment).filter(Enrollment.user_id==a.user_id).filter(Enrollment.course_id==temp_course[0].id)
        if e.count():
            section = session.query(Section).filter(Section.id==e[0].course_section_id)
            if section.count():
                a.section_name = section[0].name
                a.section_id = section[0].id

    a.assignment_name = assignment.name
    a.assignment_desc = assignment.description

    rubric = session.query(Rubric).filter(Rubric.rubric_id==a.rubric_id)
    if rubric.count():
        a.max_points = rubric[0].points
        a.outcome_id = rubric[0].outcome_id
        a.rubric_desc = rubric[0].description
        a.rubric_long_desc = rubric[0].long_description
        result = session.query(RubricRatings).filter(RubricRatings.parent_rubric_id==a.rubric_id).filter(RubricRatings.points==a.points)
        if result.count():
            a.rubric_result = result[0].description
        if rubric[0].outcome_id:
            o = session.query(Outcome).filter(Outcome.id==rubric[0].outcome_id)
            if o.count():
                a.outcome_name = o[0].display_name
                a.outcome_title = o[0].title
                a.outcome_desc = o[0].description
        #moved the following lines over so that we won't commit assessment for deleted rubrics
        if a.user_id in user_ids:
            a.user_name = user_names[user_ids.index(a.user_id)]
            a.sis_user_id = user_sis_ids[user_ids.index(a.user_id)]
            a.sortable_name = sortable_names[user_ids.index(a.user_id)]
        #NEW CODE: ---------------------------------------------------
        if s.grader_id in user_ids:
            a.instructor = user_names[user_ids.index(s.grader_id)]
        #END NEW CODE --------------------
        #session.add(a)
        #session.commit()
        #Make sure it's a real student
        if a.user_name:
            try:
                session.add(a)
                session.commit()
            except IntegrityError:
                #print "Error Assessment ID %s" % (a.assessment_id)
                session.rollback()


'''
#PAGINATION TEST
incomplete = True
page = 1
while incomplete:
    r = requests.get(base_url + "/courses/410/enrollments?page="+str(page), **settings)
    print r.headers["link"]
    page+=1
    if 'rel=\"next\"' not in r.headers["link"]:
        incomplete = False
'''
accounts = [75,76,77,78,79,1]

for account in accounts:
    print "getting users account "+str(account)
    incomplete = True
    page = 1
    while incomplete:
        #sleep(1)
        #r = requests.get(
        #    base_url + "/accounts/"+str(account)+"/users?page="+str(page), verify=False, **settings)
        r = getWeb(base_url + "/accounts/"+str(account)+"/users?page="+str(page), settings)
        #base_url + "/courses/" + str(course.id) +
        #"/students", **settings)
        print "  page "+str(page)
        for user in r.json():
            user_info = _(user).pick(["id", "name","sis_user_id"])
            #sis_user_id not sis_account_id?
            u = User(**user_info)
            u.sortable_name = user["sortable_name"]
            #u = User()
            #u.id = user["id"]
            #u.name = user["name"]
            #u.sis_account_id = user["sis_account_id"]
            u_string = str(u.id)
            if len(u_string) > 5:
                u_string = u_string[6:]
            #print u_string
            u.id = int(u_string)
            #print u.id
            user_ids.append(u.id)
            user_names.append(u.name)
            sortable_names.append(u.sortable_name)
            user_sis_ids.append(u.sis_user_id)
            if account == 75:
                u.grade_level = "4th Grade"
            elif account == 76:
                u.grade_level = "5th Grade"
            elif account == 77:
                u.grade_level = "6th Grade"
            elif account == 78:
                u.grade_level = "7th Grade"
            elif account == 78:
                u.grade_level = "7th Grade"
            elif account == 79:
                u.grade_level = "8th Grade"
            try:
                session.add(u)
                session.commit()
            except IntegrityError:
                session.rollback()
        page+=1
        if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
            incomplete = False


incomplete = True
page = 1
while incomplete:
    print "getting courses"
    #sleep(1)
    #r = requests.get(base_url + "/courses?page="+str(page), verify=False, **settings)
    r = getWeb(base_url + "/courses?page="+str(page), settings)
    courses = r.json()

    for course in courses:
        course_info = _(course).pick([
            "id",
            "sis_course_id",
            "name",
            "course_code",
            "account_id",
            "root_account_id",
            "integration_id",
            "workflow_state",
            "enrollment_term_id",
            "start_at",
            "end_at",
            "term",
            "needs_grading_count"
        ])
        c = Course(**course_info)
        session.add(c)
        session.commit()
    page+=1
    if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
        incomplete = False


print "getting enrollments from courses"
for course in session.query(Course).all():
    c_id = str(course.id)
    incomplete = True
    page = 1
    while incomplete:
        #sleep(1)
        #r = requests.get(base_url + "/courses/" + c_id + "/enrollments?page="+str(page), verify=False, **settings)
        r = getWeb(base_url + "/courses/" + c_id + "/enrollments?page="+str(page), settings)
        print "  course id:" +str(c_id)+" page "+str(page)
        for enrollment in r.json():
            enrollment_info = _(enrollment).pick([
                "id",
                "course_id",
                "sis_course_id",
                "course_section_id",
                "sis_section_id",
                "enrollment_state",
                "user_id",
                "root_account_id",
                "type",
                "role"
            ])
            e = Enrollment(**enrollment_info)
            try:
                if e.enrollment_state == 'active':
                    session.add(e)
                    session.commit()
            except IntegrityError:
                #print "Integrity error on enrollment"
                session.rollback()
        page+=1
        if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
            incomplete = False


print "getting sections"
for course in session.query(Course).all():
    c_id = str(course.id)
    incomplete = True
    page = 1
    while incomplete:
        #sleep(1)
        #r = requests.get(base_url + "/courses/" + c_id + "/sections?page="+str(page), verify=False, **settings)
        r = getWeb(base_url + "/courses/" + c_id + "/sections?page="+str(page), settings)
        print "  course id:" +str(c_id)+" page "+str(page)
        for section in r.json():
            section_info = _(section).pick([
                "id",
                "name",
                "sis_section_id",
                "integration_id",
                "sis_import_id",
                "course_id",
                "sis_course_id"
            ])
            s = Section(**section_info)
            try:
                session.add(s)
                session.commit()
            except IntegrityError:
                print "Integrity error on section"
                session.rollback()

        page+=1
        if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
            incomplete = False


print "getting enrollments from sections"
for section in session.query(Section).all():
    s_id = str(section.id)
    incomplete = True
    page = 1
    while incomplete:
        #sleep(1)
        #r = requests.get(base_url + "/sections/" + s_id + "/enrollments?page="+str(page), verify=False, **settings)
        r = getWeb(base_url + "/sections/" + s_id + "/enrollments?page="+str(page), settings)
        print "  page "+str(page)
        for enrollment in r.json():
            enrollment_info = _(enrollment).pick([
                "id",
                "course_id",
                "sis_course_id",
                "course_section_id",
                "sis_section_id",
                "enrollment_state",
                "user_id",
                "root_account_id",
                "type",
                "role"
            ])
            e = Enrollment(**enrollment_info)
            try:
                if e.enrollment_state == 'active':
                    session.add(e)
                    session.commit()
            except IntegrityError:
                #print "Integrity error on enrollment"
                session.rollback()
        page+=1
        if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
            incomplete = False




assignment_settings = {
    "params": {
        "per_page": 250,
        "include": "rubric"
    },
    "headers": {
        "Authorization": "Bearer %s" % api_token
    }
}


for course in session.query(Course).all():
    incomplete = True
    page = 1
    print "getting assignments for course: %i - %s" % (course.id, course.name)
    while incomplete:
        #sleep(1)
        print "   page "+str(page)
        #r = requests.get(
        #    base_url + "/courses/" + str(course.id) +
        #    "/assignments?page="+str(page), verify=False, **assignment_settings)
        r = getWeb(base_url + "/courses/" + str(course.id) +
            "/assignments?page="+str(page), assignment_settings)
        for assignment in r.json():
            assignment_info = _(assignment).pick([
                "id",
                "name",
                "assignment_group_id",
                "created_at",
                "description",
                "due_at",
                "grading_type",
                "points_possible",
                "course_id"
            ])
            a = Assignment(**assignment_info)
            a.description = strip_tags(a.description)

            if collectAll or "narrative" in a.name.lower() or "conduct" in a.name.lower() or "attendance" in a.name.lower() or "academic behavior" in a.name.lower() or "social communication" in a.name.lower():
                try:
                        session.add(a)
                        session.commit()
                except IntegrityError:
                    session.rollback()
                if "rubric" in assignment:
                    for i in range(len(assignment["rubric"])):
                        #print assignment["rubric"][i]
                        rubric = Rubric()
                        rubric.rubric_id = assignment["rubric"][i]["id"]
                        rubric.assignment_id = a.id
                        rubric.points = assignment["rubric"][i]["points"]
                        rubric.description = strip_tags(assignment["rubric"][i]["description"])
                        if "outcome_id" in assignment["rubric"][i]:
                            rubric.outcome_id = assignment["rubric"][i]["outcome_id"]
                            outcome_ids.append(assignment["rubric"][i]["outcome_id"])
                        if assignment["rubric"][i]["long_description"]:
                            rubric.long_description = strip_tags(assignment["rubric"][i]["long_description"])
                        try:
                            session.add(rubric)
                            session.commit()
                        except IntegrityError:
                            print "Rubric error"
                            session.rollback()
                        if assignment["rubric"][i]["ratings"]:
                            for j in range(len(assignment["rubric"][i]["ratings"])):
                                ratings = RubricRatings()
                                ratings.parent_id = rubric.id
                                ratings.parent_rubric_id = rubric.rubric_id
                                ratings.assignment_id = a.id
                                ratings.rubric_id = assignment["rubric"][i]["ratings"][j]["id"]
                                ratings.points = assignment["rubric"][i]["ratings"][j]["points"]
                                ratings.description = strip_tags(assignment["rubric"][i]["ratings"][j]["description"])
                                try:
                                    session.add(ratings)
                                    session.commit()
                                except IntegrityError:
                                    print "Ratings error"
                                    session.rollback()
        page+=1
        if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
            incomplete = False



submission_settings = {
    "params": {
        "per_page": 2500,
        "student_ids": "all",
        "include": "rubric_assessment"

    },
    "headers": {
        "Authorization": "Bearer %s" % api_token
    }
}

submission_settings2 = {
    "params": {
        "per_page": 2500,
        "student_ids": "all",
        "include": "submission_comments"

    },
    "headers": {
        "Authorization": "Bearer %s" % api_token
    }
}


print "getting terms"
incomplete = True
page = 1
while incomplete:
    #sleep(1)
    print "  page "+str(page)
    #r = requests.get(base_url + "/accounts/1/terms?page="+str(page), verify=False, **settings)
    r = getWeb(base_url + "/accounts/1/terms?page="+str(page), settings)
    terms = r.json()["enrollment_terms"]

    for term in terms:
        term_info = _(term).pick(["id", "name", "sis_term_id"])
        e = EnrollmentTerm(**term_info)
        session.add(e)
        session.commit()

    page+=1
    if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
        incomplete = False

#Are outcome ID's supposed to be <rubric ID>_<criteron_id> ?



outcome_ids = _(outcome_ids).uniq()
print "getting outcomes"

for outcome_id in outcome_ids:
    incomplete = True
    page = 1
    while incomplete:
        #sleep(1)
        print "  page "+str(page)
        #r = requests.get(base_url + "/outcomes/" + str(outcome_id)+"/?page="+str(page), verify=False,
        #    **settings)
        r = getWeb(base_url + "/outcomes/" + str(outcome_id)+"/?page="+str(page), settings)
        outcome = r.json()
        outcome_info = _(outcome).pick([
            "id",
            "display_name",
            "title",
            "description",
            "points_possible",
            "mastery_points"
            ])
        o = Outcome(**outcome_info)
        session.add(o)
        session.commit()

        for rating in outcome["ratings"]:
            rating_info = _(rating).pick([
                "description",
                "points"
                ])
            otr = OutcomeRating(**rating_info)
            o.description = strip_tags(o.description)
            otr.outcome_id = o.id
            session.add(otr)
            session.commit()

        page+=1
        if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
            incomplete = False



#COURSE SUBMISSIONS
if collectAll:
    for course in session.query(Course).all():
        print "getting submissions for course: %s id: %i" % (course.name, course.id)
        incomplete = True
        page = 1
        while incomplete:
            #sleep(1)
            print "  page "+str(page)
            #r = requests.get(
            #    base_url + "/courses/" + str(course.id) +
            #    "/students/submissions?page="+str(page), verify=False,
            #    **submission_settings)
            r = getWeb(base_url + "/courses/" + str(course.id) +
                "/students/submissions?page="+str(page), submission_settings)
            if not "error_report_id" in r.json():
                for submission in r.json():
                    submission_info = _(submission).pick([
                        "id",
                        "assignment_id",
                        "grade",
                        "grader_id",
                        "score",
                        "user_id"
                    ])
                    s = Submission(**submission_info)
                    try:
                        session.add(s)
                        session.commit()
                    except IntegrityError:
                        session.rollback()
                    ###
                    s_com = ""
                    '''
                    sleep(1)
                    r2 = requests.get(
                        base_url + "/courses/" + str(course.id) +
                        "/assignments/"+str(submission["assignment_id"])+"/submissions/"+str(submission["user_id"]), verify=False,
                        **submission_settings2)
                    sub_c = r2.json()
                    sub_c = json.dumps(sub_c)
                    if not "error_report_id" in r2.json():
                        if len(json.loads(sub_c)['submission_comments']) > 0:
                            s_com = json.loads(sub_c)['submission_comments'][0]['comment']
                            print s_com
                    '''
                    if "rubric_assessment" in submission:
                        for k, v in submission["rubric_assessment"].iteritems():
                            outcome_id, assessment_id = k.split('_')
                            #outcome_ids.append(outcome_id)

                            assignment = session.query(Assignment).filter(Assignment.id==s.assignment_id)
                            if assignment.count():
                                parse_assessment(s, k, v, assignment[0], session, s_com)
            page+=1
            if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
                incomplete = False


#SECTION SUBMISSIONS
if collectAll:
    for section in session.query(Section).all():
        print "getting submissions for section: %s id: %i" % (section.name, section.id)
        incomplete = True
        page = 1
        while incomplete:
            #sleep(1)
            print "  page "+str(page)
            #r = requests.get(
            #    base_url + "/sections/" + str(section.id) +
            #    "/students/submissions?page="+str(page), verify=False,
            #    **submission_settings)
            r = getWeb(base_url + "/sections/" + str(section.id) +
                "/students/submissions?page="+str(page), submission_settings)
            if not "error_report_id" in r.json():
                for submission in r.json():
                    success = True
                    submission_info = _(submission).pick([
                        "id",
                        "assignment_id",
                        "grade",
                        "grader_id",
                        "score",
                        "user_id"
                    ])
                    s = Submission(**submission_info)
                    try:
                        session.add(s)
                        session.commit()
                    except IntegrityError:
                        session.rollback()
                        success = False
                    if success:
                        s_com = ""
                        '''
                        sleep(1)
                        r2 = requests.get(
                            base_url + "/sections/" + str(section.id) +
                            "/assignments/"+str(submission["assignment_id"])+"/submissions/"+str(submission["user_id"]), verify=False,
                            **submission_settings2)
                        sub_c = r2.json()
                        sub_c = json.dumps(sub_c)
                        if not "error_report_id" in r2.json():
                            if len(json.loads(sub_c)['submission_comments']) > 0:
                                s_com = json.loads(sub_c)['submission_comments'][0]['comment']
                                print s_com
                        '''
                        if "rubric_assessment" in submission:
                            for k, v in submission["rubric_assessment"].iteritems():
                                outcome_id, assessment_id = k.split('_')
                                #outcome_ids.append(outcome_id)

                                assignment = session.query(Assignment).filter(Assignment.id==s.assignment_id)
                                if assignment.count():
                                    parse_assessment(s, k, v, assignment[0], session, s_com)
            page+=1
            if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
                incomplete = False


if not collectAll:
    for assignment in session.query(Assignment).all():
        print "getting submissions for assignment: %s id: %i" % (assignment.name, assignment.id)
        incomplete = True
        page = 1
        course_id = assignment.course_id
        while incomplete:
            #sleep(1)
            print "  page "+str(page)
            '''
            r = requests.get(
                base_url + "/courses/" + str(course_id) +
                "/assignments/"+str(assignment.id)+"/submissions?page="+str(page), verify=False,
                **submission_settings)
            '''
            r = getWeb(base_url + "/courses/" + str(course_id) +
                "/assignments/"+str(assignment.id)+"/submissions?page="+str(page), submission_settings)
            '''
            r = requests.get(
                base_url + "/courses/" + str(assignment.course_id) +
                "/assignments/"+str(assignment.id)+"/submissions?page="+str(page), verify=False,
                **submission_settings)
            '''
            if not "error_report_id" in r.json():
                for submission in r.json():
                    success = True
                    submission_info = _(submission).pick([
                        "id",
                        "assignment_id",
                        "grade",
                        "grader_id",
                        "score",
                        "user_id"
                    ])
                    s = Submission(**submission_info)
                    try:
                        session.add(s)
                        session.commit()
                    except IntegrityError:
                        session.rollback()
                        success = False
                    if success:
                        ###
                        s_com = ""
                        '''
                        sleep(1)
                        r2 = requests.get(
                            base_url + "/courses/" + str(course_id) +
                            "/assignments/"+str(s.assignment_id)+"/submissions/"+str(s.user_id), verify=False,
                            **submission_settings2)
                        '''
                        r2 = getWeb(base_url + "/courses/" + str(course_id) +
                            "/assignments/"+str(s.assignment_id)+"/submissions/"+str(s.user_id), submission_settings2)
                        '''
                        r2 = requests.get(
                            base_url + "/courses/" + str(assignment.course_id) +
                            "/assignments/"+str(submission["assignment_id"])+"/submissions/"+str(submission["user_id"]), verify=False,
                            **submission_settings2)
                        '''
                        sub_c = r2.json()
                        #sub_c = json.load(r2)
                        #if "submission_comment" in sub_c:
                        #s_com = sub_c['submission_comments'][0]
                        sub_c = json.dumps(sub_c)
                        if not "error_report_id" in r2.json():
                            if len(json.loads(sub_c)['submission_comments']) > 0:
                                s_com = json.loads(sub_c)['submission_comments'][0]['comment']
                                print s_com

                        ###
                        if "rubric_assessment" in submission:
                            for k, v in submission["rubric_assessment"].iteritems():
                                outcome_id, assessment_id = k.split('_')
                                #outcome_ids.append(outcome_id)

                                assignment = session.query(Assignment).filter(Assignment.id==s.assignment_id)
                                if assignment.count():
                                    parse_assessment(s, k, v, assignment[0], session, s_com)
            page+=1
            if "link" not in r.headers or 'rel=\"next\"' not in r.headers["link"]:
                incomplete = False


session.close()
