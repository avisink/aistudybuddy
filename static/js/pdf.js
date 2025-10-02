/**
 * Generate a PDF report of the practice results
 * @param {Array} questions 
 * @param {Array} userAnswers 
 * @param {string} practiceMode 
 * @param {string} difficultyLevel
 */
function generateResultsPdf(questions, userAnswers, practiceMode, difficultyLevel) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    
    doc.setProperties({
        title: 'Study Buddy Practice Results',
        subject: 'Practice Session Results',
        author: 'Study Buddy Application',
        creator: 'Study Buddy Application'
    });
    
    doc.setFontSize(22);
    doc.setTextColor(66, 133, 244); // #4285f4
    doc.text('Study Buddy Practice Results', 105, 20, { align: 'center' });
    
    
    doc.setFontSize(12);
    doc.setTextColor(51, 51, 51);
    doc.text('Practice Summary', 20, 35);
    
    doc.setFontSize(10);
    doc.text(`Practice Mode: ${formatPracticeMode(practiceMode)}`, 20, 45);
    doc.text(`Difficulty Level: ${formatDifficultyLevel(difficultyLevel)}`, 20, 52);
    doc.text(`Number of Questions: ${questions.length}`, 20, 59);
    
    
    let correctCount = 0;
    questions.forEach((question, index) => {
        if (checkAnswer(question, userAnswers[index])) {
            correctCount++;
        }
    });
    
    const score = Math.round((correctCount / questions.length) * 100);
    
    doc.text(`Score: ${score}% (${correctCount} out of ${questions.length} correct)`, 20, 66);
    
    
    doc.setDrawColor(200, 200, 200);
    doc.line(20, 75, 190, 75);
    
    
    doc.setFontSize(12);
    doc.setTextColor(51, 51, 51);
    doc.text('Questions Review', 20, 85);
    
    let yPosition = 95;
    
   
    questions.forEach((question, index) => {
        const userAnswer = userAnswers[index];
        const isCorrect = checkAnswer(question, userAnswer);
        
        
        if (yPosition > 300) {
            doc.addPage();
            yPosition = 20;
        }
        
        
        doc.setFontSize(10);
        doc.setTextColor(51, 51, 51);
        doc.text(`Question ${index + 1}: ${truncateText(question.question, 80)}`, 20, yPosition);
        yPosition += 7;
        
        
        doc.setTextColor(...(isCorrect ? [52, 168, 83] : [234, 67, 53]));;
        doc.text(`Your Answer: ${formatAnswer(question.type, userAnswer)}`, 25, yPosition);
        yPosition += 7;
        
        
        doc.setTextColor(52, 168, 83); 
        doc.text(`Correct Answer: ${formatCorrectAnswer(question)}`, 25, yPosition);
        yPosition += 12;
    });
    
    
    const filename = `StudyBuddy_Results_${new Date().toISOString().slice(0,10)}.pdf`;
    doc.save(filename);
}

function formatPracticeMode(mode) {
    const modes = {
        'multiple-choice': 'Multiple Choice',
        'true-false': 'True/False',
        'fill-blank': 'Fill in the Blank',
        'short-answer': 'Short Answer',
        'random': 'Random Mode'
    };
    
    return modes[mode] || mode;
}


function formatDifficultyLevel(level) {
    const levels = {
        'beginner': 'Beginner',
        'intermediate': 'Intermediate',
        'expert': 'Expert'
    };
    
    return levels[level] || level;
}


function checkAnswer(question, userAnswer) {
    if (userAnswer === null) return false;
    
    switch (question.type) {
        case 'multiple-choice':
            return userAnswer === question.correctAnswerIndex;
            
        case 'true-false':
            return userAnswer === question.correctAnswer;
            
        case 'fill-blank':
            return userAnswer.toLowerCase() === question.correctAnswer.toLowerCase();
            
        case 'short-answer':
            if (!question.keyTerms || !question.keyTerms.length) return true; 
            
            const lowerUserAnswer = userAnswer.toLowerCase();
            return question.keyTerms.some(term => lowerUserAnswer.includes(term.toLowerCase()));
            
        default:
            return false;
    }
}


function formatAnswer(questionType, userAnswer) {
    if (userAnswer === null) return 'Not answered';
    
    switch (questionType) {
        case 'multiple-choice':
            return `Option ${userAnswer + 1}`;
            
        case 'true-false':
            return userAnswer ? 'True' : 'False';
            
        default:
            return truncateText(userAnswer, 50);
    }
}


function formatCorrectAnswer(question) {
    switch (question.type) {
        case 'multiple-choice':
            return `Option ${question.correctAnswerIndex + 1} (${truncateText(question.options[question.correctAnswerIndex], 40)})`;
            
        case 'true-false':
            return question.correctAnswer ? 'True' : 'False';
            
        case 'fill-blank':
            return question.correctAnswer;
            
        case 'short-answer':
            return question.keyTerms ? `Key terms: ${question.keyTerms.join(', ')}` : 'Any reasonable answer';
            
        default:
            return '';
    }
}

function truncateText(text, maxLength) {
    if (!text) return '';
    
    if (text.length <= maxLength) {
        return text;
    }
    
    return text.substring(0, maxLength) + '...';
}