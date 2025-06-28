from flask import Flask, render_template, request
from youtube_transcript_api import YouTubeTranscriptApi
import re
from collections import Counter
from heapq import nlargest
import os
import time
import random

app = Flask(__name__)

def extract_video_id(url_or_id):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url_or_id)
    return match.group(1) if match else url_or_id.strip()

def get_transcript(video_id):
    try:
        # Add a randomized delay to avoid hitting YouTube's rate limits
        delay = random.uniform(3, 6)
        print(f"[INFO] Waiting {delay:.2f} seconds before requesting transcript...")
        time.sleep(delay)

        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript_data
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

def find_topic_segments(transcript_data, keywords):
    segments = {}
    for keyword in keywords:
        keyword = keyword.lower()
        times = [entry['start'] for entry in transcript_data if keyword in entry['text'].lower()]
        if times:
            start_time = min(times)
            end_time = max(times)
            segments[keyword] = (format_time(start_time), format_time(end_time))
        else:
            segments[keyword] = ("Not Found", "Not Found")
    return segments

def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02}:{seconds:02}"

def get_keywords(text, num_keywords=5):
    stopwords = set([
        'the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'on', 'with', 'as',
        'that', 'this', 'at', 'by', 'an', 'be', 'or', 'from', 'are', 'was',
        'it', 'not', 'have', 'has', 'but', 'if', 'you', 'we'
    ])
    words = re.findall(r'\w+', text.lower())
    filtered = [w for w in words if w not in stopwords and len(w) > 2]
    most_common = Counter(filtered).most_common(num_keywords)
    return [word for word, freq in most_common]

@app.route('/', methods=['GET', 'POST'])
def index():
    summary = ""
    error = ""
    topics = {}

    if request.method == 'POST':
        video_url = request.form.get('video_url')
        topic_input = request.form.get('topics', '')

        video_id = extract_video_id(video_url)
        transcript_data = get_transcript(video_id)

        if isinstance(transcript_data, str) and transcript_data.startswith("[Error]"):
            error = transcript_data
        else:
            full_text = " ".join([entry["text"] for entry in transcript_data])
            summary = summarize_text(full_text)

            # Use provided topics or auto-generate
            if topic_input.strip():
                topic_list = [t.strip() for t in topic_input.split(',') if t.strip()]
            else:
                topic_list = get_keywords(full_text)

            topics = find_topic_segments(transcript_data, topic_list)

    return render_template("index.html", summary=summary, error=error, topics=topics)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
