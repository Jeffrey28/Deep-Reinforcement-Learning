import numpy as np
import tensorflow as tf

'''Model that implements deep q learning'''
class DDQN:
    
    def __init__(self, scope,env,target_network, flags, exp_replay):
        
        self.state_size=len(env.observation_space.sample())
        self.action_size = env.action_space.n
        self.FLAGS=flags
        
        if scope=='target':
            
            with tf.variable_scope(scope):
                
                self.x=tf.placeholder(tf.float32, shape=(None,4), name='state')  
                self.q=self.build_target_network()
                self.param = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope=scope + '/target_network')

        elif scope=='q_network':
            
            with tf.variable_scope(scope):

                self.target_network=target_network
                
                self.exp_replay=exp_replay

                self.x=tf.placeholder(tf.float32, shape=(None,4))
                self.target=tf.placeholder(tf.float32, shape=(None,), name='target')
                self.action_indices=tf.placeholder(tf.int32, shape=(None,2), name='selected_actions')
                self.q=self.build_q_network()
                self.param = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope=scope + '/q_network')
                
                with tf.name_scope('q_network_loss'):
                    loss=tf.losses.mean_squared_error(self.target,tf.gather_nd(self.q, self.action_indices))
            
                with tf.name_scope('q_network_gradients'):
                    self.gradients=tf.gradients(loss, self.param)
            
                with tf.name_scope('train_q_network'):
                    self.train_opt=tf.train.AdamOptimizer(5e-4).apply_gradients(zip(self.gradients,self.param))
            
                with tf.name_scope('update_target_parameter'):     
                    self.update_opt=[tp.assign(lp) for tp, lp in zip(self.target_network.param,self.param)]
                
        else:
            raise ValueError('No network in scope %s'%scope)
                
        
    '''Build neural network for the target.'''
    def build_target_network(self):
        
        with tf.variable_scope('target_network'):
                 
            W1=tf.get_variable('W1', shape=(4,200), initializer=tf.random_normal_initializer())
            W2=tf.get_variable('W2', shape=(200,200), initializer=tf.random_normal_initializer())
            W3=tf.get_variable('W3', shape=(200,2), initializer=tf.random_normal_initializer())
            
            b1=tf.get_variable('b1', shape=(200), initializer=tf.zeros_initializer())
            b2=tf.get_variable('b2', shape=(200), initializer=tf.zeros_initializer())
            
 
            h1=tf.nn.tanh(tf.matmul(self.x, W1)+b1)
            h2=tf.nn.tanh(tf.matmul(h1, W2)+b2)
            q=tf.matmul(h2, W3)
            
        return q
    
    '''Build neural network for the Q-value.'''
    def build_q_network(self):
        
        with tf.variable_scope('q_network'):
            W1=tf.get_variable('W1', shape=(4,200), initializer=tf.random_normal_initializer())
            W2=tf.get_variable('W2', shape=(200,200), initializer=tf.random_normal_initializer())
            W3=tf.get_variable('W3', shape=(200,2), initializer=tf.random_normal_initializer())
            
            b1=tf.get_variable('b1', shape=(200), initializer=tf.zeros_initializer())
            b2=tf.get_variable('b2', shape=(200), initializer=tf.zeros_initializer())
            
 
            h1=tf.nn.tanh(tf.matmul(self.x, W1)+b1)
            h2=tf.nn.tanh(tf.matmul(h1, W2)+b2)
            q=tf.matmul(h2, W3)
              
        return q
    
    '''Train the Q-Network.'''
    def train_q_network(self):
        
        experience=self.exp_replay.get_experience()
        
        if len(experience['state']) < self.exp_replay.get_min_experience_count():
            return
        
        #pick random indices from the experience memory
        idx = np.random.choice(len(experience['state']), size=self.FLAGS.batch_size, replace=False)
        #pick the according collected experience according to the random indices
        state=np.array([experience['state'][i] for i in idx]).reshape(self.FLAGS.batch_size,self.state_size)
        action=[experience['action'][i] for i in idx]
        reward=[experience['reward'][i] for i in idx]
        next_state=np.array([experience['next_state'][i] for i in idx]).reshape(self.FLAGS.batch_size,self.state_size)
        dones=[experience['done'][i] for i in idx]

        ######Deep Double Q-Learning Implementation######
        
        #q-values according to target-network
        q_target=self.session.run(self.target_network.q, feed_dict={self.target_network.x:next_state})
        
        #q-values according to q-network
        q_network=self.session.run(self.q, feed_dict={self.x:next_state})
        
        #select actions according to highest q-values in q-network
        a=np.argmax(q_network, axis=1)
        
        #evaluate the q values with the target-network
        q_next=[np.take(q_target[i],a[i]) for i in range(0,self.FLAGS.batch_size)]

        #calculate the target
        targets=[r+self.FLAGS.gamma*q if not done else r for r, q, done in zip(reward,q_next,dones)]
        
        #get the indices of the taken actions in state s
        indices=[[i,action[i]] for i in range(0, len(action))]

        feed_dict={self.x:state, 
                   self.target:targets, 
                   self.action_indices:indices
                   }
        
        self.session.run(self.train_opt,feed_dict)
    
    '''Get the action by calculating the q value of an possible action by the Q-Network '''
    def get_action(self, X, eps):
        
        if np.random.random()<eps:
            return np.random.choice(self.action_size)
        else:
            return np.argmax(self.session.run(self.q, feed_dict={self.x:X}))
    
    '''Sets the session of the appropriate network. '''
    def set_session(self, session):
        self.session=session
    
    '''Set the parameter of the target network to the parameter of the Q-network '''                
    def update_target_parameter(self):
        self.session.run(self.update_opt)




