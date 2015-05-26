import sqlite3
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    sortable_name = Column(String)
    sis_user_id = Column(String)
    grade_level = Column(String)


class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)
    sis_course_id = Column(String)
    name = Column(String)
    course_code = Column(String)
    account_id = Column(Integer)
    root_account_id = Column(Integer)
    integration_id = Column(String)
    workflow_state = Column(String)
    enrollment_term_id = Column(Integer)
    start_at = Column(String)
    end_at = Column(String)
    term = Column(String)
    needs_grading_count = Column(Integer)


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    assignment_group_id = Column(Integer)
    created_at = Column(String)
    description = Column(String)
    due_at = Column(String)
    grading_type = Column(String)
    points_possible = Column(Integer)
    course_id = Column(Integer)
    name = Column(String)


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer)
    grade = Column(String)
    grader_id = Column(Integer)
    score = Column(Integer)
    user_id = Column(Integer)


class EnrollmentTerm(Base):
    __tablename__ = "enrollment_term"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    sis_term_id = Column(String)


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True)
    #assessment_id = Column(Integer)
    a_type = Column(String)
    term = Column(String)
    course_name = Column(String)
    course_id = Column(Integer)
    instructor = Column(String) #new
    section_name = Column(String)
    section_id = Column(Integer)
    rubric_id = Column(String)
    rubric_desc = Column(String)
    rubric_long_desc = Column(String)
    rubric_result = Column(String)
    user_id = Column(Integer)
    sis_user_id = Column(String)
    user_name = Column(String)
    sortable_name = Column(String)
    assignment_id = Column(Integer)
    assignment_name = Column(String)
    assignment_desc = Column(String)
    outcome_id = Column(Integer)
    outcome_name = Column(String)
    outcome_title = Column(String)
    outcome_desc = Column(String)
    points = Column(Integer)
    max_points = Column(Integer)
    grade = Column(String)
    comments = Column(String)
    sub_comments = Column(String)


'''
class Score(Base):
    __tablename__ = "assessment_scores"

    id = Column(Integer, primary_key=True)
    user_name = Column(String)
    course_name = Column(String)
    section_name = Column(String)
    assignment_name = Column(String)
    rubric_id = Column(String)
    outcome_id = Column(Integer)
    outcome = Column(String)
    max_points = Column(Integer)
    score = Column(Integer)
    comments = Column(String)
'''
'''
class Narrative(Base):
    __tablename__ = "narratives"

    id = Column(Integer, primary_key=True)
    #assessment_id = Column(Integer)
    term = Column(String)
    course_name = Column(String)
    course_id = Column(Integer)
    section_name = Column(String)
    section_id = Column(Integer)
    rubric_id = Column(String)
    rubric_desc = Column(String)
    rubric_long_desc = Column(String)
    rubric_result = Column(String)
    user_id = Column(Integer)
    sis_user_id = Column(String)
    user_name = Column(String)
    sortable_name = Column(String)
    assignment_id = Column(Integer)
    assignment_name = Column(String)
    assignment_desc = Column(String)
    outcome_id = Column(Integer)
    outcome_name = Column(String)
    outcome_title = Column(String)
    outcome_desc = Column(String)
    points = Column(Integer)
    max_points = Column(Integer)
    grade = Column(String)
    comments = Column(String)


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)
    #assessment_id = Column(Integer)
    term = Column(String)
    course_name = Column(String)
    course_id = Column(Integer)
    section_name = Column(String)
    section_id = Column(Integer)
    rubric_id = Column(String)
    rubric_desc = Column(String)
    rubric_long_desc = Column(String)
    rubric_result = Column(String)
    user_id = Column(Integer)
    sis_user_id = Column(String)
    user_name = Column(String)
    sortable_name = Column(String)
    assignment_id = Column(Integer)
    assignment_name = Column(String)
    assignment_desc = Column(String)
    outcome_id = Column(Integer)
    outcome_name = Column(String)
    outcome_title = Column(String)
    outcome_desc = Column(String)
    points = Column(Integer)
    max_points = Column(Integer)
    grade = Column(String)
    comments = Column(String)


class Conduct(Base):
    __tablename__ = "conduct"

    id = Column(Integer, primary_key=True)
    #assessment_id = Column(Integer)
    term = Column(String)
    course_name = Column(String)
    course_id = Column(Integer)
    section_name = Column(String)
    section_id = Column(Integer)
    rubric_id = Column(String)
    rubric_desc = Column(String)
    rubric_long_desc = Column(String)
    rubric_result = Column(String)
    user_id = Column(Integer)
    sis_user_id = Column(String)
    user_name = Column(String)
    assignment_id = Column(Integer)
    assignment_name = Column(String)
    assignment_desc = Column(String)
    outcome_id = Column(Integer)
    outcome_name = Column(String)
    outcome_title = Column(String)
    outcome_desc = Column(String)
    points = Column(Integer)
    max_points = Column(Integer)
    grade = Column(String)
    comments = Column(String)
'''

class Rubric(Base):
    __tablename__ = "rubric_criterion"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer)
    outcome_id = Column(Integer)
    rubric_id = Column(String)
    points = Column(Integer)
    description = Column(String)
    long_description = Column(String)


class RubricRatings(Base):
    __tablename__ = "rubric_criterion_ratings"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer)
    parent_id = Column(Integer)
    parent_rubric_id = Column(String)
    rubric_id = Column(String)
    points = Column(Integer)
    description = Column(String)
    long_description = Column(String)


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True)
    display_name = Column(String)
    title = Column(String)
    description = Column(String)
    points_possible = Column(Integer)
    mastery_points = Column(Integer)


class OutcomeRating(Base):
    __tablename__ = "outcome_ratings"

    id = Column(Integer, primary_key=True)
    description = Column(String)
    points = Column(Integer)
    outcome_id = Column(Integer)

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True)
    #enrollment_id = Column(Integer)
    course_id = Column(Integer)
    sis_course_id  = Column(String)
    course_section_id = Column(Integer)
    sis_section_id  = Column(String)
    enrollment_state  = Column(String)
    user_id = Column(Integer)
    root_account_id = Column(Integer)
    type = Column(String)
    role = Column(String)

class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True)
    #enrollment_id = Column(Integer)
    name = Column(String)
    sis_section_id = Column(String)
    integration_id = Column(String)
    sis_import_id = Column(String)
    course_id = Column(Integer)
    sis_course_id  = Column(String)



# example:
# [
#   {
#     'id': 'crit1',
#     'points': 10,
#     'description': 'Criterion 1',
#     'ratings':
#     [
#       { 'description': 'Good', 'points': 10 },
#       { 'description': 'Poor', 'points': 3 }
#     ]
#   },
#   {
#     'id': 'crit2',
#     'points': 5,
#     'description': 'Criterion 2',
#     'ratings':
#     [
#       { 'description': 'Complete', 'points': 5 },
#       { 'description': 'Incomplete', 'points': 0 }
#     ]
#   }
# ]
# -rubric: [
# -{
# id: "52_8153",
# points: 6,
# description: "Expressions and Equations",
# long_description: "",
# -ratings: [
# -{
# id: "blank",
# points: 6,
# description: "Applies the Concept"
# },
# -{
# id: "52_790",
# points: 5,
# description: "Occasionally Applies the Concept"
# },
# -{
# id: "52_3326",
# points: 4,
# description: "Grasps the Concept Independently"
# },
# -{
# id: "52_1428",
# points: 3,
# description: "Needs Assistance to Grasp the Concept"
# },
# -{
# id: "52_2443",
# points: 2,
# description: "Grasps the Concept with Assistance"
# },
# -{
# id: "blank_2",
# points: 1,
# description: "Not Evident"
# }
# ],
# outcome_id: 95652,
# vendor_guid: null
# },
