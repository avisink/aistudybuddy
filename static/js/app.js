document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');
    const practiceMode = document.getElementById('practice-mode');
    const difficultyLevel = document.getElementById('difficulty-level');
    const questionCount = document.getElementById('question-count');
    const startPracticeBtn = document.getElementById('start-practice-btn');
    const questionsContainer = document.getElementById('questions-container');
    const questionDisplay = document.getElementById('question-display');
    const questionProgress = document.getElementById('question-progress');
    const prevQuestionBtn = document.getElementById('prev-question');
    const nextQuestionBtn = document.getElementById('next-question');
    const finishPracticeBtn = document.getElementById('finish-practice');
    const resultsSection = document.getElementById('results-section');
    const resultsSummary = document.getElementById('results-summary');
    const downloadPdfBtn = document.getElementById('download-pdf');
    const newPracticeBtn = document.getElementById('new-practice');
 

    let notesContent = '';
    let currentQuestions = [];
    let userAnswers = [];
    let currentQuestionIndex = 0;

    restoreSession();


    uploadBtn.addEventListener('click', handleFileUpload);
    practiceMode.addEventListener('change', handlePracticeModeChange);
    difficultyLevel.addEventListener('change', handleDifficultyChange);
    startPracticeBtn.addEventListener('click', startPracticeSession);
    prevQuestionBtn.addEventListener('click', showPreviousQuestion);
    nextQuestionBtn.addEventListener('click', showNextQuestion);
    finishPracticeBtn.addEventListener('click', finishPractice);
    downloadPdfBtn.addEventListener('click', downloadResultsPdf);
    newPracticeBtn.addEventListener('click', resetPractice);

  

    async function handleFileUpload() {
        const file = fileInput.files[0];
        if (!file) {
            showUploadStatus('Please select a file first.', 'error');
            return;
        }

        const fileType = file.name.split('.').pop().toLowerCase();
        uploadBtn.disabled = true;
        showUploadStatus('Processing your file...', '');

        try {
            if (fileType === 'pdf') {
                notesContent = await parsePdfFile(file);
            } else if (fileType === 'docx') {
                notesContent = await parseWordFile(file);
            } else if (fileType === 'txt') {
                notesContent = await parseTextFile(file);
            } else {
                throw new Error('Unsupported file format. Please upload a PDF, Word, or Text file.');
            }

            console.log('Parsed notes content:', notesContent.substring(0, 100) + '...');
            showUploadStatus('File uploaded and parsed successfully!', 'success');
            practiceMode.disabled = false;

            saveToLocalStorage('notesContent', notesContent);
        } catch (error) {
            console.error('Error processing file:', error);
            showUploadStatus(`Error: ${error.message}`, 'error');
        } finally {
            uploadBtn.disabled = false;
        }
    }

    function showUploadStatus(message, status) {
        uploadStatus.textContent = message;
        uploadStatus.className = status ? `status-${status}` : '';
    }

    function handlePracticeModeChange() {
        const selected = practiceMode.value;
        if (selected) {
            difficultyLevel.disabled = false;
            saveToLocalStorage('practiceMode', selected);
        }
    }

    function handleDifficultyChange() {
        const selected = difficultyLevel.value;
        if (selected) {
            questionCount.disabled = false;
            startPracticeBtn.disabled = false;
            saveToLocalStorage('difficultyLevel', selected);
        }
    }

    async function startPracticeSession() {
        const mode = practiceMode.value;
        const difficulty = difficultyLevel.value;
        const count = parseInt(questionCount.value);

        if (!mode || !difficulty || isNaN(count)) {
            alert('Please select all options before starting.');
            return;
        }

        saveToLocalStorage('practiceMode', mode);
        saveToLocalStorage('difficultyLevel', difficulty);
        saveToLocalStorage('questionCount', count);

        startPracticeBtn.disabled = true;
        startPracticeBtn.textContent = "Generating questions...";

        try {
            const response = await fetch('/api/generate-questions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    notesContent: notesContent,
                    practiceMode: mode,
                    difficultyLevel: difficulty,
                    count: count
                })
            });

            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }

            const data = await response.json();
            currentQuestions = data.questions;
            
            if (!currentQuestions || currentQuestions.length === 0) {
                throw new Error("Failed to generate questions. Please try again.");
            }

            if (mode === 'random') {
                console.log('Random mode active with question types:', 
                    currentQuestions.map(q => q.type).join(', '));
            }

            userAnswers = Array(currentQuestions.length).fill(null);
            currentQuestionIndex = 0;

            document.getElementById('practice-section').classList.add('hidden');
            questionsContainer.classList.remove('hidden');
            displayCurrentQuestion();
        } catch (error) {
            alert(`Failed to generate questions: ${error.message}`);
            console.error(error);
        } finally {
            startPracticeBtn.disabled = false;
            startPracticeBtn.textContent = "Start Practice";
        }
    }


    async function parsePdfFile(file) {
        return new Promise((resolve, reject) => {
            const fileReader = new FileReader();

            fileReader.onload = async function(event) {
                try {
                    const typedArray = new Uint8Array(event.target.result);
                    const loadingTask = pdfjsLib.getDocument({ data: typedArray });
                    const pdf = await loadingTask.promise;

                    let fullText = '';

                    for (let i = 1; i <= pdf.numPages; i++) {
                        const page = await pdf.getPage(i);
                        const textContent = await page.getTextContent();
                        const pageText = textContent.items.map(item => item.str).join(' ');
                        fullText += pageText + '\n';
                    }

                    resolve(fullText);
                } catch (error) {
                    reject(error);
                }
            };

            fileReader.onerror = function() {
                reject(new Error('Failed to read the PDF file.'));
            };

            fileReader.readAsArrayBuffer(file);
        });
    }

    async function parseWordFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = function(event) {
                mammoth.extractRawText({ arrayBuffer: event.target.result })
                    .then(result => {
                        resolve(result.value);
                    })
                    .catch(error => {
                        reject(error);
                    });
            };

            reader.onerror = function() {
                reject(new Error('Failed to read the Word file.'));
            };

            reader.readAsArrayBuffer(file);
        });
    }

    async function parseTextFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = function(event) {
                resolve(event.target.result);
            };

            reader.onerror = function() {
                reject(new Error('Failed to read the text file.'));
            };

            reader.readAsText(file);
        });
    }


    function displayCurrentQuestion() {
        const question = currentQuestions[currentQuestionIndex];
        questionProgress.textContent = `Question ${currentQuestionIndex + 1} of ${currentQuestions.length}`;

        prevQuestionBtn.disabled = currentQuestionIndex === 0;
        nextQuestionBtn.disabled = currentQuestionIndex === currentQuestions.length - 1;
        nextQuestionBtn.classList.toggle('hidden', currentQuestionIndex === currentQuestions.length - 1);
        finishPracticeBtn.classList.toggle('hidden', currentQuestionIndex !== currentQuestions.length - 1);

        let html = '';
        switch (question.type) {
            case 'multiple-choice':
                html = createMultipleChoiceHTML(question);
                break;
            case 'true-false':
                html = createTrueFalseHTML(question);
                break;
            case 'fill-blank':
                html = createFillBlankHTML(question);
                break;
            case 'short-answer':
                html = createShortAnswerHTML(question);
                break;
        }

        questionDisplay.innerHTML = html;
        setupQuestionInteractions(question.type);
    }

    function createMultipleChoiceHTML(question) {
        const userAnswer = userAnswers[currentQuestionIndex];
        return `
            <div class="question-text">${question.question}</div>
            <ul class="options-list">
                ${question.options.map((opt, i) => `
                    <li class="option-item ${userAnswer === i ? 'selected' : ''}" data-index="${i}">${opt}</li>
                `).join('')}
            </ul>
        `;
    }

    function createTrueFalseHTML(question) {
        const userAnswer = userAnswers[currentQuestionIndex];
        return `
            <div class="question-text">${question.question}</div>
            <ul class="options-list">
                <li class="option-item ${userAnswer === true ? 'selected' : ''}" data-value="true">True</li>
                <li class="option-item ${userAnswer === false ? 'selected' : ''}" data-value="false">False</li>
            </ul>
        `;
    }

    function createFillBlankHTML(question) {
        const userAnswer = userAnswers[currentQuestionIndex] || '';
        return `
            <div class="question-text">${question.question}</div>
            <input type="text" class="blank-input" value="${userAnswer}">
        `;
    }

    function createShortAnswerHTML(question) {
        const userAnswer = userAnswers[currentQuestionIndex] || '';
        return `
            <div class="question-text">${question.question}</div>
            <textarea class="answer-input">${userAnswer}</textarea>
        `;
    }

    function setupQuestionInteractions(type) {
        switch (type) {
            case 'multiple-choice':
                document.querySelectorAll('.option-item').forEach(item => {
                    item.addEventListener('click', () => {
                        userAnswers[currentQuestionIndex] = parseInt(item.dataset.index);
                        displayCurrentQuestion();
                    });
                });
                break;
            case 'true-false':
                document.querySelectorAll('.option-item').forEach(item => {
                    item.addEventListener('click', () => {
                        userAnswers[currentQuestionIndex] = item.dataset.value === 'true';
                        displayCurrentQuestion();
                    });
                });
                break;
            case 'fill-blank':
                document.querySelector('.blank-input').addEventListener('input', e => {
                    userAnswers[currentQuestionIndex] = e.target.value.trim();
                });
                break;
            case 'short-answer':
                document.querySelector('.answer-input').addEventListener('input', e => {
                    userAnswers[currentQuestionIndex] = e.target.value.trim();
                });
                break;
        }
    }

    function showPreviousQuestion() {
        if (currentQuestionIndex > 0) {
            currentQuestionIndex--;
            displayCurrentQuestion();
        }
    }

    function showNextQuestion() {
        if (currentQuestionIndex < currentQuestions.length - 1) {
            currentQuestionIndex++;
            displayCurrentQuestion();
        }
    }

    function finishPractice() {
        const unanswered = userAnswers.filter(ans => ans === null).length;
        if (unanswered > 0 && !confirm(`You have ${unanswered} unanswered question(s). Finish anyway?`)) return;

        const results = evaluateAnswers();
        questionsContainer.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        displayResults(results);
    }

    function evaluateAnswers() {
        let correctCount = 0;
        const detailedResults = currentQuestions.map((q, i) => {
            const userAnswer = userAnswers[i];
            const isCorrect = checkAnswer(q, userAnswer);
            if (isCorrect) correctCount++;
            return {
                question: q.question,
                userAnswer: formatUserAnswer(q.type, userAnswer),
                correctAnswer: formatCorrectAnswer(q),
                isCorrect
            };
        });

        return {
            totalQuestions: currentQuestions.length,
            correctCount,
            score: Math.round((correctCount / currentQuestions.length) * 100),
            detailedResults,
            practiceMode: practiceMode.value,
            difficultyLevel: difficultyLevel.value
        };
    }

    function formatUserAnswer(type, answer) {
        if (answer === null || answer === undefined) return 'Not answered';
    
        const question = currentQuestions[currentQuestionIndex];
    
        if (type === 'multiple-choice') {
            return Array.isArray(question.options) && question.options[answer] !== undefined
                ? question.options[answer]
                : 'Invalid option';
        }
    
        if (type === 'true-false') {
            return answer === true ? 'True' : answer === false ? 'False' : 'Invalid';
        }
    
        return typeof answer === 'string' ? answer : String(answer);
    }
    

    function formatCorrectAnswer(question) {
        switch (question.type) {
            case 'multiple-choice':
                return Array.isArray(question.options) && question.options[question.correctAnswerIndex] !== undefined
                    ? question.options[question.correctAnswerIndex]
                    : 'Invalid correct option';
    
            case 'true-false':
                return question.correctAnswer === true ? 'True' : question.correctAnswer === false ? 'False' : 'Invalid';
    
            case 'fill-blank':
                return question.correctAnswer || 'Not specified';
    
            case 'short-answer':
                return question.keyTerms && question.keyTerms.length > 0
                    ? `Key terms: ${question.keyTerms.join(', ')}`
                    : 'Any reasonable answer';
    
            default:
                return 'Unknown type';
        }
    }
    

    function checkAnswer(question, answer) { //im trying as much as possible to normalize answers that require typing, so that stuff like punctuation, synonyms and typos dont affect evaluation
        if (answer === null || answer === undefined) return false;
    
        switch (question.type) {
            case 'multiple-choice':
                return answer === question.correctAnswerIndex;
    
            case 'true-false':
                return answer === question.correctAnswer;
    
            case 'fill-blank':
                return fuzzyMatch(answer, question.correctAnswer).matched;
    
            case 'short-answer':
                if (!question.keyTerms || question.keyTerms.length === 0) return true;
                return fuzzyMatchKeyTerms(answer, question.keyTerms).matched;
    
            default:
                return false;
        }
    }
    
    function normalize(text) {
        return text.toLowerCase().replace(/[^\w\s]/g, '').trim();
    }

    function fuzzyMatch(answer, term) {
        const answerWords = normalize(answer).split(/\s+/);
        const fuse = new Fuse(answerWords, { includeScore: true, threshold: 0.4 });
        const result = fuse.search(term.toLowerCase());
        return {
            matched: result.length > 0 && result[0].score <= 0.4,
            matchedWord: result.length > 0 ? result[0].item : null
        };
    }

    function fuzzyMatchKeyTerms(answer, keyTerms) { //using fusein these fuzzy functions to normalize a lot of stuff
        const matchedTerms = [];

        for (let term of keyTerms) {
            const match = fuzzyMatch(answer, term);
            if (match.matched) matchedTerms.push(term);
        }

        return {
            matched: matchedTerms.length > 0,
            matchedTerms
        };
    }
    
    function similarity(a, b) {
        const aSet = new Set(a.split(' '));
        const bSet = new Set(b.split(' '));
        const intersection = [...aSet].filter(x => bSet.has(x));
        return intersection.length / Math.max(aSet.size, bSet.size);
    }
    

    function displayResults(results) {
        const html = results.detailedResults.map((item, i) => `
            <div class="review-item ${item.isCorrect ? 'correct' : 'incorrect'}">
                <div class="review-question">Question ${i + 1}: ${item.question}</div>
                <div class="review-answers">
                    <strong>Your Answer:</strong> ${item.userAnswer}<br>
                    <strong>Correct Answer:</strong> ${item.correctAnswer}
                </div>
            </div>
        `).join('');

        resultsSummary.innerHTML = `
            <div class="result-stats">
                <h3>Score: ${results.score}%</h3>
                <p>You answered ${results.correctCount} out of ${results.totalQuestions} questions correctly.</p>
                <p>Practice Mode: ${formatPracticeMode(results.practiceMode)}</p>
                <p>Difficulty Level: ${formatDifficultyLevel(results.difficultyLevel)}</p>
            </div>
            <h3>Questions Review</h3>
            <div class="questions-review">${html}</div>
        `;
    }

    function resetPractice() {
        resultsSection.classList.add('hidden');
        document.getElementById('practice-section').classList.remove('hidden');
        practiceMode.value = '';
        difficultyLevel.value = '';
        questionCount.value = '';
        difficultyLevel.disabled = true;
        questionCount.disabled = true;
        startPracticeBtn.disabled = true;
        currentQuestions = [];
        userAnswers = [];
        currentQuestionIndex = 0;
    }


    function downloadResultsPdf() {
        generateResultsPdf(currentQuestions, userAnswers, practiceMode.value, difficultyLevel.value);
    }

    function generateResultsPdf(questions, answers, mode, difficulty) {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        const title = 'Study Buddy - Practice Results';

        doc.setFontSize(18);
        doc.text(title, 105, 15, { align: 'center' });
        
        doc.setFontSize(12);
        doc.text(`Practice Mode: ${formatPracticeMode(mode)}`, 20, 30);
        doc.text(`Difficulty Level: ${formatDifficultyLevel(difficulty)}`, 20, 38);
        
        
        let correctCount = 0;
        for (let i = 0; i < questions.length; i++) {
            if (checkAnswer(questions[i], answers[i])) correctCount++;
        }
        const score = Math.round((correctCount / questions.length) * 100);
        doc.text(`Score: ${score}% (${correctCount}/${questions.length})`, 20, 46);
        
        
        doc.text('Questions Review:', 20, 60);
        
        let yPos = 70;
        for (let i = 0; i < questions.length; i++) {
            const q = questions[i];
            const userAnswer = answers[i];
            const isCorrect = checkAnswer(q, userAnswer);
            
           
            if (yPos > 270) {
                doc.addPage();
                yPos = 20;
            }
            
            doc.setFontSize(11);
            doc.text(`Question ${i + 1}: ${q.question}`, 20, yPos, { maxWidth: 170 });
            yPos += 10;
            
            doc.setFontSize(10);
            doc.text(`Your Answer: ${formatUserAnswer(q.type, userAnswer)}`, 25, yPos);
            yPos += 7;
            
            doc.text(`Correct Answer: ${formatCorrectAnswer(q)}`, 25, yPos);
            yPos += 7;
            
            doc.text(`Result: ${isCorrect ? 'Correct' : 'Incorrect'}`, 25, yPos);
            yPos += 15;
        }
        
        
        const now = new Date();
        doc.setFontSize(9);
        doc.text(`Generated on ${now.toLocaleDateString()} at ${now.toLocaleTimeString()}`, 105, 290, { align: 'center' });
        
       
        doc.save('study-buddy-results.pdf');
    }

    function formatPracticeMode(mode) {
        return {
            'multiple-choice': 'Multiple Choice',
            'true-false': 'True/False',
            'fill-blank': 'Fill in the Blank',
            'short-answer': 'Short Answer',
            'random': 'Random Mode'
        }[mode] || mode;
    }

    function formatDifficultyLevel(level) {
        return {
            'beginner': 'Beginner',
            'intermediate': 'Intermediate',
            'expert': 'Expert'
        }[level] || level;
    }


    function saveToLocalStorage(key, value) {
        try {
            localStorage.setItem(key, typeof value === 'object' ? JSON.stringify(value) : value);
            localStorage.setItem('sessionTimestamp', Date.now().toString());
        } catch (error) {
            console.error('Error saving to localStorage:', error);
        }
    }

    function getFromLocalStorage(key) {
        const raw = localStorage.getItem(key);
        try {
            return JSON.parse(raw);
        } catch {
            return raw;
        }
    }

    function restoreSession() {
        if (isSessionExpired()) {
            localStorage.clear();
            return;
        }

        notesContent = getFromLocalStorage('notesContent') || '';
        practiceMode.value = getFromLocalStorage('practiceMode') || '';
        difficultyLevel.value = getFromLocalStorage('difficultyLevel') || '';
        questionCount.value = getFromLocalStorage('questionCount') || '';

        if (notesContent) {
            practiceMode.disabled = false;
        }
        if (practiceMode.value) {
            difficultyLevel.disabled = false;
        }
        if (difficultyLevel.value) {
            questionCount.disabled = false;
            startPracticeBtn.disabled = false;
        }
    }

    function toggleDarkMode() {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('prefersDark', document.body.classList.contains('dark-mode'));
      }
      
      window.addEventListener('DOMContentLoaded', () => {
        if (localStorage.getItem('prefersDark') === 'true') {
          document.body.classList.add('dark-mode');
        }
      });

    function isSessionExpired() {
        const timestamp = localStorage.getItem('sessionTimestamp');
        if (!timestamp) return true;
        const days = (Date.now() - parseInt(timestamp)) / (1000 * 60 * 60 * 24);
        return days > 7;
    }
})