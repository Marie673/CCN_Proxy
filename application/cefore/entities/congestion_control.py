import time

class CUBIC:
    def __init__(self):
        self.C = 0.4
        self.beta_cubic = 0.7
        self.W_last_max = 0
        self.K = 0
        self.cwnd = 1
        self.ssthresh = 64
        self.time_last_congestion = time.time()

    def update(self):
        t = time.time() - self.time_last_congestion
        W_cubic = self.C * (t-self.K)**3 + self.W_last_max
        if self.cwnd < self.ssthresh:
            self.cwnd += 1
        else:
            if W_cubic > self.cwnd:
                self.cwnd += (W_cubic - self.cwnd) / self.cwnd

    def handle_congestion_event(self):
        self.cwnd *= self.beta_cubic
        self.ssthresh = self.cwnd
        self.W_last_max = max(self.W_last_max, self.cwnd)
        self.K = (self.W_last_max - self.ssthresh) / (self.C * self.W_last_max)**(1/3)
