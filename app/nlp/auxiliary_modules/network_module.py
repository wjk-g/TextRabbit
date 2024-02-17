import numpy as np
import pandas as pd
import networkx as nx
from pyvis import network as net
import community as community_louvain
from flask import current_app

def prepare_network_data(df):

    df["new_id"] = df.reset_index().index # In the future I could use the real id here
    
    df_from_to = (df.explode("tokens")
    .merge(df, how="left", on="new_id")
    .rename(columns = { "tokens_x":"from", "tokens_y":"to" })
    .explode("to")
    .query("`from` != `to`")
    .value_counts(["from", "to"])
    .reset_index())

    # Now we need to remove mirror images like this:
    # humpty dumpty - dumpty humpty
    weights = df_from_to.iloc[:,2:3]
    pairs = df_from_to.iloc[:,:2]

    # Horizontal (row-wise) sorting of pairs and duplicates removal
    df_filtered = (pd.DataFrame(np.sort(pairs, axis=1), 
                                        columns = pairs.columns)
    .drop_duplicates()
    .merge(weights, left_index=True, right_index=True))
    
    df_filtered.columns = ["from", "to", "weight"]

    # Renaming cols according to networkx rules
    df_filtered["title"] = df_filtered["weight"]
    # Dividing the weight by 4: it just looks better when the lines are thinner ¯\_(ツ)_/¯ 
    df_filtered["weight"] = df_filtered["weight"] / 4
    
    return df_filtered

def visualize_network(df, network_size):

    df = df.head(network_size)
    G = nx.from_pandas_edgelist(df, source='from', target='to', edge_attr=["weight", "title"]) # this is our graph object
    word_net = net.Network(height='800px', width='100%', notebook=False, bgcolor='#222222', font_color='white')
    node_degree = dict(G.degree)
    nx.set_node_attributes(G, node_degree, 'size') # should be automatically detected
    communities = community_louvain.best_partition(G)
    nx.set_node_attributes(G, communities, 'group') # should be automatically detected
    word_net.from_nx(G)

    create_html_network(word_net)

def create_html_network(word_net):
        path = current_app.static_folder
        word_net.save_graph(f'{path}/pyvis_graph.html')
        HtmlFile = open(f'{path}/pyvis_graph.html','r',encoding='utf-8')
        
        return HtmlFile

def visualize_network_for_selected_words(df, selected_words):

    selected_words = selected_words.split()

    df = df[df["from"].isin(selected_words)]
    df = df.groupby("from").head(50)
    G = nx.from_pandas_edgelist(df, source='from', target='to', edge_attr=["weight", "title"]) # this is our graph object
    word_net = net.Network(height='800px', width='100%', notebook=False, bgcolor='#222222', font_color='white')
    node_degree = dict(G.degree)
    nx.set_node_attributes(G, node_degree, 'size') # should be automatically detected
    communities = community_louvain.best_partition(G)
    nx.set_node_attributes(G, communities, 'group') # should be automatically detected
    word_net.from_nx(G)

    create_html_network(word_net)