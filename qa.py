import streamlit as st
import os
import requests

def get_answer(question):
    try:
        url = os.environ.get("BACKEND_URL") + "qa"
        # send post request
        response = requests.post(url, json={"query": question})
        response.raise_for_status()
        return response.json()["answer"]
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")


def qa():
    with st.expander("Question Answering"):
        question = st.text_input("Enter your question:")
        if st.button("Get Answer"):
            if question:
                answer = get_answer(question)
                st.write("**Answer:**\n", answer)
            else:
                st.warning("Please enter a question.")