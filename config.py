"""
Configuration settings for the Clio KPI Dashboard
"""

import os
from datetime import datetime
from pathlib import Path

import streamlit as st

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading .env file
    pass

# Database configuration
DB_PATH = os.getenv('CLIO_SQLITE', '/home/sysadmin01/firm_analytics_dashboard/data/analytics/clio-analytics.db')

# Clio Brand Colors (from brand guidelines)
CLIO_BRAND_COLORS = {
    # Primary Brand Colors
    "sand": "#EEEDEA",
    "ocean_blue": "#0070E0", 
    "mountain_blue": "#04304C",
    "coral": "#D74417",
    "emerald": "#018b76",
    "white": "#FFFFFF",
    
    # Extended Tints & Secondary Colors (from brand.clio.com)
    "amber": "#F4A540",          # Medium priority, 30-90 day urgency
    "coral_light": "#E6674A",    # Lighter coral for warnings
    "coral_dark": "#B8320F",     # Darker coral for critical items
    "emerald_light": "#33A691",  # Lighter emerald for success variants
    "emerald_dark": "#016B5C",   # Darker emerald for completed items
    "ocean_light": "#3D8FE8",    # Lighter blue for secondary actions
    "ocean_dark": "#005BB8",     # Darker blue for primary emphasis
    "amber_light": "#F7BE73",    # Lighter amber for soft warnings
    "amber_dark": "#E6941A",     # Darker amber for medium alerts
}


# Page configuration
def configure_page():
    """Configure Streamlit page settings with Clio branding"""
    st.set_page_config(
        page_title="Clio KPI Dashboard",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Load custom CSS
    css_file = Path(__file__).parent.parent / "styles" / "theme.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Additional inline CSS for immediate color application
    st.markdown(
        """
    <style>
    /* Force correct colors immediately */
    .stApp {
        background-color: #EEEDEA !important;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #04304C !important;
    }
    
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stMain"] {
        background-color: #EEEDEA !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


# Data directory configuration
def get_data_directory():
    """Get the data directory path"""
    return Path(__file__).parent.parent.parent / "reports" / "csv"


def find_latest_csv_files():
    """Automatically find the most recent CSV files in the data directory"""
    data_dir = get_data_directory()

    if not data_dir.exists():
        return DATA_FILES  # Return defaults if directory doesn't exist

    # Find all CSV files
    csv_files = list(data_dir.glob("*.csv"))

    if not csv_files:
        return DATA_FILES  # Return defaults if no CSV files found

    # Group files by type (tasks/matters)
    tasks_files = [f for f in csv_files if "task" in f.name.lower()]
    matters_files = [f for f in csv_files if "matter" in f.name.lower()]

    # Sort by modification time (most recent first)
    tasks_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    matters_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # Build result dictionary
    result = {}

    if tasks_files:
        result["tasks"] = tasks_files[0].name
    else:
        result["tasks"] = DATA_FILES["tasks"]  # Default fallback

    if matters_files:
        result["matters"] = matters_files[0].name
    else:
        result["matters"] = DATA_FILES["matters"]  # Default fallback

    return result


def show_available_csv_files():
    """Display available CSV files in the data directory"""
    data_dir = get_data_directory()

    if not data_dir.exists():
        return []

    csv_files = list(data_dir.glob("*.csv"))

    if not csv_files:
        return []

    # Sort by modification time (most recent first)
    csv_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    file_info = []
    for file_path in csv_files:
        stat = file_path.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        size_mb = stat.st_size / (1024 * 1024)

        file_info.append(
            {
                "name": file_path.name,
                "modified": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                "size_mb": round(size_mb, 2),
                "type": (
                    "Tasks"
                    if "task" in file_path.name.lower()
                    else "Matters" if "matter" in file_path.name.lower() else "Other"
                ),
            }
        )

    return file_info


# Chart color schemes using Clio brand colors
CHART_COLORS = {
    "status": {
        "pending": CLIO_BRAND_COLORS["coral"],      # Red for attention needed
        "completed": CLIO_BRAND_COLORS["emerald"],  # Green for success
        "in_progress": CLIO_BRAND_COLORS["ocean_blue"], # Blue for active work  
        "in_review": CLIO_BRAND_COLORS["ocean_light"],  # Light blue for review state
    },
    "priority": {
        "high": CLIO_BRAND_COLORS["coral"],         # Red for high priority (matches Clio "High")
        "medium": CLIO_BRAND_COLORS["amber"],       # Amber for medium priority (custom)
        "normal": CLIO_BRAND_COLORS["ocean_blue"],  # Blue for normal priority (matches Clio "Normal")
        "low": CLIO_BRAND_COLORS["emerald"],        # Green for low priority (matches Clio "Low")
    },
    "urgency": {
        "critical": CLIO_BRAND_COLORS["coral_dark"],    # < 7 days overdue or critical
        "high": CLIO_BRAND_COLORS["coral"],             # < 30 days due or overdue
        "medium": CLIO_BRAND_COLORS["amber"],           # 30-90 days due  
        "low": CLIO_BRAND_COLORS["amber_light"],        # > 90 days due
        "completed": CLIO_BRAND_COLORS["emerald"],      # Completed tasks
    },
    "date_based": {
        "overdue": CLIO_BRAND_COLORS["coral_dark"],     # Past due
        "due_soon": CLIO_BRAND_COLORS["coral"],         # Due within 7 days
        "due_medium": CLIO_BRAND_COLORS["amber"],       # Due within 30 days
        "due_later": CLIO_BRAND_COLORS["ocean_blue"],   # Due in 30+ days
        "no_due_date": CLIO_BRAND_COLORS["mountain_blue"], # No due date set
    },
    "performance": {
        "excellent": CLIO_BRAND_COLORS["emerald_dark"], # > 90% completion rate
        "good": CLIO_BRAND_COLORS["emerald"],           # 70-90% completion rate  
        "average": CLIO_BRAND_COLORS["amber"],          # 50-70% completion rate
        "poor": CLIO_BRAND_COLORS["coral"],             # < 50% completion rate
    },
    "clio_primary": CLIO_BRAND_COLORS["ocean_blue"],
    "clio_secondary": CLIO_BRAND_COLORS["mountain_blue"],
    "clio_accent_1": CLIO_BRAND_COLORS["coral"],
    "clio_accent_2": CLIO_BRAND_COLORS["emerald"],
    "clio_background": CLIO_BRAND_COLORS["sand"],
}

# File paths - will be dynamically detected
DATA_FILES = {
    "tasks": "tasks 2025-06-30.csv",  # Default fallback
    "matters": "matters 2025-06-30.csv",  # Default fallback
}

# API Configuration
API_CONFIG = {
    "clio_assistant_url": "https://clio-assistant.ngrok.app",
    "local_backend_url": "http://localhost:8001",  # Will be overridden by env var
}
