import re
import pandas as pd
from dash import Dash, html, dcc, Input, Output, callback_context
import plotly.express as px

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
    Transform the wide Google-Form style sheet into the long format.
    """
    rows = []

    # Define exact column names for each platform
    platform_columns = {
        'Facebook': {
            'posts': 'Facebook - Total Posts ',
            'interactions': 'Facebook - Total Interactions ',
            'views': 'Facebook - Total Views  ',
            'followers': 'Facebook - Followers Gained  '
        },
        'Instagram': {
            'posts': 'Instagram - Total Posts  ',
            'interactions': 'Instagram - Total Interactions  ',
            'views': 'Instagram - Total Views  ',
            'followers': 'Instagram - Followers Gained  '
        },
        'YouTube': {
            'posts': 'YouTube - Total Posts  ',
            'interactions': 'YouTube - Total Interactions  ',
            'views': 'YouTube - Total Views  ',
            'followers': 'YouTube - Followers Gained  '
        },
        'WhatsApp': {
            'posts': 'WhatsApp - Total Posts  ',
            'interactions': 'WhatsApp - Total Interactions  ',
            'views': 'WhatsApp - Total Views  ',
            'followers': 'WhatsApp - Followers Gained  '
        }
    }

    for _, row in df_wide.iterrows():
        for platform, cols in platform_columns.items():
            posts = row[cols['posts']]
            interactions = row[cols['interactions']]
            views = row[cols['views']]
            followers = row[cols['followers']]
            
            # Engagement Rate = (Total_Interactions / Total_Views) * 100
            engagement_rate = (interactions / views) * 100 if views > 0 else 0
            
            rows.append({
                'Month': row['Month'],
                'District': row['District  '],
                'Platform': platform,
                'Total_Posts': posts,
                'Total_Interactions': interactions,
                'Total_Views': views,
                'Followers_Gained': followers,
                'Engagement_Rate': engagement_rate
            })

    df_long = pd.DataFrame(rows)
    return df_long

def load_data():
    """
    Load and transform data from Google Sheets.
    If fails, raises an error.
    """
    try:
        print("📥 Fetching data from Google Sheets...")
        df_wide = read_google_sheet_as_df(GOOGLE_SHEET_URL)
        print("✅ Google Sheets data loaded successfully!")
        
        df = transform_wide_to_long(df_wide)
        print("✅ Data transformed to long format!")
        
        print(f"📊 Loaded {len(df)} records")
        print(f"🏛️  Districts: {df['District'].unique()}")
        print(f"📅 Months: {df['Month'].unique()}")
        
        return df
        
    except Exception as e:
        print(f"❌ ERROR: Could not load Google Sheet - {e}")
        raise Exception("Please check your data connection. Unable to load data from Google Sheets.")

# Load data
try:
    df = load_data()
except Exception as e:
    # Create empty DataFrame with correct columns if loading fails
    df = pd.DataFrame(columns=[
        'Month', 'District', 'Platform', 'Total_Posts', 
        'Total_Interactions', 'Total_Views', 'Followers_Gained', 'Engagement_Rate'
    ])
    print("⚠️  Using empty dataset due to loading error")

# Create district codes dynamically from available data
available_districts = df['District'].unique() if not df.empty else []
district_codes = {}
for district in available_districts:
    if district == "State Entry":
        district_codes[district] = "ST"
    elif len(district) <= 3:
        district_codes[district] = district.upper()
    else:
        words = district.split()
        if len(words) > 1:
            code = ''.join([word[0] for word in words])
            district_codes[district] = code.upper()
        else:
            district_codes[district] = district[:3].upper()

# Create dropdown options for month and platform
month_options = [{"label": str(m), "value": str(m)} for m in df["Month"].fillna("Unknown").unique()]
month_options.insert(0, {"label": "All Months", "value": "All"})

platform_options = [{"label": p, "value": p} for p in df["Platform"].unique()]
platform_options.insert(0, {"label": "All Platforms", "value": "All"})

app = Dash(__name__)

# KPI card function with matching gradients
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

# Platform performance card with circular progress
def platform_progress_card(platform_name, actual_views, target_views, color):
    # Ensure target is always greater than achieved
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

# Platform colors with actual brand colors
platform_colors = {
    'Facebook': '#1877F2',
    'Instagram': '#E4405F',
    'YouTube': '#FF0000',
    'WhatsApp': '#25D366'
}

# Layout
app.layout = html.Div(
    style={
        "background": "linear-gradient(135deg, #F5F5FF 0%, #E6E6FA 100%)",
        "padding": "25px",
        "fontFamily": "Inter, sans-serif",
        "minHeight": "100vh",
        "position": "relative"
    },
    children=[
        # Error message (hidden by default)
        html.Div(id="error_message", style={"display": "none"}),
        
        # District buttons on right side
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

        # Data status indicator
        html.Div(id="data_status", style={
            "textAlign": "center", 
            "marginBottom": "10px",
            "fontSize": "14px",
            "color": "#666"
        }),

        # Filters
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

        # Hidden store for district selection
        dcc.Store(id='district_store', data='All'),

        # KPI Section
        html.Div(id="kpi_section", style={
            "display": "flex", 
            "justifyContent": "space-between", 
            "marginBottom": "25px"
        }),

        # Graphs and Platform Cards
        html.Div([
            # Platform Performance Chart
            html.Div([
                dcc.Graph(id="platform_chart", style={"height": "400px"})
            ], style={
                "width": "65%", 
                "display": "inline-block", 
                "padding": "15px",
                "background": "white",
                "borderRadius": "12px",
                "border": "1px solid #E6E6FA",
                "boxShadow": "0 2px 8px rgba(47, 47, 77, 0.05)"
            }),
            
            # Platform Performance Cards (Circular Progress)
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
                "width": "33%", 
                "display": "inline-block", 
                "padding": "15px",
                "background": "white",
                "borderRadius": "12px",
                "border": "1px solid #E6E6FA",
                "boxShadow": "0 2px 8px rgba(47, 47, 77, 0.05)"
            })
        ], style={"display": "flex", "justifyContent": "space-between", "gap": "15px"}),

        # Engagement Chart
        html.Div([
            dcc.Graph(id="engagement_chart", style={"height": "400px"})
        ], style={
            "width": "100%", 
            "marginTop": "20px",
            "padding": "15px",
            "background": "white",
            "borderRadius": "12px",
            "border": "1px solid #E6E6FA",
            "boxShadow": "0 2px 8px rgba(47, 47, 77, 0.05)"
        })
    ]
)

# Callback to generate district buttons dynamically
@app.callback(
    [Output('district_buttons_container', 'children'),
     Output('data_status', 'children')],
    [Input('district_store', 'data'),
     Input('district_store', 'data')]  # Double input to trigger on load
)
def update_district_buttons(selected_district, _):
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
    available_districts = df['District'].unique() if not df.empty else []
    for district in available_districts:
        if district in district_codes:
            buttons.append(html.Button(
                district_codes[district], 
                id=f"btn_{district}", 
                n_clicks=0,
                style=active_style if selected_district == district else inactive_style
            ))
    
    # Data status message
    if df.empty:
        status_msg = "❌ Please check your data connection. Unable to load data from Google Sheets."
    else:
        district_count = len(available_districts)
        total_records = len(df)
        status_msg = f"✅ Loaded {total_records} records from {district_count} districts"
    
    return buttons, status_msg

# Callback to update district selection
@app.callback(
    Output('district_store', 'data'),
    [Input(f"btn_All", 'n_clicks')] + 
    [Input(f"btn_{district}", 'n_clicks') for district in district_codes.keys()],
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
     Output("engagement_chart", "figure")],
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

    # KPI Calculations
    total_posts = filtered_df["Total_Posts"].sum()
    total_interactions = filtered_df["Total_Interactions"].sum()
    total_views = filtered_df["Total_Views"].sum()
    followers_gained = filtered_df["Followers_Gained"].sum()

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

    # Engagement Chart
    if not filtered_df.empty:
        engagement_chart = px.scatter(
            filtered_df,
            x="Total_Posts",
            y="Engagement_Rate",
            size="Total_Interactions",
            color="Platform",
            hover_name="District",
            title="Engagement Analysis",
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
    else:
        engagement_chart = px.scatter(title="No data available for selected filters")
        engagement_chart.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font_color="#2F2F4D",
            title_font_color="#2F2F4D",
            title_x=0.5
        )

    return platform_chart, platform_cards_content, kpis, engagement_chart

# Railway-compatible setup
if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8080)
