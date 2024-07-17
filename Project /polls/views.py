from django.shortcuts import render, redirect
from .models import Question, UserResponse, UserInterest
import google.generativeai as genai
import re
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError

def homepage(request):
    return render(request, 'home.html')

def configure_genai():
    genai.configure(api_key="UR API key")
    return genai.GenerativeModel(
        model_name="gemini-1.0-pro",
        generation_config={
            "temperature": 0.2,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 100,
        }
    )

def validate_interest(interest):
    model = configure_genai()
    prompt = f"""
    Determine if '{interest}' is a valid technical and educational topic related to computer science, programming, or technology.
    Respond with only 'VALID' if it is, or 'INVALID' if it's not, followed by a brief explanation.
    If the topic is inappropriate or offensive, respond with 'INAPPROPRIATE'.
    """
    
    response = model.generate_content(prompt)   
    result = response.text.strip().upper()
    
    if result.startswith('VALID'):
        return True
    elif result.startswith('INVALID'):
        explanation = result.split('INVALID')[1].strip()
        raise ValidationError(f"'{interest}' is not a valid technical topic. {explanation}")
    elif result.startswith('INAPPROPRIATE'):
        raise ValidationError("The entered topic is inappropriate. Please enter a valid technical interest.")
    else:
        raise ValidationError("Unable to validate the topic. Please try again.")

def index(request):
    if request.method == 'POST':
        try:
            user_id = generate_user_id()
            interest = request.POST.get('interest')
            if validate_interest(interest):
                UserInterest.objects.create(user_id=user_id, interest=interest)
                questions = generate_questions(interest)
                for q in questions:
                    Question.objects.create(text=q, course=interest)
                return redirect('questionnaire', user_id=user_id)
        except ValidationError as e:
            return render(request, 'interests.html', {'error_message': str(e)})

    return render(request, 'interests.html')

def dynamic_questionnaire(request, user_id):
    user_interest = UserInterest.objects.filter(user_id=user_id).first()
    
    if not user_interest:
        return JsonResponse({'message': 'No user interest found.'})
    
    if request.method == 'POST':
        questions = Question.objects.filter(course=user_interest.interest)
        
        for question in questions:
            answer = request.POST.get(f'answer_{question.id}')
            if answer:
                UserResponse.objects.create(user_id=user_id, question=question, answer=answer)
        
        return redirect('recommendation', user_id=user_id)
    
    else:
        questions = Question.objects.filter(course=user_interest.interest).order_by('-time')[:10]
        if questions:
            return render(request, 'questionnaire.html', {'questions': questions, 'user_id': user_id})
        else:
            return JsonResponse({'message': 'No questions found.'})

# def get_next_question(user_id):
#     user_interest = UserInterest.objects.filter(user_id=user_id).first()

#     if user_interest:
#         answered_questions = UserResponse.objects.filter(user_id=user_id).values_list('question', flat=True)
#         next_question = Question.objects.filter(course=user_interest.interest).exclude(id__in=answered_questions).first()
#         return next_question
#     else:
#         return None


def get_course_recommendation(request, user_id):

    user_responses = UserResponse.objects.filter(user_id=user_id).order_by('id')

    if not user_responses.exists():
        return HttpResponse("No responses found for the user.")


    response_list = [{'question': response.question.text, 'answer': response.answer} for response in user_responses]
    user_input = "\n".join([f"Q: {response['question']} A: {response['answer']}" for response in response_list])

    genai.configure(api_key="UR API key")

    generation_config = {
        "temperature": 0.9,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 500,
    }

    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
    ]

    model = genai.GenerativeModel(
        model_name="gemini-1.0-pro",
        generation_config=generation_config,
        safety_settings=safety_settings
    )

    convo = model.start_chat(history=[])

    context = (
    "You are an AI course recommendation assistant specializing in technical computer-related courses "
    "such as MERN Stack, AI, ML, Data Security, System Security, Cyber Security, etc. "
    "Your task is to create a dynamic and adaptive questionnaire that adjusts based on the user's responses. "
    "Ensure the questions cover various aspects of technical skills and interests without repetition. "
    "Analyze the user's responses to assess their current skill level, identify areas for improvement, "
    "and determine their aptitude in different technical areas. "
    "Based on this analysis, provide personalized course recommendations and a detailed course path tailored to the user's needs and goals. "
    "Evaluate the user's proficiency level in relevant technical domains to suggest targeted courses and skill-building activities. "
    "Additionally, recommend relevant industrial standard examinations (e.g., CompTIA Security+, Certified Ethical Hacker, AWS Certified Solutions Architect) "
    "that align with the user's career goals and current competencies."
    )

    message = f"{context}\nUser responses:\n{user_input}\nProvide the best course recommendations, detailed course path, and relevant examination suggestions."

    try:   
        response = convo.send_message(message)
        formatted_response = format_response(response.text)

        user_interest = UserInterest.objects.get(user_id=user_id)
        Question.objects.filter(course=user_interest.interest).delete()
        return render(request, 'recommendation.html', {'recommendation': formatted_response})
    
    except Exception as e:
        return f"Error generating recommendations: {str(e)}"


def format_response(response_text):
    response_html = response_text

    # Remove the initial "Your Course Recommendations" as it's already in the template
    response_html = re.sub(r'Your Course Recommendations', '', response_html, 1)

    response_html = re.sub(r'Course Recommendations:', r'<h2>Course Recommendations</h2>', response_html)
    response_html = re.sub(r'Detailed Course Path:', r'<h2>Detailed Course Path</h2>', response_html)
    response_html = re.sub(r'Relevant Examination Suggestions:', r'<h2>Relevant Examination Suggestions</h2>', response_html)
    response_html = re.sub(r'Skill Development and Personalized Recommendations', r'<h2>Skill Development and Personalized Recommendations</h2>', response_html)
    
    response_html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', response_html)
    response_html = re.sub(r'\* (.+)', r'<li>\1</li>', response_html)

    response_html = re.sub(r'(<h2>Course Recommendations</h2>)(.*?)(<h2>|$)', r'\1<ul>\2</ul>\3', response_html, flags=re.DOTALL)
    response_html = re.sub(r'(<h2>Relevant Examination Suggestions</h2>)(.*?)(<h2>|$)', r'\1<ul>\2</ul>\3', response_html, flags=re.DOTALL)
    response_html = re.sub(r'(<h2>Skill Development and Personalized Recommendations</h2>)(.*)', r'\1<ul>\2</ul>', response_html, flags=re.DOTALL)
    
    response_html = re.sub(r'(<h2>Detailed Course Path</h2>)(.*?)(<h2>|$)', r'\1<ol>\2</ol>\3', response_html, flags=re.DOTALL)

    return response_html
def generate_user_id():
    import uuid
    return str(uuid.uuid4())

def generate_questions(interest):
    genai.configure(api_key="UR API key")

    generation_config = {
        "temperature": 0.7,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 1000,
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.0-pro",
        generation_config=generation_config
    )
    
    prompt = f"Generate 10 technical questions related to {interest} whose answers should be short so that user can answer them easily and the course recommendation system can recommend. Format each question on a new line, prefixed with 'Q: '."

    response = model.generate_content(prompt)
    questions = [q.strip()[3:] for q in response.text.split('\n') if q.strip().startswith('Q: ')]
    
    return questions