import streamlit as st
import pandas as pd
import plotly.express as px
import os

with st.sidebar:
    st.header("Options")
    if st.button("Delete All Feedback Data"):
        if os.path.exists("feedback_logs.jsonl"):
            os.remove("feedback_logs.jsonl")
            st.success("Data cleared successfully!")
            st.rerun()
st.set_page_config(page_title="Feedback Analytics", page_icon="📊", layout="wide")

st.title("Customer Sentiment & Feedback Dashboard")
st.markdown("Dashboard to analyze customer satisfaction and evaluate RAG performance.")

try:
    df = pd.read_json("feedback_logs.jsonl", lines=True)
except FileNotFoundError:
    st.warning("No feedback recorded yet. (File not found)")
    st.stop()
except ValueError:
    st.warning("The file is empty or formatted incorrectly.")
    st.stop()

df = df.drop_duplicates(subset=['question', 'answer'], keep='last')
total_feedback = len(df)
positive_feedback = len(df[df['sentiment'] == 'Positive'])
negative_feedback = len(df[df['sentiment'] == 'Negative'])

if total_feedback > 0:
    satisfaction_rate = (positive_feedback / total_feedback) * 100
else:
    satisfaction_rate = 0.0


col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Feedback", total_feedback)
col2.metric("Positive", positive_feedback)
col3.metric("Negative", negative_feedback)
col4.metric("Satisfaction Rate", f"{satisfaction_rate:.1f}%")

st.divider()
st.subheader("Satisfaction Analytics")

if total_feedback > 0:
    chart_col1, chart_col2 = st.columns(2)
    sentiment_counts = df['sentiment'].value_counts().reset_index()
    sentiment_counts.columns = ['Sentiment', 'Count']
    with chart_col1:
        fig_pie = px.pie(
            sentiment_counts,
            values='Count',
            names='Sentiment',
            title='Overall Satisfaction Ratio',
            color='Sentiment',
            color_discrete_map={'Positive': '#28a745', 'Negative': '#dc3545'}
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col2:
        fig_bar = px.bar(
            sentiment_counts,
            x='Sentiment',
            y='Count',
            title='Feedback Count by Sentiment',
            color='Sentiment',
            color_discrete_map={'Positive': '#28a745', 'Negative': '#dc3545'},
            text='Count'
        )
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("Not enough data to display charts yet.")
st.divider()
st.subheader("Negative Feedback (Needs Review)")
negative_df = df[df['sentiment'] == 'Negative']
if not negative_df.empty:
    st.dataframe(
        negative_df[['question', 'answer']],
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("Great news! No negative feedback yet.")
st.divider()
with st.expander("View Full Feedback Log"):
    st.dataframe(df, use_container_width=True)