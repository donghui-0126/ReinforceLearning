import gym
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
from replay_memory import ReplayMemory 
from collections import namedtuple, deque
import torch.nn.functional as F


seed_value = 42
np.random.seed(seed_value)
seed_value = 42
torch.manual_seed(seed_value)
seed_value = 42
random.seed(seed_value)


class DQN(nn.Module):
    def __init__(self, n_observations, n_actions):
        super(DQN, self).__init__()
        self.layer1 = nn.Linear(n_observations, 128)
        self.layer2 = nn.Linear(128, 128)
        self.layer3 = nn.Linear(128, n_actions)

    # 최적화 중에 다음 행동을 결정하기 위해서 하나의 요소 또는 배치를 이용해 호촐됩니다.
    # ([[left0exp,right0exp]...]) 를 반환합니다.
    def forward(self, x):
        x = F.relu(self.layer1(x))
        x = F.relu(self.layer2(x))
        return self.layer3(x)
    
class DQN_Agent(nn.Module):
    def __init__(self, num_states, num_actions):
        self.num_states = num_states
        self.num_actions = num_actions
        super(DQN_Agent, self).__init__()

        self.policy_net = DQN(num_states, num_actions)
        self.target_net = DQN(num_states, num_actions)
        self.target_net.load_state_dict(self.policy_net.state_dict())

        self.gamma = 0.99
        self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=1e-4, amsgrad=True)

        self.tau = 1.
        self.tau_decay = .99999
        self.tau_min = 0.01
        
        self.epsilon = 1.
        self.epsilon_decay = .99995
        self.epsilon_min = 0.01
            
        self.Transition = namedtuple('Transition',
                        ('state', 'action', 'next_state', 'reward', 'done'))

    
        self.train() # 훈련 모드 설정

    
    def act(self, state):
        # # 볼츠만 정책
        # q_values = self.forward(state)
        # q_values = nn.Softmax(dim=0)(q_values/self.tau )
        # action = torch.argmax(q_values).item()
        # return action
        
        # 입실론 그리디 정책
        if np.random.rand() < self.epsilon:
            action = np.random.choice(self.num_actions)
        else:
            q_values = self.policy_net(state)
            action = torch.argmax(q_values).item()
        return action
    
    def decrease_tau(self):
        if self.tau > self.tau_min:
            self.tau *= self.tau_decay
    
    def decrease_epsilon(self):
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def optimize(self, replay_memory, batch_size=128):
        if len(replay_memory) < replay_memory.max_capacity:
            return

        self.optimizer.zero_grad()

        batch = replay_memory.sample(batch_size)
        
        batch = self.Transition(*zip(*batch))
        

        
        non_final_mask = torch.tensor(tuple(map(lambda s: s is not None,
                                          batch.next_state)), dtype=torch.bool)
        non_final_next_states = torch.cat([s for s in batch.next_state
                                                if s is not None])

        state_batch = torch.cat(batch.state)
        action_batch = torch.cat(batch.action).unsqueeze(-1)
        reward_batch = torch.cat(batch.reward)
        

        
        q_values = self.policy_net(state_batch).gather(1, action_batch)
        
        next_state_values = torch.zeros(batch_size)
        
        with torch.no_grad():
            next_state_values[non_final_mask] = self.policy_net(non_final_next_states).max(1)[0]
            
        # 기대 Q 값 계산
        target_q_values = (next_state_values * self.gamma) + reward_batch
        
        criterion = nn.SmoothL1Loss()
        loss = criterion(q_values, target_q_values.unsqueeze(1))        
        
        
        loss.backward()                 # 역전파
        
        torch.nn.utils.clip_grad_value_(self.policy_net.parameters(), 100)
        self.optimizer.step()           # 경사 하강, 가중치를 업데이트     
        self.decrease_epsilon()
    
        return loss
    


def main(B=5, U=3, batch_size=32):
    TAU = 0.005

    env = gym.make('CartPole-v1')
    dqn_agent = DQN_Agent(4,2)    # SARSA를 위한 행동-가치 함수
    
    
    max_capacity = 10000

    # ('state', 'action', 'next_state', 'reward', 'done')
    replay = ReplayMemory(max_capacity)

    MAX_STEP = 10000

    # replay.recent_point
    for step in range(MAX_STEP):
        state = env.reset()[0]
        state = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
        done = False
        # 볼츠만 정책을 사용함.
        
        action = dqn_agent.act(state)
        total_reward = 0
        while not done:
            next_state, reward, done, truncated, _ = env.step(action)
            next_state, reward, done =  torch.tensor(next_state, dtype=torch.float32).unsqueeze(0),\
                                        torch.tensor(reward, dtype=torch.float32).unsqueeze(0),\
                                        torch.tensor(done, dtype=torch.bool).unsqueeze(0)
            
            replay.push(state, torch.tensor(action).unsqueeze(0), next_state, reward, done)

            
            state = next_state
            action = dqn_agent.act(torch.tensor(state, dtype=torch.float32))

            total_reward += 1
            
            loss = dqn_agent.optimize(replay, batch_size=128)
            

        
            
        if (step+1) % 50 == 0:
            if len(replay) == max_capacity:
                print("step: {}, epsilon: {:.3f}, rewards: {}, loss: {}".format(step+1, dqn_agent.epsilon, total_reward, loss))

            else: 
                print(f"step: {step+1}, memory size:{len(replay)}")
                
if __name__ == '__main__':
    main()
