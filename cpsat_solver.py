# -*- coding: utf-8 -*-
"""
CP-SAT 求解器 (高级版)。
同时处理 FJSP (柔性机器选择)、工件释放时间和机器维护时间。
"""

from ortools.sat.python import cp_model

def solve_jssp_cpsat(data, time_limit_sec=60):
    model = cp_model.CpModel()
    jobs_data = data["jobs_data"]
    num_machines = data["machine_count"]
    release_times = data.get("release_times", {})
    maintenance = data.get("maintenance", {})

    all_tasks = {}
    machine_intervals = {m: [] for m in range(num_machines)}
    
    # 新增一个字典，用于记录所有选机器的布尔变量
    select_vars_dict = {}

    total_duration = sum(d for job in jobs_data for alts in job for (m, d) in alts)
    
    max_release = max(release_times.values()) if release_times else 0

    total_maint_duration = sum(
        m_dur 
        for maint_list in maintenance.values() 
        for (m_start, m_dur) in maint_list
    )

    max_time = total_duration + max_release + total_maint_duration + 100

    # 1. 添加机器维护区间 (把维护当成一个无法被选中的长工序)
    for mach, maint_list in maintenance.items():
        for idx, (m_start, m_dur) in enumerate(maint_list):
            maint_interval = model.NewIntervalVar(
                m_start, m_dur, m_start + m_dur, f"maint_{mach}_{idx}"
            )
            machine_intervals[mach].append(maint_interval)

    # 2. 遍历所有工件和工序
    for job_idx, job in enumerate(jobs_data):
        prev_end = None
        for op_idx, alternatives in enumerate(job):
            suffix = f"j{job_idx}_o{op_idx}"
            
            # 考虑释放时间
            start_lb = release_times.get(job_idx, 0) if op_idx == 0 else 0
            start = model.NewIntVar(start_lb, max_time, "start_" + suffix)
            end = model.NewIntVar(0, max_time, "end_" + suffix)
            
            # 记录当前工序选中的布尔变量
            select_vars = []
            
            # 遍历该工序的所有候选机器
            for mach, dur in alternatives:
                is_selected = model.NewBoolVar(f"sel_{suffix}_{mach}")
                select_vars.append(is_selected)
                
                # 将布尔变量存入字典，以便后续读取
                select_vars_dict[(job_idx, op_idx, mach)] = is_selected
                
                # 核心：可选区间变量 OptionalIntervalVar
                interval = model.NewOptionalIntervalVar(
                    start, dur, end, is_selected, f"interval_{suffix}_{mach}"
                )
                machine_intervals[mach].append(interval)

            # 约束：必须且只能选择一台机器
            model.AddExactlyOne(select_vars)

            all_tasks[(job_idx, op_idx)] = (start, end)
            
            # 约束：工序先后顺序
            if prev_end is not None:
                model.Add(start >= prev_end)
            prev_end = end

    # 3. 机器不重叠约束 (自动包含工件和维护)
    for m in machine_intervals:
        model.AddNoOverlap(machine_intervals[m])

    # 4. 目标函数：最小化 Makespan
    makespan = model.NewIntVar(0, max_time, "makespan")
    for j_idx, job in enumerate(jobs_data):
        last_op_idx = len(job) - 1
        _, e = all_tasks[(j_idx, last_op_idx)]
        model.Add(e <= makespan)
    model.Minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_sec
    solver.parameters.num_search_workers = 2
    
    print(f"[CP-SAT] 求解 FJSP+维护+释放, 限制 {time_limit_sec}s...")
    status = solver.Solve(model)
    
    schedule = {}
    status_str = "UNKNOWN"
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
        for (j, op), (s, e) in all_tasks.items():
            # 从我们刚才存的字典里，通过 solver.Value() 取出真实结果
            chosen_mach = -1
            for mach, _ in jobs_data[j][op]:
                if solver.Value(select_vars_dict[(j, op, mach)]):
                    chosen_mach = mach
                    break
                    
            schedule[(j, op)] = {
                "start": solver.Value(s),
                "end": solver.Value(e),
                "machine": chosen_mach
            }
            
    return {
        "obj": solver.ObjectiveValue() if schedule else float('inf'),
        "status": status_str,
        "schedule": schedule,
        "time": solver.WallTime()
    }