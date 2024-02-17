import pandas as pd
import numpy as np

from sklearn.cluster import MiniBatchKMeans #?
from sklearn.metrics import silhouette_samples, silhouette_score
from sklearn.decomposition import PCA

import gensim
from gensim.models import Word2Vec
from gensim.models import KeyedVectors

# ==========
# Load model
# ==========

def load_pretrained_word2vec_model():
    word2vec = gensim.models.KeyedVectors.load_word2vec_format("static/word2vec/nkjp_wiki_lemmas_all_300_cbow_hs.txt")
    return word2vec

# =============
# Vectorization
# =============

def vectorize_kv(list_of_docs, kv):
    """Generate vectors for list of documents using a Word Embedding

    Args:
        list_of_docs: List of documents
        kv: KeyedVectors object (a pretrained w2v model)

    Returns:
        List of document vectors
    """
    features = []

    for tokens in list_of_docs:
        zero_vector = np.zeros(kv.vector_size) # creates a vector of zeros equal to the w2v vector size
        vectors = []
        for token in tokens:
            if token in kv: # replace tokens with KeyedVector object
                try:
                    vectors.append(kv[token]) # return kv object (a vector) 
                except KeyError:
                    continue
        if vectors:
            vectors = np.asarray(vectors)
            avg_vec = vectors.mean(axis=0)
            features.append(avg_vec)
        else:
            features.append(zero_vector) # replace missing vectors with the zero vector
    return features



def perform_pca(vectorized_docs, n_of_pcs, labels, standardize):
    """Performs PCA on a vectorized object created with the vectorize_kv function

    Args:
        vectorized_docs: A document vectorized with the vectorize_kv function
        n_of_pcs: The number of primary components to produce
        labels: Labels to match rows

    Returns:
        ...
    """

    df_pca = vectorized_docs
    pca = PCA(n_components=n_of_pcs)

    fitted_pca = pca.fit_transform(df_pca) # numeric vectors of pc scores
    var_explained = pca.explained_variance_ratio_
    print(var_explained)
    df = pd.DataFrame(fitted_pca)

    if standardize == "tak":
        df = (df - df.mean()) / df.std()
        fitted_pca = df.values.tolist()

    df.insert(0, "text", pd.Series(labels)) # I am attaching labels (actual responses) to numeric vectors of pc scores
    
    # A slightly convoluted (?) way of creating colnames
    pcs = [f"pc{pc+1}" for pc in df.columns[1:]]
    colnames = ["text"]
    for pc in pcs:
        colnames.append(pc)
    df.columns = colnames
    
    return fitted_pca, df # fitted_pca and fitted_pca_with_labels

### 
def mbkmeans_clusters(
	X, 
    k
):
    """Generate clusters and print Silhouette metrics using MBKmeans

    Args:
        X: Matrix of features.
        k: Number of clusters.
        mb: Size of mini-batches.
        print_silhouette_values: Print silhouette values per cluster.

    Returns:
        Trained clustering model and labels based on X.
    """
    km = MiniBatchKMeans(n_clusters=k, batch_size=500).fit(X)
    print(f"For n_clusters = {k}")
    print(f"Silhouette coefficient: {silhouette_score(X, km.labels_):0.2f}") # sil score
    print(f"Inertia:{km.inertia_}")

    sample_silhouette_values = silhouette_samples(X, km.labels_)
    print(f"Silhouette values:")
    silhouette_values = []
    for i in range(k):
        cluster_silhouette_values = sample_silhouette_values[km.labels_ == i]
        silhouette_values.append(
            (
                i,
                cluster_silhouette_values.shape[0],
                cluster_silhouette_values.mean(),
                cluster_silhouette_values.min(),
                cluster_silhouette_values.max(),
            )
        )
    #silhouette_values = sorted(
    #    silhouette_values, key=lambda tup: tup[2], reverse=True
    #)
    
    cluster_information = pd.DataFrame(silhouette_values, columns=["index", "size", "mean_sil", "min_sil", "max_sil"])
    cluster_information = cluster_information.drop("index", axis=1).to_json()
    for s in silhouette_values:
        print(
            f"    Cluster {s[0]}: Size:{s[1]} | Avg:{s[2]:.2f} | Min:{s[3]:.2f} | Max: {s[4]:.2f}"
        )
    return km, km.labels_, silhouette_values, cluster_information

def display_most_representative_terms(model, clustering, n_of_ks, cluster_information):

    cluster_number = []
    list_of_terms = []

    for i in range(n_of_ks):
        tokens_per_cluster = ""
        most_representative = model.most_similar(positive=[clustering.cluster_centers_[i]], topn=10)
        for t in most_representative:
            tokens_per_cluster += f"{t[0]} "
        list_of_terms.append(tokens_per_cluster)
        cluster_number.append(i)

    df = pd.DataFrame({"cluster":cluster_number, "terms":list_of_terms})
    cluster_information = pd.read_json(cluster_information) 
    df_combined = pd.concat([df, cluster_information], axis=1)
    df_combined = df_combined.to_json()

    #df = df.to_html(classes="data", header="true", index=False)
    
    return df_combined