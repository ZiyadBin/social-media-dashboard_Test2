import re
import pandas as pd
from dash import Dash, html, dcc, Input, Output, callback_context
import plotly.express as px
import numpy as np

# --- CONFIG: Google Sheet link
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QyeUhUye7O9p29GT3arc70hmMT42XWOnpXeGrtLtC5M/edit?usp=sharing"

def extract_sheet_id(url: str) -> str:
    """Extract spreadsheet id from a standard Google Sheets URL."""
    m = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if not m:
        raise ValueError("Could not extract sheet id from URL.")
    return m.group(1)

def read_google_sheet_as_df(sheet_url: str) -> pd.DataFrame:
    """
    Read a Google Sheet tab as a pandas DataFrame using the CSV export link.
    """
    sheet_id = extract_sheet_id(sheet_url)
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(export_url)
    return df

def transform_wide_to_long(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Transform the wide Google-Form style sheet into the long format expected by the dashboard.
    """
    platforms = ['Facebook', 'Instagram', 'YouTube', 'WhatsApp']
    rows = []

    print("Available columns in Google Sheet:", list(df_wide.columns))
    
    # Debug: Print first few rows to see actual data
    print("First few rows of raw data:")
    print(df_wide.head())

    # Map column names - handle different naming patterns
    column_mapping = {
        'Timestamp': ['Timestamp', 'timestamp', 'Time'],
        'District': ['District', 'district', 'Districts'],
        'Month': ['Month', 'month', 'months']
    }
    
    # Find actual column names
    actual_columns = {}
    for standard_name, possible_names in column_mapping.items():
        for possible in possible_names:
            if possible in df_wide.columns:
                actual_columns[standard_name] = possible
                break
        if standard_name not in actual_columns:
            print(f"Warning: Column '{standard_name}' not found. Using default.")
            df_wide[standard_name] = pd.NA

    for _, r in df_wide.iterrows():
        # Use actual column names from mapping
        base_timestamp = r.get(actual_columns.get('Timestamp', 'Timestamp'))
        base_district = r.get(actual_columns.get('District', 'District'))
        base_month = r.get(actual_columns.get('Month', 'Month'))

        print(f"Processing row - District: {base_district}, Month: {base_month}")

        for p in platforms:
            # Build wide column names - handle different formats
            possible_post_names = [f"{p} - Total Posts", f"{p} - Total posts", f"{p} - Posts"]
            possible_inter_names = [f"{p} - Total Interactions", f"{p} - Total interactions", f"{p} - Interactions"]
            possible_views_names = [f"{p} - Total Views", f"{p} - Total views", f"{p} - Views"]
            possible_followers_names = [f"{p} - Followers Gained", f"{p} - Followers gained", f"{p} - Followers"]

            # Find actual column names
            col_posts = None
            for name in possible_post_names:
                if name in df_wide.columns:
                    col_posts = name
                    break
            
            col_inter = None
            for name in possible_inter_names:
                if name in df_wide.columns:
                    col_inter = name
                    break
            
            col_views = None
            for name in possible_views_names:
                if name in df_wide.columns:
                    col_views = name
                    break
            
            col_followers = None
            for name in possible_followers_names:
                if name in df_wide.columns:
                    col_followers = name
                    break

            # Get values with proper column names
            total_posts = pd.to_numeric(r.get(col_posts, 0), errors="coerce") if col_posts else 0
            total_interactions = pd.to_numeric(r.get(col_inter, 0), errors="coerce") if col_inter else 0
            total_views = pd.to_numeric(r.get(col_views, 0), errors="coerce") if col_views else 0
            followers_gained = pd.to_numeric(r.get(col_followers, 0), errors="coerce") if col_followers else 0

            # Fill NaN with 0 for numeric fields
            total_posts = int(0 if pd.isna(total_posts) else total_posts)
            total_interactions = int(0 if pd.isna(total_interactions) else total_interactions)
            total_views = int(0 if pd.isna(total_views) else total_views)
            followers_gained = int(0 if pd.isna(followers_gained) else followers_gained)

            # Compute engagement rate safely (Total_Interactions / Total_Views) * 100
            if total_views > 0:
                engagement_rate = (total_interactions / total_views) * 100
            else:
                engagement_rate = 0.0

            # Only add row if there's actual data
            if total_posts > 0 or total_interactions > 0 or total_views > 0:
                rows.append({
                    "Timestamp": base_timestamp,
                    "District": base_district,
                    "Month": base_month,
                    "Platform": p,
                    "Total_Posts": total_posts,
                    "Total_Interactions": total_interactions,
                    "Total_Views": total_views,
                    "Followers_Gained": followers_gained,
                    "Engagement_Rate": engagement_rate
                })

    df_long = pd.DataFrame(rows)
    
    # Convert Timestamp to datetime if possible
    try:
        df_long["Timestamp"] = pd.to_datetime(df_long["Timestamp"], errors="coerce")
    except Exception:
        pass

    # Fill missing District/Month with placeholder to avoid filter issues
    df_long["District"] = df_long["District"].fillna("Unknown")
    df_long["Month"] = df_long["Month"].fillna("Unknown")
    
    print(f"Transformed data shape: {df_long.shape}")
    print(f"Districts in transformed data: {df_long['District'].unique()}")
    print(f"Sample of transformed data:")
    print(df_long.head())
    
    return df_long

def create_fallback_data():
    """Create dummy data as fallback when Google Sheets fails"""
    # Your actual districts
    districts = [
        'Kasaragod', 'Kannur', 'Kozhikode North', 'Kozhikode South', 'Wayanad',
        'Malappuram West', 'Malappuram East', 'Nilgris', 'Thrissur', 'Palakkad',
        'Ernakulam', 'Idukki HR', 'Idukki LR', 'Kottayam', 'Alappuzha',
        'Pathanamthitta', 'Kollam', 'Thiruvananthapuram', 'State Entry'
    ]
    months = ['October', 'November', 'December']
    platforms = ['Facebook', 'Instagram', 'YouTube', 'WhatsApp']
    
    rows = []
    for district in districts:
        for month in months:
            for platform in platforms:
                total_posts = np.random.randint(5, 20)
                total_views = np.random.randint(1000, 10000)
                total_interactions = np.random.randint(100, 2000)
                followers_gained = np.random.randint(10, 100)
                engagement_rate = (total_interactions / total_views) * 100 if total_views > 0 else 0
                
                rows.append({
                    "District": district,
                    "Month": month,
                    "Platform": platform,
                    "Total_Posts": total_posts,
                    "Total_Interactions": total_interactions,
                    "Total_Views": total_views,
                    "Followers_Gained": followers_gained,
                    "Engagement_Rate": engagement_rate
                })
    
    return pd.DataFrame(rows)

# --- Load & transform data from Google Sheet
try:
    print("Attempting to load data from Google Sheets...")
    df_wide = read_google_sheet_as_df(GOOGLE_SHEET_URL)
    print("Google Sheets data loaded successfully!")
    print(f"Columns found: {list(df_wide.columns)}")
    print(f"Number of rows: {len(df_wide)}")
    
    df = transform_wide_to_long(df_wide)
    print("Data transformed to long format successfully!")
    
except Exception as e:
    print(f"Warning: could not load Google Sheet ({e}). Creating fallback data.")
    df = create_fallback_data()

print(f"Final dataset shape: {df.shape}")
print(f"Available districts: {df['District'].unique()}")
print(f"Available months: {df['Month'].unique()}")

# Your actual districts list
ACTUAL_DISTRICTS = [
    'Kasaragod', 'Kannur', 'Kozhikode North', 'Kozhikode South', 'Wayanad',
    'Malappuram West', 'Malappuram East', 'Nilgris', 'Thrissur', 'Palakkad',
    'Ernakulam', 'Idukki HR', 'Idukki LR', 'Kottayam', 'Alappuzha',
    'Pathanamthitta', 'Kollam', 'Thiruvananthapuram', 'State Entry'
]

# Create district codes dynamically
district_codes = {}
for district in ACTUAL_DISTRICTS:
    if district == "State Entry":
        district_codes[district] = "ST"
    elif len(district) <= 3:
        district_codes[district] = district.upper()
    else:
        # Create codes like KSG for Kasaragod, KNR for Kannur, etc.
        words = district.split()
        if len(words) > 1:
            code = ''.join([word[0] for word in words])
            district_codes[district] = code.upper()
        else:
            district_codes[district] = district[:3].upper()

# District coordinates for Kerala map
district_coords = {
    'Kasaragod': {"lat": 12.50, "lon": 75.00},
    'Kannur': {"lat": 11.87, "lon": 75.37},
    'Kozhikode North': {"lat": 11.45, "lon": 75.70},
    'Kozhikode South': {"lat": 11.25, "lon": 75.77},
    'Wayanad': {"lat": 11.68, "lon": 76.13},
    'Malappuram West': {"lat": 11.07, "lon": 76.00},
    'Malappuram East': {"lat": 11.07, "lon": 76.20},
    'Nilgris': {"lat": 11.40, "lon": 76.70},
    'Thrissur': {"lat": 10.52, "lon": 76.21},
    'Palakkad': {"lat": 10.77, "lon": 76.65},
    'Ernakulam': {"lat": 10.00, "lon": 76.33},
    'Idukki HR': {"lat": 9.85, "lon": 76.94},
    'Idukki LR': {"lat": 9.75, "lon": 76.85},
    'Kottayam': {"lat": 9.59, "lon": 76.52},
    'Alappuzha': {"lat": 9.49, "lon": 76.33},
    'Pathanamthitta': {"lat": 9.27, "lon": 76.78},
    'Kollam': {"lat": 8.88, "lon": 76.60},
    'Thiruvananthapuram': {"lat": 8.52, "lon": 76.93},
    'State Entry': {"lat": 10.85, "lon": 76.27}  # Center of Kerala
}

# Create dropdown options for month and platform
month_options = [{"label": str(m), "value": str(m)} for m in df["Month"].fillna("Unknown").unique()]
month_options.insert(0, {"label": "All Months", "value": "All"})

platform_options = [{"label": p, "value": p} for p in df["Platform"].unique()]
platform_options.insert(0, {"label": "All Platforms", "value": "All"})

app = Dash(__name__)

# ... [KEEP ALL THE SAME FUNCTIONS: kpi_card, platform_progress_card, platform_colors, layout] ...

# KPI card function (same as before)
def kpi_card(title, value, color_scheme):
    gradient_colors = {
        "violet": "linear-gradient(135deg, #7A288A 0%, #9D4BB5 100%)",
        "dark_blue": "linear-gradient(135deg, #2F2F4D 0%, #4A4A6A 100%)",
        "rose": "linear-gradient(135deg, #FFC0CB 0%, #FFB6C1 100%)",
        "lavender": "linear-gradient(135deg, #E6E6FA 0%, #F5F5FF 100%)"
    }
    
    text_color = "#FFFFFF" if color_scheme in ["violet", "dark_blue"] else "#2F2F4D"
    
    return html.Div(
        style={
            "background": gradient_colors[color_scheme],
            "borderRadius": "12px",
            "padding": "20px",
            "textAlign": "center",
            "width": "23%",
            "margin": "5px",
            "color": text_color,
            "minHeight": "100px",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "center",
            "boxShadow": "0 4px 12px rgba(47, 47, 77, 0.1)"
        },
        children=[
            html.H4(title, style={"fontSize": "13px", "margin": "0", "opacity": 0.9, "fontWeight": "500"}),
            html.H2(f"{value:,.0f}", style={"fontSize": "24px", "margin": "5px 0", "fontWeight": "600"}),
        ]
    )

# Platform performance card (same as before)
def platform_progress_card(platform_name, actual_views, target_views, color):
    if actual_views >= target_views:
        target_views = actual_views + 1000
    
    percentage = min(100, (actual_views / target_views) * 100) if target_views > 0 else 0
    
    if percentage >= 80:
        progress_color = "#43e97b"
        performance_text = "Excellent"
    elif percentage >= 60:
        progress_color = "#f5576c"
        performance_text = "Good"
    else:
        progress_color = "#ff4757"
        performance_text = "Needs Improvement"
    
    return html.Div(
        style={
            "background": "white",
            "borderRadius": "12px",
            "padding": "15px",
            "margin": "8px",
            "width": "48%",
            "textAlign": "center",
            "minHeight": "180px",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "center",
            "alignItems": "center",
            "boxShadow": "0 2px 8px rgba(47, 47, 77, 0.05)",
            "border": "1px solid #E6E6FA"
        },
        children=[
            html.H3(platform_name, style={
                "color": color,
                "margin": "0 0 12px 0",
                "fontSize": "14px",
                "fontWeight": "600"
            }),
            
            html.Div(
                style={
                    "position": "relative",
                    "width": "80px",
                    "height": "80px",
                    "marginBottom": "12px"
                },
                children=[
                    html.Div(
                        style={
                            "position": "absolute",
                            "width": "80px",
                            "height": "80px",
                            "borderRadius": "50%",
                            "background": f"conic-gradient({progress_color} {percentage * 3.6}deg, #E6E6FA {percentage * 3.6}deg 360deg)",
                            "display": "flex",
                            "justifyContent": "center",
                            "alignItems": "center"
                        }
                    ),
                    
                    html.Div(
                        style={
                            "position": "absolute",
                            "width": "64px",
                            "height": "64px",
                            "background": "white",
                            "borderRadius": "50%",
                            "top": "8px",
                            "left": "8px"
                        }
                    ),
                    
                    html.Div(
                        style={
                            "position": "absolute",
                            "top": "50%",
                            "left": "50%",
                            "transform": "translate(-50%, -50%)",
                            "textAlign": "center"
                        },
                        children=[
                            html.Div(f"{percentage:.0f}%", style={
                                "fontSize": "16px",
                                "fontWeight": "700",
                                "color": "#2F2F4D",
                                "lineHeight": "1"
                            }),
                            html.Div("Target", style={
                                "fontSize": "9px",
                                "color": "#2F2F4D",
                                "opacity": 0.6,
                                "marginTop": "2px"
                            })
                        ]
                    )
                ]
            ),
            
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "width": "100%",
                    "marginTop": "8px"
                },
                children=[
                    html.Div(
                        style={"textAlign": "center", "flex": "1"},
                        children=[
                            html.Div("Achieved", style={
                                "fontSize": "9px",
                                "color": "#2F2F4D",
                                "opacity": 0.7,
                                "marginBottom": "2px"
                            }),
                            html.Div(f"{actual_views:,}", style={
                                "fontSize": "12px",
                                "fontWeight": "600",
                                "color": "#2F2F4D"
                            })
                        ]
                    ),
                    html.Div(
                        style={"textAlign": "center", "flex": "1"},
                        children=[
                            html.Div("Target", style={
                                "fontSize": "9px",
                                "color": "#2F2F4D",
                                "opacity": 0.7,
                                "marginBottom": "2px"
                            }),
                            html.Div(f"{target_views:,}", style={
                                "fontSize": "12px",
                                "fontWeight": "600",
                                "color": "#2F2F4D"
                            })
                        ]
                    )
                ]
            ),
            
            html.Div(
                style={
                    "marginTop": "8px",
                    "padding": "3px 10px",
                    "background": progress_color + "20",
                    "borderRadius": "10px",
                    "border": f"1px solid {progress_color}40"
                },
                children=[
                    html.Span(
                        performance_text,
                        style={
                            "fontSize": "9px",
                            "fontWeight": "600",
                            "color": progress_color
                        }
                    )
                ]
            )
        ]
    )

# Platform colors
platform_colors = {
    'Facebook': '#1877F2',
    'Instagram': '#E4405F',
    'YouTube': '#FF0000',
    'WhatsApp': '#25D366'
}

# Layout (same as before)
app.layout = html.Div(
    style={
        "background": "linear-gradient(135deg, #F5F5FF 0%, #E6E6FA 100%)",
        "padding": "25px",
        "fontFamily": "Inter, sans-serif",
        "minHeight": "100vh",
        "position": "relative"
    },
    children=[
        html.Div(
            id="district_buttons_container",
            style={
                "position": "fixed",
                "right": "20px",
                "top": "50%",
                "transform": "translateY(-50%)",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "center",
                "zIndex": 1000,
                "background": "rgba(255, 255, 255, 0.8)",
                "backdropFilter": "blur(10px)",
                "padding": "15px 10px",
                "borderRadius": "25px",
                "border": "1px solid #E6E6FA",
                "boxShadow": "0 4px 15px rgba(47, 47, 77, 0.1)",
                "maxHeight": "80vh",
                "overflowY": "auto"
            }
        ),

        html.H1("Social Media Dashboard", 
                style={
                    "color": "#2F2F4D", 
                    "textAlign": "center", 
                    "marginBottom": "25px",
                    "fontWeight": "600",
                    "fontSize": "28px"
                }),

        html.Div([
            html.Div([
                html.Label("Month:", style={"fontWeight": "500", "marginBottom": "5px", "color": "#2F2F4D", "fontSize": "14px"}),
                dcc.Dropdown(
                    id="month_filter", 
                    options=month_options, 
                    value="All", 
                    clearable=False,
                    style={
                        "borderRadius": "8px", 
                        "border": "1px solid #E6E6FA",
                        "background": "white"
                    }
                )
            ], style={"width": "48%", "display": "inline-block", "padding": "5px"}),

            html.Div([
                html.Label("Platform:", style={"fontWeight": "500", "marginBottom": "5px", "color": "#2F2F4D", "fontSize": "14px"}),
                dcc.Dropdown(
                    id="platform_filter", 
                    options=platform_options, 
                    value="All", 
                    clearable=False,
                    style={
                        "borderRadius": "8px", 
                        "border": "1px solid #E6E6FA",
                        "background": "white"
                    }
                )
            ], style={"width": "48%", "display": "inline-block", "padding": "5px"})
        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "25px", "gap": "10px"}),

        dcc.Store(id='district_store', data='All'),

        html.Div(id="kpi_section", style={
            "display": "flex", 
            "justifyContent": "space-between", 
            "marginBottom": "25px"
        }),

        html.Div([
            html.Div([
                dcc.Graph(id="platform_chart", style={"height": "350px"})
            ], style={
                "width": "48%", 
                "display": "inline-block", 
                "padding": "15px",
                "background": "white",
                "borderRadius": "12px",
                "border": "1px solid #E6E6FA",
                "boxShadow": "0 2px 8px rgba(47, 47, 77, 0.05)"
            }),
            
            html.Div([
                html.H3("Platform Performance", style={
                    "color": "#2F2F4D", 
                    "textAlign": "center", 
                    "marginBottom": "20px",
                    "fontWeight": "600",
                    "fontSize": "18px"
                }),
                html.Div(id="platform_cards", style={
                    "display": "flex", 
                    "flexWrap": "wrap", 
                    "justifyContent": "space-between"
                })
            ], style={
                "width": "48%", 
                "display": "inline-block", 
                "padding": "15px",
                "background": "white",
                "borderRadius": "12px",
                "border": "1px solid #E6E6FA",
                "boxShadow": "0 2px 8px rgba(47, 47, 77, 0.05)"
            })
        ], style={"display": "flex", "justifyContent": "space-between", "gap": "15px"}),

        html.Div(id="map_engagement_section", style={"marginTop": "20px"})
    ]
)

# ... [KEEP ALL THE SAME CALLBACKS] ...

# Callback to generate district buttons dynamically
@app.callback(
    Output('district_buttons_container', 'children'),
    Input('district_store', 'data')
)
def update_district_buttons(selected_district):
    active_style = {
        "width": "50px", "height": "50px", "borderRadius": "50%",
        "border": "2px solid #7A288A", 
        "background": "linear-gradient(135deg, #7A288A 0%, #9D4BB5 100%)",
        "color": "white", "fontWeight": "600", "fontSize": "12px",
        "margin": "8px 0", "cursor": "pointer",
        "boxShadow": "0 2px 8px rgba(122, 40, 138, 0.3)"
    }
    
    inactive_style = {
        "width": "50px", "height": "50px", "borderRadius": "50%",
        "border": "2px solid #E6E6FA", "background": "white",
        "color": "#7A288A", "fontWeight": "600", "fontSize": "12px",
        "margin": "8px 0", "cursor": "pointer",
        "boxShadow": "0 2px 6px rgba(47, 47, 77, 0.1)",
        "transition": "all 0.3s ease"
    }
    
    buttons = []
    
    # All button
    buttons.append(html.Button(
        "All", 
        id="btn_All", 
        n_clicks=0,
        style=active_style if selected_district == "All" else inactive_style
    ))
    
    # District buttons - only show districts that have data
    available_districts = df['District'].unique()
    for district in ACTUAL_DISTRICTS:
        if district in available_districts:
            buttons.append(html.Button(
                district_codes[district], 
                id=f"btn_{district}", 
                n_clicks=0,
                style=active_style if selected_district == district else inactive_style
            ))
    
    return buttons

# Callback to update district selection
@app.callback(
    Output('district_store', 'data'),
    [Input(f"btn_All", 'n_clicks')] + 
    [Input(f"btn_{district}", 'n_clicks') for district in ACTUAL_DISTRICTS],
    prevent_initial_call=True
)
def update_district_selection(all_clicks, *district_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return 'All'
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    selected_district = button_id.replace('btn_', '')
    
    return selected_district

# Main dashboard callback
@app.callback(
    [Output("platform_chart", "figure"),
     Output("platform_cards", "children"),
     Output("kpi_section", "children"),
     Output("map_engagement_section", "children")],
    [Input("district_store", "data"),
     Input("month_filter", "value"),
     Input("platform_filter", "value")]
)
def update_dashboard(selected_district, selected_month, selected_platform):
    filtered_df = df.copy()
    
    # Apply filters
    if selected_district != "All":
        filtered_df = filtered_df[filtered_df["District"] == selected_district]
    if selected_month != "All":
        filtered_df = filtered_df[filtered_df["Month"] == selected_month]
    if selected_platform != "All":
        filtered_df = filtered_df[filtered_df["Platform"] == selected_platform]

    print(f"Filtered data shape: {filtered_df.shape}")
    print(f"Filtered data sample:")
    print(filtered_df.head())

    # KPI Calculations
    total_posts = filtered_df["Total_Posts"].sum()
    total_interactions = filtered_df["Total_Interactions"].sum()
    total_views = filtered_df["Total_Views"].sum()
    followers_gained = filtered_df["Followers_Gained"].sum()

    print(f"KPIs - Posts: {total_posts}, Interactions: {total_interactions}, Views: {total_views}, Followers: {followers_gained}")

    # KPI Cards
    kpis = [
        kpi_card("Total Posts", total_posts, "violet"),
        kpi_card("Total Interactions", total_interactions, "dark_blue"),
        kpi_card("Total Views", total_views, "rose"),
        kpi_card("Followers Gained", followers_gained, "lavender")
    ]

    # Platform Performance Chart
    if not filtered_df.empty:
        platform_chart = px.bar(
            filtered_df, 
            x="Platform", 
            y="Total_Interactions", 
            color="District",
            title="Platform Performance by District",
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        platform_chart.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font_color="#2F2F4D",
            title_font_color="#2F2F4D",
            title_x=0.5,
            showlegend=True
        )
    else:
        platform_chart = px.bar(title="No data available for selected filters")
        platform_chart.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font_color="#2F2F4D",
            title_font_color="#2F2F4D",
            title_x=0.5
        )

    # Platform Performance Cards
    platform_cards = []
    if not filtered_df.empty:
        TARGET_VIEWS_PER_POST = 2500
        
        platforms_to_show = ['Facebook', 'Instagram', 'YouTube', 'WhatsApp']
        
        for platform in platforms_to_show:
            platform_data = filtered_df[filtered_df['Platform'] == platform]
            
            if not platform_data.empty:
                total_posts = platform_data['Total_Posts'].sum()
                actual_views = platform_data['Total_Views'].sum()
                target_views = total_posts * TARGET_VIEWS_PER_POST
                
                platform_cards.append(platform_progress_card(
                    platform_name=platform,
                    actual_views=actual_views,
                    target_views=target_views,
                    color=platform_colors[platform]
                ))
            else:
                platform_cards.append(platform_progress_card(
                    platform_name=platform,
                    actual_views=0,
                    target_views=1000,
                    color=platform_colors[platform]
                ))
        
        rows = []
        for i in range(0, len(platform_cards), 2):
            row_cards = platform_cards[i:i+2]
            rows.append(
                html.Div(
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "marginBottom": "10px",
                        "width": "100%"
                    },
                    children=row_cards
                )
            )
        
        platform_cards_content = rows
    else:
        platform_cards_content = html.Div("No data available", style={"textAlign": "center", "color": "#999"})

    # MAP or ENGAGEMENT CHART
    map_engagement_section = []
    
    if selected_district == "All":
        if not filtered_df.empty:
            map_data = []
            for district in district_coords.keys():
                if district in filtered_df['District'].values:
                    district_data = filtered_df[filtered_df['District'] == district]
                    if not district_data.empty:
                        total_interactions = district_data['Total_Interactions'].sum()
                        total_views = district_data['Total_Views'].sum()
                        
                        map_data.append({
                            'District': district,
                            'Total_Interactions': total_interactions,
                            'Total_Views': total_views,
                            'lat': district_coords[district]['lat'],
                            'lon': district_coords[district]['lon']
                        })
            
            if map_data:
                map_df = pd.DataFrame(map_data)
                
                platform_map = px.scatter_mapbox(
                    map_df,
                    lat="lat",
                    lon="lon",
                    size="Total_Interactions",
                    color="Total_Interactions",
                    hover_name="District",
                    hover_data={
                        "Total_Interactions": True,
                        "Total_Views": True,
                        "lat": False,
                        "lon": False
                    },
                    color_continuous_scale="Viridis",
                    size_max=30,
                    zoom=7,
                    height=400,
                    title="Social Media Engagement Across Districts"
                )
                
                platform_map.update_layout(
                    mapbox_style="open-street-map",
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font_color="#2F2F4D",
                    title_font_color="#2F2F4D",
                    title_x=0.5,
                    margin={"r":0,"t":40,"l":0,"b":0}
                )
                
                map_engagement_section = html.Div([
                    dcc.Graph(
                        id="platform_map", 
                        figure=platform_map, 
                        style={"height": "450px"}
                    )
                ], style={
                    "width": "100%", 
                    "padding": "15px",
                    "background": "white",
                    "borderRadius": "12px",
                    "border": "1px solid #E6E6FA",
                    "boxShadow": "0 2px 8px rgba(47, 47, 77, 0.05)"
                })
    
    else:
        if not filtered_df.empty:
            engagement_chart = px.scatter(
                filtered_df,
                x="Total_Posts",
                y="Engagement_Rate",
                size="Total_Interactions",
                color="Platform",
                hover_name="Platform",
                title=f"Engagement Analysis - {selected_district}",
                size_max=30,
                color_discrete_map=platform_colors
            )
            engagement_chart.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                font_color="#2F2F4D",
                title_font_color="#2F2F4D",
                title_x=0.5
            )
            
            map_engagement_section = html.Div([
                dcc.Graph(
                    id="engagement_chart", 
                    figure=engagement_chart, 
                    style={"height": "400px"}
                )
            ], style={
                "width": "100%", 
                "padding": "15px",
                "background": "white",
                "borderRadius": "12px",
                "border": "1px solid #E6E6FA",
                "boxShadow": "0 2px 8px rgba(47, 47, 77, 0.05)"
            })

    return platform_chart, platform_cards_content, kpis, map_engagement_section

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8080)
