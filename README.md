# Study Buddy - AI-Powered Quiz Generator

An intelligent study companion that transforms your notes into personalized practice questions. Simply paste your study materials and get instant quizzes tailored to your learning needs.

## Features

- **Multiple Question Types**: Generate multiple-choice, true/false, fill-in-the-blank, and short-answer questions
- **Difficulty Levels**: Choose from beginner, intermediate, or expert difficulty
- **Local AI Processing**: Powered by Ollama and Llama 3 for fast, private question generation
- **Automatic Fallback**: Built-in local generation ensures you always get questions, even offline
- **Smart Parsing**: Intelligently extracts key concepts from your notes to create relevant questions

## Tech Stack

- **Backend**: Flask (Python)
- **AI Model**: Ollama with Llama 3
- **Frontend**: HTML/CSS/JavaScript

## Prerequisites

- Python 3.7+
- [Ollama](https://ollama.ai/) installed locally
- Llama 3 model downloaded (`ollama pull llama3`)

## Quick Start

1. Install dependencies: `pip install flask python-dotenv requests`
2. Ensure Ollama is running: `ollama serve`
3. Start the app: `python app.py`
4. Open `http://localhost:5001` in your browser