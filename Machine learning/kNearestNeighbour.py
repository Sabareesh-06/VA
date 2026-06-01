import numpy as np

def get_dist(p1, p2):
    return np.sqrt(np.sum((p1 - p2)**2))

def run_knn(train_data, train_labels, new_point, k):
    all_results = []
    
    for i in range(len(train_data)):
        current_dist = get_dist(new_point, train_data[i])
        current_label = train_labels[i]
        
        all_results.append([current_dist, current_label])
    
    all_results.sort()
    
    top_k = all_results[:k]
    
    votes = [item[1] for item in top_k]
    
    if votes.count(1) > votes.count(0):
        return 1
    else:
        return 0

data = np.array([[20, 500], [80, 700], [90, 750], [25, 520], [85, 710]])
labels = np.array([0, 1, 1, 0, 1])

new_guy = np.array([82, 705])

final_decision = run_knn(data, labels, new_guy, k=3)

print(f"Numerical Decision for New Guy: {'Approve' if final_decision == 1 else 'Reject'}")