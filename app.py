from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import requests
import time
import random
import re
from typing import List, Dict, Any, Union, Optional
from dotenv import load_dotenv

load_dotenv()
#default localhost port 11434
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


app = Flask(__name__, static_folder='static', template_folder='templates')


def clean_notes(text):
    text = re.sub(r'http[s]?://\S+', '', text) 
    text = re.sub(r'&\w+=\S+', '', text)        
    text = re.sub(r'\s+', ' ', text)            
    return text.strip()


# for the static files
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/css/<path:path>')
def serve_css(path):
    return send_from_directory('static/css', path)

@app.route('/js/<path:path>')
def serve_js(path):
    return send_from_directory('static/js', path)

@app.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory('static/assets', path)

#testing the Ollama connection
@app.route('/api/test-ollama', methods=['GET'])
def test_ollama():
    try:
        prompt = """You are a quiz-generation assistant.
Generate 1 multiple-choice question (with A–D) about photosynthesis:
Photosynthesis converts light into chemical energy in plants."""
        
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
        )
        
        print("STATUS", response.status_code)  
        data = response.json()
        print("RAW Ollama response:", data)
        
        return jsonify(data)
    except Exception as e:
        print(f"Error testing Ollama: {e}")
        return jsonify({"error": str(e)}), 500


#api endpoint for generating questions
@app.route('/api/generate-questions', methods=['POST'])
def generate_questions_api():
    data = request.get_json()
    notes_content = data.get('notesContent', '')
    practice_mode = data.get('practiceMode', 'multiple-choice')
    difficulty_level = data.get('difficultyLevel', 'beginner')
    count = data.get('count', 5)
    
    print(f"Generating questions: {practice_mode}, {difficulty_level}, {count}")
    
    try:
        questions = attempt_ollama(notes_content, practice_mode, difficulty_level, count)
        return jsonify({"questions": questions})
    except Exception as error:
        print(f"Error with Ollama API: {error}")
        
        print("Falling back to local question generation...")
        questions = simulate_ai_generation(notes_content, practice_mode, difficulty_level, count)
        return jsonify({"questions": questions})
    
def create_prompt(notes_content: str, practice_mode: str, difficulty_level: str, count: int) -> str:
    """Create an improved prompt based on question type to get better model responses."""
    content = clean_notes(notes_content[:1500]) #token limit*
    base_prompt = f"""You are an expert educator. Generate {count} {difficulty_level} level questions based on these notes:

{content}

"""
    
    if practice_mode == 'multiple-choice':
        return base_prompt + f"""
Generate EXACTLY {count} multiple choice questions with 4 options (A, B, C, D) and answers.
Format each question EXACTLY like this:
Question: [question text]
A) [option A]
B) [option B]
C) [option C]
D) [option D]
Answer: [correct letter]

Make sure each question is complete with all 4 options and an answer.
"""
    elif practice_mode == 'true-false':
        return base_prompt + f"""
Generate EXACTLY {count} true/false questions.
Format each question EXACTLY like this:
Question: [statement]
Answer: [True/False]

Make sure each question has a clear True or False answer.
"""
    elif practice_mode == 'fill-blank':
        return base_prompt + f"""
Generate EXACTLY {count} fill-in-the-blank questions.
Format each question EXACTLY like this:
Question: [sentence with _____ for the blank]
Answer: [word or phrase that goes in the blank]

Make sure each question contains a blank marked with _____ and has an answer.
"""
    elif practice_mode == 'short-answer':
        return base_prompt + f"""
Generate EXACTLY {count} short-answer questions.
Format each question EXACTLY like this:
Question: [question requiring explanation]
Key Terms: [key term 1], [key term 2], [key term 3]

Make sure each question includes at least 3 key terms.
"""
    elif practice_mode == 'random':
        return base_prompt + f"""
Generate EXACTLY {count} mixed questions including multiple choice, true/false, fill-in-blank, and short answer.

Use these formats:
---
**Multiple Choice Question**
Question: ...
A) ...
B) ...
C) ...
D) ...
Answer: B
---
**True/False Question**
Question: ...
Answer: True
---
**Fill-in-the-Blank Question**
Question: The main cause of this issue is _____.
Answer: stress
---
**Short Answer Question**
Question: Explain the effects of isolation on mental health.
Key Terms: loneliness, depression, support

Separate each question with a line of three equal signs:
===
"""

    return base_prompt + f"Generate EXACTLY {count} questions with clear questions and answers."

def attempt_ollama(
    notes_content: str, 
    practice_mode: str, 
    difficulty_level: str, 
    count: int
) -> List[Dict[str, Any]]:
    """Try to generate questions using Ollama with retries on failure."""
    max_retries = 3
    base_delay = 1  
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting Ollama generation, attempt {attempt+1}/{max_retries}")
            questions = generate_with_ollama(notes_content, practice_mode, difficulty_level, count)
            print(f"Success with Ollama")
            return questions
        except Exception as error:
            print(f"Failed attempt {attempt+1}: {error}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  #exponential backoff
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise error

def generate_with_ollama(
    notes_content: str, 
    practice_mode: str, 
    difficulty_level: str, 
    count: int
) -> List[Dict[str, Any]]:
    """Generate questions using Ollama."""
    prompt = create_prompt(notes_content, practice_mode, difficulty_level, count)

    timeout = 90  
    
    try:
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 2048 #limit is 1500 though but for longer stuff
                }
            },
            timeout=timeout
        )
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code} {response.reason}")
            error_text = response.text
            raise Exception(f"Ollama API error: {response.status_code} - {error_text}")
        
        result = response.json()
        
        generated_text = result.get("response", "")
        
        if not generated_text:
            raise Exception("No text was generated by the model")
        
        print(f"Generated text length: {len(generated_text)}")
        

        questions = parse_questions(generated_text, practice_mode, count)

        if len(questions) < count:
            print(f"Only parsed {len(questions)} questions, adding {count - len(questions)} fallback questions")
            additional_questions = generate_fallback_questions(
                notes_content, practice_mode, difficulty_level, count - len(questions)
            )
            questions.extend(additional_questions)
        
        return questions[:count]  
    
    except requests.exceptions.Timeout:
        raise Exception(f"Request to Ollama timed out")
    except Exception as e:
        raise e

# 

def parse_questions(text: str, practice_mode: str, requested_count: int) -> List[Dict[str, Any]]:
    """Parse LLM-generated text into structured question objects."""
    print(f"Parsing generated text (first 200 chars): {text[:200]}...")
    questions = []

    blocks = re.split(r'\n?={3,}\n?', text)
    print(f"Found {len(blocks)} blocks after splitting.")

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lowered = block.lower()

        if 'multiple choice question' in lowered:
            match = re.search(
                r'Question:(.*?)\nA\)(.*?)\nB\)(.*?)\nC\)(.*?)\nD\)(.*?)\nAnswer:\s*([A-Da-d])',
                block, re.DOTALL
            )
            if match:
                q, a, b, c, d, ans = [m.strip() for m in match.groups()]
                index = 'ABCD'.index(ans.upper())
                questions.append({
                    'type': 'multiple-choice',
                    'question': q,
                    'options': [a, b, c, d],
                    'correctAnswerIndex': index
                })

        elif 'true/false question' in lowered or 'true or false' in lowered:
            match = re.search(r'Question:(.*?)\nAnswer:\s*(True|False)', block, re.DOTALL | re.IGNORECASE)
            if match:
                q, ans = [m.strip() for m in match.groups()]
                questions.append({
                    'type': 'true-false',
                    'question': q if q.lower().startswith("true or false") else f"True or False: {q}",
                    'correctAnswer': ans.lower() == 'true'
                })

        elif 'fill-in-the-blank question' in lowered:
            match = re.search(r'Question:(.*?)\nAnswer:\s*(.*)', block, re.DOTALL)
            if match:
                q, ans = [m.strip() for m in match.groups()]
                questions.append({
                    'type': 'fill-blank',
                    'question': q.replace('[BLANK]', '_____').replace('blank', '_____'),
                    'correctAnswer': ans
                })

        elif 'short answer question' in lowered:
            match = re.search(r'Question:(.*?)\n(?:Key Terms:|Keywords:)(.*)', block, re.DOTALL)
            if match:
                q, keywords = [m.strip() for m in match.groups()]
                terms = [term.strip() for term in re.split(r',|;', keywords) if term.strip()]
                questions.append({
                    'type': 'short-answer',
                    'question': q,
                    'keyTerms': terms
                })

        if len(questions) >= requested_count:
            break

    print(f"Successfully parsed {len(questions)} questions.")
    return questions


def create_from_extracted(questions: List[Dict[str, Any]], question_type: str, question_part: str, answer_part: str):
    """Create a question from extracted text."""
    if any(q.get('question') == question_part for q in questions):
        return
    
    if question_type == 'multiple-choice':
        options = []
        option_pattern = r'(?:A\)|A\.)(.*?)(?:B\)|B\.)(.*?)(?:C\)|C\.)(.*?)(?:D\)|D\.)(.*)'
        option_match = re.search(option_pattern, question_part, re.DOTALL)
        
        if option_match:
            clean_question = re.sub(option_pattern, '', question_part, flags=re.DOTALL).strip()
            options = [group.strip() for group in option_match.groups()]
        else:
            clean_question = question_part
            options = generate_default_options(question_part)
        
        correct_idx = 0
        if re.search(r'(?:^|\s+)a(?:\s+|$|\.)', answer_part.lower()):
            correct_idx = 0
        elif re.search(r'(?:^|\s+)b(?:\s+|$|\.)', answer_part.lower()):
            correct_idx = 1
        elif re.search(r'(?:^|\s+)c(?:\s+|$|\.)', answer_part.lower()):
            correct_idx = 2
        elif re.search(r'(?:^|\s+)d(?:\s+|$|\.)', answer_part.lower()):
            correct_idx = 3
        
        questions.append({
            'type': 'multiple-choice',
            'question': clean_question,
            'options': options,
            'correctAnswerIndex': correct_idx
        })
        
    elif question_type == 'true-false':
        is_true = 'true' in answer_part.lower()
        questions.append({
            'type': 'true-false',
            'question': question_part if "true or false" in question_part.lower() else f"True or False: {question_part}",
            'correctAnswer': is_true
        })
        
    elif question_type == 'fill-blank':
        if '_' in question_part or 'blank' in question_part.lower() or '[BLANK]' in question_part:
            if '[BLANK]' in question_part:
                question_part = question_part.replace('[BLANK]', '_____')
            elif 'BLANK' in question_part:
                question_part = question_part.replace('BLANK', '_____')
            
            questions.append({
                'type': 'fill-blank',
                'question': question_part,
                'correctAnswer': answer_part
            })
        else:
            words = question_part.split()
            if len(words) > 4:
                replace_idx = len(words) // 2
                words[replace_idx] = '_____'
                question_with_blank = ' '.join(words)
                
                questions.append({
                    'type': 'fill-blank',
                    'question': question_with_blank,
                    'correctAnswer': words[replace_idx]
                })
            
    elif question_type == 'short-answer':
        key_terms = []
        key_terms_match = re.search(r'Key Terms:(.*)', answer_part, re.IGNORECASE)
        
        if key_terms_match:
            key_terms_text = key_terms_match.group(1).strip()
            key_terms = [term.strip() for term in re.split(r',|;', key_terms_text) if term.strip()]
        
        questions.append({
            'type': 'short-answer',
            'question': question_part,
            'keyTerms': key_terms if key_terms else extract_keywords(question_part)
        })

def generate_with_simplified_prompt(
    notes_content: str, 
    practice_mode: str, 
    difficulty_level: str, 
    count: int
) -> List[Dict[str, Any]]:
    """Generate questions using an extremely simplified prompt for Ollama."""
    content = notes_content[:500]  #reduce tokens

    prompt = f"""Create {count} {practice_mode} questions about:
{content}

"""
    
    if practice_mode == 'multiple-choice':
        prompt += """Format each question like:
Question: [question text]
A) [option A]
B) [option B]
C) [option C]
D) [option D]
Answer: [correct letter]

"""
    elif practice_mode == 'true-false':
        prompt += """Format each question like:
Question: True or False: [statement]
Answer: [True/False]

"""
    elif practice_mode == 'fill-blank':
        prompt += """Format each question like:
Question: [sentence with _____ for blank]
Answer: [correct word or phrase]

"""
    elif practice_mode == 'short-answer':
        prompt += """Format each question like:
Question: [question text]
Answer: [brief answer]
Key Terms: [comma-separated key terms]

"""
    else:  
        prompt += """Format each question like:
Question: [question text]
Answer: [answer]

"""
    
    timeout = min(45, 30 + (count * 3))  
    
    try:
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.6, 
                    "top_p": 0.85,
                    "num_predict": max(512, 200 * count), 
                    "top_k": 30,
                    "repeat_penalty": 1.2
                }
            },
            timeout=timeout
        )
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code} {response.reason}")
            error_text = response.text
            raise Exception(f"Ollama API error: {response.status_code} - {error_text}")
        
        result = response.json()
        generated_text = result.get("response", "")
        
        if not generated_text:
            raise Exception("No text was generated")
        
        print(f"Generated text length: {len(generated_text)}")
        
        questions = parse_simplified_questions(generated_text, practice_mode, count)
        

        if len(questions) < count:
            print(f"Only parsed {len(questions)} questions, adding {count - len(questions)} fallback questions")
            additional_questions = create_basic_fallback_questions(
                notes_content, practice_mode, count - len(questions)
            )
            questions.extend(additional_questions)
        
        return questions[:count]  
    
    except requests.exceptions.Timeout:
        print(f"Request to Ollama timed out")
        return []
    except Exception as e:
        print(f"Simplified prompt generation failed: {str(e)}")
        return []

def parse_simplified_questions(text: str, practice_mode: str, count: int) -> List[Dict[str, Any]]:
    """Parse questions from a simplified text format."""
    questions = []

    qa_pairs = re.finditer(r"Question:(.*?)Answer:(.*?)(?=Question:|$)", text, re.DOTALL | re.IGNORECASE)
    
    for match in qa_pairs:
        if len(questions) >= count:
            break
            
        q_text = match.group(1).strip()
        a_text = match.group(2).strip()
        
        if not q_text or not a_text:
            continue
            
        if practice_mode == 'multiple-choice':
            options_pattern = r'(?:A[\.\)])(.*?)(?:B[\.\)])(.*?)(?:C[\.\)])(.*?)(?:D[\.\)])(.*)'
            option_match = re.search(options_pattern, q_text, re.DOTALL)
            
            if option_match:
                clean_question = re.sub(options_pattern, '', q_text, flags=re.DOTALL).strip()
                options = [group.strip() for group in option_match.groups()]
                
                correct_answer_index = 0
                if re.search(r'\b[aA]\b', a_text):
                    correct_answer_index = 0
                elif re.search(r'\b[bB]\b', a_text):
                    correct_answer_index = 1
                elif re.search(r'\b[cC]\b', a_text):
                    correct_answer_index = 2
                elif re.search(r'\b[dD]\b', a_text):
                    correct_answer_index = 3
                
                questions.append({
                    'type': 'multiple-choice',
                    'question': clean_question,
                    'options': options,
                    'correctAnswerIndex': correct_answer_index
                })
            else:
                options = []
                correct_answer_index = 0
                
                option_lines = a_text.split('\n')
                if len(option_lines) >= 4:
                    for i, line in enumerate(option_lines[:4]):
                        option_match = re.search(r'[A-D][\.\)]?\s*(.*)', line)
                        if option_match:
                            option_text = option_match.group(1).strip()
                            options.append(option_text)
                            if '*' in line or 'correct' in line.lower():
                                correct_answer_index = i
                
                if len(options) == 4:
                    questions.append({
                        'type': 'multiple-choice',
                        'question': q_text,
                        'options': options,
                        'correctAnswerIndex': correct_answer_index
                    })
                else:
                    keywords = extract_keywords2(q_text)
                    questions.append(create_basic_mc_question(q_text, a_text, keywords))
        
        elif practice_mode == 'true-false':
            clean_question = q_text
            if not re.search(r'true or false', clean_question, re.IGNORECASE):
                clean_question = f"True or False: {clean_question}"
            
            is_true = 'true' in a_text.lower()
            
            questions.append({
                'type': 'true-false',
                'question': clean_question,
                'correctAnswer': is_true
            })
        
        elif practice_mode == 'fill-blank':
            clean_question = q_text
            if not re.search(r'_+|\[BLANK\]|BLANK', clean_question, re.IGNORECASE):
                key_term = a_text.strip()
                if key_term and key_term in clean_question:
                    clean_question = clean_question.replace(key_term, '_____', 1)
                else:
                    words = clean_question.split()
                    if len(words) > 3:
                        middle_idx = len(words) // 2
                        words[middle_idx] = '_____'
                        clean_question = ' '.join(words)
            
            clean_question = clean_question.replace('[BLANK]', '_____')
            clean_question = re.sub(r'\bBLANK\b', '_____', clean_question, flags=re.IGNORECASE)
            
            questions.append({
                'type': 'fill-blank',
                'question': clean_question,
                'correctAnswer': a_text.strip()
            })
        
        elif practice_mode == 'short-answer':
            key_terms = []
            key_terms_match = re.search(r'Key Terms:(.*?)(?=\n|$)', a_text, re.IGNORECASE)
            
            if key_terms_match:
                key_terms_text = key_terms_match.group(1).strip()
                key_terms = [term.strip() for term in re.split(r',|;', key_terms_text) if term.strip()]
                clean_answer = re.sub(r'Key Terms:.*?(?=\n|$)', '', a_text, flags=re.IGNORECASE).strip()
            else:
                clean_answer = a_text.strip()
                key_terms = extract_keywords2(q_text)
            
            questions.append({
                'type': 'short-answer',
                'question': q_text,
                'keyTerms': key_terms if key_terms else extract_keywords2(q_text)
            })
        
        else:  
            if re.search(r'A\)|A\.|B\)|B\.', q_text):
                options_pattern = r'(?:A[\.\)])(.*?)(?:B[\.\)])(.*?)(?:C[\.\)])(.*?)(?:D[\.\)])(.*)'
                option_match = re.search(options_pattern, q_text, re.DOTALL)
                
                if option_match:
                    clean_question = re.sub(options_pattern, '', q_text, flags=re.DOTALL).strip()
                    options = [group.strip() for group in option_match.groups()]
                    
                    correct_answer_index = 0
                    if re.search(r'\b[aA]\b', a_text):
                        correct_answer_index = 0
                    elif re.search(r'\b[bB]\b', a_text):
                        correct_answer_index = 1
                    elif re.search(r'\b[cC]\b', a_text):
                        correct_answer_index = 2
                    elif re.search(r'\b[dD]\b', a_text):
                        correct_answer_index = 3
                    
                    questions.append({
                        'type': 'multiple-choice',
                        'question': clean_question,
                        'options': options,
                        'correctAnswerIndex': correct_answer_index
                    })
                
            elif re.search(r'true|false', q_text, re.IGNORECASE) or re.search(r'true|false', a_text, re.IGNORECASE):
                clean_question = q_text
                if not re.search(r'true or false', clean_question, re.IGNORECASE):
                    clean_question = f"True or False: {clean_question}"
                
                questions.append({
                    'type': 'true-false',
                    'question': clean_question,
                    'correctAnswer': 'true' in a_text.lower()
                })
                
            elif re.search(r'_+|\[BLANK\]|BLANK', q_text, re.IGNORECASE):
                clean_question = q_text.replace('[BLANK]', '_____')
                clean_question = re.sub(r'\bBLANK\b', '_____', clean_question, flags=re.IGNORECASE)
                
                questions.append({
                    'type': 'fill-blank',
                    'question': clean_question,
                    'correctAnswer': a_text.strip()
                })
                
            else:
                questions.append({
                    'type': 'short-answer',
                    'question': q_text,
                    'keyTerms': extract_keywords2(q_text)
                })
    
    return questions

def create_basic_fallback_questions(notes_content: str, practice_mode: str, count: int) -> List[Dict[str, Any]]:
    """Create very basic fallback questions when parsing fails."""
    fallback_questions = []
    
    sentences = re.split(r'[.!?]\s+', notes_content)
    sentences = [s.strip() + '.' for s in sentences if len(s.strip()) > 10]
    
    usable_sentences = sentences[:min(len(sentences), count * 2)]
    
    for i in range(min(count, len(usable_sentences))):
        if i >= len(usable_sentences):
            break
            
        if practice_mode == 'multiple-choice':
            fallback_questions.append(create_basic_mc_question(usable_sentences[i], "", extract_keywords2(usable_sentences[i])))
            
        elif practice_mode == 'true-false':
            fallback_questions.append({
                'type': 'true-false',
                'question': f"True or False: {usable_sentences[i]}",
                'correctAnswer': random.choice([True, False])
            })
            
        elif practice_mode == 'fill-blank':
            words = usable_sentences[i].split()
            if len(words) > 3:
                replace_idx = len(words) // 2
                answer = words[replace_idx]
                words[replace_idx] = '_____'
                question = ' '.join(words)
                
                fallback_questions.append({
                    'type': 'fill-blank',
                    'question': question,
                    'correctAnswer': answer
                })
                
        elif practice_mode == 'short-answer':
            fallback_questions.append({
                'type': 'short-answer',
                'question': f"Explain the concept of {extract_keywords2(usable_sentences[i])[0] if extract_keywords2(usable_sentences[i]) else 'this topic'} mentioned in the notes.",
                'keyTerms': extract_keywords2(usable_sentences[i])
            })
            
        else:  # random
            question_type = ['multiple-choice', 'true-false', 'fill-blank', 'short-answer'][i % 4]
            if question_type == 'multiple-choice':
                fallback_questions.append(create_basic_mc_question(usable_sentences[i], "", extract_keywords2(usable_sentences[i])))
            elif question_type == 'true-false':
                fallback_questions.append({
                    'type': 'true-false',
                    'question': f"True or False: {usable_sentences[i]}",
                    'correctAnswer': random.choice([True, False])
                })
            elif question_type == 'fill-blank':
                words = usable_sentences[i].split()
                if len(words) > 3:
                    replace_idx = len(words) // 2
                    answer = words[replace_idx]
                    words[replace_idx] = '_____'
                    question = ' '.join(words)
                    fallback_questions.append({
                        'type': 'fill-blank',
                        'question': question,
                        'correctAnswer': answer
                    })
            else:
                fallback_questions.append({
                    'type': 'short-answer',
                    'question': f"Explain the concept of {extract_keywords2(usable_sentences[i])[0] if extract_keywords2(usable_sentences[i]) else 'this topic'} mentioned in the notes.",
                    'keyTerms': extract_keywords2(usable_sentences[i])
                })
    
    return fallback_questions

def create_basic_mc_question(sentence: str, answer: str, keywords: List[str]) -> Dict[str, Any]:
    """Create a basic multiple choice question from a sentence."""
    question = sentence
    
    options = []
    if answer:
        options.append(answer)
    else:
        words = sentence.split()
        if len(words) >= 3:
            mid_point = len(words) // 2
            correct_answer = ' '.join(words[mid_point:mid_point+2])
            options.append(correct_answer)
        else:
            options.append(sentence)
    
    #distractorzzzzzz
    while len(options) < 4:
        if keywords and len(keywords) > len(options) - 1:
            options.append(keywords[len(options) - 1])
        else:
            distractors = [
                "None of the above",
                "All of the above",
                "This concept doesn't apply here",
                "The opposite is true"
            ]
            options.append(distractors[len(options) - 1])
    
    correct_answer = options[0]
    random.shuffle(options)
    correct_index = options.index(correct_answer)
    
    return {
        'type': 'multiple-choice',
        'question': f"Which of the following is true about: {question}",
        'options': options,
        'correctAnswerIndex': correct_index
    }

def extract_keywords2(text: str) -> List[str]: #this extraction function is for the simplified functions if the regular ones dont work
    """Extract potential keywords from text."""
    words = re.findall(r'\b[A-Za-z][A-Za-z-]{3,}\b', text)
    stopwords = {'the', 'and', 'or', 'but', 'for', 'nor', 'on', 'at', 'to', 'from', 'by', 'with', 'in', 'out', 'about', 'than'}
    keywords = [word for word in words if word.lower() not in stopwords]
    return list(set(keywords))[:3]  #limited to top 3 keywords

def extract_keywords(text: str) -> List[str]: #this is the main extraction function for the regfular question parsing function(s?)
    """Extract keywords from text."""
    common_words = {'the', 'and', 'or', 'but', 'for', 'nor', 'on', 'at', 'to', 'from', 'by', 'with', 'in', 'out', 'about', 'than','about', 'after', 'again', 'below', 'could', 'every', 'first', 'found', 'great', 
                    'house', 'large', 'learn', 'never', 'other', 'place', 'small', 'study', 'think', 
                    'where', 'which', 'world', 'would', 'write'}
    
    words = re.sub(r'[^\w\s]', '', text.lower()).split()
    filtered_words = [word for word in words if len(word) > 4 and word not in common_words]
    
    unique_words = list(set(filtered_words))
    return unique_words[:5]

def generate_default_options(question: str) -> List[str]:
    """Generate default options for multiple choice questions."""
    keywords = extract_keywords(question)
    return [
        keywords[0] if keywords else "Correct answer",
        "Alternative answer 1",
        "Alternative answer 2",
        "Alternative answer 3"
    ]

def simulate_ai_generation(
    notes_content: str, 
    practice_mode: str, 
    difficulty: str, 
    count: int
) -> List[Dict[str, Any]]:
    """Generate questions locally when API requests fail."""
    print("Starting local simulation for question generation")
    
    time.sleep(0.8)
    
    concepts = extract_key_concepts(notes_content)
    questions = []

    if practice_mode == 'random':
        types = ['multiple-choice', 'true-false', 'fill-blank', 'short-answer']
        for _ in range(count):
            question_type = random.choice(types)
            questions.append(create_question(concepts, question_type, difficulty))
    else:
        for _ in range(count):
            questions.append(create_question(concepts, practice_mode, difficulty))

    print(f"Generated {len(questions)} questions locally")
    return questions

def extract_key_concepts(text: str) -> List[Dict[str, Union[str, int]]]:
    """Extract key concepts from text."""
    paragraphs = [p for p in text.split('\n\n') if len(p.strip()) > 40]
    
    if len(paragraphs) < 10:
        lower_text = re.sub(r'[^\w\s.?!]', '', text.lower())
        words = lower_text.split()

        freq = {}
        for word in words:
            if len(word) > 3:
                freq[word] = freq.get(word, 0) + 1

        sentences = [s.strip() for s in re.split(r'[.?!]', text) if len(s.strip()) > 20]

        scored = []
        for s in sentences:
            tokens = s.lower().split()
            score = sum(freq.get(word, 0) for word in tokens)
            scored.append({'text': s, 'score': score})

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:25]
    else:
        return [{'text': p, 'score': len(p)} for p in paragraphs]

def create_question(
    concepts: List[Dict[str, Any]], 
    question_type: str, 
    difficulty: str
) -> Dict[str, Any]:
    """Create questions with improved variety."""
    # Select a concept with some weighting toward higher scores
    weighted_index = int(random.random() * random.random() * len(concepts))
    concept = concepts[weighted_index] if weighted_index < len(concepts) else None
    
    if not concept:
        return generate_fallback_questions("", question_type, difficulty, 1)[0]

    sentences = [s.strip() for s in re.split(r'[.?!]', concept['text']) if len(s.strip()) > 15]
    sentence = random.choice(sentences) if sentences else concept['text']
    
    if question_type == 'multiple-choice':
        return create_multiple_choice_question(sentence, difficulty)
    elif question_type == 'true-false':
        return create_true_false_question(sentence)
    elif question_type == 'fill-blank':
        return create_fill_blank_question(sentence)
    elif question_type == 'short-answer':
        return create_short_answer_question(sentence, difficulty)
    else:
        return create_multiple_choice_question(sentence, difficulty)

def create_multiple_choice_question(text: str, difficulty: str) -> Dict[str, Any]:
    """Create multiple choice questions."""
    question = f"What is the main concept described in this text: '{text[:50]}...'?"
    
    options = generate_options(text, difficulty)
    
    return {
        'type': 'multiple-choice',
        'question': question,
        'options': options,
        'correctAnswerIndex': 0  # First option is correct
    }

def generate_options(text: str, difficulty: str) -> List[str]:
    """Generate options for multiple choice questions."""
    key_terms = extract_key_terms(text, difficulty)
    
    correct_answer = key_terms[0] if key_terms else "Correct answer"
    
    distractors = generate_smart_distractors(correct_answer, difficulty)
    
    all_options = [correct_answer] + distractors
    random.shuffle(all_options)
    
    return all_options


def create_true_false_question(text: str) -> Dict[str, Any]:
    """Create true/false questions."""
    is_true = random.random() > 0.4  
    
    if is_true:
        statement = text
    else:
        words = text.split(' ')
        if len(words) > 8:
            method = random.randint(0, 2)
            
            if method == 0:
                split_point = len(words) // 2
                statement = ' '.join(words[split_point:] + words[:split_point])
            elif method == 1:
                statement = f"It is not the case that {text}"
            else:
                insert_point = random.randint(0, len(words) - 1)
                contradictions = ['never', 'always', 'rarely', 'incorrectly', 'falsely']
                words.insert(insert_point, random.choice(contradictions))
                statement = ' '.join(words)
        else:
            statement = f"It is incorrect that {text}"
    
    return {
        'type': 'true-false',
        'question': f"True or False: {statement}",
        'correctAnswer': is_true
    }

def create_fill_blank_question(text: str) -> Dict[str, Any]:
    """Create fill-in-the-blank questions."""
    important_word_pattern = r'\b(is|are|was|were|has|have|will|should|could|must|main|key|critical|important|essential|primary|necessary|fundamental|crucial|significant)\b'
    
    words = text.split(' ')
    target_index = -1
    
    for i, word in enumerate(words):
        if len(word) > 4 and re.search(important_word_pattern, word, re.IGNORECASE):
            target_index = i
            break
    
    if target_index == -1:
        candidates = [(word, i) for i, word in enumerate(words) if len(word) > 4]
        if candidates:
            _, target_index = random.choice(candidates)
        else:
            target_index = random.randint(0, len(words) - 1)
    
    target = words[target_index]
    words[target_index] = '_______'
    
    return {
        'type': 'fill-blank',
        'question': ' '.join(words),
        'correctAnswer': target
    }

def create_short_answer_question(text: str, difficulty: str) -> Dict[str, Any]:
    """Create short answer questions."""
    try:
        question = query_hugging_face_api(text)
        if not question:
            question = f"Explain the following concept: {text[:50]}..."
    except Exception:
        question = f"Explain the following concept: {text[:50]}..."
    
    key_terms = extract_key_terms(text, difficulty)
    
    return {
        'type': 'short-answer',
        'question': question,
        'keyTerms': key_terms
    }

def extract_key_terms(text: str, difficulty: str) -> List[str]:
    """Extract key terms based on difficulty level."""
    capitalized_terms = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', text) or []

    words = [w for w in text.split() if len(w) > 5]

    combined = capitalized_terms + words
    unique = list(set(term.lower() for term in combined))

    count = 4 if difficulty == 'expert' else 3 if difficulty == 'intermediate' else 2
    
    random.shuffle(unique)
    return unique[:count]

def generate_smart_distractors(correct: str, difficulty: str) -> List[str]:
    """Generate smart distractors for multiple choice questions."""
    pool = [
        'process', 'context', 'analysis', 'perspective', 'outcome', 'result', 
        'response', 'summary', 'concept', 'method', 'approach', 'technique', 
        'strategy', 'system', 'function', 'structure', 'element', 'factor',
        'principle', 'theory', 'model', 'framework', 'procedure', 'mechanism'
    ]

    distractors = [p for p in pool if p != correct]

    distractors = [word for word in distractors if abs(len(word) - len(correct)) < 4]

    if len(distractors) < 5:
        general_distractors = [
            'the opposite approach',
            'an unrelated concept',
            'a different methodology',
            'an alternative perspective'
        ]
        distractors.extend(general_distractors)

    count = 5 if difficulty == 'expert' else 4 if difficulty == 'intermediate' else 3
    random.shuffle(distractors)
    return distractors[:count]


    
def generate_fallback_questions(notes_content: str, practice_mode: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
    """Generate higher-quality fallback questions based on the actual notes content."""
    print(f"Generating {count} fallback questions for {practice_mode} mode")
    
    #extracting key sentences from the notes
    sentences = []
    for paragraph in notes_content.split('\n\n'):
        if len(paragraph.strip()) < 30 or '@app.' in paragraph or 'def ' in paragraph:
            continue
            
        paragraph_sentences = re.split(r'[.!?]', paragraph)
        sentences.extend([s.strip() for s in paragraph_sentences if len(s.strip()) > 20])
    
    if not sentences:
        return [create_generic_fallback_question(practice_mode) for _ in range(count)]
    
    questions = []
    for _ in range(count):
        sentence = random.choice(sentences) if sentences else ""
        
        if practice_mode == 'multiple-choice':
            questions.append(create_smarter_multiple_choice(sentence, difficulty))
        elif practice_mode == 'true-false':
            questions.append(create_smarter_true_false(sentence))
        elif practice_mode == 'fill-blank':
            questions.append(create_smarter_fill_blank(sentence))
        elif practice_mode == 'short-answer':
            questions.append(create_smarter_short_answer(sentence, difficulty))
        elif practice_mode == 'random':
            question_types = ['multiple-choice', 'true-false', 'fill-blank', 'short-answer']
            random_type = random.choice(question_types)
            
            if random_type == 'multiple-choice':
                questions.append(create_smarter_multiple_choice(sentence, difficulty))
            elif random_type == 'true-false':
                questions.append(create_smarter_true_false(sentence))
            elif random_type == 'fill-blank':
                questions.append(create_smarter_fill_blank(sentence))
            else:
                questions.append(create_smarter_short_answer(sentence, difficulty))
    
    return questions


def create_smarter_multiple_choice(sentence: str, difficulty: str) -> Dict[str, Any]:
    """Create a better multiple choice question based on a sentence."""
    words = sentence.split()
    
    if len(words) > 10:
        start_idx = random.randint(0, len(words) - 5)
        key_phrase = ' '.join(words[start_idx:start_idx + min(5, len(words) - start_idx)])
        question = f"What comes next in this sequence: '{key_phrase}...'?"
        
        next_idx = start_idx + 5
        if next_idx < len(words):
            correct_answer = ' '.join(words[next_idx:next_idx + 3])
        else:
            correct_answer = "the end of the text"
    else:
        question = f"Which statement best describes the following: '{sentence}'?"
        correct_answer = "This statement is accurate"
    
    if difficulty == 'beginner':
        distractors = [
            "This statement is inaccurate",
            "This statement is only partly correct",
            "None of the above"
        ]
    elif difficulty == 'intermediate':
        distractors = [
            f"The opposite is true: {' '.join([w for w in reversed(words[:10])])}",
            f"A different approach is described: {sentence.replace('is', 'is not')}",
            "This statement relates to a different topic"
        ]
    else:  #expert
        distractors = [
            f"This is misleading because {words[0]} doesn't {' '.join(words[1:3])}",
            f"While {' '.join(words[:3])}, the rest is incorrect",
            f"Only {' '.join(words[-3:])} is accurate"
        ]
    
    options = [correct_answer] + distractors
    random.shuffle(options)
    correct_answer_index = options.index(correct_answer)
    
    return {
        'type': 'multiple-choice',
        'question': question,
        'options': options,
        'correctAnswerIndex': correct_answer_index
    }

def create_smarter_true_false(sentence: str) -> Dict[str, Any]:
    """Create a better true/false question based on a sentence."""
    is_true = random.random() > 0.3  #bias toward true statements
    
    if is_true:
        question = f"True or False: {sentence}"
    else:
        words = sentence.split()
        if len(words) > 5:
            method = random.randint(0, 2)
            
            if method == 0:
                for i in range(len(words)):
                    if words[i] in ['is', 'are', 'was', 'were', 'has', 'have', 'will', 'can', 'should']:
                        words[i] = words[i] + ' not'
                        break
                    elif words[i] in ['not']:
                        words[i] = ''
                        break
                question = f"True or False: {' '.join([w for w in words if w])}"
            elif method == 1:
                if len(words) > 8:
                    mid = len(words) // 2
                    words[mid], words[mid-1] = words[mid-1], words[mid]
                    question = f"True or False: {' '.join(words)}"
                else:
                    question = f"True or False: The opposite of '{sentence}' is correct"
            else:
                question = f"True or False: {sentence}, which is never the case"
        else:
            question = f"True or False: The opposite of '{sentence}' is correct"
    
    return {
        'type': 'true-false',
        'question': question,
        'correctAnswer': is_true
    }

def create_smarter_fill_blank(sentence: str) -> Dict[str, Any]:
    """Create a better fill-in-the-blank question based on a sentence."""
    words = sentence.split()
    
    common_words = {'about', 'after', 'again', 'below', 'could', 'every', 'first', 'found', 'great', 
                    'house', 'large', 'learn', 'never', 'other', 'place', 'small', 'study', 'think', 
                    'where', 'which', 'world', 'would', 'write', 'their', 'there', 'these', 'those'}
    
    candidate_indices = [i for i, word in enumerate(words) 
                        if len(word) > 4 and word.lower() not in common_words]
    
    if not candidate_indices:
        candidate_indices = [i for i, word in enumerate(words) if len(word) > 3]
    
    if candidate_indices:
        target_idx = random.choice(candidate_indices)
        correct_answer = words[target_idx]
        words[target_idx] = '_____'
        question = ' '.join(words)
    else:
        question = f"The purpose of the code is to _____."
        correct_answer = "generate questions"
    
    return {
        'type': 'fill-blank',
        'question': question,
        'correctAnswer': correct_answer
    }

def create_smarter_short_answer(sentence: str, difficulty: str) -> Dict[str, Any]:
    """Create a better short-answer question based on a sentence."""
    if len(sentence) > 50:
        question = f"Explain the meaning and implications of: '{sentence}'"
    else:
        question = f"Describe the concept mentioned in: '{sentence}'"
    
    key_terms = []
    words = [w for w in re.sub(r'[^\w\s]', '', sentence.lower()).split() if len(w) > 4]
    
    common_words = {'about', 'after', 'again', 'below', 'could', 'every', 'first', 'found', 'great', 
                    'house', 'large', 'learn', 'never', 'other', 'place', 'small', 'study', 'think', 
                    'where', 'which', 'world', 'would', 'write', 'their', 'there', 'these', 'those'}
                    
    unique_words = list(set(w for w in words if w not in common_words))
    
    num_terms = 5 if difficulty == 'expert' else 4 if difficulty == 'intermediate' else 3
    
    unique_words.sort(key=len, reverse=True)
    key_terms = unique_words[:num_terms]
    
    if len(key_terms) < num_terms:
        generic_terms = ['concept', 'analysis', 'process', 'function', 'implementation']
        key_terms.extend(generic_terms[:num_terms - len(key_terms)])
    
    return {
        'type': 'short-answer',
        'question': question,
        'keyTerms': key_terms
    }

def create_generic_fallback_question(question_type: str) -> Dict[str, Any]:
    """Create a generic fallback question when other methods fail."""
    if question_type == 'multiple-choice':
        return {
            'type': 'multiple-choice',
            'question': 'Which API is this application using to generate questions?',
            'options': [
                'Hugging Face API',
                'OpenAI API',
                'Google AI API',
                'Custom local model'
            ],
            'correctAnswerIndex': 0
        }
    elif question_type == 'true-false':
        return {
            'type': 'true-false',
            'question': 'True or False: This application uses the Hugging Face API to generate questions from user notes.',
            'correctAnswer': True
        }
    elif question_type == 'fill-blank':
        return {
            'type': 'fill-blank',
            'question': 'This application uses the _____ API to generate questions for users.',
            'correctAnswer': 'Hugging Face'
        }
    elif question_type == 'short-answer':
        return {
            'type': 'short-answer',
            'question': 'Explain how this application processes user notes to generate questions.',
            'keyTerms': [
                'API', 
                'parsing', 
                'generation', 
                'fallback', 
                'question format'
            ]
        }
    else:
        return {
            'type': 'multiple-choice',
            'question': 'What fallback mechanism does this application use when external APIs fail?',
            'options': [
                'Local simulation',
                'Abort operation',
                'Output nothing',
                'Raise an exception'
            ],
            'correctAnswerIndex': 0
        }
    
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
        