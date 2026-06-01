import numpy as np

def get_dist(p1, p2):
    return np.sqrt(np.sum((p1 - p2)**2))

def run_kmeans(data, k, steps=5):
    centers = data[np.random.choice(len(data), k, replace=False)]
    
    for _ in range(steps):
        clusters = []
        for point in data:
            distances = [get_dist(point, c) for c in centers]
            closest_center_idx = np.argmin(distances)
            clusters.append(closest_center_idx)
        
        clusters = np.array(clusters)
        
        new_centers = []
        for i in range(k):
            group_points = data[clusters == i]
            if len(group_points) > 0:
                new_centers.append(group_points.mean(axis=0))
            else:
                new_centers.append(centers[i]) 
                
        centers = np.array(new_centers)
        
    return clusters, centers

data = np.array([
    [15, 39], [16, 81], [85, 5], [90, 95], [20, 40], [80, 88]
])

labels, final_centers = run_kmeans(data, k=2)

print(f"Group IDs for each shopper: {labels}")
print(f"Numerical Centers of the 2 groups:\n{final_centers}")