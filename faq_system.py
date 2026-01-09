"""
Sistema FAQ con matching de similitud (copiado/ajustado del taller)
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
        "answer": "Aceptamos dos métodos de pago: tarjeta de crédito/débito (card) y efectivo. Para pagos con tarjeta, procesamos la transacción de forma segura. Para efectivo, coordinamos la entrega contra pago."
    },
    {
        "question": "¿Hacen envíos a domicilio?",
        "variations": [
            "¿entregan a domicilio?",
            "¿tienen delivery?",
            "envío a casa",
            "¿cómo es la entrega?",
            "¿cuánto cuesta el envío?"
        ],
        "answer": "Sí, hacemos envíos a domicilio en toda la ciudad. El envío es gratis para compras superiores a $200. Para compras menores, el costo de envío es de $15. El tiempo de entrega es de 2-5 días hábiles."
    },
    {
        "question": "¿Tienen garantía los productos?",
        "variations": [
            "¿dan garantía?",
            "garantía de productos",
            "¿qué garantía tienen?",
            "¿cuánto dura la garantía?",
            "política de garantía"
        ],
        "answer": "Todos nuestros productos tienen garantía. Laptops y componentes tienen 1 año de garantía del fabricante. Periféricos tienen 6 meses. Cubrimos defectos de fábrica, no daños por mal uso."
    }
]


class FAQMatcher:
    def __init__(self, threshold=0.85):
        self.threshold = threshold
        self.faq_database = FAQ_DATABASE
        self.vectorizer = TfidfVectorizer()

        # Preparar todas las preguntas y variaciones para vectorización
        self.all_questions = []
        self.question_to_answer = {}

        for faq in self.faq_database:
            # Agregar pregunta principal
            self.all_questions.append(faq['question'])
            self.question_to_answer[faq['question']] = faq['answer']

            # Agregar variaciones
            for variation in faq['variations']:
                self.all_questions.append(variation)
                self.question_to_answer[variation] = faq['answer']

        # Vectorizar todas las preguntas
        if self.all_questions:
            self.question_vectors = self.vectorizer.fit_transform(self.all_questions)
        else:
            self.question_vectors = None

    def find_answer(self, user_question: str):
        """
        Busca una respuesta en la base de datos FAQ
        Retorna (answer, similarity_score) si encuentra una coincidencia
        Retorna (None, 0.0) si no hay coincidencia suficiente
        """
        if not self.question_vectors:
            return None, 0.0

        # Vectorizar la pregunta del usuario
        user_vector = self.vectorizer.transform([user_question])

        # Calcular similitud con todas las preguntas
        similarities = cosine_similarity(user_vector, self.question_vectors)[0]

        # Encontrar la mejor coincidencia
        max_similarity_idx = np.argmax(similarities)
        max_similarity = similarities[max_similarity_idx]

        # Si supera el umbral, retornar la respuesta
        if max_similarity >= self.threshold:
            matched_question = self.all_questions[max_similarity_idx]
            answer = self.question_to_answer[matched_question]
            return answer, float(max_similarity)

        return None, float(max_similarity)
