import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime

st.set_page_config(page_title="Inkwell", page_icon="✒️", layout="centered")

DATA_DIR = "data"
UPLOADS_DIR = "uploads"
POST_IMG_DIR = os.path.join(UPLOADS_DIR, "images")
PFP_DIR = os.path.join(UPLOADS_DIR, "profile_pics")

POSTS_FILE = os.path.join(DATA_DIR, "posts.csv")
COMMENTS_FILE = os.path.join(DATA_DIR, "comments.csv")
REACTIONS_FILE = os.path.join(DATA_DIR, "reactions.csv")
USERS_FILE = os.path.join(DATA_DIR, "users.csv")

def initialize_and_migrate():
    """Create directories, files, and migrate old data schemas if necessary."""
    for path in [DATA_DIR, POST_IMG_DIR, PFP_DIR]:
        os.makedirs(path, exist_ok=True)
    if not os.path.exists(POSTS_FILE):
        pd.DataFrame(columns=["post_id", "author_name", "title", "content", "post_image_path", "timestamp"]).to_csv(POSTS_FILE, index=False)
    if not os.path.exists(COMMENTS_FILE):
        pd.DataFrame(columns=["comment_id", "post_id", "author_name", "comment", "timestamp"]).to_csv(COMMENTS_FILE, index=False)
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=["author_name", "profile_pic_path"]).to_csv(USERS_FILE, index=False)
    if not os.path.exists(REACTIONS_FILE):
        pd.DataFrame(columns=["reaction_id", "post_id", "reaction_type"]).to_csv(REACTIONS_FILE, index=False)

    if os.path.getsize(POSTS_FILE) > 0:
        posts_df = pd.read_csv(POSTS_FILE)
        rename_map = {}
        if 'author' in posts_df.columns: rename_map['author'] = 'author_name'
        if 'image_path' in posts_df.columns: rename_map['image_path'] = 'post_image_path'
        if rename_map:
            posts_df.rename(columns=rename_map, inplace=True)
            posts_df.to_csv(POSTS_FILE, index=False)

#CSS & DATA HANDLING
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

@st.cache_data
def load_df(file_path):
    return pd.read_csv(file_path) if os.path.exists(file_path) else pd.DataFrame()

def save_df(df, file_path):
    df.to_csv(file_path, index=False)
    st.cache_data.clear()

def get_profile_pic(author_name, users_df):
    if not users_df.empty:
        user_row = users_df[users_df['author_name'] == author_name]
        if not user_row.empty:
            return user_row.iloc[0]['profile_pic_path']
    return None

#UI

def render_post_creation_form():
    with st.expander("✒️ Write a new post..."):
        with st.form("new_post_form", clear_on_submit=True, border=False):
            author = st.text_input("Your Name*", placeholder="e.g., Jane Doe")
            pfp_file = st.file_uploader("Upload a Profile Picture (first time only)", type=["png", "jpg", "jpeg"])
            title = st.text_input("Post Title*", placeholder="A catchy title for your story")
            content = st.text_area("Your Story*", height=250, placeholder="Share your thoughts...")
            post_image = st.file_uploader("Add an image to your post", type=["png", "jpg", "jpeg"])
            
            if st.form_submit_button("Publish Post"):
                if not all([author, title, content]):
                    st.error("Please fill out all required fields: Name, Title, and Story.")
                else:
                    users_df = load_df(USERS_FILE)
                    if pfp_file and not (author in users_df['author_name'].values):
                        ext = pfp_file.name.split('.')[-1]
                        pfp_path = os.path.join(PFP_DIR, f"{author.replace(' ', '_')}_{int(datetime.now().timestamp())}.{ext}")
                        with open(pfp_path, "wb") as f: f.write(pfp_file.getbuffer())
                        new_user = pd.DataFrame([{"author_name": author, "profile_pic_path": pfp_path}])
                        users_df = pd.concat([users_df, new_user]).drop_duplicates(subset=["author_name"], keep="last")
                        save_df(users_df, USERS_FILE)

                    post_image_path = None
                    if post_image:
                        ext = post_image.name.split('.')[-1]
                        post_image_path = os.path.join(POST_IMG_DIR, f"post_{int(datetime.now().timestamp())}.{ext}")
                        with open(post_image_path, "wb") as f: f.write(post_image.getbuffer())
                    
                    posts_df = load_df(POSTS_FILE)
                    post_id = hashlib.sha1(f"{author}{title}{datetime.now()}".encode()).hexdigest()[:10]
                    new_post = pd.DataFrame([{"post_id": post_id, "author_name": author, "title": title, "content": content, "post_image_path": post_image_path, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                    posts_df = pd.concat([posts_df, new_post], ignore_index=True)
                    save_df(posts_df, POSTS_FILE)
                    st.success("Your post has been published!")
                    st.rerun()

def render_post_card(post, users_df):
    st.markdown('<div class="post-card">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 5])
    with col1:
        pfp_path = get_profile_pic(post['author_name'], users_df)
        st.image(pfp_path if pfp_path and os.path.exists(pfp_path) else "https://static.thenounproject.com/png/5144310-200.png", use_container_width=True)
    with col2:
        st.markdown(f"### <a href='/?post_id={post['post_id']}' target='_self'>{post['title']}</a>", unsafe_allow_html=True)
        st.caption(f"By {post['author_name']} on {pd.to_datetime(post['timestamp']).strftime('%B %d, %Y')}")
    st.markdown("---")
    if pd.notna(post['post_image_path']) and os.path.exists(post['post_image_path']):
        st.image(post['post_image_path'])
    st.markdown(post['content'][:300] + ("..." if len(post['content']) > 300 else ""))
    st.markdown("</div>", unsafe_allow_html=True)

def render_single_post_page(post_id):
    posts_df, users_df = load_df(POSTS_FILE), load_df(USERS_FILE)
    post = posts_df[posts_df['post_id'] == post_id].iloc[0]

    st.markdown(f"<a href='/' target='_self'>← Back to all posts</a>", unsafe_allow_html=True)
    st.title(post['title'])

    pfp_path = get_profile_pic(post['author_name'], users_df)
    col1, col2 = st.columns([1, 6])
    with col1:
        st.image(pfp_path if pfp_path and os.path.exists(pfp_path) else "https://static.thenounproject.com/png/5144310-200.png", use_container_width=True)
    with col2:
        st.subheader(f"By {post['author_name']}")
        st.caption(f"Published on {pd.to_datetime(post['timestamp']).strftime('%B %d, %Y')}")
    st.markdown("---")
    if pd.notna(post['post_image_path']) and os.path.exists(post['post_image_path']):
        st.image(post['post_image_path'])
    st.markdown(post['content'])
    st.markdown("---")

    #REACTION SECTION
    reactions_df = load_df(REACTIONS_FILE)
    post_reactions = reactions_df[reactions_df['post_id'] == post_id]
    react_cols = st.columns(5)
    for i, emoji in enumerate(["❤️", "👍", "😂", "🤯", "🤔"]):
        count = post_reactions[post_reactions['reaction_type'] == emoji].shape[0]
        if react_cols[i].button(f"{emoji} {count}", key=f"react_{emoji}"):
            reaction_id = hashlib.sha1(f"{post_id}{emoji}{datetime.now()}".encode()).hexdigest()
            new_reaction = pd.DataFrame([{"reaction_id": reaction_id, "post_id": post_id, "reaction_type": emoji}])
            save_df(pd.concat([reactions_df, new_reaction]), REACTIONS_FILE)
            st.rerun()

    #COMMENT SECTION
    st.subheader("Comments")
    comments_df = load_df(COMMENTS_FILE)
    post_comments = comments_df[comments_df['post_id'] == post_id].sort_values("timestamp")
    for _, comment in post_comments.iterrows():
        pfp = get_profile_pic(comment['author_name'], users_df)
        c1, c2 = st.columns([1, 8])
        c1.image(pfp if pfp and os.path.exists(pfp) else "https://static.thenounproject.com/png/5144310-200.png", width=40)
        c2.markdown(f"**{comment['author_name']}**")
        c2.write(comment['comment'])
        c2.caption(pd.to_datetime(comment['timestamp']).strftime('%I:%M %p, %b %d'))

    with st.form(key="comment_form", clear_on_submit=True):
        author = st.text_input("Your Name", help="Use the same name you post with to show your profile picture!")
        comment_text = st.text_area("Add a comment...", height=100)
        if st.form_submit_button("Post Comment"):
            if author and comment_text:
                comment_id = hashlib.sha1(f"{post_id}{author}{comment_text}{datetime.now()}".encode()).hexdigest()
                new_comment = pd.DataFrame([{"comment_id": comment_id, "post_id": post_id, "author_name": author, "comment": comment_text, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
                save_df(pd.concat([comments_df, new_comment]), COMMENTS_FILE)
                st.rerun()

#MAIN APP ROUTER
def main():
    initialize_and_migrate()
    load_css("style.css")
    query_params = st.query_params
    if "post_id" in query_params:
        render_single_post_page(query_params.get("post_id"))
    else:
        st.title("✒️ The Inkwell")
        st.markdown("A place for ideas, stories, and connection.")
        render_post_creation_form()
        st.markdown("---")
        st.markdown("### 📰 Latest Posts")
        posts_df, users_df = load_df(POSTS_FILE), load_df(USERS_FILE)
        if posts_df.empty:
            st.info("No posts yet. Why not be the first?")
        else:
            for _, post in posts_df.sort_values(by="timestamp", ascending=False).iterrows():
                render_post_card(post, users_df)

if __name__ == "__main__":
    main()
