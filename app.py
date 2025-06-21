from flask import Flask, render_template, request
from youtube_transcript_api import YouTubeTranscriptApi
import re
from collections import Counter
from heapq import nlargest
import os

app = Flask(__name__)

def extract_video_id(url_or_id):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url_or_id)
    return match.group(1) if match else url_or_id.strip()

def get_transcript(video_id):
    try:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([item["text"] for item in transcript_data])
        return full_text
    except Exception as e:
        return f"[Error] Could not retrieve transcript: {e}"

def clean_text(text):
    return re.sub(r'[^\w\s]', '', text).lower()

def split_sentences(text):
    return re.split(r'(?<=[.!?]) +', text)

def summarize_text(text, top_n=3):
    if not text:
        return "No text to summarize."

    cleaned = clean_text(text)
    words = cleaned.split()
    
    stopwords = set([
        'the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'on', 'with', 'as',
        'that', 'this', 'at', 'by', 'an', 'be', 'or', 'from', 'are', 'was',
        'it', 'not', 'have', 'has', 'but', 'if', 'you', 'we'
    ])
    
    word_freq = Counter(word for word in words if word not in stopwords)

    sentences = split_sentences(text)
    sentence_scores = {}

    for sentence in sentences:
        sentence_clean = clean_text(sentence)
        sentence_words = sentence_clean.split()
        for word in sentence_words:
            if word in word_freq:
                sentence_scores[sentence] = sentence_scores.get(sentence, 0) + word_freq[word]

    best_sentences = nlargest(top_n, sentence_scores, key=sentence_scores.get)
    return "\n".join(best_sentences)

@app.route('/', methods=['GET', 'POST'])
def index():
    summary = ""
    error = ""
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        video_id = extract_video_id(video_url)
        transcript = get_transcript(video_id)
        if transcript.startswith("[Error]"):
            error = transcript
        else:
            summary = summarize_text(transcript)

    return render_template("index.html", summary=summary, error=error)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
