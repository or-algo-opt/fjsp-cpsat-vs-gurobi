# -*- coding: utf-8 -*-
"""
Gurobi 求解器 ( FJSP + 维护 + 释放时间)。
警告：由于 FJSP 包含大量 0-1 选择与大 M 约束,MILP 求解极其耗时。
本代码用于展示 Gurobi 在复杂柔性调度下的建模方式及其性能边界。
"""
import gurobipy as gp
from gurobipy import GRB

def solve_fjsp_gurobi_full(data, time_limit_sec=60):
    jobs_data = data["jobs_data"]
    num_machines = data["machine_count"]
    release_times = data.get("release_times", {})
    maintenance = data.get("maintenance", {})

    m = gp.Model("FJSP_Full")
    m.Params.TimeLimit = time_limit_sec
    m.Params.LogToConsole = 0

    # 1. 整理所有工序信息
    ops = []
    for j, job in enumerate(jobs_data):
        for o, alts in enumerate(job):
            ops.append((j, o, alts)) # alts 是 [(m1, d1), (m2, d2)]
    num_ops = len(ops)
    
    # 计算所有工序在最坏机器上的加工总耗时（全串行极端情况）
    total_duration = sum(max(d for m, d in alts) for _, _, alts in ops)
    
    # 找出最晚的物料释放时间（如果传了空字典，默认 0）
    max_release = max(release_times.values()) if release_times else 0
    
    # 找出所有机器维护时间的总和（维护时间会强制插队，顺延总工期）
    total_maint_duration = sum(
        m_dur 
        for maint_list in maintenance.values() 
        for (m_start, m_dur) in maint_list
    )
    
    # 终极上界 = 串行总耗时 + 最晚释放时间 + 维护总耗时 + 安全缓冲
    max_time = total_duration + max_release + total_maint_duration + 100

    # 2. 创建变量
    start = m.addVars(num_ops, vtype=GRB.CONTINUOUS, name="start")
    end = m.addVars(num_ops, vtype=GRB.CONTINUOUS, name="end")
    makespan = m.addVar(vtype=GRB.CONTINUOUS, name="makespan")
    
    # 记录每道工序在各个机器上的分配变量 x[op_idx, mach]
    x = {}
    for idx, (j, o, alts) in enumerate(ops):
        for mach, dur in alts:
            x[idx, mach] = m.addVar(vtype=GRB.BINARY, name=f"x_{idx}_{mach}")

    # 3. 约束：每道工序必须且只能选一台机器
    for idx, (j, o, alts) in enumerate(ops):
        m.addConstr(gp.quicksum(x[idx, mach] for mach, _ in alts) == 1)

    # 4. 约束：工序的结束时间 = 开始时间 + 选中机器的耗时
    for idx, (j, o, alts) in enumerate(ops):
        # 耗时 = sum(x * dur)
        m.addConstr(end[idx] == start[idx] + gp.quicksum(x[idx, mach] * dur for mach, dur in alts))

    # 5. 约束：工件内部先后顺序 & 释放时间
    op_idx = 0
    for j, job in enumerate(jobs_data):
        for o in range(len(job)):
            if o == 0:
                m.addConstr(start[op_idx] >= release_times.get(j, 0))
            else:
                m.addConstr(start[op_idx] >= end[op_idx - 1])
            op_idx += 1
        m.addConstr(makespan >= end[op_idx - 1])

    # 6. 约束：机器不重叠 (含维护时间)
    # 获取每台机器上可能出现的所有工序
    machine_ops = {mach: [] for mach in range(num_machines)}
    for idx, (j, o, alts) in enumerate(ops):
        for mach, _ in alts:
            machine_ops[mach].append(idx)

    for mach in range(num_machines):
        ops_list = machine_ops[mach]
        
        # 6.1 处理维护时间冲突 (大 M 法)
        for m_start, m_dur in maintenance.get(mach, []):
            for idx in ops_list:
                # 如果这台工序分配给了这台机器，它要么在维护前做完，要么在维护后开始
                z = m.addVar(vtype=GRB.BINARY, name=f"z_maint_{idx}_{mach}")
                m.addConstr(end[idx] <= m_start + max_time * (1 - z) + max_time * (1 - x[idx, mach]))
                m.addConstr(start[idx] >= m_start + m_dur - max_time * z - max_time * (1 - x[idx, mach]))

        # 6.2 处理工序间的不重叠 (大 M 法)
        for i in range(len(ops_list)):
            for j in range(i + 1, len(ops_list)):
                op1, op2 = ops_list[i], ops_list[j]
                y = m.addVar(vtype=GRB.BINARY, name=f"y_{op1}_{op2}")
                
                # 如果 op1 在 op2 之前 (y=1)，且它们都在 mach 上运行
                m.addConstr(start[op2] >= end[op1] - max_time * (1 - y) - max_time * (2 - x[op1, mach] - x[op2, mach]))
                m.addConstr(start[op1] >= end[op2] - max_time * y - max_time * (2 - x[op1, mach] - x[op2, mach]))

    # 7. 目标函数
    m.setObjective(makespan, GRB.MINIMIZE)
    
    print(f"[Gurobi-FJSP] 开始求解满血版, 限制 {time_limit_sec}s...")
    m.optimize()

    # 8. 提取结果
    schedule = {}
    status_str = "UNKNOWN"
    if m.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL) and m.SolCount > 0:
        status_str = "OPTIMAL" if m.Status == GRB.OPTIMAL else "FEASIBLE"
        for idx, (j, o, alts) in enumerate(ops):
            # 找出选了哪台机器
            chosen_mach = -1
            for mach, _ in alts:
                if x[idx, mach].X > 0.5:
                    chosen_mach = mach
                    break
            schedule[(j, o)] = {
                "start": start[idx].X,
                "end": end[idx].X,
                "machine": chosen_mach
            }

    return {
        "obj": m.ObjVal if m.SolCount > 0 else float('inf'),
        "status": status_str,
        "schedule": schedule,
        "time": m.Runtime
    }