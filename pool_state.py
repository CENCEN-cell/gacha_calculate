"""
卡池状态类
"""


class PoolState:
    """单个卡池的状态"""
    def __init__(self):
        self.small_pity_counter = 0  # 小保底计数（跨池继承）
        self.large_pity_counter = 0  # 大保底计数（仅当期）
        self.total_pulls = 0  # 当期总抽数
        self.got_30_bonus = False  # 是否已获得30抽奖励
        self.bonus_10_special = 0  # 特殊10抽剩余
        self.bonus_10_normal = 0  # 正常10抽剩余（来自上期）
        self.welfare_limited = 0  # 策划限时福利抽（仅当期，过期作废）
        self.welfare_permanent = 0  # 策划不限时福利抽（可跨期积攒）
