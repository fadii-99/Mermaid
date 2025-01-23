from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv
import os
import openai


load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-4o-mini")


def intro_LLm(request):
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

    intro_chain = LLMChain(llm=llm, prompt=intro_prompt)

    intro_result = intro_chain.run({
            "child_dob": request.data.get('child_dob'), "requester": request.data.get('requester'),
            "pronoun": request.data.get('pronoun'), "assesment_administered": request.data.get('assesment_administered'),
            "assesment_time": request.data.get('assesment_time'), "meet_teacher": request.data.get('meet_teacher'),
            "meet_parent": request.data.get('meet_parent'), "meet_therapy_team": request.data.get('meet_therapy_team'),
            "lessons_observed": request.data.get('lessons_observed'), "sensory_profile": request.data.get('sensory_profile'),
            "parent_assesment": request.data.get('parent_assesment')
        })
    

    return intro_result




def external_report(all_external_content):
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

    external_report_chain = LLMChain(llm=llm, prompt=external_report_prompt)

    external_report_result = external_report_chain.run({"external_report_content": all_external_content})

    return external_report_result




def intinal_report(all_internal_content):
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

    initial_referral_chain = LLMChain(llm=llm, prompt=initial_referral_prompt)
    initial_referral_result = initial_referral_chain.run({"initial_referral_content": all_internal_content})

    return initial_referral_result



def views_LLm(therapist_input):
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

    views_chain = LLMChain(llm=llm, prompt=views_prompt)
    views_result = views_chain.run({"therapist_input": therapist_input})

    return views_result





def clean_table_LLM(table):
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

    response = clean_table_chain.run(table_data=table)

    return response




def clinical_LLM(clinical_analysis_content):
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

    summary_result = clinical_analysis_chain.run({"clinical_analysis_content": clinical_analysis_content})

    return summary_result



def summary_of_strength(assessment_content):
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

    summary_of_strengths_result = summary_of_strengths_chain.run({"assessment_content": assessment_content})

    return summary_of_strengths_result



def summary_of_need(assessment_content):
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

    summary_of_needs_result = summary_of_needs_chain.run({"assessment_content": assessment_content})

    return summary_of_needs_result




def recommendation_LLM(intro_content, external_report_content, initial_referral_content, views_content, assessment_content, clinical_analysis_content, summary_of_strengths_content, summary_of_needs_content):

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


    return recommendations_result



def appendix_LLM(assessment_tables, pdf_texts):
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

    appendix_result = appendix_chain.run({
            "assessment_tables": assessment_tables,
            "pdf_texts": pdf_texts
        })
    
    return appendix_result

































