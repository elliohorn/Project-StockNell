class CO:
    def __init__(self, name, cop_stars, scop_stars, co_power, super_power, power_gain_per_turn):
        self.name = name
        self.coMeter = 0            # current meter [0 to CO max]
        self.coStars = 0            
        self.copStars = cop_stars
        self.scopStars = scop_stars
        self.powerStage = 0         # 0=none, 1=CO Power, 2=Super Power
        self.coPower = co_power     # function(game) → applies CO Power
        self.superPower = super_power

    def gain_meter(self, gain):
        self.coMeter = self.coMeter + gain
        self.coStars = self.coMeter / 5000
        if self.coStars > self.copStars:
            print("COP Available")
            if self.copStars > self.scopStars:
                print("SCOP Available")
    
    def activate_co(self, game):
        if self.coStars > self.copStars:
            self.co_meter -= self.copStars * 5000
            self.coPower(game)
    
    def activate_super(self, game):
        if self.coStars > self.scopStars:
            self.co_meter = 0
            self.superPower(game)