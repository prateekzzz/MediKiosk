import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from database import get_all_consultations

def get_consultation_dataframe():
    """Convert consultations to DataFrame for analysis"""
    consultations = get_all_consultations(500)
    
    if not consultations:
        return pd.DataFrame()
    
    data = []
    for c in consultations:
        data.append({
            'token': c.get('token_number'),
            'name': c.get('name', 'Unknown'),
            'age': c.get('age'),
            'gender': c.get('gender'),
            'complaint': c.get('chief_complaint'),
            'duration': c.get('duration'),
            'severity': c.get('severity'),
            'risk': c.get('risk_assessment', 'Standard'),
            'created_at': c.get('created_at'),
            'language': c.get('language', 'English')
        })
    
    df = pd.DataFrame(data)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['date'] = df['created_at'].dt.date
    df['hour'] = df['created_at'].dt.hour
    
    return df

def plot_consultations_by_hour(df):
    """Plot consultations by hour"""
    if df.empty:
        return None
    
    hourly = df.groupby('hour').size().reset_index(name='count')
    
    fig = px.bar(
        hourly, x='hour', y='count',
        title='Consultations by Hour',
        labels={'hour': 'Hour of Day', 'count': 'Number of Patients'},
        color='count',
        color_continuous_scale='Viridis'
    )
    fig.update_layout(showlegend=False, height=350)
    return fig

def plot_top_complaints(df):
    """Plot top chief complaints"""
    if df.empty:
        return None
    
    complaints = df['complaint'].value_counts().head(10).reset_index()
    complaints.columns = ['Complaint', 'Count']
    
    fig = px.bar(
        complaints, y='Complaint', x='Count',
        orientation='h',
        title='Top Chief Complaints',
        color='Count',
        color_continuous_scale='Blues'
    )
    fig.update_layout(showlegend=False, height=400)
    return fig

def plot_risk_distribution(df):
    """Plot risk level distribution"""
    if df.empty:
        return None
    
    df['risk_level'] = df['risk'].apply(
        lambda x: 'Critical' if 'CRITICAL' in str(x).upper() else
                  'High' if 'HIGH' in str(x).upper() else
                  'Moderate' if 'MODERATE' in str(x).upper() else 'Standard'
    )
    
    risk_counts = df['risk_level'].value_counts().reset_index()
    risk_counts.columns = ['Risk Level', 'Count']
    
    colors = {
        'Critical': '#f44336',
        'High': '#ff9800',
        'Moderate': '#ffc107',
        'Standard': '#4caf50'
    }
    
    fig = px.pie(
        risk_counts, values='Count', names='Risk Level',
        title='Patient Risk Distribution',
        color='Risk Level',
        color_discrete_map=colors
    )
    fig.update_layout(height=350)
    return fig

def plot_age_distribution(df):
    """Plot age distribution"""
    if df.empty or 'age' not in df.columns:
        return None
    
    fig = px.histogram(
        df, x='age', nbins=20,
        title='Patient Age Distribution',
        labels={'age': 'Age', 'count': 'Number of Patients'},
        color_discrete_sequence=['#667eea']
    )
    fig.update_layout(showlegend=False, height=350)
    return fig

def plot_gender_distribution(df):
    """Plot gender distribution"""
    if df.empty:
        return None
    
    gender_counts = df['gender'].value_counts().reset_index()
    gender_counts.columns = ['Gender', 'Count']
    
    fig = px.pie(
        gender_counts, values='Count', names='Gender',
        title='Gender Distribution',
        color_discrete_sequence=['#667eea', '#f093fb', '#feca57']
    )
    fig.update_layout(height=350)
    return fig

def plot_language_distribution(df):
    """Plot language distribution"""
    if df.empty:
        return None
    
    lang_counts = df['language'].value_counts().reset_index()
    lang_counts.columns = ['Language', 'Count']
    
    fig = px.bar(
        lang_counts, x='Language', y='Count',
        title='Language Distribution',
        color='Count',
        color_continuous_scale='Purples'
    )
    fig.update_layout(showlegend=False, height=350)
    return fig

def plot_time_series(df):
    """Plot consultations over time"""
    if df.empty:
        return None
    
    daily = df.groupby('date').size().reset_index(name='count')
    
    fig = px.line(
        daily, x='date', y='count',
        title='Consultations Over Time',
        labels={'date': 'Date', 'count': 'Patients'},
        markers=True
    )
    fig.update_traces(line_color='#667eea', line_width=3, marker_size=10)
    fig.update_layout(height=350)
    return fig