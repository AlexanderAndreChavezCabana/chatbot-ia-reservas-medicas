"""
FAQ matcher for reservas project (subset of original FAQ).
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

FAQ_DATABASE = [
    {
        "question": "¿Cuáles son los métodos de pago disponibles?",
        "variations": [
            "¿cómo puedo pagar?",
            "¿qué formas de pago aceptan?",
            "métodos de pago",
            "¿aceptan tarjeta?",
            "¿puedo pagar en efectivo?"
        ],
        "answer": "Aceptamos tarjeta y efectivo. Para tarjeta procesamos la transacción de forma segura."
    },
    {
        "question": "¿Cómo canceló una cita?",
        "variations": ["cancelar cita", "cómo cancelar", "anular turno"],
        "answer": "Para cancelar una cita escribe 'cancelar' durante la conversación o contáctanos por teléfono."
    }
]


class FAQMatcher:
    def __init__(self, threshold=0.85):
        self.threshold = threshold
        self.faq_database = FAQ_DATABASE
        self.vectorizer = TfidfVectorizer()

        self.all_questions = []
        self.question_to_answer = {}

        for faq in self.faq_database:
            self.all_questions.append(faq['question'])
            self.question_to_answer[faq['question']] = faq['answer']
            for variation in faq.get('variations', []):
                self.all_questions.append(variation)
                self.question_to_answer[variation] = faq['answer']

        if self.all_questions:
            self.question_vectors = self.vectorizer.fit_transform(self.all_questions)
        else:
            self.question_vectors = None

    def find_answer(self, user_question: str):
        if not self.question_vectors:
            return None, 0.0
        user_vector = self.vectorizer.transform([user_question])
        similarities = cosine_similarity(user_vector, self.question_vectors)[0]
        max_idx = np.argmax(similarities)
        max_sim = similarities[max_idx]
        if max_sim >= self.threshold:
            q = self.all_questions[max_idx]
            return self.question_to_answer[q], float(max_sim)
        return None, float(max_sim)
