import logging
import os
import openai


prompt = """
    Here is a conversation between a customer and an operator. The customer is interested in buying an online IT course. The operator is trying to sell the course to the customer. The conversation is in Uzbek language. According to the conversation, answer the following questions and return in json format with the following:
    Response format: {
        "is_conversation_over": true or false,
        "sentiment_analysis_of_conversation": "positive" or "negative" or "neutral",
        "sentiment_analysis_of_operator": "positive" or "negative" or "neutral",
        "sentiment_analysis_of_customer": "positive" or "negative" or "neutral",
        "is_customer_satisfied": true or false,
        "is_customer_agreed_to_buy": true or false,
        "is_customer_interested_to_product": true or false,
        "which_course_customer_interested": "[
            Kiberxavfsizlik: Pentesting,
            Computer Vision,
            Data Science va Sun'iy Intellekt,
            Sunʼiy intellekt - NLP (nutq bilan ishlash),
            No-Code: Kod yozmasdan sayt tuzish,
            QA - testing va avtomatlashtirish,
            Project Management,
            Android & Kotlin dasturlash,
            PHP & Yii dasturlash,
            Full Stack Java,
            Node.js praktikum,
            Robototexnika,
            iOS & Swift dasturlash,
            Full Stack Python,
            .NET dasturlash,
            UX/UI Design,
            Front-End dasturlash,
            English for IT
        ]" or None use correct course name if customer interested to product it might be multiple courses,
        "summary": "The summary of the conversation in Uzbek language with punctuation corrected and aroun 20-30 words. Summarize as checker's discretion."
        
    }
"""


def request_to_gpt(text, prompt):

    logging.warning(f"Text in function request_to_gpt: {text}")
    """
    Corrects punctuation in Uzbek language text.

    Parameters:
    - text (str): The input text in Uzbek that needs punctuation correction.

    Returns:
    - str: The corrected text.
    """

    deployment_name = os.getenv("DEPLOYMENT_NAME", "gpt4")

    try:
        # response = openai.ChatCompletion.create(
        #     deployment_id=deployment_name,
        #     messages=[
        #         {
        #             "role": "system",
        #             "content": prompt,
        #         },
        #         {"role": "user", "content": text},
        #     ],
        # )
        #
        # corrected_text = (
        #     response.get("choices", [{}])[0].get("message", {}).get("content", "")
        # )
        corrected_text = """json{
             "is_conversation_over": true,
             "sentiment_analysis_of_conversation": "neutral",
             "sentiment_analysis_of_operator": "neutral",
             "sentiment_analysis_of_customer": "neutral",
             "is_customer_satisfied": false,
             "is_customer_agreed_to_buy": false,
             "is_customer_interested_to_product": false,
             "which_course_customer_interested": null,
             "summary": "Mijoz va operator o'rtasida kurslar haqida qisqa muloqot bo'lib o'tdi. Aniq bir kurs haqida gapirilmadi, mijoz qayta qo'ng'iroq qilishni so'radi."
             }"""
        return corrected_text

    except Exception as e:
        print(f"An error occurred: {e}")
        return text
