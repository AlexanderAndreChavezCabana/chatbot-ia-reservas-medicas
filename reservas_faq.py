"""
Sistema FAQ para Reservas Médicas - Preguntas frecuentes del servicio.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

FAQ_DATABASE = [
    # === HORARIOS Y ATENCIÓN ===
    {
        "question": "¿Cuál es el horario de atención?",
        "variations": [
            "¿a qué hora atienden?",
            "horario de la clínica",
            "¿cuándo abren?",
            "¿cuándo cierran?",
            "horarios disponibles",
            "¿qué días atienden?",
            "horario de consultas"
        ],
        "answer": "🕐 Nuestro horario de atención es:\n• Lunes a Viernes: 8:00 AM - 8:00 PM\n• Sábados: 8:00 AM - 2:00 PM\n• Domingos y feriados: Cerrado\n\nLas citas de urgencia están disponibles 24/7."
    },
    {
        "question": "¿Atienden los fines de semana?",
        "variations": [
            "¿abren sábados?",
            "¿atienden domingos?",
            "citas fin de semana",
            "sábado y domingo"
        ],
        "answer": "📅 Sí, atendemos los sábados de 8:00 AM a 2:00 PM. Los domingos y feriados permanecemos cerrados, excepto para urgencias."
    },
    
    # === ESPECIALIDADES ===
    {
        "question": "¿Qué especialidades tienen disponibles?",
        "variations": [
            "¿qué doctores tienen?",
            "especialidades médicas",
            "¿tienen pediatra?",
            "¿tienen cardiólogo?",
            "lista de especialidades",
            "¿qué médicos atienden?",
            "especialistas disponibles"
        ],
        "answer": "👨‍⚕️ Contamos con las siguientes especialidades:\n• Medicina General\n• Pediatría\n• Cardiología\n• Dermatología\n• Ginecología\n• Traumatología\n• Oftalmología\n• Neurología\n• Psicología\n• Nutrición\n\n¿Te gustaría agendar una cita? Escribe 'quiero una cita'."
    },
    {
        "question": "¿Tienen pediatra?",
        "variations": [
            "cita para niño",
            "doctor de niños",
            "médico infantil",
            "consulta pediátrica"
        ],
        "answer": "👶 Sí, contamos con servicio de Pediatría. Atendemos niños desde recién nacidos hasta 18 años. ¿Deseas agendar una cita con el pediatra?"
    },
    
    # === MÉTODOS DE PAGO ===
    {
        "question": "¿Cuáles son los métodos de pago?",
        "variations": [
            "¿cómo puedo pagar?",
            "formas de pago",
            "¿aceptan tarjeta?",
            "¿puedo pagar en efectivo?",
            "métodos de pago disponibles",
            "¿aceptan transferencia?",
            "pago con tarjeta"
        ],
        "answer": "💳 Aceptamos los siguientes métodos de pago:\n• Efectivo\n• Tarjetas de crédito/débito (Visa, Mastercard)\n• Transferencia bancaria\n• Yape / Plin\n• Seguros médicos (previa verificación)\n\nEl pago se realiza al momento de la consulta."
    },
    {
        "question": "¿Aceptan seguros médicos?",
        "variations": [
            "¿trabajan con seguros?",
            "seguro de salud",
            "EPS",
            "cobertura de seguro",
            "¿aceptan mi seguro?"
        ],
        "answer": "🏥 Sí, trabajamos con los principales seguros médicos:\n• Rímac\n• Pacífico\n• La Positiva\n• Mapfre\n• Sanitas\n\nPor favor, trae tu carnet de seguro vigente a la cita para verificar la cobertura."
    },
    
    # === PRECIOS Y COSTOS ===
    {
        "question": "¿Cuánto cuesta una consulta?",
        "variations": [
            "precio de consulta",
            "costo de la cita",
            "¿cuánto cobran?",
            "tarifas",
            "precio de atención"
        ],
        "answer": "💰 Nuestras tarifas son:\n• Consulta General: S/. 50\n• Consulta Especialista: S/. 80 - S/. 120\n• Consulta de Urgencia: S/. 100\n• Control/Seguimiento: S/. 40\n\nLos precios pueden variar según el especialista. ¿Deseas agendar una cita?"
    },
    
    # === CITAS Y RESERVAS ===
    {
        "question": "¿Cómo puedo agendar una cita?",
        "variations": [
            "quiero una cita",
            "reservar cita",
            "sacar turno",
            "agendar consulta",
            "necesito una cita",
            "cómo reservo",
            "hacer una reserva"
        ],
        "answer": "📋 Para agendar una cita, simplemente escribe 'quiero una cita' y te guiaré paso a paso:\n1. Elegir especialidad\n2. Seleccionar fecha\n3. Elegir horario disponible\n4. Confirmar reserva\n\n¡Es muy fácil! ¿Empezamos?"
    },
    {
        "question": "¿Cómo cancelo una cita?",
        "variations": [
            "cancelar cita",
            "anular reserva",
            "no puedo asistir",
            "cambiar mi cita",
            "reagendar cita"
        ],
        "answer": "❌ Para cancelar o reagendar tu cita:\n• Escribe 'cancelar' durante la conversación\n• Llama al (01) 555-1234\n• Cancela con al menos 24 horas de anticipación para evitar cargos\n\n¿Necesitas cancelar una cita existente?"
    },
    {
        "question": "¿Con cuánta anticipación debo reservar?",
        "variations": [
            "anticipación para cita",
            "¿puedo reservar para hoy?",
            "cita de emergencia",
            "cita urgente"
        ],
        "answer": "⏰ Recomendamos reservar con al menos 24-48 horas de anticipación. Sin embargo:\n• Citas del mismo día: Sujetas a disponibilidad\n• Urgencias: Atención inmediata disponible\n• Especialistas: Reservar con 3-5 días de anticipación\n\n¿Te gustaría verificar disponibilidad?"
    },
    
    # === UBICACIÓN Y CONTACTO ===
    {
        "question": "¿Dónde están ubicados?",
        "variations": [
            "dirección de la clínica",
            "¿dónde queda?",
            "ubicación",
            "cómo llego",
            "dirección"
        ],
        "answer": "📍 Nuestra ubicación:\nAv. Salud 123, Centro Médico Plaza\nPiso 3, Consultorios 301-310\n\n🚗 Contamos con estacionamiento gratuito\n🚌 A 2 cuadras de la estación del metro\n\n¿Necesitas indicaciones adicionales?"
    },
    {
        "question": "¿Cuál es el teléfono de contacto?",
        "variations": [
            "número de teléfono",
            "teléfono de la clínica",
            "cómo los contacto",
            "whatsapp",
            "contacto"
        ],
        "answer": "📞 Puedes contactarnos por:\n• Teléfono: (01) 555-1234\n• WhatsApp: +51 999-888-777\n• Email: citas@clinicasalud.com\n\nHorario de atención telefónica: Lunes a Sábado 7:00 AM - 9:00 PM"
    },
    
    # === DOCUMENTOS Y REQUISITOS ===
    {
        "question": "¿Qué documentos necesito llevar?",
        "variations": [
            "documentos para la cita",
            "qué debo llevar",
            "requisitos para la consulta",
            "necesito llevar algo"
        ],
        "answer": "📄 Para tu cita, por favor trae:\n• DNI o documento de identidad\n• Carnet de seguro (si aplica)\n• Resultados de exámenes previos (si los tienes)\n• Lista de medicamentos actuales\n• Historial médico relevante\n\n¿Tienes alguna otra consulta?"
    },
    
    # === RESULTADOS Y SEGUIMIENTO ===
    {
        "question": "¿Cómo recojo mis resultados?",
        "variations": [
            "resultados de exámenes",
            "recoger análisis",
            "resultados de laboratorio",
            "cuándo están mis resultados"
        ],
        "answer": "📊 Sobre tus resultados:\n• Análisis de sangre: 24-48 horas\n• Radiografías: Mismo día\n• Estudios especiales: 3-5 días\n\nPuedes recogerlos en recepción o recibirlos por email. ¿Necesitas más información?"
    },
    
    # === SALUDOS Y DESPEDIDAS ===
    {
        "question": "Hola",
        "variations": [
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "hey",
            "holi",
            "qué tal"
        ],
        "answer": "¡Hola! 👋 Bienvenido al sistema de reservas médicas. Puedo ayudarte a:\n• 📅 Agendar una cita\n• ❓ Responder preguntas sobre horarios, precios y especialidades\n• 📋 Consultar tus citas\n\n¿En qué puedo ayudarte hoy?"
    },
    {
        "question": "Gracias",
        "variations": [
            "muchas gracias",
            "te agradezco",
            "thanks",
            "gracias por la ayuda"
        ],
        "answer": "¡De nada! 😊 Ha sido un placer ayudarte. Si necesitas algo más, no dudes en escribirme. ¡Que tengas un excelente día!"
    },
    {
        "question": "Adiós",
        "variations": [
            "hasta luego",
            "chao",
            "bye",
            "nos vemos",
            "me voy"
        ],
        "answer": "¡Hasta pronto! 👋 Recuerda que estoy aquí 24/7 para ayudarte con tus reservas médicas. ¡Cuídate mucho!"
    }
]


class FAQMatcher:
    def __init__(self, threshold=0.65):
        self.threshold = threshold
        self.faq_database = FAQ_DATABASE
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2))

        self.all_questions = []
        self.question_to_answer = {}

        for faq in self.faq_database:
            self.all_questions.append(faq['question'].lower())
            self.question_to_answer[faq['question'].lower()] = faq['answer']
            for variation in faq.get('variations', []):
                self.all_questions.append(variation.lower())
                self.question_to_answer[variation.lower()] = faq['answer']

        if self.all_questions:
            self.question_vectors = self.vectorizer.fit_transform(self.all_questions)
        else:
            self.question_vectors = None

    def find_answer(self, user_question: str):
        if self.question_vectors is None:
            return None, 0.0
        user_vector = self.vectorizer.transform([user_question.lower()])
        similarities = cosine_similarity(user_vector, self.question_vectors)[0]
        max_idx = np.argmax(similarities)
        max_sim = similarities[max_idx]
        if max_sim >= self.threshold:
            q = self.all_questions[max_idx]
            return self.question_to_answer[q], float(max_sim)
        return None, float(max_sim)
