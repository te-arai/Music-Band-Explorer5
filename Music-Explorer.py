import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events

# --- Load your dataset ---
elements = pd.read_excel("Data/ArtistsBands.xlsx", sheet_name="Elements")
connections = pd.read_excel("Data/ArtistsBands.xlsx", sheet_name="Connections")

# --- Build the undirected graph ---
G = nx.Graph()

# Add nodes
for _, row in elements.iterrows():
    label = str(row["Label"]).strip()
    node_type = row.get("Type", "Unknown")
    G.add_node(label, type=node_type, original_member="NO")

# Add edges
for _, row in connections.iterrows():
    from_node = str(row["From"]).strip()
    to_node = str(row["To"]).strip()
    is_original = str(row.get("Original Member", "NO")).strip().upper() == "YES"

    if from_node not in G.nodes:
        G.add_node(from_node, type="Unknown", original_member="NO")
    if to_node not in G.nodes:
        G.add_node(to_node, type="Unknown", original_member="NO")

    G.add_edge(from_node, to_node, original_member=is_original)

    if is_original:
        if G.nodes[from_node].get("type") == "Musician":
            G.nodes[from_node]["original_member"] = "YES"
        if G.nodes[to_node].get("type") == "Musician":
            G.nodes[to_node]["original_member"] = "YES"

# --- Streamlit UI ---
st.title("🎶 Musician ↔ Band Explorer")

# Sidebar controls
query = st.sidebar.text_input(
    "Enter a musician or band name:",
    value=st.session_state.get("query", "")
)
radius = st.sidebar.slider("Connection depth (hops)", 1, 3, 2)
filter_originals = st.sidebar.checkbox("Only Original Members", value=False)
theme_choice = st.sidebar.selectbox("Background Theme", ["White", "Black"])
node_size = st.sidebar.slider("Node size", 20, 60, 40)

# --- Theme palettes ---
if theme_choice == "White":
    bg_color = "white"
    font_color = "black"
    band_color = "#1f77b4"        # medium blue
    original_color = "#ff7f0e"    # orange/gold
    musician_color = "#2ca02c"    # green
    edge_normal = "#888888"       # medium gray
else:  # Black theme
    bg_color = "black"
    font_color = "white"
    band_color = "#6baed6"        # light blue
    original_color = "#ffd700"    # bright gold
    musician_color = "#98fb98"    # pale green
    edge_normal = "#aaaaaa"       # light gray

# --- Sidebar legend/key ---
st.sidebar.markdown("### 🔑 Color Key")
st.sidebar.markdown(
    f"<span style='color:{band_color}; font-weight:bold;'>■ Band</span>",
    unsafe_allow_html=True
)
st.sidebar.markdown(
    f"<span style='color:{musician_color}; font-weight:bold;'>■ Musician</span>",
    unsafe_allow_html=True
)
st.sidebar.markdown(
    f"<span style='color:{original_color}; font-weight:bold;'>■ Original Member</span>",
    unsafe_allow_html=True
)

# --- Function to build subgraph ---
def build_subgraph(root, radius, filter_originals):
    nodes_within_radius = [
        n for n, dist in nx.single_source_shortest_path_length(G, root).items()
        if dist <= radius
    ]
    if filter_originals:
        nodes_within_radius = [
            n for n in nodes_within_radius
            if G.nodes[n].get("original_member") == "YES" or G.nodes[n].get("type") == "Band"
        ]
    return G.subgraph(nodes_within_radius)

# --- Main logic ---
if query:
    lookup = {str(name).lower(): str(name) for name in G.nodes}
    if query.lower() in lookup:
        root = lookup[query.lower()]
        subgraph = build_subgraph(root, radius, filter_originals)

        pos = nx.spring_layout(subgraph, seed=42)

        # Build edge traces
        edge_x, edge_y = [], []
        for u, v, data in subgraph.edges(data=True):
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color=edge_normal),
            hoverinfo='none',
            mode='lines'
        )

        # Build node traces
        node_x, node_y, text, colors = [], [], [], []
        for node, data in subgraph.nodes(data=True):
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            text.append(node)
            if data.get("type") == "Band":
                colors.append(band_color)
            elif data.get("original_member") == "YES":
                colors.append(original_color)
            else:
                colors.append(musician_color)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=text,
            textposition="top center",
            hoverinfo='text',
            marker=dict(size=node_size, color=colors)
        )

        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20,l=5,r=5,t=40),
                            plot_bgcolor=bg_color,
                            paper_bgcolor=bg_color,
                            font=dict(color=font_color),
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            dragmode="pan"  # enable pan by default
                        ))

        # Show chart with zoom/pan enabled AND capture clicks
        selected_points = plotly_events(fig, click_event=True, hover_event=False)

        # Handle clicks safely
        if selected_points:
            point = selected_points[0]
            if "pointIndex" in point:
                idx = point["pointIndex"]
                if idx < len(text):
                    clicked_node = text[idx]
                    st.success(f"You clicked on: {clicked_node}")
                    if st.session_state.get("query") != clicked_node:
                        st.session_state["query"] = clicked_node
                        st.experimental_rerun()  # <-- immediate rerun here
            else:
                st.info("Click detected, but not on a node.")
    else:
        st.warning("Name not found in dataset.")
