import numpy as np


def getMean(list_values):
    return np.mean(list_values)

def getQuantile(list_values, q):
    return np.quantile(list_values, q)

def getSlope(list_values):
    print(list_values)
    if len(list_values) < 2:
        return 0
    x = np.arange(len(list_values))
    y = np.array(list_values)
    slope = np.polyfit(x, y, 1)[0]
    return slope

def getStd(list_values):
    return np.std(list_values)

def getEntropyTransition(list_values):
    if len(list_values) == 0:
        return 0
    
    
    numOfTransition = 0
    
    for val in list_values:
        numOfTransition += val[1]

    probabilities = {}
    for val in list_values:
        probabilities[val[0]] = val[1] / numOfTransition

    p = np.array(list(probabilities.values()), dtype=float)
    entropy = -np.sum(p * np.log2(p + 1e-10))

    return entropy

def entropyNormalize(raw_entropy, num_of_unique_transitions):
    if num_of_unique_transitions < 2:
        return 0
    
    return raw_entropy / np.log2(num_of_unique_transitions + 1e-10)

def getTransitionRepeatRate(list_values):
    if len(list_values) == 0:
        return 0
    
    numOfTransition = 0
    numOfUniqueTransition = len(list_values)
    transition_counts = {}

    for val in list_values:
        numOfTransition += val[1]

    repeat_rate = (numOfTransition - numOfUniqueTransition) / numOfTransition

    return repeat_rate