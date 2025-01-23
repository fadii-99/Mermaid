from accounts.models import User
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view  #type: ignore
from rest_framework import status
from accounts.auth_jwt import decode_jwt_token, generate_jwt_token, validate_token
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
import os
from werkzeug.utils import secure_filename
import json
from .utils.helper_functions import format_report_content, extract_text_from_pdf, allowed_file, extract_tables_with_tabula, format_table_as_text, deduplicate_tables, parse_markdown_table, parse_assessment_tables, format_report_content

import report_processing



UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# ALLOWED_EXTENSIONS = {'pdf'}

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
        is_valid, decoded_or_error = validate_token(request)
        if not is_valid:
            return JsonResponse(decoded_or_error, status=status.HTTP_401_UNAUTHORIZED)

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

        external_report_result = report_processing.external_report(all_external_content)

        initial_referral_result = report_processing.intinal_report(all_internal_content)

        request.session['external_report_result'] = external_report_result
        request.session['initial_referral_result'] = initial_referral_result

        request.session['external_report_content'] = all_external_content  
        request.session['initial_referral_content'] = all_internal_content

        return Response({'status': 'success', 'message': 'Form data saved successfully',
                         'external_report_result': external_report_result, 
                         'initial_referral_result': initial_referral_result,
                         'external_report_content': all_external_content,
                         'initial_referral_content': all_internal_content}, 
                         status=status.HTTP_200_OK)
    except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
def viewsObtained(request):
    try:
        is_valid, decoded_or_error = validate_token(request)
        if not is_valid:
            return JsonResponse(decoded_or_error, status=status.HTTP_401_UNAUTHORIZED)
        
        parent_input = request.data.get('parent_input')
        teacher_input = request.data.get('teacher_input')
        other_input = request.data.get('other_input')

        therapist_input = f"""
        Parent Views: {parent_input}
        Teacher Views: {teacher_input}
        Other Views: {other_input}
        """

        views_result = report_processing.views_LLm(therapist_input)

        request.session['views_result'] = views_result
        return Response({'status': 'success', 'message': 'success','views_result':views_result}, status=status.HTTP_200_OK)
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
    if request.method == 'POST':
        is_valid, decoded_or_error = validate_token(request)
        if not is_valid:
            return JsonResponse(decoded_or_error, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data.get('assessments')
        print(data)

        fs = FileSystemStorage()
        pdf_results = {}
        manual_data = {}
        pdf_texts = {}
        enhanced_tables = []

        selected_fields = []
        for idx, assessment in enumerate(data):
            if assessment['type'] == 'manual':
                fields = manual_assessment_fields.get(assessment['label'], [])
                selected_fields.extend(fields)

                for field in fields:
                    field_name = field['label']
                    manual_data[field_name] = request.POST.get(field_name, "N/A")

            elif assessment['type'] == 'pdf':
                pdf_field = f"pdf_{idx + 1}"
                file = request.FILES.get(pdf_field)
                if file and allowed_file(file.name):
                    filename = secure_filename(file.name)
                    file_path = os.path.join(fs.location, filename)
                    file.save(file_path)

                    pdf_text = extract_text_from_pdf(file_path)
                    pdf_texts[assessment['label']] = pdf_text

                    tables = extract_tables_with_tabula(file_path)
                    formatted_tables = deduplicate_tables(format_table_as_text(tables))

                    extracted_tables = []
                    for table in formatted_tables:
                        response = report_processing.clean_table_LLM(table)
                        response = response.split('```markdown')[-1].split('```')[0]
                        try:
                            parsed_table = parse_markdown_table(response)
                            if parsed_table:
                                extracted_tables.append(parsed_table)
                        except Exception as e:
                            print(f"Error processing table: {e}")

                    pdf_results[assessment['label']] = extracted_tables

        request.session['pdf_results'] = pdf_results
        request.session['cleaned_tables'] = enhanced_tables
        request.session['pdf_texts'] = pdf_texts


        assessment_input = {key: value for key, value in manual_data.items() if value != "N/A"}
        dynamic_template = generate_dynamic_prompt(selected_fields)
        formatted_template = dynamic_template.format(**assessment_input)

        assessment_prompt = "Generated prompt using the template and inputs"
        assessment_result = "Simulated result from some LLM processing"

        request.session['assessment_result'] = assessment_result
    
    return Response({
            'success': 'Assessment completed successfully',
            'pdf_results': pdf_results,
            'cleaned_tables': enhanced_tables,
            'pdf_texts': pdf_texts,
            'assessment_result': assessment_result
        }, status=status.HTTP_200_OK)





@api_view(['POST'])
def generate_report(request):
    try:
        is_valid, decoded_or_error = validate_token(request)
        if not is_valid:
            return JsonResponse(decoded_or_error, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data.get('payload')
        if data is None:
            return Response({
                'error': 'No data provided.'
            }, status=status.HTTP_400_BAD_REQUEST)


        selected_statements = []
        
        for key, values in data.items():
            selected_statements.extend(values) 


        clinical_analysis_content = " ".join(selected_statements)
        
        summary_result = report_processing.clinical_LLM(clinical_analysis_content)


        request.session['clinical_analysis_result'] = summary_result  # Dummy function call for demonstration


        assessment_tables = request.data.get('assessment_tables', '')
        # cleaned_tables = session.get('cleaned_tables', '')
        pdf_texts = request.data.get('pdf_texts', {})


        appendix_result = report_processing.appendix_LLM(assessment_tables, pdf_texts
        )

        request.session['appendix_result'] = appendix_result




        
        intro_result = report_processing.intro_LLm(request)

        intro_content = format_report_content(intro_result)
        # print('\n\Intro Section : ', intro_content)

        external_report_result = request.data.get('external_report_result', '')
        external_report_content = format_report_content(external_report_result)
        # print('\n\nBackground Section External : ', external_report_content)

        initial_referral_result = request.data.get('initial_referral_result', '')
        initial_referral_content = format_report_content(initial_referral_result)
        # print('\n\nBackground Section Internal: ', initial_referral_content)

        views_result = request.data.get('views_result', '')
        views_content = format_report_content(views_result)
        # print('\n\nViews Section : ', views_content)

        cleaned_tables = request.data.get('cleaned_tables', [])
        # print('\n\nPDF Results Tables : ', cleaned_tables)

        pdf_texts = request.data.get('pdf_texts', '')
        # print('\n\nPDF Results Tables : ', pdf_texts)

        assessment_content = request.data.get('assessment_result', '')
        # print('\n\nAsessment Content : ', assessment_content)
    
        assessment_tables = parse_assessment_tables(assessment_content)
        # print(json.dumps(assessment_data, indent=4))
        print('\n\nAsessment Tables : ', json.dumps(assessment_tables, indent=4))

        clinical_analysis_content = format_report_content(summary_result)
        # print('\nClinical Analysis Content : ', clinical_analysis_content)

        summary_of_strengths_result = report_processing.summary_of_strength(assessment_content)
        summary_of_strengths_content = format_report_content(summary_of_strengths_result)

        summary_of_needs_result = report_processing.summary_of_need(assessment_content)
        summary_of_needs_content = format_report_content(summary_of_needs_result)

        recommendations_result = report_processing.recommendation_LLM(intro_content,external_report_content,initial_referral_content,views_content,assessment_content,clinical_analysis_content,summary_of_strengths_content,summary_of_needs_content)
        recommendations_content = format_report_content(recommendations_result)

        appendix_result = report_processing.appendix_LLM(assessment_tables,pdf_texts)
        appendix_content = format_report_content(appendix_result)
        
        return Response({
            'success': 'Recommendations processed successfully.',
            'intro_content': intro_content,
            'external_report_content': external_report_content,
            'initial_referral_content': initial_referral_content,
            'views_content': views_content,
            'cleaned_tables': cleaned_tables,
            'clinical_analysis_content': clinical_analysis_content,
            'summary_of_strengths_content': summary_of_strengths_content,
            'summary_of_needs_content': summary_of_needs_content,
            'recommendations_content': recommendations_content,
            'appendix_content': appendix_content
            }, status=status.HTTP_200_OK)
    except Exception as e:
        print('Error occurred during processing: ', str(e))
        return Response({
            'error': 'An error occurred during processing.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


