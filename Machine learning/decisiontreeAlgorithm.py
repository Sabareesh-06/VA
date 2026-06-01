import numpy as np

def get_messiness(labels):
    size = len(labels)
    if size == 0: return 0
    p0 = np.sum(labels == 0) / size
    p1 = np.sum(labels == 1) / size
    return 1 - (p0**2 + p1**2)

def find_best_cut(data, labels):
    best_messiness = 1.0
    best_cut_value = None
    best_feature_idx = None
    
    num_features = data.shape[1]

    for f_idx in range(num_features):

        possible_cuts = np.unique(data[:, f_idx])
        
        for cut in possible_cuts:
            left_mask = data[:, f_idx] <= cut
            right_mask = data[:, f_idx] > cut
            
            left_labels = labels[left_mask]
            right_labels = labels[right_mask]

            if len(left_labels) == 0 or len(right_labels) == 0:
                continue

            m_left = get_messiness(left_labels)
            m_right = get_messiness(right_labels)
            
            total_size = len(labels)
            current_messiness = (len(left_labels)/total_size) * m_left + \
                                (len(right_labels)/total_size) * m_right

            if current_messiness < best_messiness:
                best_messiness = current_messiness
                best_cut_value = cut
                best_feature_idx = f_idx
                
    return best_feature_idx, best_cut_value

data = np.array([
    [50, 700], [20, 550], [100, 800], [30, 600], [70, 750], [25, 580]
])
labels = np.array([1, 0, 1, 0, 1, 0])

feat, cut = find_best_cut(data, labels)

name = "Income" if feat == 0 else "Credit Score"
print(f"The best numerical rule is: If {name} <= {cut}, then Reject.")