from accounts.models import User, ContactUs
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, permission_classes  #type: ignore
from datetime import datetime, timedelta
from rest_framework import status
from accounts.auth_jwt import decode_jwt_token, generate_jwt_token
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage

from dotenv import load_dotenv
import os
import openai
import fitz
import secrets
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
import pdfplumber
from werkzeug.utils import secure_filename
import redis
import json
from .utilss.checkbox_options import checkbox_statements
from .utilss.helper_functions import format_report_content, extract_text_from_pdf, allowed_file, extract_tables_with_tabula, format_table_as_text, deduplicate_tables, parse_markdown_table, parse_assessment_tables, format_report_content




UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# ALLOWED_EXTENSIONS = {'pdf'}


load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-4o-mini")

intro_template = """
    Assume you are an expert in writing introduction for post-therapy reports.
    Your task is to generate an Introduction based on the following details:

    - child_dob = {child_dob} 
    - requester = {requester}
    - pronoun = {pronoun}
    - assesment_administered = {assesment_administered}
    - assesment_time = {assesment_time}
    - meet_teacher = {meet_teacher}
    - meet_parent = {meet_parent}
    - meet_therapy_team = {meet_therapy_team}
    - lessons_observed = {lessons_observed}
    - sensory_profile = {sensory_profile}
    - parent_assesment = {parent_assesment}

    your response should adhere to the following format:
    
     An occupational therapy assessment was requested by child's 'requester'.

     This assessment will focus on analyzing the impact of 'child's name' motor, sensory, perceptual, and functional needs on 'pronoun' everyday activities and what needs to be in place to enable 'pronoun' to adequately access, learn, and progress with all the academic, social, personal, and independence demands expected within an educational setting.

     In line with the College of Occupational Therapy (COT) guidelines, the assessment follows a top-down approach. This means that the individual's abilities to carry out daily life tasks (occupational performance) are primarily considered.  In children and young people these consist of their ability to engage and participate in activities relating to learning, personal care, play, social interaction and activities, and functioning at home, school and the community.

     However, when working with children who often present with complex and overlapping difficulties the underlying performance components (motor, sensory, perception and volition) are equally important in understanding the ways in which performance components (foundation skills) interfere with occupational and role performance.  This assessment specifically focuses on the child's role as a learner and how foundation skills impact on their ability to access learning opportunities. 

     I met 'child's name' at 'assesment_administered' where I
        • Observed 'pronoun' in 'lessons_observed' lessons
        • Met with 'pronoun' teacher (if 'meet_teacher' = Yes) (If no then leave out)
        • The teacher completed the Sensory Profile: 2nd edition (if 'sensory_profile' = Yes) (If no then leave out)
        • Met with the school therapy team (if 'meet_therapy_team' = Yes) (If no then leave out)
        • Met with (if 'meet_parent' = yes) (If no then leave out)

    REMEBER above format is just an example, you should return this type of response.
"""
intro_prompt = PromptTemplate(
    input_variables=["child_dob", "requester", "pronoun", "assesment_administered", 
                     "assesment_time", "meet_teacher", "meet_parent", "meet_therapy_team", 
                     "lessons_observed", "sensory_profile", "parent_assesment"],
    template=intro_template
)

external_report_template = """
    You are an expert in analyzing occupational therapy reports. Based on the external report content provided:

    External Report Content: {external_report_content}

    There could be multiple reports content given. From each report,

    Please extract the following details:
    - Author and designation.
    - Date of the report.
    - Summary of conclusions and recommendations.

    Your response for each external report should adhere to the following format:

    Report name:
     Author: [Author's name], [Designation]
     Date of Report: [Date]
     Summary of Conclusions and Recommendations: [Summary here]
    Report name:
     Author: [Author's name], [Designation]
     Date of Report: [Date]
     Summary of Conclusions and Recommendations: [Summary here]
    ...

     Generated summary should be of more than 200 words.
     Name of report should be in bold.
"""

external_report_prompt = PromptTemplate(
    input_variables=["external_report_content"],
    template=external_report_template
)

initial_referral_template = """
    You are an expert in analyzing occupational therapy reports. Given the initial internal referral content:

    Initial Internal Referral Content: {initial_referral_content}

    There could be multiple reports content given. From each report,

    Please summarize each described point into separate paragraphs containing more than 100 words.
    - Summarize previous school's attendance, current school, and current school year. 
    - Summarize other professionals involved. 
    - Summarize family structure.
    - Summarize answers to the following questions:
            - Who lives with your child at present?
            - How do your child's difficulties impact upon the family?
            - Have there been any major changes in the family? (e.g., divorce/separation; new baby; deaths; frequent moves; change of schools, etc.). If so, please provide details about the event, when it happened, and the impact it had on your child and/or family:
    - Summarize emotional regulation.
    - Summarize Play section.
    - Summarize Self-care section.

    Instructions to follow:
    - Replace child's first name with "Rxx". Ignore all phone numbers, email addresses, home address, school address, child’s surname, parents' names and surnames, date of birth, current SENCO, all GP info.
    - From date of birth and today's date, work out the child's age.
    - Use child's preferred pronouns throughout the document.

    Your response for each initial internal referral report should adhere to the following format:
    Report name:
        summary
        summary
        summary
        ...

    Report name:
        summary
        summary
        summary
        ...
    
    ....


    DONOT give any type of heading in response except report name, only return report name and paragraphs.

"""

initial_referral_prompt = PromptTemplate(
    input_variables=["initial_referral_content"],
    template=initial_referral_template
)



views_template = """
    Assume you are an expert in writing Views for post therapy reports. Your task is to generate a summary of parent views, teacher views, and other views
    based on the following therapist input:

    - Therapist Input: {therapist_input}

    Your response should adhere to the following format:

    - Parent Views: [parent views]
    - Teacher Views: [teacher views]
    - Other Views: [other views]
"""

views_prompt = PromptTemplate(
    input_variables=["therapist_input"], 
    template=views_template
)


clean_tables_prompt_template = """
    The following table has some junk data and extra content. Please clean the table and only return structured rows and columns with proper alignment. Remove any unnecessary or repeated data.
    some tables may appear twice, so all tables should appear once do not reapeat same table twice.

    Raw Data:
    {table_data}

    your response should adhere to the following format:

        Cleaned Structured Table,
        Cleaned Structured Table,
        ...

    return tables in markdowns.
"""
prompt = PromptTemplate(input_variables=["table"], template=clean_tables_prompt_template)

clean_table_chain = LLMChain(llm=llm, prompt=prompt)

def generate_dynamic_prompt(selected_fields):
    dynamic_template = """
        Assume you are an expert in generating descriptions for therapy assessments. 
        Generate a description based on the table, category, standard scores, and percentiles.\n\n
        Give summary of each table as well after generating table.
        Table name should start with three hashes only once.
        summary heading should also start with three hashes only once.
 
        Your response should adhere to the following format for each assessment:

        ### Table Name
        |Category              |       Score                   |       Percentile       |      Description      |
        |Copying               |       score                   |   percentile           |    description here   |
        |Figure Ground         |       score                   |   percentile           |    description here   |
        ...
      """

    table_grouped_fields = {}
    for field in selected_fields:
        table_name = field.get("table", "Unknown Table")
        if table_name not in table_grouped_fields:
            table_grouped_fields[table_name] = []
        table_grouped_fields[table_name].append(field)

    table_counter = 1
    for table_name, fields in table_grouped_fields.items():
        dynamic_template += f"Table {table_counter}: For {table_name}:\n"
        dynamic_template += " | Category              |    Score                      | Percentile                        | Description |\n"
        dynamic_template += " | ----------------------|------------------------------|-----------------------------------|----------------- |\n"

        category_grouped_fields = {}
        for field in fields:
            category = field.get("category", "Uncategorized")
            if category not in category_grouped_fields:
                category_grouped_fields[category] = []
            category_grouped_fields[category].append(field)

        for category, category_fields in category_grouped_fields.items():
            score_field = next((f for f in category_fields if "score" in f["name"]), None)
            percentile_field = next((f for f in category_fields if "percentile" in f["name"]), None)

            score_value = f"{{{{{score_field['name']}}}}}" if score_field else "N/A"
            percentile_value = f"{{{{{percentile_field['name']}}}}}" if percentile_field else "N/A"
            dynamic_template += (
                f"  {category:<22} | {score_value:<30} | {percentile_value:<35} | description here\n"
            )
        dynamic_template += "\n"
        table_counter += 1

    return dynamic_template


clinical_analysis_template = """
        Assume you are a specialist in generating summary of clinical assesments based on the sentences. Given the sentences:

        sentences : {clinical_analysis_content}

        your task is to Summarize each sentence in paragaraph of more than 120 words, to provide an overview of the clinical findings.

        For every sentence summarise in such a way that:
            - Give heading for each sentence.
            - First define the selected sentence.
            - gives 3 implications for children of this child's age group.

        your response should adhere to the following format:

            summary,
            implications
            summary,
            implications
            ...
        
"""

clinical_analysis_prompt = PromptTemplate(
    input_variables=["clinical_analysis_content"],
    template=clinical_analysis_template
)
clinical_analysis_chain = LLMChain(llm=llm, prompt=clinical_analysis_prompt)

summary_of_strengths_template = """
    Assume you are an expert in identifying sentences from asessment's content based on keywords. Given the Assessment content:

    Assessment content={assessment_content}

    Based on the following assessment contents, generate a summary of strengths by identifying sentences containing specific keywords:
    Keywords: 
        - Above average, 
        - Responds just like the majority of others, 
        - Average, 
        - Similar to Most People.

    summarise each sentence into seperate paragraph containing more than 100 words.

    your response should adhere to the following format:
        summary
        summary
        ...

    DONOT give any type of heading in response, only return paragraphs.
"""

summary_of_strengths_prompt = PromptTemplate(
    input_variables=["assessment_content"],
    template=summary_of_strengths_template
)

summary_of_strengths_chain = LLMChain(llm=llm, prompt=summary_of_strengths_prompt)

summary_of_needs_template = """
    Assume you are an expert in identifying sentences from asessment's content based on keywords. Given the Assessment content:

    Assessment content={assessment_content}

    Based on the following assessment content, generate a summary of needs by identifying sentences containing specific keywords:
    Keywords: 
        - Below average, 
        - Very low, 
        - Well-Below Average, 
        - Less than most people.
    
    summarise each sentence into seperate paragraph containing more than 100 words.

    your response should adhere to the following format:
        summary
        summary
        ...

    DONOT give any type of heading in response, only return paragraphs.
"""

summary_of_needs_prompt = PromptTemplate(
    input_variables=['assessment_content'],
    template=summary_of_needs_template
)

summary_of_needs_chain = LLMChain(llm=llm, prompt=summary_of_needs_prompt)

recommendations_template = """
        Assume you are an expert in occupational therapy and creating client-specific recommendations.
        Based on the following data from all sections of the report:

            Introduction:
            {intro_content}

            External Report:
            {external_report_content}

            Initial Referral:
            {initial_referral_content}

            Views:
            {views_content}

            Assessment:
            {assessment_content}

            Clinical Analysis:
            {clinical_analysis_content}

            Strengths:
            {summary_of_strengths_content}

            Needs:
            {summary_of_needs_content}

        Generate:
        1. A conclusion.
        2. Specific, measurable, achievable, realistic OT-specific goals for the next year, 6 months, and 3 months.
        3. Goals for school and home.
        4. Individualized recommendations for occupational therapy input.
        5. Reasonable accommodations and adjustments in lessons, and the wider school environment (e.g., lunch, PE, break times).
"""

recommendations_prompt = PromptTemplate(
    input_variables=[
        "intro_content", "external_report_content", "initial_referral_content", 
        "views_content", "assessment_content", "clinical_analysis_content", 
        "summary_of_strengths_content", "summary_of_needs_content"
    ],
    template=recommendations_template
)

recommendations_chain = LLMChain(llm=llm, prompt=recommendations_prompt)


appendix_template = """
        Assume you are an expert in occupational therapy and creating appendix.
        Based on the following data from assessment section of the report:

            pdf assessments:
            {pdf_texts}

            Tabular assessments:
            {assessment_tables}

        There are two type of assessments contnt given one is pdf assessments for which content is extracted from pdf's,
        And second is Tabular assessments content whose data is presented into tabular form.
        There could be more than one assessments for both types.

        Your task is to extract these details from each assessment from the given content:
            - Name of the assesment.
            - Author.
            - Date of Publication and short description who this assessment is for and what the assessment is for.

        Your response should adhere to the following format:
            1- Name of the Assessment: [Assessments name]
                Author: [Author's Name]
                Date of Publication: [Publication Date]
                Target Audience and Purpose: [Description of who the assessment is intended for, e.g., students, employees, etc. Brief description of the assessment's goals and what it aims to measure or evaluate.] 
            2- Name of the Assessment: [Assessments name]
                Author: [Author's Name]
                Date of Publication: [Publication Date]
                Target Audience and Purpose: [Description of who the assessment is intended for, e.g., students, employees, etc. Brief description of the assessment's goals and what it aims to measure or evaluate.] 
            ...

        Assessments name should be in bold.
        If some detail does not found in the given content skip it and return only available details.
"""

appendix_prompt = PromptTemplate(
    input_variables=[
        "pdf_texts", "assessment_tables"
    ],
    template=appendix_template
)

appendix_chain = LLMChain(llm=llm, prompt=appendix_prompt)


@api_view(['POST'])
def form_view(request):
    try:
        request.session['child_dob'] = request.data.get('child_dob')
        request.session['requester'] = request.data.get('requester')
        request.session['pronoun'] = request.data.get('pronoun')
        request.session['assessment_administered'] = request.data.get('assessment_administered')
        request.session['assessment_time'] = request.data.get('assessment_time')
        request.session['meet_teacher'] = request.data.get('meet_teacher')
        request.session['meet_parent'] = request.data.get('meet_parent')
        request.session['meet_therapy_team'] = request.data.get('meet_therapy_team')
        request.session['lessons_observed'] = request.data.get('lessons_observed')
        request.session['sensory_profile'] = request.data.get('sensory_profile')
        request.session['parent_assessment'] = request.data.get('parent_assessment')

        if request.session['parent_assessment'] == "Yes":
            selected_assessments = request.data.get('assessments')
            assessment_mapping = {
                "The Sensory Profile": {"name": "The Sensory Profile", "type": "pdf"},
                "Sensory Processing Measure": {"name": "Sensory Processing Measure", "type": "pdf"},
                "The Adaptive Behaviour Assessment System - Third Edition (ABAS-3)": {"name": "The Adaptive Behaviour Assessment System - Third Edition (ABAS-3)", "type": "pdf"},
                "Pediatric Evaluation of Disability Inventory Computer Adaptive Test": {"name": "Pediatric Evaluation of Disability Inventory Computer Adaptive Test", "type": "pdf"},
                "The Developmental Test of Visual Perception: Third Edition Manual Scoring": {"name": "The Developmental Test of Visual Perception: Third Edition Manual Scoring", "type": "manual"},
                "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring": {"name": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring", "type": "manual"},
                "The Movement Assessment Battery for Children: Third Edition Manual Scoring": {"name": "The Movement Assessment Battery for Children: Third Edition Manual Scoring", "type": "manual"},
                "The Miller Function and Participation Scales (M-FUN) Manual Scoring": {"name": "The Miller Function and Participation Scales (M-FUN): Manual Scoring", "type": "manual"},
                "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring": {"name": "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring", "type": "manual"},
            }

            request.session['selected_assessments'] = [assessment_mapping[assess] for assess in selected_assessments if assess in assessment_mapping]

        return Response({'status': 'success', 'message': 'Form data saved successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def background(request):
    try:
        print(request.session)
        external_report_files = request.FILES.getlist('external_report')
        internal_referral_files = request.FILES.getlist('initial_referral')

        all_external_content = ""
        all_internal_content = ""

        for file in external_report_files:
            if file and file.filename.endswith('.pdf'):
                path = os.path.join('uploads', file.filename)
                file.save(path)
                content = extract_text_from_pdf(path)
                
                all_external_content += f"{file.filename}:\n{content}\n\n"

        for file in internal_referral_files:
            if file and file.filename.endswith('.pdf'):
                path = os.path.join('uploads', file.filename)
                file.save(path)
                content = extract_text_from_pdf(path)
                
                all_internal_content += f"{file.filename}:\n{content}\n\n"

        external_report_chain = LLMChain(llm=llm, prompt=external_report_prompt)
        external_report_result = external_report_chain.run({"external_report_content": all_external_content})

        initial_referral_chain = LLMChain(llm=llm, prompt=initial_referral_prompt)
        initial_referral_result = initial_referral_chain.run({"initial_referral_content": all_internal_content})

        request.session['external_report_result'] = external_report_result
        request.session['initial_referral_result'] = initial_referral_result

        request.session['external_report_content'] = all_external_content  
        request.session['initial_referral_content'] = all_internal_content

        return Response({'status': 'success', 'message': 'Form data saved successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
def viewsObtained(request):
    try:
        parent_input = request.data.get('parent_input')
        teacher_input = request.data.get('teacher_input')
        other_input = request.data.get('other_input')

        therapist_input = f"""
        Parent Views: {parent_input}
        Teacher Views: {teacher_input}
        Other Views: {other_input}
        """

        views_chain = LLMChain(llm=llm, prompt=views_prompt)
        views_result = views_chain.run({"therapist_input": therapist_input})

        request.session['views_result'] = views_result
        return Response({'status': 'success', 'message': 'success'}, status=status.HTTP_200_OK)
    except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




manual_assessment_fields = {
    "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring": [
        {"label": "Eye hand cordination score", "name": "eye_hand_coordination_score1", "category": "Eye-hand coordination", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"},
        {"label": "Eye hand cordination percentile", "name": "eye_hand_coordination_percentile1", "category": "Eye-hand coordination", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"},
        {"label": "Copying score", "name": "copying_score1", "category": "Copying", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"},
        {"label": "Copying percentile", "name": "copying_percentile1", "category": "Copying", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"},
        {"label": "Figure Ground score", "name": "figure_ground_score1", "category": "Figure Ground", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"},
        {"label": "Figure Ground percentile", "name": "figure_ground_percentile1", "category": "Figure Ground", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"},
        {"label": "Visual Closure score", "name": "visual_closure_score1", "category": "Visual Closure", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"},
        {"label": "Visual Closure percentile", "name": "visual_closure_percentile1", "category": "Visual Closure", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"},
        {"label": "Form Constancy score", "name": "form_constancy_score1", "category": "Form Constancy", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"},
        {"label": "Form Constancy percentile", "name": "form_constancy_percentile1", "category": "Form Constancy", "table": "The Developmental Test of Visual Perception: Adult and Adolescent version Manual Scoring"}
    ],
    "The Developmental Test of Visual Perception: Third Edition Manual Scoring": [
        {"label": "Copying score", "name": "copying_score2", "category": "Copying", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Copying percentile", "name": "copying_percentile2", "category": "Copying", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Figure Ground score", "name": "figure_ground_score2", "category": "Figure Ground", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Figure Ground percentile", "name": "figure_ground_percentile2", "category": "Figure Ground", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Visual motor search score", "name": "visual_motor_search_score2", "category": "Visual motor search", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Visual motor search percentile", "name": "visual_motor_search_percentile2", "category": "Visual motor search", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Visual Closure score", "name": "visual_closure_score2", "category": "Visual Closure", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Visual Closure percentile", "name": "visual_closure_percentile2", "category": "Visual Closure", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Visual motor speed score", "name": "visual_motor_speed_score2", "category": "Visual motor speed", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Visual motor speed percentile", "name": "visual_motor_speed_percentile2", "category": "Visual motor speed", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Form Constancy score", "name": "form_constancy_score2", "category": "Form Constancy", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"},
        {"label": "Form Constancy percentile", "name": "form_constancy_percentile2", "category": "Form Constancy", "table": "The Developmental Test of Visual Perception: Third Edition Manual Scoring"}
    ],
    "The Movement Assessment Battery for Children: Third Edition Manual Scoring": [
        {"label": "Manual dexterity score", "name": "manual_dexterity_score3", "category": "Manual dexterity", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Manual dexterity percentile", "name": "manual_dexterity_percentile3", "category": "Manual dexterity", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Pegs score", "name": "pegs_score3", "category": "Pegs", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Pegs percentile", "name": "pegs_percentile3", "category": "Pegs", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Threading score", "name": "threading_score3", "category": "Threading", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Threading percentile", "name": "threading_percentile3", "category": "Threading", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Drawing trail score", "name": "drawing_trail_score3", "category": "Drawing trail", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Drawing trail percentile", "name": "drawing_trail_percentile3", "category": "Drawing trail", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Catching and throwing score", "name": "catching_and_throwing_score3", "category": "Catching and throwing", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Catching and throwing percentile", "name": "catching_and_throwing_percentile3", "category": "Catching and throwing", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Balance score", "name": "balance_score3", "category": "Balance", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"},
        {"label": "Balance percentile", "name": "balance_percentile3", "category": "Balance", "table": "The Movement Assessment Battery for Children: Third Edition Manual Scoring"}
    ],
    "The Miller Function and Participation Scales (M-FUN): Manual Scoring": [
        {"label": "M-FUN visual motor subset score", "name": "mfun_visual_motor_subset_score4", "category": "M-FUN visual motor subset", "table": "The Miller Function and Participation Scales (M-FUN) Manual Scoring"},
        {"label": "M-FUN visual motor subset percentile", "name": "mfun_visual_motor_subset_percentile4", "category": "M-FUN visual motor subset", "table": "The Miller Function and Participation Scales (M-FUN) Manual Scoring"},
        {"label": "M-FUN fine motor subset score", "name": "mfun_fine_motor_subset_score4", "category": "M-FUN fine motor subset", "table": "The Miller Function and Participation Scales (M-FUN) Manual Scoring"},
        {"label": "M-FUN fine motor subset percentile", "name": "mfun_fine_motor_subset_percentile4", "category": "M-FUN fine motor subset", "table": "The Miller Function and Participation Scales (M-FUN) Manual Scoring"},
        {"label": "M-FUN gross motor subset score", "name": "mfun_gross_motor_subset_score4", "category": "M-FUN gross motor subset", "table": "The Miller Function and Participation Scales (M-FUN) Manual Scoring"},
        {"label": "M-FUN gross motor subset percentile", "name": "mfun_gross_motor_subset_percentile4", "category": "M-FUN gross motor subset", "table": "The Miller Function and Participation Scales (M-FUN) Manual Scoring"},
    ],
    "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring": [
        {"label": "Copy best score", "name": "copy_best_score5", "category": "Copy best", "table": "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring"},
        {"label": "Copy best percentile", "name": "copy_best_percentile5", "category": "Copy best", "table": "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring"},
        {"label": "Alphabet writing score", "name": "alphabet_writing_score5", "category": "Alphabet writing", "table": "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring"},
        {"label": "Alphabet writing percentile", "name": "alphabet_writing_percentile5", "category": "Alphabet writing", "table": "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring"},
        {"label": "Copy fast score", "name": "copy_fast_score5", "category": "Copy fast","table": "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring"},
        {"label": "Copy fast percentile", "name": "copy_fast_percentile5", "category": "Copy fast", "table": "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring"},
        {"label": "Free writing score", "name": "free_writing_score5", "category": "Free writing", "table": "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring"},
        {"label": "Free writing percentile", "name": "free_writing_percentile5", "category": "Free writing", "table": "Detailed Assessment of Speed of Handwriting: 3rd edition Manual Scoring"},
    ]
}



@api_view(['POST'])
def assessment(request):
    data = request.data.get('assessments')

    if request.method == 'POST':
        fs = FileSystemStorage()
        pdf_results = {}
        manual_data = {}
        pdf_texts = {}

        # Process each assessment in the provided data
        for idx, assessment in enumerate(data):
            label = assessment.get('label')
            value = assessment.get('value')

            if 'Manual' in label:
                # Process manual data
                manual_data[label] = value

            elif 'PDF' in label:
                # Process PDF file - simulated since actual PDF processing isn't shown
                # This part needs to handle PDF extraction if files are actually uploaded
                pdf_texts[label] = value
                pdf_results[label] = f"Processed data for {label}"

        # Store results in session
        request.session['pdf_results'] = pdf_results
        request.session['pdf_texts'] = pdf_texts

        # Assuming additional processing and output generation code is in place

        return Response({
            'success': 'Assessment completed successfully',
            'pdf_results': pdf_results,
            'manual_data': manual_data
        }, status=status.HTTP_200_OK)

    else:
        # Handle non-POST requests
        return Response({'error': 'Invalid request method. Please use POST.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['POST'])
def clinical_analysis(request):
    if request.method == 'POST':
        data = request.data.get('payload')
        if data is None:
            return Response({
                'error': 'No data provided.'
            }, status=status.HTTP_400_BAD_REQUEST)

        print("Received Data:", data)  # Debug to check what's inside data

        selected_statements = []
        
        # Collect all received values directly
        for key, values in data.items():
            selected_statements.extend(values)  # Append all values directly to the list

        print(f'Selected Assessments are: {selected_statements}')

        # Assuming `clinical_analysis_chain` is defined and ready to process the content
        clinical_analysis_content = " ".join(selected_statements)
        print(f'Clinical Analysis Input: {clinical_analysis_content}')
        
        # Placeholder for your analysis function - replace with actual function call
        # Assuming clinical_analysis_chain is a function or method that takes content and returns a summary
        summary_result = clinical_analysis_chain.run({"clinical_analysis_content": clinical_analysis_content})
        request.session['clinical_analysis_result'] = summary_result  # Dummy function call for demonstration

        return Response({
            'success': 'Clinical analysis completed successfully',
            'result': summary_result
        }, status=status.HTTP_200_OK)

    return Response({
        'error': 'Invalid request method. Please use POST.'
    }, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['POST'])
def recommendations(request):
    intro_content = request.session.get('intro_content', '')
    external_report_content = request.session.get('external_report_result', '')
    initial_referral_content = request.session.get('initial_referral_result', '')
    views_content = request.session.get('views_result', '')
    assessment_content = request.session.get('assessment_result', '')
    clinical_analysis_content = request.session.get('clinical_analysis_result', '')
    summary_of_strengths_content = request.session.get('summary_of_strengths_result', '')
    summary_of_needs_content = request.session.get('summary_of_needs_result', '')

    recommendations_result = recommendations_chain.run({
        "intro_content": intro_content,
        "external_report_content": external_report_content,
        "initial_referral_content": initial_referral_content,
        "views_content": views_content,
        "assessment_content": assessment_content,
        "clinical_analysis_content": clinical_analysis_content,
        "summary_of_strengths_content": summary_of_strengths_content,
        "summary_of_needs_content": summary_of_needs_content
    })

    request.session['recommendations_result'] = recommendations_result

    return Response({
            'success': 'Recommendations processed successfully.',
        }, status=status.HTTP_200_OK)





@api_view(['POST'])
def appendix(request):
    assessment_tables = request.session.get('assessment_tables', '')
    # cleaned_tables = session.get('cleaned_tables', '')
    pdf_texts = request.session.get('pdf_texts', {})


    appendix_result = appendix_chain.run({
        "assessment_tables": assessment_tables,
        "pdf_texts": pdf_texts
    })

    request.session['appendix_result'] = appendix_result

    return Response({
            'success': 'Recommendations processed successfully.',
        }, status=status.HTTP_200_OK)




@api_view(['POST'])
def report(request):
    intro_chain = LLMChain(llm=llm, prompt=intro_prompt)
    intro_result = intro_chain.run({
        "child_dob": request.session['child_dob'], "requester": request.session['requester'],
        "pronoun": request.session['pronoun'], "assesment_administered": request.session['assesment_administered'],
        "assesment_time": request.session['assesment_time'], "meet_teacher": request.session['meet_teacher'],
        "meet_parent": request.session['meet_parent'], "meet_therapy_team": request.session['meet_therapy_team'],
        "lessons_observed": request.session['lessons_observed'], "sensory_profile": request.session['sensory_profile'],
        "parent_assesment": request.session['parent_assesment']
    })
    intro_content = format_report_content(intro_result)
    # print('\n\Intro Section : ', intro_content)

    external_report_result = request.session.get('external_report_result', '')
    external_report_content = format_report_content(external_report_result)
    # print('\n\nBackground Section External : ', external_report_content)

    initial_referral_result = request.session.get('initial_referral_result', '')
    initial_referral_content = format_report_content(initial_referral_result)
    # print('\n\nBackground Section Internal: ', initial_referral_content)

    views_result = request.session.get('views_result', '')
    views_content = format_report_content(views_result)
    # print('\n\nViews Section : ', views_content)

    cleaned_tables = request.session.get('cleaned_tables', [])
    # print('\n\nPDF Results Tables : ', cleaned_tables)

    pdf_texts = request.session.get('pdf_texts', '')
    # print('\n\nPDF Results Tables : ', pdf_texts)

    assessment_content = request.session.get('assessment_result', '')
    # print('\n\nAsessment Content : ', assessment_content)
 
    assessment_tables = parse_assessment_tables(assessment_content)
    # print(json.dumps(assessment_data, indent=4))
    print('\n\nAsessment Tables : ', json.dumps(assessment_tables, indent=4))

    clinical_analysis_result = request.session.get('clinical_analysis_result', '')
    clinical_analysis_content = format_report_content(clinical_analysis_result)
    # print('\nClinical Analysis Content : ', clinical_analysis_content)

    summary_of_strengths_result = summary_of_strengths_chain.run({"assessment_content": assessment_content})
    summary_of_strengths_content = format_report_content(summary_of_strengths_result)

    summary_of_needs_result = summary_of_needs_chain.run({"assessment_content": assessment_content})
    summary_of_needs_content = format_report_content(summary_of_needs_result)

    recommendations_result = recommendations_chain.run({
        "intro_content": intro_content,
        "external_report_content": external_report_content,
        "initial_referral_content": initial_referral_content,
        "views_content": views_content,
        "assessment_content": assessment_content,
        "clinical_analysis_content": clinical_analysis_content,
        "summary_of_strengths_content": summary_of_strengths_content,
        "summary_of_needs_content": summary_of_needs_content,
    })
    recommendations_content = format_report_content(recommendations_result)

    appendix_result = appendix_chain.run({
        "pdf_texts": pdf_texts,
        "assessment_tables": assessment_tables
    })
    appendix_content = format_report_content(appendix_result)
    
    return Response({
        'success': 'Recommendations processed successfully.',
        intro_content: intro_content,
        external_report_content: external_report_content,
        initial_referral_content: initial_referral_content,
        views_content: views_content,
        cleaned_tables: cleaned_tables,
        clinical_analysis_content: clinical_analysis_content,
        summary_of_strengths_content: summary_of_strengths_content,
        summary_of_needs_content: summary_of_needs_content,
        recommendations_content: recommendations_content,
        appendix_content: appendix_content
        }, status=status.HTTP_200_OK)



