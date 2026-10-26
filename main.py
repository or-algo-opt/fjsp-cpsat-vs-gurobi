# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg') 

import sys
import os
from data_loader import generate_advanced_jssp
from cpsat_solver import solve_jssp_cpsat
try:
    from gurobi_solver import solve_fjsp_gurobi_full
except ImportError:
    solve_fjsp_gurobi_full = None
from visualizer import plot_gantt

# 定义双向输出类：同时输出到终端和文件
class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush() # 确保实时写入
    def flush(self):
        for f in self.files:
            f.flush()

def run_comparison(num_jobs, num_machines, time_limit=20):
    print("\n" + "="*60)
    print(f" 车间调度对比实验 (FJSP) | {num_jobs}工件 x {num_machines}机器")
    print("="*60)
    
    data = generate_advanced_jssp(num_jobs, num_machines, seed=42)
    
    # 1. CP-SAT 求解
    cpsat_res = solve_jssp_cpsat(data, time_limit_sec=time_limit)
    print(f"[CP-SAT] 状态: {cpsat_res['status']}, Makespan: {cpsat_res['obj']:.2f}, 耗时: {cpsat_res['time']:.2f}s")
    if cpsat_res['schedule']:
        plot_gantt(data, cpsat_res['schedule'], f"CP-SAT (Makespan={cpsat_res['obj']:.1f})", f"cpsat_{num_jobs}x{num_machines}.png")
        
    # 2. Gurobi 求解
    gurobi_res = {'obj': float('inf'), 'time': 0, 'status': 'FAILED'}
    if solve_fjsp_gurobi_full is not None:
        print("\n[Gurobi] 准备求解...")
        try:
            gurobi_res = solve_fjsp_gurobi_full(data, time_limit_sec=time_limit)
            print(f"[Gurobi] 状态: {gurobi_res['status']}, Makespan: {gurobi_res['obj']:.2f}, 耗时: {gurobi_res['time']:.2f}s")
            if gurobi_res['schedule']:
                plot_gantt(data, gurobi_res['schedule'], f"Gurobi (Makespan={gurobi_res['obj']:.1f})", f"gurobi_{num_jobs}x{num_machines}.png")
        except Exception as e:
            print(f"[Gurobi] 运行失败: {e}")

    # 3. 结果总结
    print("\n" + "-"*60)
    print(" 结果总结：")
    print(f"  CP-SAT     : Makespan = {cpsat_res['obj']:.2f} (耗时 {cpsat_res['time']:.2f}s)")
    
    if gurobi_res['status'] == 'FAILED':
        print(f"  Gurobi   : 运行失败（超出限制或报错）")
    else:
        print(f"  Gurobi   : Makespan = {gurobi_res['obj']:.2f} (耗时 {gurobi_res['time']:.2f}s)")
    print("-"*60)

if __name__ == "__main__":
    # 确保 output 文件夹存在
    os.makedirs("output", exist_ok=True)
    
    # 定义你要跑的测试组
    test_cases = [
        (10, 10, 30),  # 10工件 x 10机器，限制30秒
        (50, 20, 30)   # 50工件 x 20机器，限制30秒
    ]
    
    for num_jobs, num_machines, time_limit in test_cases:
        # 动态生成输出文件名，放入 output 文件夹
        log_filename = f"output/result_{num_jobs}x{num_machines}.txt"
        
        # 保存原始的控制台输出句柄
        original_stdout = sys.stdout
        
        # 打开文件用于写入
        with open(log_filename, "w", encoding="utf-8") as f:
            # 将系统标准输出重定向到 终端 + 文件
            sys.stdout = Tee(original_stdout, f)
            
            try:
                # 运行对比实验（此时所有 print 都会同时进入终端和 txt）
                run_comparison(num_jobs, num_machines, time_limit)
            finally:
                # 实验结束（或报错崩溃时），恢复标准输出，避免影响后续
                sys.stdout = original_stdout
                
        print(f" 日志已完整保存至: {log_filename}")