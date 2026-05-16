import streamlit as st
from recommender import MovieRecommender
from chatbot import MovieChatbot
import time

st.set_page_config(
    page_title="YourNextBinge",
    page_icon="🍿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def mins_to_hours(mins):
    try:
        m = int(float(mins))
        h, rem = divmod(m, 60)
        if h and rem:
            return f"{h}h {rem}m"
        if h:
            return f"{h}h"
        return f"{rem}m"
    except Exception:
        return str(mins)

def energy_badge_class(energy):
    return {'High': 'badge-energy-high', 'Medium': 'badge-energy-medium', 'Low': 'badge-energy-low'}.get(str(energy), '')

def init_state():
    defaults = {
        'mood_text': '',
        'max_duration': 120,
        'target_energy': 'Any',
        'last_recs': None,
        'last_mood': None,
        'show_results': False,
        'skipped_ids': set(),
        'feedback_map': {},
        'chat_skipped_ids': set(),
        'refresh_count': 0,
        'seen_movie_ids': set(),
        'chat_history': [],
        'chat_feedback_map': {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

@st.cache_resource
def get_finder_recommender():
    return MovieRecommender()

@st.cache_resource
def get_chat_recommender():
    return MovieRecommender()

@st.cache_resource
def get_chatbot():
    return MovieChatbot()

recommender = get_finder_recommender()
chat_recommender = get_chat_recommender()
chatbot = get_chatbot()

def render_movie_card(
    row,
    explanation,
    key_suffix,
    include_feedback=True,
    feedback_map_key="feedback_map",
    feedback_recommender=None,
    skipped_ids_key="skipped_ids"
):
    movie_id = row['movie_id']
    feedback_map = st.session_state.get(feedback_map_key, {})
    feedback = feedback_map.get(movie_id)

    st.markdown(f"### {row['title']}")
    st.caption(f"🕐 {mins_to_hours(row['duration'])} • ⚡ {row['energy_level']} • 🎭 {row['genres']}")
    st.write(row['overview'])
    st.info(f"🧠 Why this? {explanation.replace(chr(10), ' ')}")

    if include_feedback:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👍", key=f"like_{movie_id}_{key_suffix}"):
                target_recommender = feedback_recommender or recommender
                target_recommender.update_feedback(movie_id, 'Like')
                st.session_state[feedback_map_key][movie_id] = 'liked'
                st.rerun()
        with c2:
            if st.button("👎", key=f"dislike_{movie_id}_{key_suffix}"):
                target_recommender = feedback_recommender or recommender
                target_recommender.update_feedback(movie_id, 'Dislike')
                st.session_state[feedback_map_key][movie_id] = 'disliked'
                st.rerun()
        with c3:
            if st.button("⏭ Skip", key=f"skip_{movie_id}_{key_suffix}"):
                target_recommender = feedback_recommender or recommender
                target_recommender.update_feedback(movie_id, 'Not Interested')
                st.session_state[skipped_ids_key].add(movie_id)
                st.rerun()

st.title("🍿 YourNextBinge")
tab1, tab2 = st.tabs(["🎬 Find My Movie", "💬 Chat & Discover"])

with tab1:
    mood = st.text_input("Your Mood", value=st.session_state.mood_text)
    max_duration = st.slider("Max Duration", 60, 240, st.session_state.max_duration, 10)
    target_energy = st.selectbox("Energy", ["Any", "Low", "Medium", "High"], index=["Any", "Low", "Medium", "High"].index(st.session_state.target_energy))
    col1, col2 = st.columns(2)
    with col1:
        find_btn = st.button("🚀 Find")
    with col2:
        clear_btn = st.button("🗑 Clear")

    if clear_btn:
        st.session_state.mood_text = ''
        st.session_state.max_duration = 120
        st.session_state.target_energy = 'Any'
        st.session_state.last_recs = None
        st.session_state.last_mood = None
        st.session_state.show_results = False
        st.session_state.skipped_ids = set()
        st.session_state.feedback_map = {}
        st.session_state.refresh_count = 0
        st.session_state.seen_movie_ids = set()
        st.rerun()

    if find_btn:
        st.session_state.mood_text = mood
        st.session_state.max_duration = max_duration
        st.session_state.target_energy = target_energy
        st.session_state.skipped_ids = set()
        st.session_state.feedback_map = {}
        st.session_state.refresh_count = 0
        st.session_state.seen_movie_ids = set()

        with st.spinner("Finding your perfect binge... 🍿"):
            time.sleep(0.4)
            recs, detected_mood = recommender.recommend_movies(
                user_text=mood,
                max_duration=max_duration,
                target_energy=target_energy
            )
            if len(recs) == 0:
                recs, detected_mood = recommender.recommend_movies(top_n=5)

        st.session_state.seen_movie_ids = set(recs['movie_id'].tolist())
        st.session_state.last_recs = recs
        st.session_state.last_mood = detected_mood
        st.session_state.show_results = True

    if st.session_state.show_results and st.session_state.last_recs is not None:
        recs = st.session_state.last_recs
        detected_mood = st.session_state.last_mood
        visible_recs = recs[~recs['movie_id'].isin(st.session_state.skipped_ids)]

        st.subheader("✨ Your Top Picks")
        for idx, (_, row) in enumerate(visible_recs.iterrows()):
            explanation = recommender.explain_recommendation(
                row, detected_mood, st.session_state.max_duration, st.session_state.target_energy
            )
            render_movie_card(
                row, explanation,
                key_suffix=f"t1_{st.session_state.refresh_count}_{idx}",
                include_feedback=True,
                feedback_map_key="feedback_map",
                feedback_recommender=recommender,
                skipped_ids_key="skipped_ids"
            )

        if st.button("🔄 Show Me Different Movies", key=f"refresh_{st.session_state.refresh_count}"):
            new_recs, new_mood = recommender.recommend_movies(
                user_text=st.session_state.mood_text,
                max_duration=st.session_state.max_duration,
                target_energy=st.session_state.target_energy,
                top_n=5,
                exclude_movie_ids=st.session_state.seen_movie_ids
            )

            if new_recs is not None and len(new_recs) > 0:
                st.session_state.seen_movie_ids.update(new_recs['movie_id'].tolist())

            st.session_state.last_recs = new_recs
            st.session_state.last_mood = new_mood
            st.session_state.skipped_ids = set()
            st.session_state.feedback_map = {}
            st.session_state.refresh_count += 1
            st.rerun()

with tab2:
    st.subheader("💬 Chat with YourNextBinge")
    if st.button("🗑 Clear Chat"):
        st.session_state.chat_history = []
        st.session_state.chat_feedback_map = {}
        st.session_state.chat_skipped_ids = set()
        st.rerun()

    for i, chat in enumerate(st.session_state.chat_history):
        if chat["role"] == "user":
            st.markdown(f"**You:** {chat['text']}")
        else:
            st.markdown(f"**Bot:** {chat['text']}")
            if chat.get("df") is not None:
                for idx, (_, row) in enumerate(chat["df"].iterrows()):
                    explanation = chat_recommender.explain_recommendation(
                        row,
                        chat.get('mood', 'Neutral'),
                        chat.get('duration', 120),
                        chat.get('energy', 'Any')
                    )
                    render_movie_card(
                        row, explanation,
                        key_suffix=f"chat_{i}_{idx}",
                        include_feedback=True,
                        feedback_map_key="chat_feedback_map",
                        feedback_recommender=chat_recommender,
                        skipped_ids_key="chat_skipped_ids"
                    )

    chat_query = st.text_input("Type your message", key="chat_text_input")
    if st.button("Send ✉️") and chat_query:
        st.session_state.chat_history.append({"role": "user", "text": chat_query})
        response_text, recommendations, mood, detected_duration, detected_energy = chatbot.get_response(chat_recommender, chat_query)
        st.session_state.chat_history.append({
            "role": "bot",
            "text": response_text,
            "df": recommendations,
            "mood": mood,
            "duration": detected_duration,
            "energy": detected_energy
        })
        st.rerun()