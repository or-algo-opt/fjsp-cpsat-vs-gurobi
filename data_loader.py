# -*- coding: utf-8 -*-
"""
数据生成器模块。
生成带有柔性(FJSP)、工件释放时间和机器维护时间的复杂调度算例。
"""

import random

def generate_advanced_jssp(num_jobs=6, num_machines=4, seed=42):
    """
    生成高级 JSSP/FJSP 算例。
    返回格式：
    jobs_data = [
        [ [(m1, d1), (m2, d2)],  # 工序0:可以在m1耗时d1,或在m2耗时d2
          [(m3, d3)] ],          # 工序1:只能在m3做
        ...
    ]
    """
    random.seed(seed)
    jobs_data = []
    
    for j in range(num_jobs):
        ops = []
        # 每个工件随机包含 5~7 道工序
        num_ops = random.randint(5, 7)
        for o in range(num_ops):
            # 柔性：每道工序可以选择 1~2 台机器
            candidates = []
            num_choices = random.choice([1, 2, 2]) # 大概率有选择
            chosen_machines = random.sample(range(num_machines), num_choices)
            for m in chosen_machines:
                dur = random.randint(5, 15)
                candidates.append((m, dur))
            ops.append(candidates)
        jobs_data.append(ops)
        
    # 工件释放时间（某些订单早上10点才到货）
    release_times = {j: random.choice([0, 0, 10, 20]) for j in range(num_jobs)}
    
    # 机器维护时间 {机器号: [(开始时间, 持续时长), ...]}
    maintenance = {
        0: [(30, 10)],  # 机器0 在时刻30维护10个时间单位
        1: [(50, 15)],  # 机器1 在时刻50维护15个时间单位
    }

    return {
        "jobs_data": jobs_data,
        "machine_count": num_machines,
        "job_count": num_jobs,
        "release_times": release_times,
        "maintenance": maintenance
    }