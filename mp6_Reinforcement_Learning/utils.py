import argparse
import collections
import random
import math

import gym
import numpy as np
import torch
from tqdm import tqdm

import policies
from dqn import DQNPolicy
from tabular import TabQPolicy

# Modified by Mohit Goyal (mohit@illinois.edu) on 04/20/2022

def hyperparameters():
    """
    These are the hyperparameters that you can change
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=int, default=700, help='number of episodes to simulate per iteration')
    parser.add_argument('--trainsize', type=int, default=1000, help='number of training steps to take per iteration')
    parser.add_argument('--epsilon', type=float, default=0.03, help='exploration parameter')
    #parser.add_argument('--epsilon_min', type=float, default=0.02, help='minimum exploration parameter')
    #parser.add_argument('--epsilon_decay_factor', type=float, default=2.0e-5, help='exploration decay parameter')
    parser.add_argument('--gamma', type=float, default=0.95, help='discount reward factor. represents how confident a '
                                                                  'model should be able to predict future rewards')
    parser.add_argument('--lr', type=float, default=1e-3, help='learning rate')

    args = parser.parse_args()
    return args


def rollout(env: gym.Env, policies: policies.QPolicy, episodes: int, epsilon: float, render: bool = False):
    """
    Simulates trajectories for the given number of episodes. Input policy is used to sample actions at each time step

    :param env: the gym environment
    :param policies: The policy used to sample actions (Tabular/DQN) 
    :param episodes: Number of episodes to be simulated
    :param epsilon: The exploration parameter for epsilon-greedy policy
    :param gamma: Discount factor
    :param render: If True, render the environment
    
    :return replay: Collection of (state, action, reward, next_state, done) at each timestep of all simulated episodes
    :return scores: Collection of total reward for each simulated episode  
    """
    replay = []
    scores = []
    for _ in range(episodes):
        state = env.reset()
        step = 0
        score = 0
        done = False
        while not done:
            if render:
                env.render()
            ### TODO: Your code starts here:
            pi = policies(state, epsilon)
            # How do you select the action given pi. Hint: use np.random.choice
            action = np.random.choice([action for action in range(env.action_space.n)],p=pi)
            ### Your code ends here.
            next_state, reward, done, _ = env.step(action)
            score += reward
            replay.append((state, action, reward, next_state, done))
            state = next_state
            step += 1
        env.close()
        scores.append(score)
    return replay, scores


def loadmodel(modelfile: str, env: gym.Env, statesize, actionsize):
    if '.model' in modelfile:
        # PyTorch
        pt_model = torch.load(modelfile)
        model = DQNPolicy(pt_model, statesize, actionsize, 0, None)
    elif '.npy' in modelfile:
        # Numpy
        pt_model = torch.load(modelfile)
        model = TabQPolicy(env, pt_model.shape[:-1], actionsize, 0, None, model=pt_model)
        pass
    else:
        raise Exception("Unknown model file extension")

    return model


def qlearn(env, policy, args):
    """
    Main training loop
    """
    replaymem = collections.deque(maxlen=500000)
    pbar = tqdm(range(args.episodes), desc='Iterations')
    all_scores = []
    for _ in pbar:
        # args.alpha = max(0.1, min(1, 1 - math.log10((_ + 1) / 50)))
        # args.epsilon = max(0.1, min(0.8, 1 - math.log10((_ + 1) / 50)))
        replay, scores = rollout(env, policy, 1, args.epsilon, render=False)
        all_scores.extend(scores)
        replaymem.extend(replay)
        traindata = random.sample(replaymem, min(args.trainsize, len(replaymem)))
        losses = []
        for state, action, reward, next_state, terminal in traindata:
            loss = policy.td_step(state, action, reward, next_state, terminal)
            losses.append(loss)

        smoothed_score = np.mean(all_scores[-200:])
        pbar.set_postfix_str("Smoothed Score: {:.1f} | Recent Score: {:.2f} | {:.3f} MSE | Replay Size: {}"
                             .format(smoothed_score, np.mean(all_scores[-20:]), np.mean(losses), len(replaymem)))
        if _ > 580:
            args.epsilon = min(0.01, 0.03*np.exp(-(3e-3)*(_-580)))
        #else:
            #args.epsilon = 0.03
        
