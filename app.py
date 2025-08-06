import streamlit as st
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load API key 
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Page title
st.set_page_config(page_title="ChatGenie", layout="centered")
st.title("🤖 ChatGenie")

# Chat history
if "history" not in st.session_state:
    st.session_state.history = [
        {
            "role": "system",
            "content": "You are a helpful assistant. If you cannot answer, suggest and include reputable web search results with their sources.",
        }
    ]

def call_llm_Groq(messages):
    """
    Queries the Groq API for a fast LLM response.
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192", 
        "messages": messages
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        st.error(f"LLM request failed: {e}")
        return "Sorry, I couldn't connect to the AI model right now."

def search_duckduckgo(query):
    """
     web search using DuckDuckGo.
    """
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
    try:
        response = requests.get(url).json()
        if response.get("AbstractText"):
            source = response.get("AbstractURL", "https://duckduckgo.com")
            return f"{response['AbstractText']}\n\n(Source: [{source}]({source}))"
        
        # Sometimes the answer is in a related topic
        related_topics = response.get("RelatedTopics", [])
        if related_topics and "Text" in related_topics[0]:
            source = related_topics[0].get("FirstURL", "https://duckduckgo.com")
            return f"{related_topics[0]['Text']}\n\n(Source: [{source}]({source}))"

        return None # Return None if no useful result is found
    except Exception:
        return "There was an error searching the web."

# Display chat history, skipping the initial system prompt
for message in st.session_state.history:
    if message["role"] == "system":
        continue

    sender = "You" if message["role"] == "user" else "ChatGenie"
    align = "right" if message["role"] == "user" else "left"

    st.markdown(
        f"""
        <div style='text-align: {align}; margin-top: 10px; margin-bottom: 5px;'>
            <strong>{sender}</strong><br>
            {message["content"].replace('\n', '<br>')}
            <div style='font-size: 0.75em; color: gray; margin-top: 4px;'>{message.get("timestamp", "")}</div>
        </div>
        <hr>
        """,
        unsafe_allow_html=True
    )


# Chat input form at the bottom
with st.form("chat_input_form", clear_on_submit=True):
    prompt = st.text_input("Your message:", placeholder="What's on your mind?")
    submitted = st.form_submit_button("Send")

if submitted and prompt:
    # Add user message to history
    st.session_state.history.append({
        "role": "user",
        "content": prompt,
        "timestamp": datetime.now().strftime("%H:%M")
    })

    # Prepare conversation for the API call 
    conversation = [{"role": m["role"], "content": m["content"]} for m in st.session_state.history]
    reply = call_llm_Groq(conversation)

    
    # phrases that indicate the LLM is uncertain
    uncertainty_phrases = ["i don't know", "i'm not sure", "i cannot answer", "i am unable to"]
    
    # if the LLM's response indicates uncertainty
    should_search_web = any(phrase in reply.lower() for phrase in uncertainty_phrases)

    if should_search_web:
        # If the LLM doesn't know, search the web
        web_result = search_duckduckgo(prompt)
        if web_result:
            # If the web search finds something, replace the LLM's answer
            reply = f"I wasn't sure, but here's what I found online:\n\n{web_result}"
        else:
            # If both fail, give a final message
            reply = "I couldn't find a reliable answer for that, either from my knowledge or from a web search."

    # Add assistant reply to history
    st.session_state.history.append({
        "role": "assistant",
        "content": reply,
        "timestamp": datetime.now().strftime("%H:%M")
    })

    st.rerun()