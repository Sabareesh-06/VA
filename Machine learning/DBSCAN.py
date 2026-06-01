import numpy as np

def get_dist(p1, p2):
    return np.sqrt(np.sum((p1 - p2)**2))

def run_dbscan(data, eps, min_pts):
    labels = np.full(len(data), -1)
    cluster_id = 0
    
    for i in range(len(data)):
        if labels[i] != -1: continue
        
        neighbors = []
        for j in range(len(data)):
            if get_dist(data[i], data[j]) <= eps:
                neighbors.append(j)
        
        if len(neighbors) < min_pts:
            labels[i] = -1 
        else:
            labels[i] = cluster_id
            for n_idx in neighbors:
                labels[n_idx] = cluster_id
            cluster_id += 1
            
    return labels

data = np.array([
    [10, 1], [12, 2], [11, 1], [13, 2], [15, 1],
    [500, 50], [450, 45]                        
])

data_min = data.min(axis=0)
data_max = data.max(axis=0)
data_scaled = (data - data_min) / (data_max - data_min)

results = run_dbscan(data_scaled, eps=0.1, min_pts=2)

print(f"Fraud Detection Labels: {results}")
print("Note: -1 represents detected anomalies (Fraud).")