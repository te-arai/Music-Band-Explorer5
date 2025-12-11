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
st.title("🎶 Musician ↔ Band Explorer (Interactive)")

# Sidebar controls
query = st.sidebar.text_input("Enter a musician or band name:")
radius = st.sidebar.slider("Connection depth (hops)", 1, 3, 2)
filter_originals = st.sidebar.checkbox("Only Original Members", value=False)

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
            line=dict(width=1.5, color='#888'),
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
                colors.append("#1f77b4")  # blue
            elif data.get("original_member") == "YES":
                colors.append("#ff7f0e")  # gold
            else:
                colors.append("#2ca02c")  # green

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=text,
            textposition="top center",
            hoverinfo='text',
            marker=dict(size=15, color=colors)
        )

        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20,l=5,r=5,t=40)
                        ))

        # Capture clicks
        selected_points = plotly_events(fig, click_event=True, hover_event=False)
        if selected_points:
            clicked_node = text[selected_points[0]['pointIndex']]
            st.success(f"You clicked on: {clicked_node}")
            # Rerun query with clicked node as new root
            st.experimental_set_query_params(node=clicked_node)
            st.experimental_rerun()
    else:
        st.warning("Name not found in dataset.")
