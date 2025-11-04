import re
import pandas as pd
from dash import Dash, html, dcc, Input, Output, callback_context
import plotly.express as px

# --- CONFIG: Google Sheet link (the one you provided)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QyeUhUye7O9p29GT3arc70hmMT42XWOnpXeGrtLtC5M/edit?usp=sharing"
# If your sheet's tab (gid) is not 0, replace the gid below with the correct number:
DEFAULT_SHEET_GID = "0"

def extract_sheet_id(url: str) -> str:
    """Extract spreadsheet id from a standard Google Sheets URL."""
    m = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if not m:
        raise ValueError("Could not extract sheet id from URL.")
    return m.group(1)

def read_google_sheet_as_df(sheet_url: str, gid: str = DEFAULT_SHEET_GID) -> pd.DataFrame:
    """
    Read a Google Sheet tab as a pandas DataFrame using the CSV export link.
    The sheet must be viewable publicly or shared appropriately.
    """
    sheet_id = extract_sheet_id(sheet_url)
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    df = pd.read_csv(export_url)
    return df

def transform_wide_to_long(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Transform the wide Google-Form style sheet into the long format expected by the dashboard:
    Timestamp, District, Month, Platform, Total_Posts, Total_Interactions, Total_Views, Followers_Gained, Engagement_Rate
    """
    platforms = ['Facebook', 'Instagram', 'YouTube', 'WhatsApp']
    rows = []

    # Ensure core columns exist
    for col in ["Timestamp", "District", "Month"]:
        if col not in df_wide.columns:
            # If missing, add with default empty values to avoid crashes
            df_wide[col] = pd.NA

    for _, r in df_wide.iterrows():
        base_timestamp = r.get("Timestamp")
        base_district = r.get("District")
        base_month = r.get("Month")

        for p in platforms:
            # Build wide column names
            col_posts = f"{p} - Total Posts"
            col_inter = f"{p} - Total Interactions"
            col_views = f"{p} - Total Views"
            col_followers = f"{p} - Followers Gained"

            # Safely fetch values (if column missing, treat as 0)
            total_posts = pd.to_numeric(r.get(col_posts, 0), errors="coerce")
            total_interactions = pd.to_numeric(r.get(col_inter, 0), errors="coerce")
            total_views = pd.to_numeric(r.get(col_views, 0), errors="coerce")
            followers_gained = pd.to_numeric(r.get(col_followers, 0), errors="coerce")

            # Fill NaN with 0 for numeric fields
            total_posts = int(0 if pd.isna(total_posts) else total_posts)
            total_interactions = int(0 if pd.isna(total_interactions) else total_interactions)
            total_views = int(0 if pd.isna(total_views) else total_views)
            followers_gained = int(0 if pd.isna(followers_gained) else followers_gained)

            # Compute engagement rate safely
            if total_views > 0:
                engagement_rate = (total_interactions / total_views) * 100
            else:
                engagement_rate = 0.0

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
    # Optional: convert Timestamp to datetime if possible
    try:
        df_long["Timestamp"] = pd.to_datetime(df_long["Timestamp"], errors="coerce")
    except Exception:
        pass

    # Fill missing District/Month with placeholder to avoid filter issues
    df_long["District"] = df_long["District"].fillna("Unknown")
    df_long["Month"] = df_long["Month"].fillna("Unknown")

    return df_long

# --- Load & transform data from Google Sheet
try:
    df_wide = read_google_sheet_as_df(GOOGLE_SHEET_URL, gid=DEFAULT_SHEET_GID)
    df = transform_wide_to_long(df_wide)
except Exception as e:
    # If reading the sheet fails (network / permission), fallback to local Excel (your dummy)
    print(f"Warning: could not load Google Sheet ({e}). Falling back to local Excel.")
    df = pd.read_excel("districts_social_dummy_data.xlsx")

# Create district codes (first 2-3 letters)
# Instead of hardcoded district_codes and district_coords:
district_codes = {district: generate_code(district) for district in df["District"].unique()}
district_coords = {district: get_coordinates(district) for district in df["District"].unique()}

# District coordinates for Kerala map
district_coords = {
    "Kozhikode": {"lat": 11.25, "lon": 75.77},
    "Malappuram": {"lat": 11.07, "lon": 76.07},
    "Kannur": {"lat": 11.87, "lon": 75.37},
    "Thrissur": {"lat": 10.52, "lon": 76.21},
    "Palakkad": {"lat": 10.77, "lon": 76.65}
}

# Create dropdown options for month and platform (built from transformed df)
month_options = [{"label": m, "value": m} for m in df["Month"].fillna("Unknown").unique()]
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
        target_views = actual_views + 1000  # Add 1k to achieved views
    
    # Calculate percentage
    percentage = min(100, (actual_views / target_views) * 100) if target_views > 0 else 0
    
    # Determine color based on percentage
    if percentage >= 80:
        progress_color = "#43e97b"  # Green
        performance_text = "Excellent"
    elif percentage >= 60:
        progress_color = "#f5576c"  # Orange
        performance_text = "Good"
    else:
        progress_color = "#ff4757"  # Red
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
            # Platform name with brand color
            html.H3(platform_name, style={
                "color": color,
                "margin": "0 0 12px 0",
                "fontSize": "14px",
                "fontWeight": "600"
            }),
            
            # Circular progress container
            html.Div(
                style={
                    "position": "relative",
                    "width": "80px",
                    "height": "80px",
                    "marginBottom": "12px"
                },
                children=[
                    # Single progress circle
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
                    
                    # Inner white circle to create ring effect
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
                    
                    # Percentage text in center
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
            
            # Views information
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
            
            # Performance indicator
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
    'Facebook': '#1877F2',      # Facebook blue
    'Instagram': '#E4405F',     # Instagram pink
    'YouTube': '#FF0000',       # YouTube red
    'WhatsApp': '#25D366'       # WhatsApp green
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
        # District buttons on right side
        html.Div(
            [
                # All button
                html.Button("All", id="btn_All", n_clicks=0, style={
                    "width": "50px", "height": "50px", "borderRadius": "50%",
                    "border": "2px solid #7A288A", 
                    "background": "linear-gradient(135deg, #7A288A 0%, #9D4BB5 100%)",
                    "color": "white", "fontWeight": "600", "fontSize": "12px",
                    "margin": "8px 0", "cursor": "pointer",
                    "boxShadow": "0 2px 8px rgba(122, 40, 138, 0.3)"
                }),
                # District buttons
                *[html.Button(
                    code, 
                    id=f"btn_{district}", 
                    n_clicks=0, 
                    style={
                        "width": "50px", "height": "50px", "borderRadius": "50%",
                        "border": "2px solid #E6E6FA", "background": "white",
                        "color": "#7A288A", "fontWeight": "600", "fontSize": "12px",
                        "margin": "8px 0", "cursor": "pointer",
                        "boxShadow": "0 2px 6px rgba(47, 47, 77, 0.1)",
                        "transition": "all 0.3s ease"
                    }
                ) for district, code in district_codes.items()]
            ],
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
                "boxShadow": "0 4px 15px rgba(47, 47, 77, 0.1)"
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

        # Filters (only month and platform now)
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
                "width": "48%", 
                "display": "inline-block", 
                "padding": "15px",
                "background": "white",
                "borderRadius": "12px",
                "border": "1px solid #E6E6FA",
                "boxShadow": "0 2px 8px rgba(47, 47, 77, 0.05)"
            })
        ], style={"display": "flex", "justifyContent": "space-between", "gap": "15px"}),

        # Map or Engagement Chart - Conditionally displayed
        html.Div(id="map_engagement_section", style={"marginTop": "20px"})
    ]
)

# Callback to update district selection and button styles
@app.callback(
    [Output('district_store', 'data'),
     Output('btn_All', 'style'),
     Output('btn_Kozhikode', 'style'),
     Output('btn_Malappuram', 'style'),
     Output('btn_Kannur', 'style'),
     Output('btn_Thrissur', 'style'),
     Output('btn_Palakkad', 'style')],
    [Input("btn_All", 'n_clicks'),
     Input("btn_Kozhikode", 'n_clicks'),
     Input("btn_Malappuram", 'n_clicks'),
     Input("btn_Kannur", 'n_clicks'),
     Input("btn_Thrissur", 'n_clicks'),
     Input("btn_Palakkad", 'n_clicks')],
    prevent_initial_call=True
)
def update_district_selection(all_clicks, kz_clicks, mlp_clicks, kn_clicks, tr_clicks, pkd_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return 'All', {}, {}, {}, {}, {}, {}
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    selected_district = button_id.replace('btn_', '')
    
    # Define active and inactive styles
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
    
    # Return styles for each button based on selection
    styles = {}
    districts = ['All', 'Kozhikode', 'Malappuram', 'Kannur', 'Thrissur', 'Palakkad']
    for district in districts:
        styles[f'btn_{district}'] = active_style if district == selected_district else inactive_style
    
    return (selected_district, 
            styles['btn_All'], 
            styles['btn_Kozhikode'], 
            styles['btn_Malappuram'], 
            styles['btn_Kannur'], 
            styles['btn_Thrissur'], 
            styles['btn_Palakkad'])

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
    platform_chart = px.bar(
        filtered_df, 
        x="Platform", 
        y="Total_Interactions", 
        color="District",
        title="Platform Performance by District",
        barmode="group",
        color_discrete_sequence=['#7A288A', '#2F2F4D', '#FFC0CB', '#E6E6FA', '#9D4BB5']
    )
    platform_chart.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_color="#2F2F4D",
        title_font_color="#2F2F4D",
        title_x=0.5,
        showlegend=True
    )

    # Platform Performance Cards (Circular Progress)
    platform_cards = []
    if not filtered_df.empty:
        # Define target views per post (5,000 views per post as benchmark)
        TARGET_VIEWS_PER_POST = 2500
        
        # Filter for only the 4 platforms we want
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
                # If no data for platform, show zero progress
                platform_cards.append(platform_progress_card(
                    platform_name=platform,
                    actual_views=0,
                    target_views=1000,  # Minimum target
                    color=platform_colors[platform]
                ))
        
        # Arrange cards in rows of 2
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

    # MAP or ENGAGEMENT CHART - Conditionally displayed
    map_engagement_section = []
    
    if selected_district == "All":
        # SHOW MAP when "All" districts selected
        if not filtered_df.empty:
            # Prepare data for map
            map_data = []
            for district in district_coords.keys():
                district_data = filtered_df[filtered_df['District'] == district]
                if not district_data.empty:
                    for platform in ['Facebook', 'Instagram', 'YouTube', 'WhatsApp']:
                        platform_district_data = district_data[district_data['Platform'] == platform]
                        if not platform_district_data.empty:
                            map_data.append({
                                'District': district,
                                'Platform': platform,
                                'Total_Interactions': platform_district_data['Total_Interactions'].sum(),
                                'Total_Views': platform_district_data['Total_Views'].sum(),
                                'lat': district_coords[district]['lat'],
                                'lon': district_coords[district]['lon']
                            })
            
            if map_data:
                map_df = pd.DataFrame(map_data)
                
                # Create bubble map
                platform_map = px.scatter_mapbox(
                    map_df,
                    lat="lat",
                    lon="lon",
                    size="Total_Interactions",
                    color="Platform",
                    hover_name="District",
                    hover_data={
                        "Total_Interactions": True,
                        "Total_Views": True,
                        "Platform": True,
                        "lat": False,
                        "lon": False
                    },
                    color_discrete_map=platform_colors,
                    size_max=30,
                    zoom=7,
                    height=400,
                    title="Platform Penetration Across Districts"
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
        # SHOW ENGAGEMENT CHART when single district selected
        engagement_chart = px.scatter(
            filtered_df,
            x="Total_Posts",
            y="Engagement_Rate",
            size="Total_Interactions",
            color="Platform",
            hover_name="District",
            title=f"Engagement Analysis - {selected_district}",
            size_max=30,
            color_discrete_sequence=['#7A288A', '#2F2F4D', '#FFC0CB', '#E6E6FA']
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

# Railway-compatible setup
if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8080)
